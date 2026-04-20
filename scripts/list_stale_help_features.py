#!/usr/bin/env python3
"""Print names of stale .help/ features, one per line.

Uses `attune_author.check_staleness` to avoid parsing the
`attune-author status` markdown table. Exit code is always 0 —
empty stdout means no stale features.

Usage:
    python scripts/list_stale_help_features.py
    python scripts/list_stale_help_features.py --help-dir .help --project-root .
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from attune_author import check_staleness, load_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--help-dir", default=".help")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    help_dir = Path(args.help_dir)
    project_root = Path(args.project_root)
    manifest = load_manifest(help_dir)
    report = check_staleness(manifest, help_dir, project_root)
    for name in report.stale_features:
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
