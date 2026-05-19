"""Template metadata schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LayoutEntry(BaseModel):
    index: int
    placeholders: dict[str, int] = Field(default_factory=dict)


class TemplateLayoutMapping(BaseModel):
    layouts: dict[str, LayoutEntry]
    theme: dict[str, str] = Field(default_factory=dict)
    fonts: dict[str, str] = Field(default_factory=dict)


REQUIRED_LAYOUTS = (
    "cover",
    "toc",
    "section-divider",
    "content-bullets",
    "content-image",
    "content-table",
    "closing",
)


class TemplateInfo(BaseModel):
    """What `/api/templates` returns to the frontend."""

    name: str
    display_name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    theme: dict[str, str] = Field(default_factory=dict)
    fonts: dict[str, str] = Field(default_factory=dict)
    has_master: bool = False
    thumbnail_url: str | None = None
