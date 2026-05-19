"""Roadmap schemas — feeds the in-app project bird's-eye view."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ItemStatus = Literal["done", "in-progress", "planned"]


class RoadmapItem(BaseModel):
    name: str
    status: ItemStatus = "planned"


class RoadmapMilestone(BaseModel):
    id: str
    name: str
    summary: str | None = None
    items: list[RoadmapItem] = Field(default_factory=list)


class RoadmapPhase(BaseModel):
    id: str
    name: str
    summary: str | None = None
    milestones: list[RoadmapMilestone] = Field(default_factory=list)


class RoadmapStats(BaseModel):
    total: int
    done: int
    in_progress: int
    planned: int
    done_pct: float


class RoadmapDoc(BaseModel):
    phases: list[RoadmapPhase]
    stats: RoadmapStats
