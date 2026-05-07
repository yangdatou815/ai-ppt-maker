"""OutlineDoc and friends — see docs/architecture.md §3.1."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Bullet(BaseModel):
    text: str
    note: str | None = None
    emphasis: bool = False


class TableData(BaseModel):
    headers: list[str]
    rows: list[list[str]]
    caption: str | None = None


class ImageRef(BaseModel):
    file_id: str
    caption: str | None = None


LayoutHint = Literal["content-bullets", "content-image", "content-table"]


class Section(BaseModel):
    heading: str
    bullets: list[Bullet] = Field(default_factory=list)
    image: ImageRef | None = None
    table: TableData | None = None
    speaker_notes: str | None = None
    layout_hint: LayoutHint | None = None


class OutlineDoc(BaseModel):
    title: str
    subtitle: str | None = None
    language: Literal["zh", "en", "auto"] = "auto"
    sections: list[Section]
    cover_meta: dict[str, str] = Field(default_factory=dict)
