"""Re-render the picked takes (outputs/picks.json, from scripts/picker.py) at native resolution, for the
app's previews and stills and the demo video. Each pick keeps its exact prompt, seed and length; only the
size changes. The reference photos aren't in the saved workflows, so they come from the proxy's job
record of the same prompt and seed. Results go to outputs/native/, and finished picks are skipped on a
re-run.

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/render_native.py [slug ...]
"""

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import render  # noqa: E402

OUT = ROOT / "outputs"
NATIVE = OUT / "native"
DONE = NATIVE / "done.json"
WIDTH, HEIGHT = 1344, 768
IMAGE_DIRS = [ROOT / "shotstudio" / "static" / "refs", ROOT / "shotstudio" / "static" / "locations",
              *([Path(os.environ["COMFYUI_DIR"]) / "input"] if os.environ.get("COMFYUI_DIR") else [])]

# Extra picks beyond one per move, and the moves to decide last.
EXTRA = {"orbit-360-single": "orbit-360_702970857_b0abf7a2268c.mp4"}
LAST = ["slow-zoom-out"]
# Recipes tightened after their pick was rendered: `--redo` re-renders these with the pick's prompt
# brought up to the recipe's new wording, even if they are already done.
REDO = {
    "crash-zoom-in": [("for the first two seconds", "for the first second only"),
                      ("After it lands the close-up is locked and does not change.",
                       "After it lands, the close-up is locked for the whole rest of the shot, at least the last "
                       "two seconds, and does not change.")],
    "crash-zoom-out": [("for the first two seconds", "for the first second only"),
                       ("After it lands the wide framing is locked and does not change.",
                        "After it lands, the wide framing is locked for the whole rest of the shot, at least the "
                        "last two seconds, and does not change.")],
    "cutaway-montage": [("slide on a pair of dark sunglasses with both hands.",
                         "slide on a pair of dark sunglasses with both hands, sitting in the driver's seat."),
                        ("the shot cuts to an extreme close-up of her eyes as they flick up",
                         "the shot cuts to an extreme close-up on her face, now in the driver's seat of the car, with the steering "
                         "wheel, dashboard and windscreen all around, the desert highway beyond and the dark sunglasses on, as her "
                         "gaze snaps up"),
                        ("the shot cuts back to the tight close-up of her face, now still and ready",
                         "the shot cuts to a tight close-up of her face, still in the driver's seat of the car, with the steering "
                         "wheel, dashboard and windscreen all around, the desert highway beyond and the dark sunglasses on, now "
                         "still and ready")],
    "dolly-zoom-in": [("A waist-up medium close-up frames <Subject 1>, standing", "A close-up frames <Subject 1>'s head and shoulders, standing"),
                      ("it pulls out while simultaneously zooming in, so that <Subject 1>'s size and position in frame stay exactly "
                       "constant throughout, while",
                       "it pulls out while simultaneously zooming in, the zoom exactly cancelling the pull, so that <Subject 1>'s "
                       "size and position in frame stay exactly constant throughout: her head and shoulders fill the same part of "
                       "the frame from the first frame to the last and she never gets smaller. Only the background changes:"),
                      ("crowd in close behind her as the lens's focal length changes.",
                       "crowd in close behind her as the lens's focal length changes. As the background crowds in, her expression "
                       "shifts from calm to dawning dread, then to alarm: her eyes widen, her brows lift and her lips part.")],
    "dolly-zoom": [("A waist-up medium close-up frames <Subject 1>, standing", "A close-up frames <Subject 1>'s head and shoulders, standing"),
                   ("recede, shrink, and spread apart into much greater depth as the lens's focal length changes.",
                    "recede, shrink, and spread apart into much greater depth as the lens's focal length changes. As the "
                    "background stretches away, her expression shifts from calm to dawning realisation, then to shock: "
                    "her eyes widen, her brows lift and her lips part.")],
    "overhead-swing": [("The camera swings down in an arc shot at slow speed",
                        "The camera swings down in front of her, on the side she is facing, in an arc shot at slow speed"),
                       ("the same size in frame the whole way, and ends face-on",
                        "the same size in frame the whole way, never passing behind her, and ends face-on")],
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


def find_image(name: str) -> Path:
    for d in IMAGE_DIRS:
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(name)


picks = {**json.loads((OUT / "picks.json").read_text(encoding="utf-8")), **EXTRA}
order = [s for s in picks if s not in LAST] + [s for s in LAST if s in picks]
redo = "--redo" in sys.argv
if redo:
    order = [s for s in order if s in REDO]
# --seed=N renders the given picks again with another seed, as alternates to choose from:
# they are not marked done, so the pick's own native render stays in place until he swaps it.
alt_seeds = [int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--seed=")]
args = [a for a in sys.argv[1:] if a != "--redo" and not a.startswith("--seed=")]
if args:
    order = [s for s in order if s in args]
NATIVE.mkdir(exist_ok=True)
done = json.loads(DONE.read_text(encoding="utf-8")) if DONE.exists() else {}
jobs = proxy_refs()
r = render.Renderer(NATIVE)
runs = [(key, s) for key in order for s in alt_seeds] if alt_seeds else [(key, None) for key in order]
for key, alt in runs:
    if key in done and not redo and alt is None:
        continue
    src = picks[key]
    wf = json.loads((OUT / src.replace(".mp4", ".workflow.json")).read_text(encoding="utf-8"))
    h3, seed = wf["6"]["inputs"], wf["7"]["inputs"]["noise_seed"]
    refs = [find_image(n) for n in jobs[(h3["prompt"], seed)]]
    prompt = h3["prompt"]
    for old, new in REDO.get(key, []) if redo else []:
        assert old in prompt, f"{key}: {old!r} not in the picked prompt"
        prompt = prompt.replace(old, new)
    # The move's slug names the job, so the crash zooms get their speed ramp.
    slug = key.removesuffix("-single")
    job = r.start(slug, prompt, refs, h3["length"], WIDTH, HEIGHT, seed=alt or seed, ref_image_size="max")
    print(f"== {key}: {src} at {WIDTH}x{HEIGHT}" + (f", alternate seed {alt}" if alt else ""), flush=True)
    while job.status not in ("succeeded", "failed"):
        time.sleep(10)
    print(f"  -> {job.status} {job.video or job.error} in {job.public()['elapsed']}s", flush=True)
    if job.status == "succeeded" and alt is None:
        # Another run of this script may have written since this one started.
        done = json.loads(DONE.read_text(encoding="utf-8")) if DONE.exists() else {}
        done[key] = {"from": src, "native": job.video, **({"redo": True} if redo else {})}
        DONE.write_text(json.dumps(done, indent=2) + "\n", encoding="utf-8")
