"""Async job status endpoint — wired in M3 (background pptx rendering)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    raise HTTPException(status_code=404, detail=f"job {job_id} not found (jobs not implemented yet)")
