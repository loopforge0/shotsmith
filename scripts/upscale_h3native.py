"""Re-make a picked take at 1920x1088 the way the H3 latent upscaler is meant to be used: generate the
draft exactly as the pick was made (its prompt, seed, references and 864x480 size, so the composition
is the one picked, not a new take), enlarge the draft's latent with the upscaler, then refine it
at the new size with the same prompt, references and guidance. One graph, since the refine needs the
draft's latent and conditioning. Written for the pod (32 GB); a 12 GB card runs out at full length.

    COMFY_URL=http://127.0.0.1:8188 python scripts/upscale_h3native.py crash-zoom-in [crash-zoom-out ...] [--denoise 0.45]

The draft and the result are saved next to each other in outputs/h3native/, and a move marked "snap"
gets its speed ramp, as the app does.
"""

import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import shots, snap  # noqa: E402

OUT = ROOT / "outputs"
DEST = OUT / "h3native"
COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
WIDTH, HEIGHT = 1920, 1088
UPSCALER = "minimax_h3_latent_upscaler_3d_bf16.safetensors"


def api(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(COMFY + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def refs_for(prompt: str, seed: int) -> list[str]:
    """The pick's reference images, from the proxy's record of the job (the saved workflow leaves them blank)."""
    db = sqlite3.connect(f"file:{OUT / 'proxy-state' / 'state.sqlite3'}?mode=ro", uri=True)
    for (text,) in db.execute("select workflow from jobs"):
        wf = json.loads(text)
        h3 = next((n["inputs"] for n in wf.values() if n.get("class_type") == "MiniMaxH3ReferenceToVideo"), None)
        s = next((n["inputs"].get("noise_seed") for n in wf.values() if n.get("class_type") == "RandomNoise"), None)
        if h3 and h3["prompt"] == prompt and s == seed:
            return [wf[k]["inputs"]["image"] for k in sorted(wf) if wf[k].get("class_type") == "LoadImage"]
    raise KeyError("no proxy job for this prompt and seed")


def graph(pick: str, key: str, denoise: float) -> dict:
    g = json.loads((OUT / pick.replace(".mp4", ".workflow.json")).read_text(encoding="utf-8"))
    h3 = g["6"]["inputs"]
    for name, node in zip(refs_for(h3["prompt"], g["7"]["inputs"]["noise_seed"]),
                          [k for k in sorted(g) if g[k]["class_type"] == "LoadImage"]):
        g[node]["inputs"]["image"] = name
    g["15"]["inputs"]["filename_prefix"] = f"h3native/{key}_draft"
    g.update({
        "16": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["11", 0]}},
        "17": {"class_type": "MinimaxH3LatentUpscaler3D",
               "inputs": {"latent": ["16", 0], "model_name": UPSCALER, "mode": "target dimensions",
                          "mode.width": WIDTH, "mode.height": HEIGHT, "align": 32,
                          "enable_temporal_chunking": False, "force_unload": True, "device": "cuda",
                          "precision": "fp16"}},
        "18": {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["17", 0], "audio_latent": ["16", 1]}},
        # The refine is the tail of the same schedule: a hires-fix at `denoise`, same noise and guider.
        "19": {"class_type": "BasicScheduler",
               "inputs": {"model": ["5", 0], "scheduler": "simple", "steps": 20, "denoise": denoise}},
        "20": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["7", 0], "guider": ["10", 0], "sampler": ["8", 0], "sigmas": ["19", 0],
                          "latent_image": ["18", 0]}},
        "21": {"class_type": "VAEDecode", "inputs": {"samples": ["20", 0], "vae": ["3", 0]}},
        "22": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["20", 0], "vae": ["4", 0]}},
        "23": {"class_type": "CreateVideo", "inputs": {"images": ["21", 0], "audio": ["22", 0], "fps": 24}},
        "24": {"class_type": "SaveVideo", "inputs": {"video": ["23", 0], "filename_prefix": f"h3native/{key}_final",
                                                      "format": "auto", "codec": "auto"}},
    })
    return g


def fetch(item: dict, dst: Path) -> None:
    q = urllib.parse.urlencode({"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": "output"})
    with urllib.request.urlopen(f"{COMFY}/view?{q}") as r:
        dst.write_bytes(r.read())


def run(key: str, denoise: float) -> None:
    pick = json.loads((OUT / "picks.json").read_text(encoding="utf-8"))[key]
    start = time.time()
    pid = api("/prompt", {"prompt": graph(pick, key, denoise)})["prompt_id"]
    print(f"== {key}: {pick} draft 864x480 -> latent upscale -> refine {WIDTH}x{HEIGHT} at denoise {denoise}, {pid}",
          flush=True)
    while True:
        time.sleep(10)
        hist = api(f"/history/{pid}").get(pid)
        if hist and hist["status"].get("status_str") == "error":
            raise RuntimeError(json.dumps(hist["status"].get("messages", []))[-1500:])
        if hist and hist["status"].get("completed"):
            break
    DEST.mkdir(exist_ok=True)
    tag = f"d{int(denoise * 100)}"
    for node, part in (("15", "draft"), ("24", "final")):
        item = next(i for i in hist["outputs"][node].get("images", []) + hist["outputs"][node].get("videos", []))
        dst = DEST / f"{key}_{tag}_{part}.mp4"
        fetch(item, dst)
        if shots.RECIPES.get(key, {}).get("snap"):
            raw = dst.with_name(dst.stem + "_raw.mp4")
            dst.replace(raw)
            print(f"  {part}: speed ramp {snap.snap(raw, dst)}", flush=True)
    print(f"  -> {DEST.name}/{key}_{tag}_final.mp4 in {time.time() - start:.0f}s", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    denoise = float(args[args.index("--denoise") + 1]) if "--denoise" in args else 0.45
    for key in [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--denoise")]:
        run(key, denoise)
