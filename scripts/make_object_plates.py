"""Generate the bundled object references with FLUX.3 Klein, through the Comfy SDK.

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/make_object_plates.py
"""

import json
import sys
from pathlib import Path

from comfy_sdk import Comfy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_location_plates import graph  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "shotstudio/static/objects"

OBJECTS = {
    "Lantern": ("lantern", "A product photograph of an old brass oil lantern with a glass chimney and a wire "
                "handle, slightly tarnished, centred on a plain light grey background, soft studio light."),
    "Umbrella": ("umbrella", "A product photograph of a closed bright red umbrella with a curved wooden handle, "
                 "standing upright, centred on a plain light grey background, soft studio light."),
    "Compass": ("compass", "A product photograph of an antique brass pocket compass with its lid open, a "
                "cream dial and a blue steel needle, centred on a plain light grey background, soft studio light."),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    client = Comfy()
    samples_file = ROOT / "shotstudio/samples.json"
    samples = json.loads(samples_file.read_text(encoding="utf-8"))
    samples.setdefault("objects", {})
    for name, (slug, prompt) in OBJECTS.items():
        g = graph(prompt, 5)
        g["latent"]["inputs"].update(width=1024, height=1024)
        g["shift"]["inputs"].update(width=1024, height=1024)
        job = client.run(client.workflows.from_json(g))
        path = job.get_outputs("save")[0].to_file(OUT / f"{slug}.png")
        samples["objects"][slug] = {"name": name}
        print(name, "->", path, flush=True)
    samples_file.write_text(json.dumps(samples, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
