"""Write shotstudio/presets.json: for each camera move, the approved take it starts from in the app.

A preset is that take's inputs, as the app's controls hold them (characters, location, the action
text with @mentions, extra fields, seed and size), plus the exact prompt it ran with. The app pre-loads
the inputs when the move is picked; if they are left unchanged, the exact prompt runs again and the
example clip comes back. Changed inputs build the prompt from the recipe as usual.

Inputs are read back out of each take's prompt and checked by rebuilding: the report says, per move,
whether today's recipe rebuilds the take's prompt word for word from them.

    python scripts/make_presets.py
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import shots  # noqa: E402

OUT = ROOT / "outputs"
SAMPLES = json.loads((ROOT / "shotstudio" / "samples.json").read_text(encoding="utf-8"))
SCENE_FIELDS = ("ENVIRONMENT", "PLACE", "ENVIRONMENT_PREP", "ENVIRONMENT_ELEMENTS", "SOUNDSCAPE", "MUSIC")
# The example each move's preview shows, where it is not the native batch's (the batch take is the
# reproducible one; the crash zoom in's preview came from a pod-only upscale route).
TAKES = {"cutaway-montage": OUT / "native" / "cutaway-montage_7_manual00050.workflow.json"}
# Inputs the prompt cannot give back, because the recipe was reworded after the take or the take's
# scene was written into the move itself (the POV). Read off each take's prompt by hand.
MANUAL = {
    # The vanish keeps its take's prompt, but its default cast is Sofia, set by hand in presets.json:
    # a long-sleeved character leaves the hands behind when the body goes (vanish_7_cfb72d166412).
    # The orbit's take hands over an object and has two spoken lines: the app writes those as an
    # @object and quoted speech, with each voice described where it is spoken.
    "orbit-360": {"objects": ["lantern"],
                  "text": "@Amber turns to @Kate and holds out the @Lantern. @Amber, with a soft, warm voice, says "
                          "\"This was my grandfather's.\" @Kate takes it and lifts it to her face, smiling. @Kate, "
                          "with a bright, surprised voice, says \"And it still works?\""},
    # A take's own phrases for its location, swapped like the location's words when it moves.
    "cutaway-montage": {"place_words": {"the desert highway": "LOCATION"}, "extras": {
        "INSERT_1": "snatch a set of car keys off a dusty bonnet with the right hand",
        "INSERT_2": "pull the seatbelt across and click it into place",
        "INSERT_3": "slide on a pair of dark sunglasses with both hands, sitting in the driver's seat",
        "INSERT_4": "shove the gear stick forward with the right hand, the left hand staying on the steering wheel",
        "WHERE_IT_ENDS": "in the driver's seat of the car, with the steering wheel, dashboard and windscreen all around, "
                         "the desert highway beyond and the dark sunglasses on"}},
    "pov": {"text": "The viewer takes a few slow steps toward @Mei, who stands just ahead with her back to the camera, bent "
                    "over the engine under the propped-up hood of an old dusty car at the roadside, tightening something "
                    "with a spanner. The viewer stops a couple of steps behind her and calls out her name, warm and "
                    "slightly surprised. @Mei turns around, recognises the viewer and breaks into a warm smile, then "
                    "steps closer and holds out her hand, and the viewer's hand reaches in from the bottom of the frame "
                    "to shake it."},
}


def proxy_refs() -> dict:
    db = sqlite3.connect(f"file:{OUT / 'proxy-state' / 'state.sqlite3'}?mode=ro", uri=True)
    jobs = {}
    for (text,) in db.execute("select workflow from jobs"):
        wf = json.loads(text)
        h3 = next((n["inputs"] for n in wf.values() if n.get("class_type") == "MiniMaxH3ReferenceToVideo"), None)
        seed = next((n["inputs"].get("noise_seed") for n in wf.values() if n.get("class_type") == "RandomNoise"), None)
        if h3:
            jobs[(h3["prompt"], seed)] = [wf[k]["inputs"]["image"] for k in sorted(wf)
                                          if wf[k].get("class_type") == "LoadImage"]
    return jobs


def take_workflow(slug: str, done: dict) -> Path | None:
    if slug in TAKES:
        return TAKES[slug]
    if slug not in done:
        return None
    return OUT / "native" / done[slug]["native"].replace(".mp4", ".workflow.json")


def location_of(prompt: str, images: list[str]) -> tuple[dict, str | None]:
    """The take's location: a bundled location image among its references, else the bundled scene
    whose description is in the prompt."""
    for name, sc in SAMPLES["scenes"].items():
        if "image" in sc and Path(sc["image"]).name in images:
            return {"image": name}, Path(sc["image"]).name
    for name, sc in SAMPLES["scenes"].items():
        if sc.get("ENVIRONMENT") and sc["ENVIRONMENT"] in prompt:
            return {"scene": name}, None
    return {}, None


def action_of(prompt: str, names: list[str]) -> str:
    """The action sentence the take was given, back in the app's @mention form."""
    body = prompt.split("detailed_description:", 1)[-1].split("\n\noverall_soundscape:", 1)[0]
    leads = ["As the shot plays out, "] + [g["lead"] + " " for g in shots.GROUP.values() if g.get("lead")]
    at = max((body.rfind(lead), lead) for lead in leads)
    if at[0] < 0:
        return ""
    text = body[at[0] + len(at[1]):].strip()
    return re.sub(r"<Subject (\d+)>", lambda m: "@" + names[int(m[1]) - 1] if int(m[1]) <= len(names) else m[0], text)


def extras_of(slug: str, prompt: str) -> dict:
    """Extra field values, read by matching the recipe's shot line against the prompt."""
    shot = shots.RECIPES[slug]
    slots = [s for s in shot.get("extra_slots", {}) if isinstance(shot.get("extra_slots"), dict)]
    if not slots:
        return {}
    found = {}
    # A field can sit in the framing or the shot line; each is matched on its own.
    for template in (shot.get("framing", ""), shot["shot_line"]):
        pattern, used = re.escape(template), []
        for s in slots:
            token = re.escape("{" + s + "}")
            if token in pattern:
                pattern = pattern.replace(token, f"(?P<{s}>.+?)", 1).replace(token, f"(?P={s})")
                used.append(s)
            pattern = pattern.replace(re.escape("{" + s + "_CAP}"), ".+?")
        pattern = re.sub(r"\\\{[A-Z_0-9]+\\\}", ".+?", pattern)
        m = re.search(pattern, prompt, re.S) if used else None
        if m:
            found.update({s: m.group(s) for s in used})
    return found


def main() -> None:
    done = json.loads((OUT / "native" / "done.json").read_text(encoding="utf-8"))
    jobs = proxy_refs()
    looks = {c["look"]: key for key, c in SAMPLES["cast"].items() if c.get("look")}
    presets, report = {}, []
    for entry in shots.catalog():
        slug = entry["slug"]
        wf_path = take_workflow(slug, done)
        if not wf_path or not wf_path.exists():
            report.append((slug, "no approved take"))
            continue
        wf = json.loads(wf_path.read_text(encoding="utf-8"))
        h3 = wf["6"]["inputs"]
        seed = wf["7"]["inputs"]["noise_seed"]
        prompt = h3["prompt"]
        images = jobs.get((prompt, seed)) or [wf[k]["inputs"]["image"] for k in sorted(wf)
                                               if wf[k]["class_type"] == "LoadImage" and wf[k]["inputs"].get("image")]
        location, plate = location_of(prompt, images)
        cast = [Path(i).stem for i in images if i != plate and Path(i).stem in SAMPLES["cast"]]
        names = [SAMPLES["cast"][c]["name"] for c in cast]
        action = MANUAL.get(slug, {}).get("text") or action_of(prompt, names)
        extras = {**extras_of(slug, prompt), **MANUAL.get(slug, {}).get("extras", {})}
        # The move's location fields come from the location (samples.json, which holds the takes' values),
        # not the preset; the rebuild check below says if they no longer match the take.
        own = SAMPLES["scenes"].get(list(location.values())[0], {}) if location else {}
        extras = {k: v for k, v in extras.items() if k not in shots.LOCATION_FIELDS}
        preset = {"cast": cast, "objects": MANUAL.get(slug, {}).get("objects", []), "location": location,
                  "text": action, "extras": extras, "seed": seed,
                  "width": h3["width"], "height": h3["height"], "length": h3["length"], "prompt": prompt,
                  "take": wf_path.name.replace(".workflow.json", ".mp4")}
        if MANUAL.get(slug, {}).get("place_words"):
            preset["place_words"] = MANUAL[slug]["place_words"]
        # Does today's recipe rebuild the take's prompt from these inputs?
        status = "exact"
        try:
            scene = dict(SAMPLES["scenes"][location["scene"]]) if "scene" in location else {}
            scene = {k: v for k, v in scene.items() if k in SCENE_FIELDS}
            scene.setdefault("SOUNDSCAPE", "The natural ambient sound of the location")
            scene.update(extras)
            scene.update({k: own.get(k) or v for k, v in shots.LOCATION_FIELDS.items()})
            chars = [{"pronoun": SAMPLES["cast"][c]["pronoun"], "look": SAMPLES["cast"][c].get("look", "")
                      if any(SAMPLES["cast"][c].get("look", "") in prompt for _ in [0]) else ""} for c in cast]
            labelled = re.sub(r"@(\w[\w-]*)", lambda m: f"<Subject {names.index(m[1]) + 1}>" if m[1] in names else m[0], action)
            rebuilt = shots.build(slug, scene, chars, labelled, location_plate="image" in location)
            if rebuilt != prompt:
                status = "differs"
        except Exception as exc:
            status = f"error: {exc}"[:80]
        preset["rebuilds"] = status
        presets[slug] = preset
        report.append((slug, f"{status:8} cast={','.join(cast) or '-'} loc={list(location.values())[0] if location else '-'} "
                             f"extras={len(extras)}/{len(entry['hints'])} action={'yes' if action else 'none'}"))
    (ROOT / "shotstudio" / "presets.json").write_text(json.dumps(presets, indent=1) + "\n", encoding="utf-8")
    for slug, line in report:
        print(f"{slug:20} {line}")


if __name__ == "__main__":
    main()
