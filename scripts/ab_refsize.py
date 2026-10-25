"""A/B: character photos at ref_image_size "match" (scaled to the output's pixel area) against "max"
(2048 px short edge, the setting every render so far used). Each case re-renders an existing "max"
render with the same prompt, seed, size, length and references, so the sizing is the only difference.
The node's tooltip says "max" can be several times slower; this checks what the faces lose with "match".

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/ab_refsize.py STEM:ref,ref... [...]
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import render  # noqa: E402

OUT = ROOT / "outputs"
r = render.Renderer(OUT)
for arg in sys.argv[1:]:
    stem, refs = arg.split(":")
    wf = json.loads((OUT / f"{stem}.workflow.json").read_text(encoding="utf-8"))
    h3, seed = wf["6"]["inputs"], wf["7"]["inputs"]["noise_seed"]
    paths = [ROOT / "shotstudio" / "static" / "refs" / f"{x}.png" for x in refs.split(",")]
    print(f"== {stem} (was {h3.get('ref_image_size')}), now match", flush=True)
    job = r.start(stem.split("_")[0] + "-match", h3["prompt"], paths, h3["length"], h3["width"], h3["height"],
                  seed=seed, ref_image_size="match")
    while job.status not in ("succeeded", "failed"):
        time.sleep(5)
    print(f"  -> {job.status} {job.video or job.error} in {job.public()['elapsed']}s", flush=True)
