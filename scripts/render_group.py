"""Render a move's group version (2-3 characters) to decide whether to offer it.

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/render_group.py orbit-360 amber-main kate \
        --object lantern --scene "Arctic shore" --seed 779365550 \
        --action "<Subject 1> hands <Subject 3> to <Subject 2>, who lifts it to her face and smiles"
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
ap.add_argument("characters", nargs="+")
ap.add_argument("--object", action="append", default=[])
ap.add_argument("--scene", default="Arctic shore")
ap.add_argument("--action", default="")
ap.add_argument("--seed", type=int)
args = ap.parse_args()

shots.GROUP[args.shot]["tested"] = True  # this run is the test
samples = json.loads((ROOT / "shotstudio/samples.json").read_text(encoding="utf-8"))
scene = {k: v for k, v in samples["scenes"][args.scene].items() if k != "image"}
chars = [{"pronoun": samples["cast"][c].get("pronoun", "they")} for c in args.characters]
prompt = shots.build(args.shot, scene, chars, args.action, objects=len(args.object))
refs = [ROOT / f"shotstudio/static/refs/{c}.png" for c in args.characters]
refs += [ROOT / f"shotstudio/static/objects/{o}.png" for o in args.object]
job = render.Renderer(ROOT / "outputs").start(args.shot, prompt, refs, shots.RECIPES[args.shot]["length"],
                                              864, 480, args.seed)
while job.status not in ("succeeded", "failed"):
    time.sleep(5)
print(json.dumps(job.public(), indent=1))
