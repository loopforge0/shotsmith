"""The camera shot library, wrapped for the app.

Everything shot-specific lives in the vendored minimaxh3-shots-skills library
(`vendor/h3shots`): the recipes, the prompt scaffold and `build_prompt.py`. This
module only adapts it - it never rewrites a prompt rule of its own.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
from pathlib import Path

VENDOR = Path(__file__).resolve().parent / "vendor" / "h3shots"

_spec = importlib.util.spec_from_file_location("build_prompt", VENDOR / "scripts" / "build_prompt.py")
bp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bp)

SCAFFOLD = bp.fenced_block(bp.SCAFFOLD_MD, "text")
RECIPES = bp.load_shots()
# Moves added by this app, in the library's shot-file format. Each stays "testing", and hidden,
# until a render of it has been watched and held up.
MOVES = Path(__file__).resolve().parent / "moves"
_library_dir, bp.SHOTS_DIR = bp.SHOTS_DIR, MOVES
RECIPES.update(bp.load_shots())
bp.SHOTS_DIR = _library_dir
# The library's split-screen field examples say "her". People overwrite them, but an example steers
# what they type, so these say "the person", as an unset pronoun does in the prompt.
RECIPES["split-screen"]["extra_slots"].update({
    "ACTION": "the one continuous action, with its setting, e.g. \"seated at a cluttered desk typing on a keyboard, "
              "a bright monitor in front of the person\"",
    "PANEL_1_ANGLE": "e.g. \"the person from the left side in profile, typing\"",
    "PANEL_2_ANGLE": "e.g. \"the front, framed over the back of the monitor with the screen glow on the person's face\"",
    "PANEL_3_ANGLE": "e.g. \"the person from behind in full, with the bright monitor in view\"",
})
GALLERY = {g["slug"]: g for g in json.loads((VENDOR / "gallery.json").read_text(encoding="utf-8"))}
GROUP = {k: v for k, v in json.loads((Path(__file__).resolve().parent / "group_moves.json")
                                      .read_text(encoding="utf-8")).items() if not k.startswith("_")}
STATIC = Path(__file__).resolve().parent / "static"
MAX_CHARACTERS = 3
# The group versions hold with three characters too: three-person takes were picked for the dutch angle,
# aerial pullback and handheld (2026-10-25).
GROUP_MAX = 3


def cast_range(slug: str) -> tuple[int, int]:
    """How many characters a move takes. Moves built for 2 or 3 take exactly that many; moves
    with a tested group version take 1 to 3; every other move locks onto one person."""
    needs = RECIPES[slug].get("subjects", 1)
    if needs > 1:
        return needs, needs
    if GROUP.get(slug, {}).get("tested"):
        return 1, GROUP_MAX
    return 1, 1

# Slots the cast panel fills, so the scene form must not ask for them again.
CAST_SLOTS = {"SUBJECT_DEFINITION", "PRONOUN", "PRONOUN_SUBJ", "POSSESSIVE"} | {
    f"SUBJECT_{n}_DEFINITION" for n in range(2, 5)
}
DERIVED = {"SHOT_LINE", "FRAMING", "FRAMING_LOWER", "SUBJECT_ACTION", "SUMMARY_ACTION",
           "SHOT_NAME", "POSSESSIVE_CAP", "PRONOUN_SUBJ_CAP"}

# One per row of build_prompt's KINDS vocabularies, as the cast panel offers them.
PRONOUNS = {
    "she": {"PRONOUN": "her", "PRONOUN_SUBJ": "she", "POSSESSIVE": "her"},
    "he": {"PRONOUN": "him", "PRONOUN_SUBJ": "he", "POSSESSIVE": "his"},
}


def pronouns(pronoun: str, n: int = 1, alone: bool = True) -> dict:
    """She and he as chosen. Anything else gets no pronoun at all: "they" can read as several
    people, and H3 then adds extras. The character is named instead, "the person" when they are
    the only one in the shot, or their own <Subject N> label when others are in it."""
    if pronoun in PRONOUNS:
        return PRONOUNS[pronoun]
    who = "the person" if alone else f"<Subject {n}>"
    return {"PRONOUN": who, "PRONOUN_SUBJ": who, "POSSESSIVE": f"{who}'s"}


class PromptError(ValueError):
    """The scene cannot fill this shot. `missing` names the slots still empty."""

    def __init__(self, message: str, missing: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing = missing or []


def scene_slots(shot: dict, kind: str = "person") -> list[str]:
    """The scene slots this shot needs from the user, in a stable order."""
    vocab = {k: v for k, v in bp.KINDS[kind].items() if v is not None}
    action = shot.get("subject_action") or bp.MOTION.get(shot.get("motion"), ("", ""))[0]
    needed = bp.slots_in(SCAFFOLD, shot["shot_line"], shot["framing"], action, *vocab.values())
    needed -= DERIVED | set(bp.DEFAULTS) | set(vocab) | CAST_SLOTS
    # X_CAP is X with a capital, made by build(): the user fills in X.
    needed = {s.removesuffix("_CAP") if s.removesuffix("_CAP") in shot.get("extra_slots", {}) else s for s in needed}
    # Slots a vocabulary leaves empty (an object has no eye for DETAIL) come back as required.
    needed |= {k for k, v in bp.KINDS[kind].items() if v is None and k in needed}
    order = bp.REQUIRED_FROM_SCENE + ["MUSIC"]
    return sorted(needed, key=lambda s: (order.index(s) if s in order else len(order), s))


# Recipes the library itself does not stand behind: an unreliable subject lock, and a direction
# with no render behind it. A shot is either in the app, which means it works, or it is not.
# "removed" is a move taken out of the app; its recipe and test log stay, to bring back later.
NOT_OFFERED = {"verified-unreliable", "rendered-weak-evidence", "testing", "failed", "removed"}

# A character can be a person, an animal or a bird: the shot library's wording for each (pronoun,
# what the identity lock holds, how they idle). These moves are written around a human body, with
# clothes that burn, hands that throw lightning, a smile, so they need a person in the lead.
SUBJECT_TYPES = ("person", "animal", "bird")
PEOPLE_ONLY = {"architecture-wave", "battle-knight", "cutaway-montage", "disintegration", "giant",
               "incline", "levitation", "melting", "rooftop-swing", "set-on-fire", "thunder-god", "time-lapse", "vanish"}


def catalog() -> list[dict]:
    """Every shot the app offers, in gallery order, with what the UI needs to show it."""
    out = []
    order = list(GALLERY) + [s for s in RECIPES if s not in GALLERY]
    for slug in order:
        shot = RECIPES.get(slug)
        if not shot or shot["status"] in NOT_OFFERED:
            continue
        gallery = GALLERY.get(slug, {})
        out.append({
            "slug": slug,
            "name": shot.get("label", shot["name"]),
            "length": shot["length"],
            "subjects": shot.get("subjects", 1),
            "cast": cast_range(slug),
            "group": gallery.get("group") or shot.get("group", "other"),
            "still": f"stills/{gallery.get('id') or shot['id']}.jpg",
            "preview": (f"previews/{gallery.get('id') or shot['id']}.mp4"
                        if (STATIC / "previews" / f"{gallery.get('id') or shot['id']}.mp4").exists() else None),
            "slots": scene_slots(shot),
            "note": shot.get("app_note", ""),
            "hints": shot.get("extra_slots", {}) if isinstance(shot.get("extra_slots"), dict) else {},
            "people_only": slug in PEOPLE_ONLY,
        })
    return out


def _insert_after_section(prompt: str, section: str, lines: list[str]) -> str:
    """Append lines to the end of one `name:` section of the prompt."""
    if not lines:
        return prompt
    head, sep, rest = prompt.partition(f"{section}:\n")
    body, gap, tail = rest.partition("\n\n")
    return head + sep + body + "\n" + "\n".join(lines) + gap + tail


# A location is either an image or words, never both. These stand in for the location slots when
# it is an image, so the prompt points at the picture instead of describing it a second time.
IMAGE_LOCATION = {
    "ENVIRONMENT": "the location shown in {PLATE}",
    "PLACE": "in the location shown in {PLATE}",
    "ENVIRONMENT_PREP": "in",
    "ENVIRONMENT_ELEMENTS": "the surroundings shown in {PLATE}",
}

# A move's own location fields: what recedes behind a dolly zoom, the corridor a super dolly charges
# down. They come from the location, never typed: a bundled location has its own (samples.json), any
# other location these.
LOCATION_FIELDS = {
    "LOCATION": "the surrounding place",
    "BACKGROUND": "the things in the background",
    "PLACE_2": "standing further away in the same place",
    "THE_SPACE": "the space ahead",
    "NEAR_OBJECTS": "two things close to the lens",
    "FURTHER_OBJECTS": "what lies further on",
    "GROUND": "the ground",
    "LOOSE_THINGS": "the loose things lying around",
}

_PREPOSITIONS = ("in", "on", "at", "inside", "under", "beside", "by", "near", "atop", "among", "beneath")


def describe_location(text: str) -> dict[str, str]:
    """The recipes' three location slots from one description, the way IMAGE_LOCATION fills them
    from a picture. "on a snowy pier at dawn" and "a snowy pier at dawn" both work."""
    text = text.strip().rstrip(".")
    first, _, rest = text.partition(" ")
    prep, place = (first.lower(), rest) if first.lower() in _PREPOSITIONS and rest else ("in", text)
    return {"ENVIRONMENT": place, "ENVIRONMENT_PREP": prep, "PLACE": f"{prep} {place}",
            "ENVIRONMENT_ELEMENTS": "the rest of the setting"}

# The app does not offer lighting, palette or camera gear. The scaffold's opening sentence names
# all three, so they are filled with markers and the clause is cut back out afterwards.
_UNSET = {"GEAR": "\x00G", "LIGHTING": "\x00L", "PALETTE": "\x00P"}
_PERF = "\x00PERF"
# Marks where a dialogue line's @token sat in the action text.
_TOKEN = "\x01"
# Where a sentence starts, for finding who a line's sentence names: a full stop, a spoken line, a new line.
_BREAK = re.compile(r"[.!?]\s|</d>|\n")
# Wording that makes a line a voiceover: "@Amber says off screen", "@Amber, in a voice-over, ..."
_VOICEOVER = re.compile(r"voice-?\s?over|off[- ]screen", re.I)




def _with_looks(prompt: str, characters: list[dict]) -> str:
    """Name each character's look (hair, clothing) in their definition and retention line. With several
    reference photos and only "the person in <Picture N>" to go on, H3 lets clothing bleed between
    people (a group render put one character's top on another). MiniMax's guide defines every subject
    with "the main features to follow"."""
    for i, c in enumerate(characters):
        look = (c.get("look") or "").strip().rstrip(".")
        if not look:
            continue
        n = i + 1
        prompt = re.sub(rf"^(<Subject {n}> is the person in <Picture {n}>)\.", lambda m: f"{m.group(1)}, with {look}.",
                        prompt, count=1, flags=re.M)
        prompt = re.sub(rf"^(<Subject {n}> \(appears in [^\n]*?(?:face, identity and clothing|face, hair and clothing))(?! \()",
                        lambda m: f"{m.group(1)} ({look})", prompt, count=1, flags=re.M)
    return prompt


def _end(text: str) -> str:
    text = text.strip()
    return text if not text or text[-1] in ".?!\"'" + _TOKEN else text + "."


def _identity_lines(n: int, pronoun: str, subject_type: str = "person") -> tuple[str, str]:
    """Definition and retention lines for a character beyond the ones the shot recipe binds."""
    if subject_type == "person":
        poss = pronouns(pronoun, n, alone=False)["POSSESSIVE"]
    else:
        poss = bp.KINDS[subject_type]["POSSESSIVE"]
    kept = bp.KINDS[subject_type]["RETAINED"]
    label, plate = f"<Subject {n}>", f"<Picture {n}>"
    return (f"{label} is the {subject_type} in {plate}.",
            f"{label} (appears in [Shot 1]): fully_preserved - {poss} {kept} are "
            f"held identical to {plate} in every frame with zero drift.")


def build(slug: str, scene: dict, characters: list[dict], action: str, objects: int = 0,
          location_plate: bool = False, dialogue: list[dict] | None = None,
          kind: str = "person", sound: dict[str, int] | None = None) -> str:
    """Build the full Ref2VA prompt.

    Subjects and pictures are numbered in wiring order: characters (in the order they are first
    mentioned), then objects, then the location image. `action` is the user's text with every
    @mention already replaced by its <Subject N> label. `dialogue` is a list of
    {"name", "subject", "line", "language", "voice", "audio"} in speaking order: the line's token
    name sits in `action` where it is spoken, and `audio` is the <Audio N> number of the
    speaker's voice sample, if any. A speaker's voice is only used on their first line.
    `sound` maps "ambience" and "music" to the <Audio N> clip reused as that layer."""
    shot = RECIPES.get(slug)
    if not shot:
        raise PromptError(f"no shot '{slug}'")
    # The lead character's type picks the library's wording for them (it, markings and coat...).
    if characters:
        kind = characters[0].get("type") or kind
    if kind != "person" and slug in PEOPLE_ONLY:
        raise PromptError(f"{shot.get('label', shot['name'])} is written for a person, not {('an ' if kind[0] in 'aeiou' else 'a ') + kind}. "
                          "Make a person the first character, or choose another move.")
    needs = shot.get("subjects", 1)
    lo, hi = cast_range(slug)
    n_chars = len(characters)
    if not lo <= n_chars <= hi:
        want = f"{lo}" if lo == hi else f"{lo} to {hi}"
        raise PromptError(f"{shot['name']} takes {want} character{'s' if hi > 1 else ''}; this has {n_chars}.")
    group = n_chars > 1 and needs == 1
    override = None
    if group:
        g = GROUP[slug]
        labels = [f"<Subject {i + 1}>" for i in range(n_chars)]
        fill = {"{GROUP}": ", ".join(labels[:-1]) + " and " + labels[-1],
                "{N_SHOT}": "two-shot" if n_chars == 2 else "three-shot",
                "{N_PEOPLE}": "the two of them" if n_chars == 2 else "the three of them"}
        def sub(text: str) -> str:
            for key, value in fill.items():
                text = text.replace(key, value)
            return text

        override = {**shot, "shot_intro": "custom", "shot_line": sub(g["line"]),
                    "summary_action": g["summary_action"], "framing_summary": sub(g["framing_summary"])}
    loc_n = n_chars + objects + 1

    scene = {**scene, **_UNSET, "PERFORMANCE": _PERF}
    # A background clip is reused as its own layer, in the section MiniMax's guide puts it in.
    sound = sound or {}
    if "ambience" in sound:
        scene["SOUNDSCAPE"] = f"The copied ambience layer from <Audio {sound['ambience']}> continues throughout the target video"
    if "music" in sound:
        scene["MUSIC"] = f"<Audio {sound['music']}> is directly reused as the complete audience-only score"
    if location_plate:
        plate = f"<Picture {loc_n}>"
        scene.update({k: v.replace("{PLATE}", plate) for k, v in IMAGE_LOCATION.items()})
    cast = [{"definition": f"the {c.get('type') or 'person'} in {{PLATE}}", "pronoun": c.get("pronoun", "they"),
             "type": c.get("type") or "person", "alone": n_chars == 1} for c in characters[:needs]]
    # An effect (set on fire, vanish...) owns its whole [Shot 1] line, its summary, what it keeps of
    # the character, and its sound, which plays over the location's ambience.
    effect = shot.get("kind") == "effect"
    if effect:
        override = {**shot, "shot_intro": "custom"}
        for slot in shot.get("extra_slots", {}):
            if scene.get(slot):
                scene[f"{slot}_CAP"] = scene[slot][:1].upper() + scene[slot][1:]
        if "ambience" not in sound:
            scene["SOUNDSCAPE"] = shot["sound"].replace("{SOUNDSCAPE}", scene.get("SOUNDSCAPE", "").rstrip(". "))
        if "music" not in sound and scene.get("MUSIC", "N/A").strip() in ("", "N/A"):
            scene["MUSIC"] = shot["music"]
    prompt = _build(slug, scene, cast, kind, override)
    if effect:
        pron = pronouns(characters[0].get("pronoun", "they"), 1, alone=n_chars == 1)
        vals = {**{k: v for k, v in bp.KINDS[kind].items() if v}, **pron,
                **{k: v for k, v in scene.items() if isinstance(v, str)},
                "SUBJECT": "<Subject 1>", "PLATE": "<Picture 1>",
                "POSSESSIVE_CAP": pron["POSSESSIVE"][:1].upper() + pron["POSSESSIVE"][1:],
                "PRONOUN_SUBJ_CAP": pron["PRONOUN_SUBJ"][:1].upper() + pron["PRONOUN_SUBJ"][1:]}
        summary = bp.resolve(f"The target video shows {{SUBJECT}} {{ENVIRONMENT_PREP}} {{ENVIRONMENT}}, {shot['summary']}.", vals)
        prompt = re.sub(r"^\[reference generation\] .*$", lambda m: f"[reference generation] {summary}", prompt, count=1, flags=re.M)
        kept = bp.resolve(shot["retention"], vals)
        if not kept.startswith("partially_preserved"):
            kept = f"fully_preserved - {kept}"
        prompt = re.sub(r"^<Subject 1> \(appears in \[Shot 1\]\): .*$", lambda m: f"<Subject 1> (appears in [Shot 1]): {kept}",
                        prompt, count=1, flags=re.M)
    # A definition says what each label is; what is preserved is retention_analysis's job, so the
    # recipe's identity lock after "<Subject N> is the person in <Picture N>." is dropped.
    prompt = re.sub(r"^(<Subject \d+> is [^\n]*?<Picture \d+>\.) [^\n]+$", r"\1", prompt, flags=re.M)
    if group:
        prompt = prompt.replace("shows <Subject 1> ", f"shows {fill['{GROUP}']} ", 1)

    prompt = prompt.replace(f", shot on {_UNSET['GEAR']}, {_UNSET['LIGHTING']}, {_UNSET['PALETTE']}.", ".")
    perf = f"As the shot plays out, <Subject 1>'s {_PERF}."
    lead = GROUP[slug]["lead"] if group else "As the shot plays out,"
    prompt = prompt.replace(perf, f"{lead} {_end(action)}" if action.strip() else "")
    prompt = prompt.replace(" \n", "\n")

    defs, kept = [], []
    for i in range(needs, n_chars):
        d, r = _identity_lines(i + 1, characters[i].get("pronoun", "they"), characters[i].get("type") or "person")
        defs.append(d)
        kept.append(r)
    for j in range(objects):
        n = n_chars + j + 1
        defs.append(f"<Subject {n}> is the object in <Picture {n}>.")
        kept.append(f"<Subject {n}> (appears in [Shot 1]): fully_preserved - its shape, materials and "
                    f"markings are held to <Picture {n}>.")
    if location_plate:
        label, plate = f"<Subject {loc_n}>", f"<Picture {loc_n}>"
        defs.append(f"{label} is the environment in {plate}.")
        kept.append(f"{label} (appears in [Shot 1]): fully_preserved - the environment's layout, "
                    f"materials and look are held to {plate} throughout.")

    if "ambience" in sound:
        a = f"<Audio {sound['ambience']}>"
        defs.append(f"{a} is the background ambience recording.")
        kept.append(f"{a}: partially_copy - its ambience layer is reused as the background sound, "
                    f"with the action and any dialogue added over it.")
    if "music" in sound:
        a = f"<Audio {sound['music']}>"
        defs.append(f"{a} is the background music track.")
        kept.append(f"{a}: partially_copy - its music is reused as the audience-only score, "
                    f"with the scene's own sound added around it.")

    # Dialogue, following MiniMax's speaker rules: stable (Sx) IDs in the order people first speak;
    # the speaker's voice outside <d>, on their first line only; only the language tag and the
    # user's words, verbatim, inside <d>. Each line's token sits in the action where it is spoken.
    # A recording is reused as the line itself, in its own voice and delivery.
    tasks = ["audio reuse"] if sound else []
    speakers: dict[int, str] = {}
    voiced: set[int] = set()
    for line in dialogue or []:
        k = line["subject"]
        sid = speakers.setdefault(k, f"S{len(speakers) + 1}")
        who = f"<Subject {k}> ({sid})"
        voice = ""
        first = k not in voiced
        if line.get("recording"):
            audio = f"<Audio {line['recording']}>"
            defs.append(f"{audio} is the recorded dialogue of {who}, reused in the target video.")
            kept.append(f"{audio}: partially_copy - its spoken vocal layer is reused as the dialogue of "
                        f"<Subject {k}>, with the scene's ambience and music added around it.")
            tasks.append("audio reuse")
            voice = f", in the exact voice and delivery of {audio},"
            first = False
        elif first:
            voiced.add(k)
        if first and line.get("audio"):
            audio = f"<Audio {line['audio']}>"
            defs.append(f"{audio} is the voice-timbre reference for {who}.")
            kept.append(f"{audio}: reference - its vocal timbre guides the dialogue delivery of "
                        f"<Subject {k}> without copying the original signal.")
            tasks.append("audio reference")
            voice = f", in the voice timbre referenced from {audio},"
        elif first and line.get("voice", "").strip():
            voice = f", with {line['voice'].strip()},"
        speech = f"<d>[{line.get('language') or 'English'}] {line['line'].strip()}</d>"
        token = f"{_TOKEN}{line['name']}{_TOKEN}"
        at = prompt.find(token)
        end = at + len(token)
        # The user's wording leads into the line: "<Subject 1> mutters" or "<Subject 1> turns to
        # <Subject 2> and asks". It is kept as written, with the speaker ID and voice right after
        # the speaker's name, as MiniMax's format has it.
        breaks = [m.end() for m in _BREAK.finditer(prompt, 0, at)]
        begin = breaks[-1] if breaks else 0
        name = f"<Subject {k}>"
        anchor = prompt.rfind(name, begin, at)
        lead_in = prompt[anchor + len(name):at].rstrip(" ,:") if anchor >= 0 else ""
        if voice and lead_in.startswith(","):
            lead_in = lead_in[1:]  # "(S1), with a soft voice, eyes wet, tells"
        if _VOICEOVER.search(lead_in):
            poss = pronouns(line.get("pronoun", "they"), k, alone=False)["POSSESSIVE"]
            speech += f" while {poss} lips remain completely closed"
            if line["line"].strip()[-1:] in ".!?" or prompt[end:end + 1] in ("", "\n"):
                speech += "."
        if anchor < 0:
            prompt = prompt[:at] + f"{who}{voice} says: {speech}" + prompt[end:]
        elif not lead_in:
            prompt = prompt[:anchor] + f"{who}{voice} says: {speech}" + prompt[end:]
        else:
            after = anchor + len(name)
            prompt = prompt[:after] + f" ({sid}){voice}{lead_in}: {speech}" + prompt[end:]

    prompt = _insert_after_section(prompt, "subject_definitions", defs)
    prompt = _insert_after_section(prompt, "retention_analysis", kept)
    prompt = _with_looks(prompt, characters)
    prompt = re.sub(r"performs a (?=[aeiouAEIOU])", "performs an ", prompt)
    # A shot with cuts in it (shot / reverse shot, a cut-away montage): everyone appears across them.
    last = max(int(n) for n in re.findall(r"\[Shot (\d+)\]", prompt) or ["1"])
    if last > 1:
        span = "[Shot 1] and [Shot 2]" if last == 2 else f"[Shot 1] to [Shot {last}]"
        prompt = prompt.replace("(appears in [Shot 1])", f"(appears in {span})")
    if tasks:
        tag = " + ".join(["reference generation", *dict.fromkeys(tasks)])
        prompt = prompt.replace("[reference generation]", f"[{tag}]", 1)
    return prompt


def _build(slug: str, scene: dict, cast: list[dict], kind: str = "person",
           override: dict | None = None) -> str:
    shot = override or RECIPES.get(slug)
    if not shot:
        raise PromptError(f"no shot '{slug}'")
    needs = shot.get("subjects", 1)
    if len(cast) < needs:
        raise PromptError(f"{shot['name']} needs {needs} characters, got {len(cast)}")

    values = {k: v for k, v in scene.items() if isinstance(v, str) and v.strip()}
    values["SUBJECT_KIND"] = kind
    for i, member in enumerate(cast[:needs]):
        n = i + 1
        definition = member["definition"].replace("{PLATE}", f"<Picture {n}>").strip()
        key = "SUBJECT_DEFINITION" if n == 1 else f"SUBJECT_{n}_DEFINITION"
        values[key] = definition
        pron = pronouns(member.get("pronoun", "they"), n, alone=member.get("alone", True) and n == 1)
        if n == 1:
            if kind == "person":
                values.update(pron)
        elif member.get("type", "person") != "person":
            values[f"POSSESSIVE_{n}"] = bp.KINDS[member["type"]]["POSSESSIVE"]
        else:
            values[f"POSSESSIVE_{n}"] = pron["POSSESSIVE"]

    missing = [s for s in scene_slots(shot, kind) if s not in values]
    if missing:
        raise PromptError("fill in: " + ", ".join(missing), missing)

    # build_prompt reports errors on stderr and exits; turn that into an exception.
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            return bp.build(shot, values, SCAFFOLD)
    except SystemExit as exc:
        text = err.getvalue().strip() or str(exc.code)
        raise PromptError(text) from None
