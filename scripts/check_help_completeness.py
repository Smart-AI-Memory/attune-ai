#!/usr/bin/env python3
"""Check .help/ template completeness and orphan directories.

Complements `attune-author status` (which detects hash-based staleness
on a single representative file per feature) by also checking:

    1. Each manifest feature has the full 11-kind template set
    2. No orphan template directories exist outside the manifest

Exit codes:
    0 — all features complete, no orphans
    1 — incomplete features or orphan directories found

Usage:
    python scripts/check_help_completeness.py
    python scripts/check_help_completeness.py --format=json
    python scripts/check_help_completeness.py --quiet
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

EXPECTED_KINDS = {
    "concept",
    "task",
    "reference",
    "error",
    "warning",
    "troubleshooting",
    "faq",
    "quickstart",
    "tip",
    "note",
    "comparison",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_manifest(help_dir: Path) -> set[str]:
    manifest_path = help_dir / "features.yaml"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"features.yaml not found at {manifest_path}")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    return set((data or {}).get("features", {}).keys())


def _templates_for(feature_dir: Path) -> set[str]:
    return {p.stem for p in feature_dir.glob("*.md")}


def check(help_dir: Path) -> dict:
    manifest = _load_manifest(help_dir)
    templates_dir = help_dir / "templates"
    on_disk = {p.name for p in templates_dir.iterdir() if p.is_dir()}

    orphans = sorted(on_disk - manifest)
    missing_dirs = sorted(manifest - on_disk)
    incomplete: dict[str, list[str]] = {}
    for feat in sorted(manifest & on_disk):
        present = _templates_for(templates_dir / feat)
        missing_kinds = sorted(EXPECTED_KINDS - present)
        if missing_kinds:
            incomplete[feat] = missing_kinds

    return {
        "manifest_count": len(manifest),
        "on_disk_count": len(on_disk),
        "orphans": orphans,
        "missing_dirs": missing_dirs,
        "incomplete": incomplete,
        "ok": not (orphans or missing_dirs or incomplete),
    }


def _render_human(result: dict) -> str:
    if result["ok"]:
        return (
            f"[OK] .help complete — {result['manifest_count']} features, "
            f"all 11 kinds each, no orphans"
        )
    lines = [
        f"[ISSUES] .help completeness check "
        f"({result['manifest_count']} manifest, {result['on_disk_count']} on disk):"
    ]
    if result["orphans"]:
        lines.append(f"  orphan dirs (not in manifest): {', '.join(result['orphans'])}")
    if result["missing_dirs"]:
        lines.append(
            f"  manifest features missing templates dir: " f"{', '.join(result['missing_dirs'])}"
        )
    for feat, kinds in result["incomplete"].items():
        lines.append(f"  {feat}: missing {', '.join(kinds)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--help-dir", default=".help", help="Path to .help/ directory")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print if issues found",
    )
    args = parser.parse_args()

    help_dir = Path(args.help_dir)
    if not help_dir.is_absolute():
        help_dir = _repo_root() / help_dir

    result = check(help_dir)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif result["ok"] and args.quiet:
        pass
    else:
        print(_render_human(result))

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
