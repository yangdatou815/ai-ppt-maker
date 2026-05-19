"""In-memory async job queue for long-running tasks.

Design:
- Single-machine, no Redis/Celery dependency (local deployment target)
- Jobs run in a thread pool (LLM calls are blocking httpx)
- Frontend polls GET /api/jobs/{job_id} for progress
- Results expire after 1 hour
"""

from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Callable

log = logging.getLogger(__name__)

# Single shared executor — max 2 concurrent LLM jobs (7B model is memory-limited)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="job")


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobProgress:
    stage: str = ""
    detail: str = ""
    percent: int = 0


@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.PENDING
    progress: JobProgress = field(default_factory=JobProgress)
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status.value,
            "progress": {
                "stage": self.progress.stage,
                "detail": self.progress.detail,
                "percent": self.progress.percent,
            },
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


# In-memory store
_jobs: dict[str, Job] = {}
_lock = Lock()
_EXPIRE_SECONDS = 3600  # 1 hour


def _cleanup_expired() -> None:
    """Remove jobs older than expiry threshold."""
    now = time.time()
    expired = [
        jid
        for jid, j in _jobs.items()
        if j.completed_at and (now - j.completed_at) > _EXPIRE_SECONDS
    ]
    for jid in expired:
        del _jobs[jid]


def submit_job(fn: Callable[[Job], Any]) -> str:
    """Submit a job function to the thread pool.

    The function receives the Job instance and should:
    - Update job.progress periodically
    - Return the result (stored in job.result)
    - Raise on failure (stored in job.error)
    """
    with _lock:
        _cleanup_expired()
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id)
        _jobs[job_id] = job

    def _wrapper():
        job.status = JobStatus.RUNNING
        try:
            result = fn(job)
            job.result = result
            job.status = JobStatus.COMPLETED
        except Exception as exc:
            job.error = str(exc)[:500]
            job.status = JobStatus.FAILED
            log.exception("Job %s failed", job_id)
        finally:
            job.completed_at = time.time()

    _executor.submit(_wrapper)
    return job_id


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def get_job_result(job_id: str) -> Any | None:
    job = _jobs.get(job_id)
    if job and job.status == JobStatus.COMPLETED:
        return job.result
    return None
