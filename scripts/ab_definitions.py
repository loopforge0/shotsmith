"""A/B: re-render past shots with the identity/preservation sentences cut from their definitions.

Everything else (prompt, seed, size, length, references) is copied from the original render, so the
definitions are the only difference.

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/ab_definitions.py
"""

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shotstudio import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
STATIC = ROOT / "shotstudio" / "static"

# The original render, and its references in wiring order.
CASES = {
    "snorricam_7_8d77358afcd0": ([STATIC / "refs/allie.png"], []),
    "dutch-angle_21_84157a1f7733": ([STATIC / "refs/kate.png", STATIC / "locations/arctic-shore.png"],
                                    [ROOT / "uploads/e6c79bc660738cea.wav"]),
    "orbit-360_779365550_de2f80badbab": ([STATIC / "refs/amber-main.png", STATIC / "refs/kate.png",
                                         STATIC / "objects/lantern.png"], []),
}
# A definition line keeps what the label is; the sentence after it (identity lock or "follows") goes.
LOCK = re.compile(r"^(<Subject \d+> is [^\n]*?<Picture \d+>(?::[^\n]*?)?\.) [^\n]*(?:stay|follow)[^\n]*$", re.M)


def strip(prompt: str) -> str:
    head, sep, rest = prompt.partition("\n\nsummary:")
    return LOCK.sub(r"\1", head) + sep + rest


r = render.Renderer(OUT)
for stem, (refs, audios) in CASES.items():
    wf = json.loads((OUT / f"{stem}.workflow.json").read_text(encoding="utf-8"))
    h3, seed = wf["6"]["inputs"], wf["7"]["inputs"]["noise_seed"]
    prompt = strip(h3["prompt"])
    removed = len(h3["prompt"]) - len(prompt)
    print(f"{stem}: removed {removed} chars", flush=True)
    job = r.start(stem.split("_")[0], prompt, refs, length=h3["length"], width=h3["width"],
                  height=h3["height"], seed=seed, audios=audios)
    while job.status not in ("succeeded", "failed"):
        time.sleep(5)
    print(f"  -> {job.status} {job.video or job.error} in {job.public()['elapsed']}s", flush=True)
