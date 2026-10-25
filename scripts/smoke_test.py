"""Wiring test: one cheap render through the SDK (2 steps, 33 frames, 480p).

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/smoke_test.py [--full]

--full renders the real settings (20 steps, the shot's own length) instead.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shotstudio import render, shots  # noqa: E402

full = "--full" in sys.argv
if not full:
    render.STEPS = 2

root = Path(__file__).resolve().parent.parent
scene = json.loads((root / "shotstudio/vendor/h3shots/scene.example.json").read_text(encoding="utf-8"))
cast = [{"definition": scene["SUBJECT_DEFINITION"].replace("<Picture 1>", "{PLATE}"), "pronoun": "she"}]
prompt = shots.build("orbit-360", scene, cast, "")

r = render.Renderer(root / "outputs")
job = r.start("orbit-360", prompt, [root / "shotstudio/static/refs/amber-main.png"],
              length=124 if full else 33, width=864, height=480, seed=42)
last = None
while job.status not in ("succeeded", "failed"):
    line = f"{job.status} {job.progress:.0%} {job.message}"
    if line != last:
        print(f"[{job.public()['elapsed']:>4}s] {line}", flush=True)
        last = line
    time.sleep(1)
print(json.dumps(job.public(), indent=1))
sys.exit(0 if job.status == "succeeded" else 1)
