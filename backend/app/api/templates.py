"""Templates registry — scans backend/templates/<name>/layout-mapping.yaml."""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas.template import REQUIRED_LAYOUTS, TemplateInfo, TemplateLayoutMapping

log = logging.getLogger(__name__)
router = APIRouter()


_DISPLAY: dict[str, tuple[str, str, list[str]]] = {
    "executive-dark": (
        "Executive Dark",
        "深色商务风：高管汇报、产品发布。深墨蓝 + 古铜金 + 思源宋体 Heavy。",
        ["business", "dark", "premium", "keynote"],
    ),
    "minimal-light": (
        "Minimal Light",
        "极简白底：投资路演、咨询提案。米白 + 朱砂橙 + Inter / 思源黑体 Bold。",
        ["minimal", "light", "pitch", "consulting"],
    ),
    "tech-blue": (
        "Tech Blue",
        "科技蓝：技术发布、SaaS 路演。科技蓝 + 青绿 + Inter ExtraBold + JetBrains Mono。",
        ["tech", "saas", "engineering", "blue"],
    ),
}


def _load_one(template_dir: Path) -> TemplateInfo | None:
    name = template_dir.name
    mapping_file = template_dir / "layout-mapping.yaml"
    if not mapping_file.is_file():
        log.warning("Template %s missing layout-mapping.yaml — skipped", name)
        return None
    try:
        data = yaml.safe_load(mapping_file.read_text(encoding="utf-8")) or {}
        mapping = TemplateLayoutMapping.model_validate(data)
    except Exception as exc:
        log.warning("Template %s failed to parse: %s — skipped", name, exc)
        return None

    missing = [k for k in REQUIRED_LAYOUTS if k not in mapping.layouts]
    if missing:
        log.warning("Template %s missing layouts %s — skipped", name, missing)
        return None

    display_name, description, tags = _DISPLAY.get(
        name, (name.replace("-", " ").title(), "Custom template.", [])
    )
    return TemplateInfo(
        name=name,
        display_name=display_name,
        description=description,
        tags=tags,
        theme=mapping.theme,
        fonts=mapping.fonts,
        has_master=(template_dir / "master.pptx").is_file(),
        thumbnail_url=(
            f"/api/templates/{name}/thumbnail.png"
            if (template_dir / "thumbnail.png").is_file()
            else None
        ),
    )


@lru_cache(maxsize=1)
def _scan_templates() -> list[TemplateInfo]:
    settings = get_settings()
    root = settings.templates_dir
    if not root.is_dir():
        log.warning("templates_dir %s does not exist", root)
        return []
    items: list[TemplateInfo] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        info = _load_one(child)
        if info is not None:
            items.append(info)
    log.info("Loaded %d templates from %s", len(items), root)
    return items


def reset_cache() -> None:
    """Used by tests."""
    _scan_templates.cache_clear()


@router.get("/templates", response_model=list[TemplateInfo])
def list_templates() -> list[TemplateInfo]:
    return _scan_templates()


@router.get("/templates/{name}", response_model=TemplateInfo)
def get_template(name: str) -> TemplateInfo:
    for t in _scan_templates():
        if t.name == name:
            return t
    raise HTTPException(status_code=404, detail=f"template '{name}' not found")
