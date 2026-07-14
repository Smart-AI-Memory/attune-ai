#!/usr/bin/env python
"""SessionStart hook: surface .help/ freshness and completeness issues.

Runs quickly (<2s) and prints a short summary to stdout when any of:

    1. Manifest features have missing template kinds (< 11)
    2. Template directories exist that aren't in the manifest (orphans)
    3. Source files newer than their feature's concept.md (coarse staleness hint)

Output is informational only. Exit code is always 0 so the session starts
normally.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_manifest(help_dir: Path) -> dict[str, list[str]]:
    manifest_path = help_dir / "features.yaml"
    if not manifest_path.is_file():
        return {}
    text = manifest_path.read_text(encoding="utf-8")
    features: dict[str, list[str]] = {}
    current: str | None = None
    collecting_files = False
    for raw in text.splitlines():
        feat_match = re.match(r"^  ([a-z][a-z0-9-]*):\s*$", raw)
        if feat_match:
            current = feat_match.group(1)
            features[current] = []
            collecting_files = False
            continue
        if current is None:
            continue
        if raw.strip().startswith("files:"):
            collecting_files = True
            continue
        if collecting_files:
            item = re.match(r"^      - (.+)$", raw)
            if item:
                features[current].append(item.group(1).strip())
            elif raw and not raw.startswith("      "):
                collecting_files = False
    return features


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


def _coarse_staleness(
    manifest: dict[str, list[str]], repo_root: Path, templates_dir: Path
) -> list[str]:
    stale: list[str] = []
    for feature, globs in manifest.items():
        concept = templates_dir / feature / "concept.md"
        if not concept.is_file():
            continue
        concept_mtime = concept.stat().st_mtime
        newest_src = 0.0
        for pattern in globs:
            for path in repo_root.glob(pattern):
                if path.is_file():
                    newest_src = max(newest_src, path.stat().st_mtime)
        if newest_src > concept_mtime:
            stale.append(feature)
    return stale


def main() -> int:
    repo_root = _repo_root()
    help_dir = repo_root / ".help"
    templates_dir = help_dir / "templates"

    if not help_dir.is_dir() or not templates_dir.is_dir():
        return 0

    manifest = _load_manifest(help_dir)
    manifest_names = set(manifest)
    on_disk = {p.name for p in templates_dir.iterdir() if p.is_dir()}

    orphans = sorted(on_disk - manifest_names)
    incomplete: list[str] = []
    for feat in sorted(manifest_names & on_disk):
        present = {p.stem for p in (templates_dir / feat).glob("*.md")}
        if EXPECTED_KINDS - present:
            incomplete.append(feat)

    stale = _coarse_staleness(manifest, repo_root, templates_dir)

    if not (orphans or incomplete or stale):
        return 0

    bits = []
    if stale:
        bits.append(f"{len(stale)} stale")
    if incomplete:
        bits.append(f"{len(incomplete)} incomplete")
    if orphans:
        bits.append(f"{len(orphans)} orphan")
    print(f"[.help] {', '.join(bits)} — run `attune-author status` or the")
    print("        weekly help-freshness workflow to refresh.")

    return 0


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        sys.exit(0)
