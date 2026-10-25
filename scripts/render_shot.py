"""Render one shot from the command line, for testing a recipe change.

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/render_shot.py snorricam allie "Autumn forest track" \
        "expression is hard, fixed determination ..." [--seed N] [--native]
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import render, shots  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("shot")
ap.add_argument("character")
ap.add_argument("scene")
ap.add_argument("performance")
ap.add_argument("--seed", type=int)
ap.add_argument("--native", action="store_true")
ap.add_argument("--image", action="store_true", help="use the location's image instead of its description")
ap.add_argument("--slot", action="append", default=[], help="KEY=VALUE, for a move's extra slots")
args = ap.parse_args()

samples = json.loads((ROOT / "shotstudio/samples.json").read_text(encoding="utf-8"))
scene = dict(samples["scenes"][args.scene], PERFORMANCE=args.performance)
scene.update(kv.split("=", 1) for kv in args.slot)
char = samples["cast"][args.character]
# The performance goes in as the action text, worded to follow "As the shot plays out,".
perf = args.performance.strip()
if perf.startswith("expression"):
    action = f"<Subject 1>'s {perf}"
elif perf.split(" ", 1)[0] in ("her", "his", "their"):
    action = perf  # follows "As the shot plays out," so it stays lower case
else:
    action = f"<Subject 1> {perf}"
prompt = shots.build(args.shot, scene, [{"definition": "the person in {PLATE}", "pronoun": char["pronoun"]}],
                     action,
                     location_plate=args.image)
refs = [ROOT / f"shotstudio/static/refs/{args.character}.png"]
if args.image:
    refs.append(ROOT / "shotstudio/static" / scene["image"])
w, h = (1344, 768) if args.native else (864, 480)

job = render.Renderer(ROOT / "outputs").start(
    args.shot, prompt, refs,
    shots.RECIPES[args.shot]["length"], w, h, args.seed)
while job.status not in render.DONE:
    time.sleep(5)
print(json.dumps(job.public(), indent=1))
