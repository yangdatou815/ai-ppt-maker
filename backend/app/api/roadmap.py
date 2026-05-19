"""GET /api/roadmap — project bird's-eye view fed from backend/roadmap.yaml.

The view is intentionally read-only; the YAML file is the single source of
truth. Hand-edit the file when scope changes, then redeploy.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from app.schemas.roadmap import (
    RoadmapDoc,
    RoadmapPhase,
    RoadmapStats,
)

router = APIRouter()
log = logging.getLogger(__name__)

# Resolved at import: <repo_root>/backend/roadmap.yaml
_DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent / "roadmap.yaml"


def _compute_stats(phases: list[RoadmapPhase]) -> RoadmapStats:
    total = done = in_progress = planned = 0
    for ph in phases:
        for ms in ph.milestones:
            for it in ms.items:
                total += 1
                if it.status == "done":
                    done += 1
                elif it.status == "in-progress":
                    in_progress += 1
                else:
                    planned += 1
    pct = (done / total * 100.0) if total else 0.0
    return RoadmapStats(
        total=total,
        done=done,
        in_progress=in_progress,
        planned=planned,
        done_pct=round(pct, 1),
    )


@lru_cache(maxsize=1)
def _load_roadmap_cached(path_str: str) -> RoadmapDoc:
    path = Path(path_str)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    phases = [RoadmapPhase.model_validate(p) for p in raw.get("phases", [])]
    return RoadmapDoc(phases=phases, stats=_compute_stats(phases))


def load_roadmap(path: Path | None = None) -> RoadmapDoc:
    """Load + validate roadmap. Cached by absolute path string."""
    target = (path or _DEFAULT_PATH).resolve()
    return _load_roadmap_cached(str(target))


@router.get("/roadmap", response_model=RoadmapDoc)
def get_roadmap() -> RoadmapDoc:
    if not _DEFAULT_PATH.is_file():
        log.warning("roadmap.yaml not found at %s", _DEFAULT_PATH)
        raise HTTPException(status_code=404, detail="roadmap.yaml not found")
    try:
        return load_roadmap()
    except (yaml.YAMLError, ValueError) as exc:
        log.error("roadmap.yaml is invalid: %s", exc)
        raise HTTPException(status_code=500, detail=f"roadmap.yaml invalid: {exc}") from exc
