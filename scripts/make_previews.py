"""Make each camera-move tile's still and hover preview from the picked takes at native resolution
(outputs/native/done.json, written by render_native.py): the preview is a small, silent, looping clip,
the still is one full-size frame from late in the take, once the move has played out.

    python scripts/make_previews.py
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import shots  # noqa: E402

OUTPUTS = ROOT / "outputs"
STATIC = ROOT / "shotstudio" / "static"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

# Takes that replace the native batch's: the crash zoom in re-made from the 864x480 pick through the
# H3 latent upscaler, which keeps his composition where the native re-render changed it.
OVERRIDE = {"crash-zoom-in": OUTPUTS / "h3native" / "crash-zoom-in_d45_final.mp4"}
# Where in the take the still is taken, as a fraction of its length; the move has played out by then.
STILL_AT = 0.8
# Moves whose still needs another moment: the end leaves the subject gone or out of shot (crumbled,
# vanished, tiny, risen past), or, for the tilt up, the face only arrives at the very end.
# These take theirs from where the subject reads.
STILL_AT_MOVE = {"disintegration": 0.45, "vanish": 0.35, "super-dolly-out": 0.5, "pedestal-up": 0.45, "tilt-up-reveal": 0.97}


def source(slug: str, done: dict) -> Path | None:
    if slug in OVERRIDE:
        return OVERRIDE[slug]
    return OUTPUTS / "native" / done[slug]["native"] if slug in done else None


def duration(video: Path) -> float:
    return float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(video)], capture_output=True, text=True, check=True).stdout.strip())


done = json.loads((OUTPUTS / "native" / "done.json").read_text(encoding="utf-8"))
(STATIC / "previews").mkdir(exist_ok=True)
for shot in shots.catalog():
    src = source(shot["slug"], done)
    if not src or not src.exists():
        print(f"{shot['slug']}: no native take, keeps what it has")
        continue
    stem = Path(shot["still"]).stem
    preview, still = STATIC / "previews" / f"{stem}.mp4", STATIC / shot["still"]
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-an", "-vf", "scale=432:-2,fps=24",
                    "-c:v", "libx264", "-crf", "30", "-preset", "slow", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(preview)], check=True)
    at = STILL_AT_MOVE.get(shot["slug"], STILL_AT)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{duration(src) * at:.2f}", "-i", str(src),
                    "-frames:v", "1", "-vf", "scale=1344:-2", "-q:v", "3", str(still)], check=True)
    print(f"{shot['slug']}: {src.name} -> {preview.name} ({preview.stat().st_size // 1024} KB), {still.name}")
