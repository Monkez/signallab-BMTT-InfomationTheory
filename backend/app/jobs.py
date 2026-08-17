from __future__ import annotations

import threading
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from .engine import run_simulation
from .models import SimulationRequest


class JobManager:
    def __init__(self):
        self.jobs: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.cancel_events: dict[str, threading.Event] = {}

    def create(self, request: SimulationRequest) -> str:
        job_id = uuid.uuid4().hex
        event = threading.Event()
        with self.lock:
            self.cancel_events[job_id] = event
            self.jobs[job_id] = {
                "id": job_id,
                "status": "queued",
                "progress": 0,
                "completed_trials": 0,
                "trials": request.config.trials,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        thread = threading.Thread(target=self._run, args=(job_id, request, event), daemon=True)
        thread.start()
        return job_id

    def _run(self, job_id: str, request: SimulationRequest, event: threading.Event):
        self._update(job_id, status="running")

        def progress(data):
            self._update(job_id, **data, progress=data["completed_trials"] / data["trials"])

        try:
            result = run_simulation(request.graph, request.config, progress, event.is_set)
            self._update(job_id, status="cancelled" if result["cancelled"] else "completed", progress=1 if not result["cancelled"] else self.jobs[job_id]["progress"], result=result)
        except Exception as exc:
            self._update(job_id, status="failed", error=str(exc), detail=traceback.format_exc(limit=4))

    def _update(self, job_id: str, **values):
        with self.lock:
            self.jobs[job_id].update(values)

    def get(self, job_id: str):
        with self.lock:
            job = self.jobs.get(job_id)
            return dict(job) if job else None

    def cancel(self, job_id: str) -> bool:
        event = self.cancel_events.get(job_id)
        if not event:
            return False
        event.set()
        return True


manager = JobManager()

