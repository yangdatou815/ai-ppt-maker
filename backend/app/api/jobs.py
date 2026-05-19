"""Async job status & result endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from app.jobs.queue import JobStatus, get_job, get_job_result

router = APIRouter()


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> dict:
    """Poll job status and progress."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found or expired")
    return job.to_dict()


@router.get("/jobs/{job_id}/result")
def download_job_result(job_id: str):
    """Download the generated file or JSON result once job is complete."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found or expired")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=409, detail=f"job is {job.status.value}, not completed")
    result = get_job_result(job_id)
    if result is None:
        raise HTTPException(status_code=500, detail="result missing")
    # If result is a dict with "data" key → binary file download
    if isinstance(result, dict) and "data" in result and isinstance(result["data"], bytes):
        return Response(
            content=result["data"],
            media_type=result["content_type"],
            headers=result.get("headers", {}),
        )
    # Otherwise → JSON response (e.g. outline result)
    return JSONResponse(content=result)
