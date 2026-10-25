"""Describe a character's photo or a location's image in the words the app's prompts use.

The bundled characters and locations come with hand-written words (samples.json): a character's look,
a location's place, what is around, its sound and the fields camera moves take from it. This fills the
same fields for one a person adds, with Qwen3-VL 8B, the text encoder Qwen Image 2.1 already uses
(H3's own 32B encoder is cut down to the layers H3 reads and cannot write text). It runs as a
workflow through the Comfy SDK like a render, from core nodes only: TextGenerate, then SaveText, so the
text comes back as an output file.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from comfy_sdk import Comfy, Progress, StatusChange

from .render import explain

MODEL = "qwen3vl_8b_int8_convrot.safetensors"

CHARACTER = """You describe a reference photo for a video model. Reply with JSON only, no other text:
{"type": "person" | "animal" | "bird",
 "look": "<one phrase: hair (length, texture, colour), facial hair, then glasses, jewellery, tattoos or other marks, then every visible piece of clothing with its colour and material, top to bottom>"}
The look is written like these, with no pronouns and no names:
"long wavy ginger-red hair, freckles, a cream short-sleeve t-shirt, a dark cord necklace with a metal cross, and high-waisted blue jeans with a brown belt"
"short black curly hair, a thick moustache, round tortoiseshell glasses, a denim jacket over a white t-shirt and black trousers"
Only what is visible in the photo. Do not guess clothing that is out of frame."""

# The examples describe a place the app does not ship, so the model describes the image, not them.
LOCATION = """You describe a location photo for a video model, so a person can be placed in it. Reply with JSON only, no other text. Every value is a short phrase in plain English about what is in this photo:
{"ENVIRONMENT": "<the place, with a or an, and the time of day if clear, e.g. a misty fishing harbour at dawn>",
 "ENVIRONMENT_PREP": "<in, on or at, whichever reads right before ENVIRONMENT>",
 "PLACE": "<where a person stands in it, with its preposition, e.g. at the end of the stone quay>",
 "ENVIRONMENT_ELEMENTS": "<four or five visible things, e.g. moored fishing boats, stacked lobster pots, a stone lighthouse and gulls over the water>",
 "SOUNDSCAPE": "<the main ambient sound, then continues throughout, then a second sound, e.g. Lapping water continues throughout, with distant gulls and creaking ropes>",
 "LOCATION": "<the place in a few words with the, e.g. the misty harbour>",
 "BACKGROUND": "<three solid things that would stand behind a person, e.g. the fishing boats, the lobster pots and the lighthouse>",
 "PLACE_2": "<where a second person could be, with a verb, e.g. standing further along the quay>",
 "THE_SPACE": "<a long space a camera could travel down, e.g. the long stone quay>",
 "NEAR_OBJECTS": "<two objects that could be close to the lens at the left and right, e.g. two near mooring posts>",
 "FURTHER_OBJECTS": "<what is further away, e.g. further posts and boats>",
 "GROUND": "<the ground, e.g. the wet stone quay>",
 "LOOSE_THINGS": "<four loose things that could slide or tumble, each with a verb, e.g. a rolling buoy, a skidding crate, a tumbling lobster pot and a sliding coil of rope>"}"""

FIELDS = {
    "character": ("type", "look"),
    "location": ("ENVIRONMENT", "ENVIRONMENT_PREP", "PLACE", "ENVIRONMENT_ELEMENTS", "SOUNDSCAPE", "LOCATION",
                 "BACKGROUND", "PLACE_2", "THE_SPACE", "NEAR_OBJECTS", "FURTHER_OBJECTS", "GROUND", "LOOSE_THINGS"),
}
# Lists the prompts read as "a, b and c", the way the bundled ones are written.
LISTS = {"look", "ENVIRONMENT_ELEMENTS", "BACKGROUND", "FURTHER_OBJECTS", "LOOSE_THINGS"}


def _tidy(key: str, value: str) -> str:
    value = re.sub(r"\s+", " ", str(value)).strip().strip('"').rstrip(".").strip()
    if key in LISTS and " and " not in value and value.count(", ") >= 1:
        head, _, last = value.rpartition(", ")
        value = f"{head} and {last}"
    if key == "ENVIRONMENT_PREP":
        value = value.lower() if value.lower() in ("in", "on", "at") else "in"
    if key in ("LOCATION", "THE_SPACE", "GROUND") and not re.match(r"(the|a|an)\s", value, re.I):
        value = "the " + value
    if key == "SOUNDSCAPE" and value:
        value = value[0].upper() + value[1:]
    return value


def parse(kind: str, text: str) -> dict[str, str]:
    """The model's JSON reply, tidied; missing or empty fields are left out."""
    body = re.search(r"\{.*\}", text, re.S)
    if not body:
        raise ValueError("the description came back without its fields")
    data = json.loads(body[0])
    out = {k: _tidy(k, data[k]) for k in FIELDS[kind] if isinstance(data.get(k), str) and data[k].strip()}
    if kind == "character" and out.get("type") not in ("person", "animal", "bird"):
        out["type"] = "person"
    return out


# How long each reply runs, in tokens, so the page can say how much is left: TextGenerate reports
# each token as a step, but its step count is the limit (700), not the reply's length. Each finished
# reply updates these (measured: a look about 70 tokens, a location about 220).
EXPECTED_TOKENS = {"character": 70, "location": 220}


@dataclass
class DescribeJob:
    id: str
    kind: str
    status: str = "running"         # running, succeeded or failed
    stage: str = "starting"         # waiting, loading the model, reading the image, writing
    tokens: int = 0
    rate: float = 0.0               # tokens a second, once writing
    started: float = field(default_factory=time.time)
    writing_since: float | None = None
    result: dict[str, str] | None = None
    error: str | None = None

    def public(self) -> dict:
        expected = max(EXPECTED_TOKENS[self.kind], self.tokens + 1)
        left = round((expected - self.tokens) / self.rate) if self.rate else None
        return {"id": self.id, "status": self.status, "stage": self.stage, "elapsed": round(time.time() - self.started),
                "progress": round(min(self.tokens / expected, 0.99), 2) if self.status == "running" else 1.0,
                "seconds_left": left, "result": self.result, "error": self.error}


JOBS: dict[str, DescribeJob] = {}


def start(image: Path, kind: str) -> DescribeJob:
    """Describe an image in the background; follow it with JOBS[id].public()."""
    job = DescribeJob(id=uuid.uuid4().hex[:12], kind=kind)
    JOBS[job.id] = job

    def run() -> None:
        try:
            job.result = describe(image, kind, job)
            job.status, job.stage = "succeeded", "done"
            EXPECTED_TOKENS[kind] = round(0.7 * EXPECTED_TOKENS[kind] + 0.3 * job.tokens)
        except Exception as exc:  # shown on the page
            job.status, job.error = "failed", f"Describing the image failed. {explain(exc)}"

    threading.Thread(target=run, daemon=True).start()
    return job


def describe(image: Path, kind: str, job: DescribeJob | None = None) -> dict[str, str]:
    """Describe one image (kind "character" or "location"): 10 to 30 seconds once the model is loaded."""
    graph = {
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": MODEL, "type": "qwen_image", "device": "default"}},
        "image": {"class_type": "LoadImage", "inputs": {"image": "describe.png"}},
        "text": {"class_type": "TextGenerate", "inputs": {"clip": ["clip", 0], "image": ["image", 0], "max_length": 700,
                 "prompt": CHARACTER if kind == "character" else LOCATION, "sampling_mode": "off"}},
        "save": {"class_type": "SaveText", "inputs": {"text": ["text", 0], "filename_prefix": "shotstudio/describe", "format": "txt"}},
    }
    client = Comfy()
    wf = client.workflows.from_json(graph)
    wf.set_input("image", "image", client.assets.from_file(image))
    handle = client.submit(wf)
    for event in handle.events():
        if job is None:
            continue
        match event:
            case StatusChange(status=s, queue_position=q):
                if s in ("queued", "pending") or q:
                    job.stage = "waiting for the render in progress"
                elif s in ("succeeded", "failed", "canceled", "cancelled"):
                    break
            case Progress(current_node=node, step=step):
                if node == "text" and step:
                    if job.writing_since is None:
                        job.writing_since, job.stage = time.time(), "writing"
                    job.tokens = step
                    spent = time.time() - job.writing_since
                    job.rate = (step - 1) / spent if step > 1 and spent > 0 else job.rate
                elif node == "text":
                    job.stage = "reading the image"
                elif node in ("clip", "image") or node is None:
                    job.stage = "loading the model" if node == "clip" else "reading the image"
    done = handle.result()
    out = next((o for o in done.get_outputs("save")), None)
    if out is None:
        raise RuntimeError("the description finished without its text")
    return parse(kind, out.to_bytes().decode("utf-8"))
