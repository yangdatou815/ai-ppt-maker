#!/usr/bin/env python3
"""Validate that paths referenced in PyInstaller spec actually exist.

Catches the class of bug where REPO_ROOT calculation is wrong and
launcher.py / frontend/dist / backend/templates can't be found at build time.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors: list[str] = []

    # Check launcher exists
    launcher = REPO_ROOT / "backend" / "launcher.py"
    if not launcher.is_file():
        errors.append(f"launcher.py not found: {launcher}")

    # Check spec file's REPO_ROOT logic
    spec_file = REPO_ROOT / "scripts" / "ai-ppt-maker.spec"
    if spec_file.is_file():
        content = spec_file.read_text()
        # The spec should use Path(SPECPATH).parent (one level) since spec is in scripts/
        if "Path(SPECPATH).parent.parent" in content:
            errors.append(
                "spec uses .parent.parent for REPO_ROOT — this is wrong when "
                "spec is in scripts/. Use Path(SPECPATH).parent instead."
            )

    # Check templates dir exists
    templates = REPO_ROOT / "backend" / "templates"
    if not templates.is_dir():
        errors.append(f"templates dir not found: {templates}")

    # Check that frozen-mode path logic exists in main.py
    main_py = REPO_ROOT / "backend" / "app" / "main.py"
    if main_py.is_file():
        main_content = main_py.read_text()
        if "sys.frozen" not in main_content and "getattr(sys" not in main_content:
            errors.append(
                "backend/app/main.py doesn't handle frozen mode — "
                "frontend/dist won't be found in PyInstaller bundle"
            )

    if errors:
        print("PyInstaller spec path validation FAILED:")
        for e in errors:
            print(f"  ✗ {e}")
        return 1

    print("PyInstaller spec paths: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
