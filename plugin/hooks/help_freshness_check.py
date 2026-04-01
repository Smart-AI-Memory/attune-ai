"""SessionStart hook: check help template freshness.

Reads source_manifest.json and checks if it's older than
24 hours. If so, runs a quick staleness check and reports
the count of stale templates.

Must complete under 500ms. Exits 0 always (informational).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

_MAX_AGE_SECONDS = 24 * 3600  # 24 hours


def _hash_file(path: Path) -> str:
    """SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Check help template freshness on session start."""
    # Find the plugin root (this script lives in hooks/)
    hook_dir = Path(__file__).resolve().parent
    plugin_root = hook_dir.parent
    generated_dir = plugin_root / "help" / "generated"
    manifest_path = generated_dir / "source_manifest.json"

    if not manifest_path.exists():
        return

    # Check manifest age
    try:
        mtime = manifest_path.stat().st_mtime
        age = time.time() - mtime
        if age < _MAX_AGE_SECONDS:
            return  # Fresh enough
    except OSError:
        return

    # Quick staleness check (no subprocess, just hash comparison)
    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8"),
        )
    except (json.JSONDecodeError, OSError):
        return

    # Walk up to find repo root (look for .git or pyproject.toml)
    repo_root = plugin_root.parent
    if not (repo_root / "pyproject.toml").exists():
        repo_root = repo_root.parent

    # Sample up to 50 entries to stay under 500ms budget
    stale_count = 0
    checked = 0
    max_checks = 50

    for entry in list(manifest.values())[:max_checks]:
        source_rel = entry.get("source", "")
        if not source_rel:
            continue
        source_path = repo_root / source_rel
        if not source_path.exists():
            stale_count += 1
            checked += 1
            continue
        try:
            if _hash_file(source_path) != entry.get("hash", ""):
                stale_count += 1
        except OSError:
            pass
        checked += 1

    if stale_count > 0:
        print(
            f"attune: {stale_count}/{checked} help template(s) "
            f"may be stale. Run /learn maintain to update.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
