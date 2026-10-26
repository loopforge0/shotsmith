"""Shotsmith: pick a named camera shot, cast it, set the location, render it.

    python -m shotstudio.server            # http://127.0.0.1:7860
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import describe, presets, shots, tasks
from .render import DONE, Renderer, generate_image, target

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = Path(os.environ.get("SHOTSTUDIO_DATA", ROOT.parent))
# The app's renders, and so its history, live in their own folder: outputs/ also holds the test and
# native batches made by the scripts, which are not anyone's history.
OUTPUTS = DATA / "outputs" / "app"
UPLOADS = DATA / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

# Canvas sizes are multiples of 32. 1344x768 is H3's native canvas.
SIZES = {
    "16:9": {"480p": (864, 480), "768p": (1344, 768)},
    "9:16": {"480p": (480, 864), "768p": (768, 1344)},
}
# H3 frame counts step by 17 from 124; its trained range is about 124-362.
DURATIONS = {"5s": 124, "8s": 192, "10s": 243}
IMAGE_EXT = ("png", "jpg", "jpeg", "webp")
AUDIO_EXT = ("wav", "mp3", "flac", "ogg", "m4a")

SAMPLES = json.loads((ROOT / "samples.json").read_text(encoding="utf-8"))
# A bundled scene chosen as a description brings its own words for these, as its approved takes used.
BUNDLED_SCENE_WORDS = ("ENVIRONMENT", "PLACE", "ENVIRONMENT_PREP", "ENVIRONMENT_ELEMENTS", "SOUNDSCAPE")
ELEMENTS = UPLOADS / "elements.json"
VOICES = UPLOADS / "voices.json"

app = FastAPI(title="Shotsmith")
renderer = Renderer(OUTPUTS)


@app.middleware("http")
async def revalidate(request, call_next):
    """The page and its scripts change while the app is developed; never serve them stale."""
    response = await call_next(request)
    if not request.url.path.startswith(("/outputs/", "/uploads/")):
        response.headers["Cache-Control"] = "no-cache"
    return response


def ref_path(ref: str) -> Path:
    """An input file: a bundled character or location, or an upload id."""
    if ref.startswith("sample:"):
        name = ref.split(":", 1)[1]
        if name not in SAMPLES["cast"]:
            raise HTTPException(404, f"no sample character '{name}'")
        return STATIC / "refs" / f"{name}.png"
    if ref.startswith("object:"):
        name = ref.split(":", 1)[1]
        if name not in SAMPLES.get("objects", {}):
            raise HTTPException(404, f"no sample object '{name}'")
        return STATIC / "objects" / f"{name}.png"
    if ref.startswith("location:"):
        name = ref.split(":", 1)[1]
        scene = SAMPLES["scenes"].get(name)
        if not scene or "image" not in scene:
            raise HTTPException(404, f"no location image for '{name}'")
        return STATIC / scene["image"]
    if not re.fullmatch(r"[0-9a-f]{16}\.(" + "|".join(IMAGE_EXT + AUDIO_EXT) + ")", ref):
        raise HTTPException(400, "bad file id")
    path = UPLOADS / ref
    if not path.exists():
        raise HTTPException(404, "file not found, upload it again")
    return path


# H3 reference limits (ComfyUI's MiniMax H3 docs): 9 images, 3 videos, 3 audio clips.
MAX_IMAGES = 9
MAX_AUDIO = 3
MENTION = re.compile(r"@([A-Za-z0-9_-]+)")
# Dialogue is written in the text in quotes: @Amber says "This was my grandfather's." A recording
# is placed the same way, by its @name: @Amber says @Toast.
QUOTE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”')
SPOKEN = re.compile(QUOTE.pattern + r"|@([A-Za-z0-9_-]+)")
SENTENCE = re.compile(r"[.!?](?=\s)|\n")
CLAUSE = re.compile(r"\b(?:and|then|while|as|before|after|but|so)\b|;", re.I)
PRONOUN = re.compile(r"\s*(?:she|he|they)\b", re.I)
# A speaker named after the line: "Hello," @Amber says.
AFTER = re.compile(r'\s*,?\s*@([A-Za-z0-9_-]+)[^"“.!?\n]*')


class Mention(BaseModel):
    name: str
    ref: str                  # an image; for a recording, its audio
    kind: str = "character"   # character, object or recording
    pronoun: str = "they"
    type: str = "person"      # a character is a person, an animal or a bird (shots.SUBJECT_TYPES)
    look: str = ""            # a character's hair and clothing, so several people's outfits don't mix
    words: str = ""           # a recording's words, exactly
    voice: str = ""           # how a character sounds, e.g. "a low, calm voice"
    voice_audio: str | None = None   # or a clip of the voice to follow; one or the other
    language: str = "English"        # what their lines (or the recording) are spoken in


class Location(BaseModel):
    ref: str | None = None   # an image; None means the location is the text in `scene`


class ShotRequest(BaseModel):
    shot: str
    text: str = ""           # what happens, with @mentions of characters and objects
    mentions: list[Mention] = []
    scene: dict[str, str] = {}
    location: Location = Location()
    ambience_audio: str | None = None   # a clip reused as the background sound, instead of SOUNDSCAPE
    music_audio: str | None = None      # a clip reused as the music, instead of MUSIC
    kind: str = "person"
    resolution: str = "480p"
    aspect: str = "16:9"
    duration: str = "5s"
    seed: int | None = None
    prompt_override: str | None = None  # the whole H3 prompt, edited by hand in the Prompt panel


class Plan(BaseModel):
    prompt: str
    images: list[str]
    audios: list[str]


def spoken_lines(text: str, chars: list[Mention], recordings: list[Mention]
                 ) -> tuple[str, list[tuple[Mention, str, Mention | None]]]:
    """Finds each line in the text, quoted or a recording's @name, and who says it, and swaps
    the line for a token.

    The speaker is the first character named in the part of the sentence leading into the quote
    ("... and @Kate asks"), else the first named anywhere in that sentence, else someone named
    right after a line ending in a comma ("Hello," @Amber says), else whoever the last sentence that names anyone
    starts with. A leading she/he/they is replaced by the speaker's @name."""
    names = {c.name.lower(): c for c in chars}
    recs = {r.name.lower(): r for r in recordings}

    def first(s: str) -> Mention | None:
        return next((names[m[1].lower()] for m in MENTION.finditer(s) if m[1].lower() in names), None)

    out, lines, pos = [], [], 0
    for q in SPOKEN.finditer(text):
        rec = recs.get((q[3] or "").lower())
        if q.start() < pos or (q[3] and not rec):
            continue  # consumed with the previous line's speaker, or a character or object
        words = rec.words.strip() if rec else (q[1] or q[2]).strip()
        # "Hello," @Amber says.
        attributed_after = text[q.end():].startswith(",") if rec else words.endswith(",")
        words = words if rec else words.rstrip(",")
        before = text[pos:q.start()]
        cuts = [m.end() for m in SENTENCE.finditer(before)]
        sentence = before[cuts[-1] if cuts else 0:]
        cuts = [m.end() for m in CLAUSE.finditer(sentence)]
        clause = sentence[cuts[-1] if cuts else 0:]
        speaker = first(clause) or first(sentence)
        tail, after = "", AFTER.match(text, q.end() + (1 if rec and attributed_after else 0))
        if not speaker and attributed_after and after and after[1].lower() in names:
            speaker, tail = names[after[1].lower()], after[0].strip(" ,")
        if not speaker:
            earlier = [s for s in SENTENCE.split(QUOTE.sub("", text[:q.start() - len(sentence)])) if first(s)]
            speaker = first(earlier[-1]) if earlier else chars[0] if len(chars) == 1 else None
        if not speaker:
            said = f"@{rec.name}" if rec else f'"{words}"'
            raise HTTPException(422, {"message": f"Who says {said}? Name them with @ in the same sentence."})
        if not first(clause) and not tail and PRONOUN.match(clause):
            p = PRONOUN.match(clause)
            start = len(before) - len(clause)
            before = before[:start] + " @" + speaker.name + before[start + p.end():]
        token = f"{shots._TOKEN}Q{len(lines)}{shots._TOKEN}"
        out += [before, f" {tail} {token}" if tail else token]
        lines.append((speaker, words, rec))
        pos = after.end() if tail else q.end()
    out.append(text[pos:])
    return "".join(out), lines


def plan(req: ShotRequest) -> Plan:
    """Number every input the way H3 sees it and build the prompt that refers to them.

    `mentions` is the cast, in order: characters first, then objects, then the location image
    follows. Pictures and subjects share that numbering. The text is optional; any @name in it
    must be in the cast."""
    known = {m.name.lower(): m for m in req.mentions}
    recordings = [m for m in req.mentions if m.kind == "recording"]
    for r in recordings:
        if not r.words.strip():
            raise HTTPException(422, {"message": f"Type the words that are in @{r.name}, under References."})
    for name in MENTION.findall(req.text):
        if name.lower() not in known:
            raise HTTPException(422, {"message": f"@{name} is not in this shot. Add it under References."})
    chars = [m for m in req.mentions if m.kind == "character"]
    objs = [m for m in req.mentions if m.kind == "object"]
    if not chars:
        raise HTTPException(422, {"message": "Add a character under References, or type @ to pick one."})
    subject = {m.name.lower(): i + 1 for i, m in enumerate(chars + objs)}
    images = [m.ref for m in chars + objs] + ([req.location.ref] if req.location.ref else [])
    if len(images) > MAX_IMAGES:
        raise HTTPException(422, {"message": f"H3 takes at most {MAX_IMAGES} reference images; this uses {len(images)}."})

    text, lines = spoken_lines(req.text, chars, recordings)
    action = MENTION.sub(lambda m: f"<Subject {subject[m.group(1).lower()]}>", text)
    action = re.sub(r"[ \t]{2,}", " ", action)
    # Voice samples (one per character) and recordings, numbered as <Audio N> in speaking order.
    audios: list[str] = []
    audio_of: dict[str, int] = {}
    dialogue = []
    for i, (who, words, rec) in enumerate(lines):
        entry = {"name": f"Q{i}", "subject": subject[who.name.lower()], "line": words,
                 "language": (rec or who).language, "voice": who.voice, "pronoun": who.pronoun}
        if rec:
            if rec.name not in audio_of:
                audios.append(rec.ref)
                audio_of[rec.name] = len(audios)
            entry["recording"] = audio_of[rec.name]
        elif who.voice_audio:
            if who.name not in audio_of:
                audios.append(who.voice_audio)
                audio_of[who.name] = len(audios)
            entry["audio"] = audio_of[who.name]
        dialogue.append(entry)
    sound = {}
    for layer, clip in (("ambience", req.ambience_audio), ("music", req.music_audio)):
        if clip:
            ref_path(clip)
            audios.append(clip)
            sound[layer] = len(audios)
    if len(audios) > MAX_AUDIO:
        raise HTTPException(422, {"message": f"H3 takes at most {MAX_AUDIO} audio clips; this uses {len(audios)}."})

    try:
        # Sound is optional: no ambience means the location's own sound, no music means none.
        scene = {k: v.strip() for k, v in req.scene.items() if v.strip()}
        # The location is one description, a bundled described scene (SCENE, its own wording), or an
        # image, which shots.build fills in itself.
        # A picture of a place with words goes with its words (the default); a picture of a place without
        # words, or the whip pan's take (tested with its picture alone), stands for the place by itself.
        take = presets.PRESETS.get(req.shot, {}).get("location", {})
        plate_place = presets.image_place(req.location.ref) if req.location.ref and \
            take.get("image") != (req.location.ref or "").removeprefix("location:") else None
        loc_ref = None if plate_place else req.location.ref
        if plate_place:
            scene["SCENE"] = plate_place
        bundled = scene.get("SCENE") if scene.get("SCENE") in presets.scenes() else None
        if not loc_ref:
            if bundled:  # the scene's own words, under anything the person typed (their ambience)
                scene = {**{k: v for k, v in presets.scenes()[bundled].items() if k in BUNDLED_SCENE_WORDS}, **scene}
            elif not scene.get("SETTING"):
                raise shots.PromptError("Describe the location, or choose an image of it.", ["SETTING"])
            else:
                scene.update(shots.describe_location(scene["SETTING"]))
        # The move's location fields follow the location: a bundled one, as a scene or its image, has its own.
        own = presets.scenes()[bundled] if bundled else presets.image_scene(loc_ref)
        the_place = re.sub(r"^(a|an)\s+", "the ", scene.get("ENVIRONMENT", ""), flags=re.I)  # "the whole harbour wall"
        described = {"LOCATION": the_place, "THE_SPACE": the_place} if not own and not loc_ref else {}
        scene.update({k: own.get(k) or described.get(k) or v for k, v in shots.LOCATION_FIELDS.items()})
        scene.setdefault("SOUNDSCAPE", "The natural ambient sound of the location")
        hints = shots.RECIPES.get(req.shot, {}).get("extra_slots") or {}
        prompt = req.prompt_override.strip() if req.prompt_override and req.prompt_override.strip() else presets.derive(
            req.shot, [{"ref": m.ref, "name": m.name, "pronoun": m.pronoun, "look": m.look} for m in chars],
            bundled, loc_ref, req.text,
            {k: scene[k] for k in hints if k in scene and k not in shots.LOCATION_FIELDS},
            simple=not audios and not any(req.scene.get(k, "").strip() for k in ("SOUNDSCAPE", "MUSIC")),
            objects=[{"ref": m.ref, "name": m.name} for m in objs])
        if prompt is None:
            prompt = shots.build(req.shot, scene, [{"pronoun": m.pronoun, "look": m.look, "type": m.type} for m in chars],
                                 action, objects=len(objs), location_plate=bool(loc_ref),
                                 dialogue=dialogue, sound=sound)
        if plate_place and not (req.prompt_override and req.prompt_override.strip()):
            prompt = presets.add_plate(prompt, len(chars) + len(objs) + 1, presets.scenes()[plate_place])
    except shots.PromptError as exc:
        names = {i + 1: m.name for i, m in enumerate(chars + objs)}
        message = re.sub(r"<Subject (\d+)>", lambda m: names.get(int(m[1]), m[0]), str(exc))
        raise HTTPException(422, {"message": message, "missing": exc.missing}) from None
    return Plan(prompt=prompt, images=images, audios=audios)


def load_elements() -> list[dict]:
    """Bundled characters and locations first, then what people uploaded."""
    out = [{"ref": f"sample:{key}", "img": f"refs/{key}.png", "kind": "character", "sample": True, **c}
           for key, c in SAMPLES["cast"].items()]
    out += [{"ref": f"object:{key}", "img": f"objects/{key}.png", "kind": "object", "sample": True, **o}
            for key, o in SAMPLES.get("objects", {}).items()]
    out += [{"ref": f"location:{name}", "img": sc["image"], "kind": "location", "sample": True,
             "name": name, "scene": {k: v for k, v in sc.items() if k != "image"}}
            for name, sc in SAMPLES["scenes"].items() if "image" in sc]
    if ELEMENTS.exists():
        out += json.loads(ELEMENTS.read_text(encoding="utf-8"))
    voices = json.loads(VOICES.read_text(encoding="utf-8")) if VOICES.exists() else {}
    for e in out:
        if e["kind"] == "character":
            e.update({"voice": "", "voice_audio": None, "language": "English", **voices.get(e["ref"], {})})
    return out


class Voice(BaseModel):
    ref: str                         # the character
    voice: str = ""                  # a description of how they sound...
    voice_audio: str | None = None   # ...or an uploaded clip of the voice, never both
    language: str = "English"


@app.post("/api/voices")
def save_voice(v: Voice) -> dict:
    """A character's voice, used whenever they speak."""
    if not any(e["ref"] == v.ref and e["kind"] == "character" for e in load_elements()):
        raise HTTPException(404, "No such character.")
    if v.voice_audio:
        ref_path(v.voice_audio)
        v.voice = ""
    voices = json.loads(VOICES.read_text(encoding="utf-8")) if VOICES.exists() else {}
    voices[v.ref] = v.model_dump(exclude={"ref"})
    VOICES.write_text(json.dumps(voices, indent=1), encoding="utf-8")
    return voices[v.ref]


class Element(BaseModel):
    ref: str
    name: str
    kind: str = "character"   # character, object, location or recording
    pronoun: str = "they"
    type: str = "person"      # person, animal or bird
    look: str = ""            # a character's hair and clothing
    words: str = ""           # a recording's words, exactly
    language: str = "English"  # a recording's language
    scene: dict[str, str] = {}  # a location's words (describe.py), as a bundled location has them


@app.get("/api/config")
def config() -> dict:
    return {"target": target(), "shots": shots.catalog(), "samples": SAMPLES, "presets": presets.public(),
            "sizes": SIZES, "durations": DURATIONS}


@app.get("/api/elements")
def elements() -> list[dict]:
    return load_elements()


@app.post("/api/elements")
def save_element(el: Element) -> dict:
    ref_path(el.ref)  # must be a real upload
    if el.type not in shots.SUBJECT_TYPES:
        raise HTTPException(422, f"A character is one of: {', '.join(shots.SUBJECT_TYPES)}.")
    if el.kind != "location" and not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", el.name):
        raise HTTPException(422, "Use one word for the name (letters, digits, - or _), so it works as an @mention.")
    if any(e["name"].lower() == el.name.lower() and e["ref"] != el.ref for e in load_elements()):
        raise HTTPException(422, f"Something is already called {el.name}.")
    saved = json.loads(ELEMENTS.read_text(encoding="utf-8")) if ELEMENTS.exists() else []
    saved = [e for e in saved if e["ref"] != el.ref]
    entry = {**el.model_dump(), "img": None if el.kind == "recording" else f"/uploads/{el.ref}", "sample": False}
    saved.append(entry)
    ELEMENTS.write_text(json.dumps(saved, indent=1), encoding="utf-8")
    return entry


class Ref(BaseModel):
    ref: str


@app.post("/api/elements/delete")
def delete_element(r: Ref) -> dict:
    """Take a character, prop, location or recording someone added out of the library. Bundled ones
    stay; renders that used it keep their copy of the prompt."""
    saved = json.loads(ELEMENTS.read_text(encoding="utf-8")) if ELEMENTS.exists() else []
    kept = [e for e in saved if e["ref"] != r.ref]
    if len(kept) == len(saved):
        raise HTTPException(404, "Only something you added can be deleted.")
    ELEMENTS.write_text(json.dumps(kept, indent=1), encoding="utf-8")
    return {"deleted": r.ref}


@app.post("/api/upload")
async def upload(file: UploadFile) -> dict:
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "file too large (25 MB max)")
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if ext not in IMAGE_EXT + AUDIO_EXT:
        raise HTTPException(400, "use an image (PNG, JPEG, WebP) or audio (WAV, MP3, FLAC, OGG, M4A)")
    name = f"{hashlib.sha256(data).hexdigest()[:16]}.{ext}"
    (UPLOADS / name).write_bytes(data)
    return {"ref": name, "url": f"/uploads/{name}"}


# Appended to every generated location, so it comes back as an empty place H3 can put people in.
LOCATION_STYLE = ("A wide cinematic photograph, eye level, natural perspective, no people, empty of any person "
                  "or figure, realistic film still with fine detail and soft depth.")
# A character's picture is a reference plate like the bundled ones: one person, from the knees up so
# the clothing shows (Fill in from the photo reads it from there), on a plain ground.
CHARACTER_STYLE = ("A realistic photograph of one person standing and facing the camera, framed from the knees up, "
                   "a relaxed neutral expression, their whole outfit clearly visible, a plain light grey studio "
                   "background, soft even light, sharp natural detail. Nobody else in the picture.")


class LocationRequest(BaseModel):
    description: str


def added_scenes() -> dict[str, dict]:
    """Locations people added and had described, by name, for presets.scenes()."""
    if not ELEMENTS.exists():
        return {}
    return {e["name"]: {**e["scene"], "ref": e["ref"], "image": e["img"]}
            for e in json.loads(ELEMENTS.read_text(encoding="utf-8"))
            if e.get("kind") == "location" and e.get("scene", {}).get("ENVIRONMENT")}


presets.extra_scenes = added_scenes


class DescribeRequest(BaseModel):
    ref: str
    kind: str   # character or location


@app.post("/api/describe")
def describe_image(req: DescribeRequest) -> dict:
    """Start filling a character's look, or a location's words, from its picture (optional,
    recommended). The page follows it on /api/describe/{id}: stage, progress and time left."""
    if req.kind not in describe.FIELDS:
        raise HTTPException(422, "Describe a character or a location.")
    return describe.start(ref_path(req.ref), req.kind).public()


@app.get("/api/describe/{job_id}")
def describe_progress(job_id: str) -> dict:
    job = describe.JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "no such description")
    return job.public()


@app.post("/api/locations/generate")
def generate_location(req: LocationRequest) -> dict:
    """Start making an image of a place from a description, with Qwen Image 2.1 turbo on the same
    ComfyUI. The page follows it on /api/locations/generate/{id}; the result is like an upload,
    which the panel then names, describes and saves as a location."""
    text = req.description.strip()
    if not text:
        raise HTTPException(422, "Describe the place first.")

    return make_image(f"{text.rstrip('.')}. {LOCATION_STYLE}", 1344, 768)


@app.post("/api/characters/generate")
def generate_character(req: LocationRequest) -> dict:
    """Start making a character's picture from a description, the same way as a place's: a portrait
    plate the panel then names, fills in from the photo and saves. Followed on its GET."""
    text = req.description.strip()
    if not text:
        raise HTTPException(422, "Describe the person first.")
    return make_image(f"{text.rstrip('.')}. {CHARACTER_STYLE}", 864, 1152)


@app.get("/api/characters/generate/{task_id}")
def character_progress(task_id: str) -> dict:
    return generate_progress(task_id)


def make_image(prompt: str, width: int, height: int) -> dict:
    """Qwen Image 2.1 turbo on the same ComfyUI, in the background; the result is like an upload."""
    def work(task: tasks.Task) -> dict:
        tmp = UPLOADS / f"gen-{task.id}.png"
        generate_image(prompt, tmp, width=width, height=height, on_progress=task.progress)
        data = tmp.read_bytes()
        name = f"{hashlib.sha256(data).hexdigest()[:16]}.png"
        tmp.replace(UPLOADS / name)
        return {"ref": name, "url": f"/uploads/{name}"}

    return tasks.start(work, "Making the image failed").public()


@app.get("/api/locations/generate/{task_id}")
def generate_progress(task_id: str) -> dict:
    task = tasks.TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "no such image")
    return task.public()


class SwapRequest(BaseModel):
    text: str
    old: list[Mention]   # the characters before the swap, in cast order
    new: list[Mention]   # and after
    kind: str = "text"   # "text": the @Name action; "prompt": a whole prompt edited by hand


@app.post("/api/swap")
def swap(req: SwapRequest) -> dict:
    """Swap characters in the action text or an edited prompt, the way a move's take is swapped: each
    changed character's name, look and pronouns, nothing else."""
    old = [{"name": m.name, "pronoun": m.pronoun, "look": m.look} for m in req.old]
    new = [{"name": m.name, "pronoun": m.pronoun, "look": m.look} for m in req.new]
    if len(old) != len(new):
        raise HTTPException(422, "the cast must keep its size")
    swapped = presets.swap_text if req.kind == "text" else presets.swap_cast
    return {"text": swapped(req.text, old, new)}


class RelocateRequest(BaseModel):
    prompt: str
    old: dict[str, str]   # {"scene": name} | {"setting": description} | {"image": ref}
    new: dict[str, str]
    old_plate: int = 0    # the location picture's number, when it is an image
    new_plate: int = 0
    shot: str = ""        # the move, whose take may name its location in its own words


@app.post("/api/relocate")
def relocate(req: RelocateRequest) -> dict:
    """Move a prompt to another location: the old location's own words swapped for the new one's,
    and, leaving the move's take location, the take's own phrases for it."""
    take = presets.PRESETS.get(req.shot, {})
    take_words = take.get("place_words") if take.get("location") == req.old else None
    return {"prompt": presets.relocate(req.prompt, presets.scene_words(req.old, req.old_plate),
                                       presets.scene_words(req.new, req.new_plate), take_words)}


class RefitRequest(BaseModel):
    prompt: str
    shot: ShotRequest
    sections: list[str]   # e.g. subject_definitions, retention_analysis, overall_soundscape


@app.post("/api/refit")
def refit(req: RefitRequest) -> dict:
    """Bring the named sections of an edited prompt in line with the shot's inputs (who and what is in
    it, the sound clips), from the prompt those inputs build; every other section keeps its words."""
    base = plan(req.shot.model_copy(update={"prompt_override": None})).prompt
    return {"prompt": presets.replace_sections(req.prompt, base, req.sections)}


@app.post("/api/prompt")
def prompt(req: ShotRequest) -> dict:
    return {"prompt": plan(req).prompt}


@app.post("/api/render")
def render(req: ShotRequest) -> dict:
    p = plan(req)
    shot = shots.RECIPES[req.shot]
    width, height = SIZES.get(req.aspect, SIZES["16:9"]).get(req.resolution, (864, 480))
    # A shot's own frame count is its minimum: three-phase moves need 192.
    length = max(shot["length"], DURATIONS.get(req.duration, 124))
    job = renderer.start(req.shot, p.prompt, [ref_path(r) for r in p.images], length, width,
                         height, req.seed, [ref_path(a) for a in p.audios],
                         inputs=req.model_dump(exclude={"prompt_override"}))
    return job.public()


@app.get("/api/jobs")
def jobs() -> list[dict]:
    return [j.public() for j in sorted(renderer.jobs.values(), key=lambda j: -j.started)]


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    job = renderer.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "no such job")

    async def stream():
        last = None
        while True:
            state = job.public()
            frame = json.dumps(state)
            if frame != last:
                yield f"data: {frame}\n\n"
                last = frame
            if state["status"] in DONE:
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/jobs/{job_id}/cancel")
def job_cancel(job_id: str) -> dict:
    if job_id not in renderer.jobs:
        raise HTTPException(404, "no such job")
    try:
        return renderer.cancel(job_id).public()
    except Exception as exc:
        raise HTTPException(502, f"ComfyUI would not cancel it: {exc}") from None


@app.post("/api/jobs/{job_id}/delete")
def job_delete(job_id: str) -> dict:
    if job_id not in renderer.jobs:
        raise HTTPException(404, "no such job")
    try:
        renderer.delete(job_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    return {"deleted": job_id}


@app.get("/api/jobs/{job_id}/prompt")
def job_prompt(job_id: str) -> dict:
    job = renderer.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "no such job")
    return {"prompt": job.prompt}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/outputs", StaticFiles(directory=OUTPUTS), name="outputs")
app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")
app.mount("/", StaticFiles(directory=STATIC), name="static")


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "7860"))
    print(f"Shotsmith on http://127.0.0.1:{port}  ->  rendering on {target()}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
