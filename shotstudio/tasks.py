"""Short jobs the page waits on with a progress bar (making a location image): what stage they are
at, how far, and roughly how long is left. Renders have their own, longer-lived jobs (render.py)."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from .render import explain


@dataclass
class Task:
    id: str
    status: str = "running"        # running, succeeded or failed
    stage: str = "starting"
    step: int = 0                  # within the stage that counts steps (sampling)
    steps: int = 0
    started: float = field(default_factory=time.time)
    stepping_since: float | None = None
    result: Any = None
    error: str | None = None

    def progress(self, stage: str, step: int = 0, steps: int = 0) -> None:
        """Report where the job is; a stage with steps also gives the time left."""
        self.stage = stage
        if steps:
            if self.stepping_since is None or step < self.step:
                self.stepping_since = time.time()
            self.step, self.steps = step, steps

    def public(self) -> dict:
        left = None
        if self.steps and self.step > 0 and self.stepping_since:
            per_step = (time.time() - self.stepping_since) / self.step
            left = round(per_step * (self.steps - self.step))
        done = self.status == "succeeded"
        return {"id": self.id, "status": self.status, "stage": self.stage, "elapsed": round(time.time() - self.started),
                "progress": 1.0 if done else round(self.step / self.steps, 2) if self.steps else 0.0,
                "seconds_left": left, "result": self.result, "error": self.error}


TASKS: dict[str, Task] = {}


def start(work: Callable[[Task], Any], failure: str) -> Task:
    """Run `work(task)` in the background; its return value is the task's result."""
    task = Task(id=uuid.uuid4().hex[:12])
    TASKS[task.id] = task

    def run() -> None:
        try:
            task.result = work(task)
            task.status, task.stage = "succeeded", "done"
        except Exception as exc:  # shown on the page
            task.status, task.error = "failed", f"{failure}. {explain(exc)}"

    threading.Thread(target=run, daemon=True).start()
    return task
