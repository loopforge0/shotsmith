"""Render moves with a cast of two or three characters, for testing group versions and multi-subject
shots. Each case is: move, characters (bundled cast keys, in order), location, action text using
<Subject N> labels, and any extra slots.

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/render_cast.py group|famous
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import render, shots  # noqa: E402

# The group versions are offered for two characters; these renders are what would allow three.
shots.GROUP_MAX = 3

SETS = {
    "group": [
        ("orbit-360", ["amber-main", "kate", "mei"], "Glass greenhouse",
         "<Subject 1> hands a small potted fern to <Subject 2>, and <Subject 3> leans in to look, all three of them smiling.", {}),
        ("aerial-pullback", ["claire", "lena", "sofia"], "Beach at sunset",
         "the three of them stand together on the sand and wave up at the sky.", {}),
        ("crane-rise", ["mei", "allie", "lena"], "Desert highway",
         "the three of them run side by side down the road, laughing, lips closed between breaths.", {}),
        ("handheld", ["sofia", "claire", "kate"], "Neon megacity",
         "the three of them run side by side through the street, glancing back over their shoulders.", {}),
        ("dutch-angle", ["lena", "amber-main", "allie"], "Castle dungeon",
         "<Subject 1> lifts a hand toward the dark staircase while <Subject 2> and <Subject 3> peer past her shoulders, uneasy.", {}),
        ("rack-focus", ["kate", "mei", "claire"], "Old library",
         "<Subject 1> looks up from her book with a faint smile.", {}),
    ],
    "famous": [
        ("double-dolly", ["lena"], "Subway platform", "<Subject 1> stares ahead with a calm, unreadable expression that slowly hardens.", {}),
        ("trunk-shot", ["claire"], "Desert highway", "<Subject 1> looks down into the boot with a slow, knowing smile.", {}),
        ("barrel-roll", ["mei"], "Space station", "<Subject 1> stays calm, her eyes wide with wonder.", {}),
        ("one-point-push", ["kate"], "Throne room", "<Subject 1> stares into the lens without blinking.",
         {"THE_SPACE": "the long red carpet between the columns"}),
        ("hero-spin", ["amber-main"], "Surface of Mars", "<Subject 1>'s face moves from strain to fierce resolve as she rises.", {}),
        ("pov", ["sofia"], "Tokyo alley", "", {}),
        ("walk-and-talk", ["allie"], "Wild West town", "<Subject 1> talks as she walks, animated and smiling.", {}),
        ("split-diopter", ["kate", "lena"], "Glowing forest",
         "<Subject 1> looks toward the lens, lost in thought, while <Subject 2> watches her from far behind.", {}),
    ],
    # The documented moves with no demo yet (zoom out, slow pan, tilt down, strong shake, cuts), the
    # POV retry and the time-lapse crowd.
    "documented": [
        ("slow-zoom-out", ["mei"], "Mountain lake", "", {}),
        ("slow-pan-reveal", ["sofia"], "Arctic shore", "", {}),
        ("tilt-down-reveal", ["claire"], "Ice cave", "", {}),
        ("impact-shake", ["allie"], "Jungle temple ruins", "", {}),
        ("time-lapse", ["kate"], "Rain-soaked city street", "", {}),
        ("shot-reverse-shot", ["amber-main", "lena"], "Fifties diner", "", {}),
        ("pov", ["sofia"], "Tokyo alley", "", {}),
    ],
    # POV take 3: walk up behind the character, tap, turn, handshake.
    "pov": [
        ("pov", ["sofia"], "Tokyo alley", "", {"TASK": "reading the paper menu pinned beside an izakaya door"}),
        ("pov", ["mei"], "Desert highway", "", {"TASK": "trying to unlock the door of an old dusty car parked at the roadside"}),
    ],
    # Montage take 2 on the stage: every insert names its object and where on it the hands work.
    "cutaway2": [
        ("cutaway-montage", ["lena"], "Concert stage", "",
         {"INSERT_1": "snap shut the black plastic buckle on the guitar strap, up at the shoulder, with both hands",
          "INSERT_2": "push the metal plug at the end of a black cable into the round socket on the lower edge of the guitar's wooden body, with the right hand",
          "INSERT_3": "flick the power switch on the front panel of the amplifier with one finger, and a small red light glows beside it",
          "INSERT_4": "turn one of the tuning pegs on the headstock at the far end of the guitar's neck, between the left thumb and finger"}),
        ("cutaway-montage", ["claire"], "Desert highway", "",
         {"INSERT_1": "snatch a set of car keys off a dusty bonnet with the right hand",
          "INSERT_2": "pull the seatbelt across and click its metal tongue into the buckle at the hip with the right hand",
          "INSERT_3": "slide on a pair of dark sunglasses with both hands",
          "INSERT_4": "shove the gear stick forward with the right hand, the left hand staying on the steering wheel"}),
    ],
    "pov4": [
        ("pov", ["sofia"], "Tokyo alley", "", {"TASK": "reading the paper menu pinned beside an izakaya door"}),
        ("pov", ["mei"], "Desert highway", "",
         {"TASK": "bent over the engine under the propped-up hood of an old dusty car at the roadside, tightening something with a spanner"}),
    ],
    "pov5": [
        ("pov", ["sofia"], "Tokyo alley", "",
         {"TASK": "studying the paper menu pinned beside an izakaya door, running one finger down it line by line"}),
        ("pov-call", ["mei"], "Desert highway", "",
         {"TASK": "bent over the engine under the propped-up hood of an old dusty car at the roadside, tightening something with a spanner",
          "NAME": "Mei"}),
    ],
    # POV take 6: the recipe is only the first-person camera; the scene is the user's action.
    "pov6": [
        ("pov", ["mei"], "Desert highway",
         "The viewer walks a few slow steps up behind <Subject 1>, who is bent over the engine under the propped-up "
         "hood of an old dusty car at the roadside, tightening something with a spanner. The viewer stops a couple of "
         "steps behind her and calls out, warm, slightly surprised and questioning, \"Mei?\" <Subject 1> hears her "
         "name, turns around, recognises the viewer and breaks into a warm smile, then steps closer and holds out her "
         "hand, and the viewer's hand reaches in to shake it.", {}),
    ],
    # The quick cut-away prep montage: a stage version and an everyday one.
    "cutaway": [
        ("cutaway-montage", ["lena"], "Concert stage", "",
         {"INSERT_1": "snap a guitar strap buckle shut", "INSERT_2": "jam a cable jack into the guitar with a click",
          "INSERT_3": "flick the amplifier switch on and its red light glows", "INSERT_4": "twist a tuning peg tight"}),
        ("cutaway-montage", ["claire"], "Desert highway", "",
         {"INSERT_1": "snatch a set of car keys off a dusty bonnet", "INSERT_2": "click a seatbelt buckle shut",
          "INSERT_3": "slide on a pair of dark sunglasses", "INSERT_4": "shove the gear stick forward"}),
    ],
}

samples = json.loads((ROOT / "shotstudio" / "samples.json").read_text(encoding="utf-8"))
r = render.Renderer(ROOT / "outputs")
# Optional: only these moves, e.g. render_cast.py group crane-rise handheld
cases = [c for c in SETS[sys.argv[1]] if not sys.argv[2:] or c[0] in sys.argv[2:]]
for slug, cast, scene_name, action, extra in cases:
    scene = {**samples["scenes"][scene_name], **extra}
    chars = [{"pronoun": samples["cast"][c]["pronoun"], "look": samples["cast"][c].get("look", "")} for c in cast]
    prompt = shots.build(slug, scene, chars, action)
    refs = [ROOT / f"shotstudio/static/refs/{c}.png" for c in cast]
    job = r.start(slug, prompt, refs, shots.RECIPES[slug]["length"], 864, 480, seed=7)
    print(f"== {slug}: {', '.join(cast)}, {scene_name}", flush=True)
    while job.status not in ("succeeded", "failed"):
        time.sleep(5)
    print(f"  -> {job.status} {job.video or job.error} in {job.public()['elapsed']}s", flush=True)
