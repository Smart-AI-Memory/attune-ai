#!/usr/bin/env python3
"""Pre-commit hook: check help template freshness.

Warns (but does not block) when help templates are stale.
Set ATTUNE_DOCS_AUTOREGEN=1 to auto-regenerate and stage.

Usage:
    python scripts/check_docs_freshness.py

Exit codes:
    0 — all fresh, or warn-only mode
    1 — auto-regen failed (only with ATTUNE_DOCS_AUTOREGEN=1)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Check docs freshness, optionally auto-regenerate."""
    repo_root = Path(__file__).resolve().parent.parent
    scripts_dir = repo_root / "scripts"

    # Run staleness check with JSON output
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(scripts_dir / "generate_all.py"),
                "--stale",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(scripts_dir),
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return 0  # Can't check, don't block

    if result.returncode == 0:
        return 0  # All fresh

    # Parse JSON output
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return 0  # Can't parse, don't block

    count = data.get("stale_count", 0)
    types = data.get("types_affected", [])

    if count == 0:
        return 0

    autoregen = os.environ.get("ATTUNE_DOCS_AUTOREGEN", "0") == "1"

    if autoregen:
        print(f"attune: {count} stale templates, auto-regenerating...")
        try:
            subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    str(scripts_dir / "generate_all.py"),
                ],
                capture_output=True,
                timeout=120,
                cwd=str(scripts_dir),
                check=True,
            )
            # Stage regenerated files
            generated_dir = repo_root / "plugin" / "help" / "generated"
            subprocess.run(
                ["git", "add", str(generated_dir)],
                capture_output=True,
                timeout=10,
                cwd=str(repo_root),
                check=False,
            )
            print(f"attune: regenerated {len(types)} template type(s), staged.")
            return 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("attune: auto-regeneration failed", file=sys.stderr)
            return 1

    # Warn-only mode (default)
    print(f"attune: {count} help template(s) may be stale")
    if types:
        print(f"  types: {', '.join(types)}")
    print("  run: /learn maintain (or ATTUNE_DOCS_AUTOREGEN=1)")
    return 0  # Warn but don't block


if __name__ == "__main__":
    raise SystemExit(main())
