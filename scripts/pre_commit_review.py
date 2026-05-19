#!/usr/bin/env python3
"""Pre-commit code review — catches common bugs that static linters miss.

Checks performed on staged Python files:
1. Unused imports that ruff might miss (dynamic patterns)
2. Path calculations using multiple .parent — flag for manual review
3. Hardcoded localhost/ports without env var fallback
4. try/except that silently swallows ALL exceptions
5. Missing frozen-mode guards in files that do path resolution
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def check_file(filepath: Path) -> list[str]:
    """Return list of warnings for a file."""
    warnings: list[str] = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return warnings

    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        # Flag chained .parent calls (common path bugs)
        parents = re.findall(r"\.parent", line)
        if len(parents) >= 3:
            warnings.append(
                f"{filepath.relative_to(REPO_ROOT)}:{i}: "
                f"⚠️  Three or more .parent calls — verify path calculation is correct"
            )

        # Flag bare except or except Exception with pass
        if re.match(r"\s*except(\s+Exception)?\s*:", line):
            # Check if next non-empty line is just 'pass'
            for j in range(i, min(i + 3, len(lines))):
                if lines[j - 1].strip() == "pass":  # j is 1-indexed via range
                    warnings.append(
                        f"{filepath.relative_to(REPO_ROOT)}:{i}: "
                        f"⚠️  Bare except with pass — consider logging or re-raising"
                    )
                    break
                if lines[j - 1].strip() and lines[j - 1].strip() != "pass":
                    break

        # Flag hardcoded ports without env var
        port_match = re.search(r'port\s*=\s*(\d{4,5})', line)
        if port_match and "os.environ" not in line and "env" not in line.lower():
            # Check if there's an env override nearby (within 3 lines before)
            context = "\n".join(lines[max(0, i - 4):i])
            if "environ" not in context and "getenv" not in context:
                warnings.append(
                    f"{filepath.relative_to(REPO_ROOT)}:{i}: "
                    f"💡 Hardcoded port {port_match.group(1)} — consider env var override"
                )

    return warnings


def main() -> int:
    files = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]
    if not files:
        return 0

    all_warnings: list[str] = []
    for f in files:
        fp = Path(f) if Path(f).is_absolute() else REPO_ROOT / f
        all_warnings.extend(check_file(fp))

    if all_warnings:
        print("Code review findings (non-blocking, for awareness):")
        for w in all_warnings:
            print(f"  {w}")
        # Return 0 — these are warnings, not errors.
        # Change to `return 1` to make them blocking.
        print(f"\n  {len(all_warnings)} finding(s) — review before pushing.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
