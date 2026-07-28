#!/usr/bin/env python3
"""Print names of stale .help/ features, one per line.

Uses `attune.authoring.staleness.check_staleness` (the hash-drift
algorithm absorbed from attune-author). Exit code is always 0 —
empty stdout means no stale features.

Manual/single-sourced features with no ``files:`` globs have no
source to hash — they are untracked (N/A), not stale, and are
excluded from the check (spec attune-author-consolidation, D9).

Usage:
    python scripts/list_stale_help_features.py
    python scripts/list_stale_help_features.py --help-dir .help --project-root .
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from attune.authoring.manifest import load_manifest
from attune.authoring.staleness import check_staleness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--help-dir", default=".help")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    help_dir = Path(args.help_dir)
    project_root = Path(args.project_root)
    manifest = load_manifest(help_dir)
    tracked = [name for name, feat in manifest.features.items() if feat.files]
    if not tracked:
        return 0
    report = check_staleness(manifest, help_dir, project_root, features=tracked)
    for name in report.stale_features:
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
