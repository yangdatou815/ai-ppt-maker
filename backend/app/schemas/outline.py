"""OutlineDoc and friends — see docs/architecture.md §3.1."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("cover_meta", mode="before")
    @classmethod
    def _drop_nulls(cls, v: Any) -> Any:
        """LLMs often emit ``{"date": null, "company": null}`` for unknown
        fields. Drop those rather than failing validation — a missing field
        is the right semantic for "the LLM didn't have this info"."""
        if isinstance(v, dict):
            return {k: str(val) for k, val in v.items() if val is not None}
        return v
