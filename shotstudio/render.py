"""Render a shot through the Comfy SDK.

The same code runs against Comfy Cloud or a local ComfyUI behind comfy-api-proxy;
only COMFY_BASE_URL (and COMFY_API_KEY for Cloud) changes.
"""

from __future__ import annotations

import copy
import json
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from comfy_sdk import Comfy, OutputReady, Progress, StatusChange

ROOT = Path(__file__).resolve().parent
TEMPLATE = json.loads((ROOT / "workflows" / "h3_ref2va_shot.json").read_text(encoding="utf-8"))
OUTPUT_NODE = "15"
H3_NODE = "6"

# Settings every verified shot was rendered with. See vendor/.../references/settings.md:
# 4-step turbo suppresses camera motion, so steps stay at 20.
STEPS = 20

# A job in one of these has stopped for good.
DONE = ("succeeded", "failed", "canceled")

# Model files differ between installs; override any of them in models.json next to this file.
MODEL_INPUTS = {"clip": ("2", "clip_name"), "video_vae": ("3", "vae_name"),
                "audio_vae": ("4", "vae_name"), "unet": ("5", "unet_name")}


# Where ComfyUI looks for each kind of model file, by the loader input that names it.
MODEL_FOLDERS = {"unet_name": "diffusion_models", "clip_name": "text_encoders", "vae_name": "vae"}


def explain(exc: Exception) -> str:
    """An error in words: a model file ComfyUI does not have is named, with the folder it goes in.
    ComfyUI checks the files when a job is submitted, so this comes back before anything runs."""
    details = getattr(exc, "details", None)
    errors = (details or {}).get("node_errors", {}) if isinstance(details, dict) else {}
    missing = []
    for node in errors.values():
        for err in node.get("errors", []):
            info = err.get("extra_info") or {}
            folder = MODEL_FOLDERS.get(info.get("input_name"))
            if err.get("type") == "value_not_in_list" and folder:
                missing.append(f"{info.get('received_value')} (in ComfyUI's models/{folder})")
    if missing:
        return "ComfyUI does not have " + " or ".join(dict.fromkeys(missing)) + ". See the README's model list."
    return f"{type(exc).__name__}: {exc}"


def target() -> str:
    url = os.environ.get("COMFY_BASE_URL", "").strip()
    return url or "https://cloud.comfy.org"


def build_graph(prompt: str, length: int, width: int, height: int, seed: int,
                n_refs: int, n_audio: int = 0, n_video: int = 0, ref_image_size: str | None = None) -> dict:
    graph = copy.deepcopy(TEMPLATE)
    overrides = ROOT / "models.json"
    if overrides.exists():
        for key, name in json.loads(overrides.read_text(encoding="utf-8")).items():
            if key in MODEL_INPUTS:
                node, field_name = MODEL_INPUTS[key]
                graph[node]["inputs"][field_name] = name
    h3 = graph[H3_NODE]["inputs"]
    h3.update(prompt=prompt, length=length, width=width, height=height)
    if ref_image_size:  # "max" (2048 short edge, the template's) or "match" (the output's pixel area)
        h3["ref_image_size"] = ref_image_size
    # Reference inputs must be flat dot-notation keys. The nested form validates and then
    # silently drops the reference (see vendor/h3shots/.../verify_refs notes).
    for i in range(n_refs):
        node_id = f"ref{i}"
        graph[node_id] = {"class_type": "LoadImage", "inputs": {"image": ""}}
        h3[f"ref_images.ref_image_{i}"] = [node_id, 0]
    # Standalone audio becomes <Audio 1..n> in the prompt, in wiring order.
    for i in range(n_audio):
        node_id = f"audio{i}"
        graph[node_id] = {"class_type": "LoadAudio", "inputs": {"audio": ""}}
        h3[f"ref_audios.ref_audio_{i}"] = [node_id, 0]
    # Reference videos become <Video 1..n>: the node takes their frames (24 fps, 2-15 s).
    for i in range(n_video):
        graph[f"video{i}"] = {"class_type": "LoadVideo", "inputs": {"file": ""}}
        graph[f"vframes{i}"] = {"class_type": "GetVideoComponents", "inputs": {"video": [f"video{i}", 0]}}
        h3[f"ref_videos.ref_video_{i}"] = [f"vframes{i}", 0]
    graph["7"]["inputs"]["noise_seed"] = seed
    graph["9"]["inputs"]["steps"] = STEPS
    return graph


@dataclass
class RenderJob:
    id: str
    shot: str
    prompt: str
    seed: int
    width: int
    height: int
    length: int
    status: str = "queued"
    progress: float = 0.0
    message: str = ""
    comfy_job_id: str | None = None
    video: str | None = None
    error: str | None = None
    started: float = field(default_factory=time.time)
    finished: float | None = None
    inputs: dict | None = None   # what the page sent (cast, location, sound, size), for Recreate
    canceling: bool = False

    def public(self) -> dict:
        d = {k: getattr(self, k) for k in ("id", "shot", "seed", "width", "height", "length",
                                            "status", "progress", "message", "video", "error",
                                            "started", "finished", "inputs")}
        d["elapsed"] = round((self.finished or time.time()) - self.started)
        return d


class Renderer:
    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, RenderJob] = {}
        self._lock = threading.Lock()
        self.pending_dir = out_dir / "pending"
        self.pending_dir.mkdir(exist_ok=True)
        self._load_finished()
        self._resume_pending()

    def _load_finished(self) -> None:
        """Past renders survive a restart: each MP4 has its prompt and workflow beside it."""
        for wf_file in self.out_dir.glob("*.workflow.json"):
            stem = wf_file.name.removesuffix(".workflow.json")
            video, prompt = self.out_dir / f"{stem}.mp4", self.out_dir / f"{stem}.txt"
            shot, seed, job_id = stem.rsplit("_", 2)
            if not (video.exists() and prompt.exists()):
                continue
            h3 = json.loads(wf_file.read_text(encoding="utf-8"))[H3_NODE]["inputs"]
            mtime = video.stat().st_mtime
            inputs_file = self.out_dir / f"{stem}.inputs.json"
            inputs = json.loads(inputs_file.read_text(encoding="utf-8")) if inputs_file.exists() else None
            took = (inputs or {}).pop("took", 0)   # how long it ran, for the page's time estimate
            self.jobs[job_id] = RenderJob(
                id=job_id, shot=shot, prompt=prompt.read_text(encoding="utf-8"), seed=int(seed),
                width=h3["width"], height=h3["height"], length=h3["length"], status="succeeded",
                progress=1.0, message="done", video=video.name, started=mtime - took, finished=mtime,
                inputs=inputs)

    def _resume_pending(self) -> None:
        """A render still on ComfyUI when the app stopped is picked up again: each submitted job
        leaves a note in pending/ until its video is saved."""
        for note in self.pending_dir.glob("*.json"):
            d = json.loads(note.read_text(encoding="utf-8"))
            job = RenderJob(id=d["id"], shot=d["shot"], prompt=d["prompt"], seed=d["seed"], width=d["width"],
                            height=d["height"], length=d["length"], status="running",
                            message="picking up after a restart", comfy_job_id=d["comfy_job_id"], started=d["started"],
                            inputs=d.get("inputs"))
            self.jobs[job.id] = job

            def resume(job=job, graph_text=d["graph"]) -> None:
                try:
                    self._finish(job, Comfy().jobs.get(job.comfy_job_id), graph_text)
                except Exception as exc:  # surfaced to the UI, never swallowed
                    job.status, job.error = "failed", explain(exc)
                    job.finished = time.time()
                    (self.pending_dir / f"{job.id}.json").unlink(missing_ok=True)

            threading.Thread(target=resume, daemon=True).start()

    def start(self, shot: str, prompt: str, refs: list[Path], length: int, width: int,
              height: int, seed: int | None = None, audios: list[Path] | None = None,
              videos: list[Path] | None = None, ref_image_size: str | None = None,
              inputs: dict | None = None) -> RenderJob:
        job = RenderJob(id=uuid.uuid4().hex[:12], shot=shot, prompt=prompt,
                        seed=seed if seed is not None else random.randrange(2**31),
                        width=width, height=height, length=length, inputs=inputs)
        with self._lock:
            self.jobs[job.id] = job
        threading.Thread(target=self._run, args=(job, refs, audios or [], videos or [], ref_image_size),
                         daemon=True).start()
        return job

    def _run(self, job: RenderJob, refs: list[Path], audios: list[Path], videos: list[Path],
             ref_image_size: str | None = None) -> None:
        try:
            client = Comfy()
            graph = build_graph(job.prompt, job.length, job.width, job.height, job.seed, len(refs),
                                len(audios), len(videos), ref_image_size)
            # Serialised before the asset handles go in; they are not JSON.
            graph_text = json.dumps(graph, indent=1)
            wf = client.workflows.from_json(graph)
            for i, path in enumerate(refs):
                wf.set_input(f"ref{i}", "image", client.assets.from_file(path))
            for i, path in enumerate(audios):
                wf.set_input(f"audio{i}", "audio", client.assets.from_file(path))
            for i, path in enumerate(videos):
                wf.set_input(f"video{i}", "file", client.assets.from_file(path))
            job.status, job.message = "submitting", "uploading references"
            handle = client.submit(wf)
            job.comfy_job_id = handle.id
            (self.pending_dir / f"{job.id}.json").write_text(json.dumps({
                "id": job.id, "shot": job.shot, "prompt": job.prompt, "seed": job.seed, "width": job.width,
                "height": job.height, "length": job.length, "comfy_job_id": handle.id, "started": job.started,
                "graph": graph_text, "inputs": job.inputs}), encoding="utf-8")
            job.status, job.message = "running", "queued on ComfyUI"
            if job.canceling:
                handle.cancel()
            self._finish(job, handle, graph_text)
        except Exception as exc:  # surfaced to the UI, never swallowed
            job.status, job.error = "failed", explain(exc)
            job.finished = time.time()
            (self.pending_dir / f"{job.id}.json").unlink(missing_ok=True)

    def _finish(self, job: RenderJob, handle, graph_text: str) -> None:
        """Follow a submitted job to its end and save the video, its prompt and its workflow."""
        try:
            for event in handle.events():
                match event:
                    case Progress() as p:
                        # Progress is per node. Only the sampler has a real step count, so the
                        # bar follows its steps and every other node is reported by phase.
                        if p.steps == STEPS and p.step is not None:
                            job.progress = p.step / p.steps * 0.9
                            job.message = f"sampling step {p.step}/{p.steps}"
                        elif job.progress >= 0.9:
                            job.message = "decoding video and audio"
                        else:
                            job.message = "encoding prompt and references"
                    case StatusChange(status=s):
                        job.message = s
                        if s in ("succeeded", "failed", "canceled", "cancelled"):
                            break
                    case OutputReady():
                        pass
            done = handle.result()
            outputs = done.get_outputs(OUTPUT_NODE)
            video = next((o for o in outputs if o.content_type.startswith("video")), None)
            if video is None:
                raise RuntimeError("the job finished without a video output")
            name = f"{job.shot}_{job.seed}_{job.id}.mp4"
            video.to_file(self.out_dir / name)
            # A move marked "snap" (the crash zooms) has its zoom sped up to a few frames, since H3
            # paces it over a second or two. The render as H3 made it is kept beside it.
            from . import shots, snap
            if shots.RECIPES.get(job.shot, {}).get("snap"):
                job.message = "speeding up the zoom"
                raw = self.out_dir / f"{job.shot}_{job.seed}_{job.id}_raw.mp4"
                (self.out_dir / name).replace(raw)
                snap.snap(raw, self.out_dir / name)
            (self.out_dir / f"{job.shot}_{job.seed}_{job.id}.txt").write_text(
                job.prompt, encoding="utf-8", newline="\n")
            (self.out_dir / f"{job.shot}_{job.seed}_{job.id}.workflow.json").write_text(
                graph_text, encoding="utf-8")
            (self.out_dir / f"{job.shot}_{job.seed}_{job.id}.inputs.json").write_text(
                json.dumps({**(job.inputs or {}), "took": round(time.time() - job.started)}, indent=1), encoding="utf-8")
            job.video, job.status, job.progress, job.message = name, "succeeded", 1.0, "done"
        except Exception as exc:  # surfaced to the UI, never swallowed
            if job.canceling:
                job.status, job.message = "canceled", "canceled"
            else:
                job.status, job.error = "failed", explain(exc)
        finally:
            job.finished = time.time()
            (self.pending_dir / f"{job.id}.json").unlink(missing_ok=True)

    def cancel(self, job_id: str) -> RenderJob:
        """Stop a render: ComfyUI interrupts it if it is running, or takes it out of the queue."""
        job = self.jobs[job_id]
        if job.status in DONE or job.canceling:
            return job
        job.canceling, job.message = True, "canceling"
        if job.comfy_job_id:
            Comfy().jobs.get(job.comfy_job_id).cancel()
        return job

    def delete(self, job_id: str) -> None:
        """Forget a finished render and delete its files: the video, its prompt, workflow and inputs."""
        job = self.jobs[job_id]
        if job.status not in DONE:
            raise ValueError("cancel the render before deleting it")
        stem = f"{job.shot}_{job.seed}_{job.id}"
        for suffix in (".mp4", "_raw.mp4", ".txt", ".workflow.json", ".inputs.json"):
            (self.out_dir / f"{stem}{suffix}").unlink(missing_ok=True)
        del self.jobs[job_id]


IMAGE_TEMPLATE = json.loads((ROOT / "workflows" / "qwen_image_location.json").read_text(encoding="utf-8"))


def generate_image(prompt: str, out: Path, seed: int | None = None, width: int = 1344,
                   height: int = 768, on_progress=None) -> Path:
    """Text to image with Qwen Image 2.1 turbo (8 steps), for location plates. Blocks until done;
    `on_progress(stage, step, steps)` hears how it is going."""
    graph = copy.deepcopy(IMAGE_TEMPLATE)
    graph["encode"]["inputs"]["prompt"] = prompt
    graph["latent"]["inputs"].update(width=width, height=height)
    graph["noise"]["inputs"]["noise_seed"] = random.randrange(2**31) if seed is None else seed
    client = Comfy()
    handle = client.submit(client.workflows.from_json(graph))
    report = on_progress or (lambda *a: None)
    for event in handle.events():
        match event:
            case StatusChange(status=s, queue_position=q):
                if s in ("queued", "pending") or q:
                    report("waiting for the render in progress")
                elif s in ("succeeded", "failed", "canceled", "cancelled"):
                    break
            case Progress(current_node=node, step=step, steps=steps):
                if node == "sampler" and steps:
                    report("making the image", step or 0, steps)
                elif node in ("unet", "clip", "vae", "cache"):
                    report("loading the models")
                elif node == "encode":
                    report("reading the description")
                elif node in ("decode", "save"):
                    report("saving the image")
    done = handle.result()
    image = next((o for o in done.get_outputs("save") if o.content_type.startswith("image")), None)
    if image is None:
        raise RuntimeError("the job finished without an image")
    image.to_file(out)
    return out
