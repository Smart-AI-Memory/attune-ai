#!/usr/bin/env python3
"""Help-system maintainer aggregator.

Merges three data sources into one view:

  1. Completeness — count of template kinds per feature vs expected 11
  2. Staleness    — attune.authoring.staleness.check_staleness report
  3. Benchmarks   — cached P@1 from .help/benchmarks/latest.json

Usage:
    uv run python scripts/help_aggregator_prototype.py
    uv run python scripts/help_aggregator_prototype.py --attention
    uv run python scripts/help_aggregator_prototype.py --drill-in bug-predict
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from attune.authoring.manifest import load_manifest
from attune.authoring.staleness import check_staleness
from attune.help.manifest import load_manifest as _load_help_manifest
from attune.help.manifest import resolve_topic

EXPECTED_KINDS: frozenset[str] = frozenset(
    {
        "comparison",
        "concept",
        "error",
        "faq",
        "note",
        "quickstart",
        "reference",
        "task",
        "tip",
        "troubleshooting",
        "warning",
    }
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HELP_DIR = REPO_ROOT / ".help"
TEMPLATE_DIR = HELP_DIR / "templates"
BENCHMARK_CACHE = HELP_DIR / "benchmarks" / "latest.json"
FIXTURES = REPO_ROOT / "tests" / "unit" / "help" / "fixtures" / "golden_queries.yaml"


@dataclass
class FeatureRow:
    """Unified view of one feature across the three data sources."""

    name: str
    kinds_present: frozenset[str]
    is_stale: bool
    stored_hash: str | None
    current_hash: str
    matched_files: list[str]
    p_at_1: float | None

    @property
    def kind_count(self) -> int:
        return len(self.kinds_present)

    @property
    def is_complete(self) -> bool:
        return self.kinds_present == EXPECTED_KINDS

    @property
    def missing_kinds(self) -> frozenset[str]:
        return EXPECTED_KINDS - self.kinds_present

    @property
    def needs_attention(self) -> bool:
        if self.is_stale or not self.is_complete:
            return True
        if self.p_at_1 is not None and self.p_at_1 < 0.70:
            return True
        return False

    @property
    def severity(self) -> int:
        """Lower = more urgent. 0=stale, 1=incomplete, 2=low P@1, 3=ok."""
        if self.is_stale:
            return 0
        if not self.is_complete:
            return 1
        if self.p_at_1 is not None and self.p_at_1 < 0.70:
            return 2
        return 3


def _scan_kinds(feature_dir: Path) -> frozenset[str]:
    if not feature_dir.is_dir():
        return frozenset()
    return frozenset(p.stem for p in feature_dir.glob("*.md"))


def _load_benchmarks() -> dict[str, float]:
    """Load cached P@1 per feature. Returns {} if cache missing or malformed."""
    if not BENCHMARK_CACHE.is_file():
        return {}
    try:
        data = json.loads(BENCHMARK_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    result = data.get("p_at_1_by_feature", {})
    if not isinstance(result, dict):
        return {}
    return {k: float(v) for k, v in result.items() if isinstance(v, (int, float))}


def _load_queries() -> list[dict]:
    if not FIXTURES.is_file():
        return []
    data = yaml.safe_load(FIXTURES.read_text(encoding="utf-8"))
    return list(data.get("queries", []))


def aggregate() -> list[FeatureRow]:
    """Build the unified FeatureRow list by merging all three sources."""
    manifest = load_manifest(HELP_DIR)
    # Manual/single-sourced features (no ``files:`` globs) have no
    # source to hash — untracked (N/A), not stale (consolidation D9).
    tracked = {name for name, feat in manifest.features.items() if feat.files}
    entries = (
        check_staleness(manifest, HELP_DIR, REPO_ROOT, features=sorted(tracked)).entries
        if tracked
        else []
    )
    benchmarks = _load_benchmarks()

    by_name = {e.feature: e for e in entries}
    rows: list[FeatureRow] = []

    for name in manifest.features:
        entry = by_name.get(name)
        kinds = _scan_kinds(TEMPLATE_DIR / name)
        rows.append(
            FeatureRow(
                name=name,
                kinds_present=kinds,
                is_stale=entry.is_stale if entry else name in tracked,
                stored_hash=entry.stored_hash if entry else None,
                current_hash=entry.current_hash if entry else "",
                matched_files=list(entry.matched_files) if entry else [],
                p_at_1=benchmarks.get(name),
            )
        )

    return rows


def _fmt_p1(p: float | None) -> str:
    return "  -  " if p is None else f"{p:>4.0%}"


def print_table(rows: list[FeatureRow]) -> None:
    """Severity-sorted table. No filtering (caller already did that)."""
    rows_sorted = sorted(rows, key=lambda r: (r.severity, r.name))

    width = max((len(r.name) for r in rows_sorted), default=8)
    header = f"{'FEATURE':<{width}}  {'KINDS':>6}  {'STATE':<7}  {'P@1':>5}"
    print(header)
    print("-" * len(header))

    for r in rows_sorted:
        kinds_str = f"{r.kind_count}/11"
        state = "STALE" if r.is_stale else ("partial" if not r.is_complete else "ok")
        print(f"{r.name:<{width}}  " f"{kinds_str:>6}  " f"{state:<7}  " f"{_fmt_p1(r.p_at_1):>5}")


def print_summary(all_rows: list[FeatureRow]) -> None:
    """Ecosystem-wide summary footer."""
    stale = sum(1 for r in all_rows if r.is_stale)
    incomplete = sum(1 for r in all_rows if not r.is_stale and not r.is_complete)
    missing_bench = sum(1 for r in all_rows if r.p_at_1 is None)
    print()
    print(
        f"{len(all_rows)} features  |  "
        f"{stale} stale  |  "
        f"{incomplete} incomplete  |  "
        f"{missing_bench} without benchmark data"
    )


def drill_in(feature_name: str) -> int:
    """Print per-template detail + source files + golden-query hits for one feature."""
    author_manifest = load_manifest(HELP_DIR)
    feat = author_manifest.features.get(feature_name)
    if not feat:
        print(f"Feature {feature_name!r} not in manifest.")
        print(f"Known features: {', '.join(sorted(author_manifest.features))}")
        return 1

    entry = None
    if feat.files:
        report = check_staleness(author_manifest, HELP_DIR, REPO_ROOT, features=[feature_name])
        entry = report.entries[0] if report.entries else None
    p_at_1 = _load_benchmarks().get(feature_name)

    print(f"# {feature_name}")
    print(f"  description: {feat.description}")
    if p_at_1 is not None:
        print(f"  P@1: {p_at_1:.0%}")
    else:
        print("  P@1: no benchmark data")
    if entry:
        print(f"  staleness: {'STALE' if entry.is_stale else 'ok'}")
    else:
        print("  staleness: untracked (no files: globs)")
    print()

    print("## Templates")
    feat_dir = TEMPLATE_DIR / feature_name
    kinds_on_disk = {p.stem: p for p in feat_dir.glob("*.md")} if feat_dir.is_dir() else {}
    for kind in sorted(EXPECTED_KINDS):
        path = kinds_on_disk.get(kind)
        if path:
            mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
            rel = path.relative_to(REPO_ROOT)
            print(f"  {kind:<18} {mtime}  {rel}")
        else:
            print(f"  {kind:<18} MISSING")
    print()

    if entry and entry.matched_files:
        print("## Source files (drive staleness)")
        for f in entry.matched_files:
            print(f"  {f}")
        print()

    queries = [q for q in _load_queries() if q.get("expected") == feature_name]
    if queries:
        print("## Golden queries")
        help_manifest = _load_help_manifest(HELP_DIR)
        hits = 0
        for q in queries:
            got = resolve_topic(q["query"], help_manifest)
            hit = got == feature_name
            if hit:
                hits += 1
            marker = "hit " if hit else "MISS"
            diff_tag = f" [{q.get('difficulty', '?')}]"
            got_str = f" -> {got!r}" if not hit else ""
            print(f"  {marker}  {q.get('id', '?'):<10} {q['query']!r}{diff_tag}{got_str}")
        print()
        print(f"  {hits}/{len(queries)} hit ({hits / len(queries):.0%})")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Help-system maintainer dashboard.")
    parser.add_argument(
        "--attention",
        action="store_true",
        help="Only show features needing work (stale, incomplete, or P@1 < 70%%).",
    )
    parser.add_argument(
        "--drill-in",
        metavar="FEATURE",
        help="Show per-template detail for one feature.",
    )
    args = parser.parse_args()

    if args.drill_in:
        return drill_in(args.drill_in)

    rows = aggregate()
    filtered = [r for r in rows if r.needs_attention] if args.attention else rows

    if not filtered:
        print("All features ok. Nothing needs attention.")
    else:
        print_table(filtered)

    print_summary(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
