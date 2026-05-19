"""
PyInstaller spec for ai-ppt-maker.

Bundles:
- FastAPI backend (all app.* modules)
- frontend/dist/ (pre-built SPA)
- backend/templates/ (PPTX master templates)
- Launcher that starts uvicorn

Usage:
    cd ai-ppt-maker
    npm run build --prefix frontend   # build SPA first
    pyinstaller scripts/ai-ppt-maker.spec
"""

import os
from pathlib import Path

block_cipher = None

REPO_ROOT = Path(SPECPATH).parent
BACKEND = REPO_ROOT / "backend"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
TEMPLATES = BACKEND / "templates"

# Collect data files
datas = []

# Frontend dist
if FRONTEND_DIST.is_dir():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))

# PPTX templates
if TEMPLATES.is_dir():
    datas.append((str(TEMPLATES), "backend/templates"))

# Hidden imports for FastAPI + dynamic modules
hiddenimports = [
    "app",
    "app.api",
    "app.api.debug",
    "app.api.generate",
    "app.api.jobs",
    "app.api.outline",
    "app.api.roadmap",
    "app.api.templates",
    "app.api.upload",
    "app.config",
    "app.logging_setup",
    "app.ollama_health",
    "app.outline",
    "app.outline.classify_fallback",
    "app.outline.classify_prompts",
    "app.outline.fallback",
    "app.outline.llm_client",
    "app.outline.prompts",
    "app.outline.repair",
    "app.outline.summarizer",
    "app.render",
    "app.render.pptx_renderer",
    "app.schemas",
    "app.schemas.classify",
    "app.schemas.outline",
    "app.jobs",
    "app.jobs.queue",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "multipart",
    "pptx",
    "httpx",
    "pydantic",
    "pydantic_settings",
]

a = Analysis(
    [str(BACKEND / "launcher.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ai-ppt-maker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ai-ppt-maker",
)
