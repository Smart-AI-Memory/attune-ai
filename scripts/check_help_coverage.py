#!/usr/bin/env python3
"""Check that every registered workflow has a `.help/features.yaml` entry.

The existing `scripts/check_help_completeness.py` catches the forward
direction (manifest features without templates). This script catches the
reverse (workflows in code without manifest entries), which is where
"shipped feature, forgot docs" drift lives.

Aliases are resolved via ALIASES below so renamed features aren't flagged.
Genuinely un-documented workflows in KNOWN_GAPS are allowlisted until
someone decides whether to manifest them or mark them internal-only.

Exit codes:
    0 — every workflow either has a manifest entry or is allowlisted
    1 — new gaps detected (a workflow exists that isn't in the manifest
        and isn't in KNOWN_GAPS)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from attune.workflows import list_workflows

# Workflow name -> canonical manifest feature name.
# Update when renaming or consolidating.
ALIASES: dict[str, str] = {
    "code-review": "code-quality",
    "test-gen": "smart-test",
}

# Workflows that do not need a manifest entry (yet). Adding to this set
# is an explicit "I acknowledge this is undocumented" — prefer adding
# a real entry to features.yaml when the feature is user-facing.
KNOWN_GAPS: set[str] = {
    "dependency-check",
    # outcome-first-fix Phase 2: CLI-only while the surface proves
    # out; help/docs surfaces are that spec's Phase 3 scope.
    "fix",
    "discovery-sweep",
    "doc-audit",
    "doc-orchestrator",
    "perf-audit",
    "rag-code-gen",
    "release-gate",
    "release-notes",
    "research-synthesis",
    "simplify-code",
    "test-audit",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _manifest_features(help_dir: Path) -> set[str]:
    manifest_path = help_dir / "features.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    return set(data.get("features", {}).keys())


def _registered_workflows() -> set[str]:
    return {w["name"] for w in list_workflows() if w.get("stages")}


def check(help_dir: Path) -> dict:
    manifest = _manifest_features(help_dir)
    workflows = _registered_workflows()

    resolved = {ALIASES.get(name, name) for name in workflows}
    covered = resolved & manifest
    uncovered = sorted(resolved - manifest - KNOWN_GAPS)
    allowlisted = sorted(resolved & KNOWN_GAPS)

    return {
        "workflow_count": len(workflows),
        "manifest_count": len(manifest),
        "covered": sorted(covered),
        "uncovered": uncovered,
        "allowlisted_gaps": allowlisted,
        "ok": not uncovered,
    }


def _render_human(result: dict) -> str:
    lines = [
        f"help coverage: {len(result['covered'])} covered, "
        f"{len(result['allowlisted_gaps'])} allowlisted, "
        f"{len(result['uncovered'])} uncovered",
    ]
    if result["uncovered"]:
        lines.append("  uncovered workflows (add to features.yaml or KNOWN_GAPS):")
        for name in result["uncovered"]:
            lines.append(f"    {name}")
    if result["allowlisted_gaps"]:
        lines.append("  allowlisted gaps (currently undocumented, explicit):")
        for name in result["allowlisted_gaps"]:
            lines.append(f"    {name}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--help-dir", default=".help")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args()

    help_dir = Path(args.help_dir)
    if not help_dir.is_absolute():
        help_dir = _repo_root() / help_dir

    result = check(help_dir)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(_render_human(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
