"""Generate the bundled location plates with FLUX.3 Klein, through the Comfy SDK.

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/make_location_plates.py

Settings follow the flux3-klein comparison project: int8 Klein, 16 steps, cfg 1, shift alpha 16.
"""

import json
import math
import sys
from pathlib import Path

from comfy_sdk import Comfy

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "shotstudio/static/locations"

PLATES = {
    "Arctic shore": ("arctic-shore", "A cinematic wide photograph of a snow-covered arctic coastline at night, nobody in it. "
                     "Dark rocky cliffs, snowy boulders on the shore, still black water, an old wooden sailing ship with "
                     "tall masts anchored offshore, green aurora borealis across the sky. Cold blue-green light, slightly "
                     "desaturated. Shot on an ARRI Alexa, natural film grain."),
    "Rain-soaked city street": ("rain-street", "A cinematic wide photograph of a narrow city street at night in heavy rain, "
                                "nobody in it. Glowing shop signs, parked cars beaded with rain, puddles reflecting neon, "
                                "steam rising from a grate. Magenta and teal neon light, wet asphalt reflections. Shot on an "
                                "ARRI Alexa with an anamorphic lens."),
    "Autumn forest track": ("forest-track", "A cinematic wide photograph of a straight track through a pine forest in late "
                            "autumn, nobody in it. Tall straight pine trunks, a carpet of orange needles, low mist between "
                            "the trees, shafts of low golden afternoon sunlight. Warm amber and green palette. Shot on an "
                            "ARRI Alexa with a Cooke S4 50mm lens."),
}


def graph(prompt: str, seed: int) -> dict:
    w, h = 1344, 768
    mu = math.log(16)
    return {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux3-image-klein-int8-convrot.safetensors", "weight_dtype": "default"}},
        "shift": {"class_type": "ModelSamplingFlux", "inputs": {"model": ["unet", 0], "max_shift": mu, "base_shift": mu, "width": w, "height": h}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_int8_convrot.safetensors", "type": "flux3", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "flux3-klein-vae.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": prompt}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": ""}},
        "latent": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "sampler": {"class_type": "KSampler", "inputs": {
            "model": ["shift", 0], "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["latent", 0],
            "seed": seed, "steps": 16, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": "shotstudio/location"}},
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    client = Comfy()
    samples_file = ROOT / "shotstudio/samples.json"
    samples = json.loads(samples_file.read_text(encoding="utf-8"))
    for name, (slug, prompt) in PLATES.items():
        job = client.run(client.workflows.from_json(graph(prompt, 11)))
        out = job.get_outputs("save")[0]
        path = out.to_file(OUT / f"{slug}.png")
        samples["scenes"][name]["image"] = f"locations/{slug}.png"
        print(name, "->", path, flush=True)
    samples_file.write_text(json.dumps(samples, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
