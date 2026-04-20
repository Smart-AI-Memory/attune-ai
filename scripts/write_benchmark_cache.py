#!/usr/bin/env python3
"""Benchmark cache writer prototype.

Runs the golden-query benchmark against the current .help/ manifest,
aggregates hits by expected feature, and writes
.help/benchmarks/latest.json in the schema the aggregator prototype
already expects. This closes the last "unknown" column in the
aggregator view.

Run:
    uv run python scripts/write_benchmark_cache.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

from attune.help.manifest import load_manifest, resolve_topic

REPO_ROOT = Path(__file__).resolve().parents[1]
HELP_DIR = REPO_ROOT / ".help"
BENCHMARK_CACHE = HELP_DIR / "benchmarks" / "latest.json"
FIXTURES = REPO_ROOT / "tests" / "unit" / "help" / "fixtures" / "golden_queries.yaml"


def _load_queries() -> list[dict]:
    data = yaml.safe_load(FIXTURES.read_text(encoding="utf-8"))
    return list(data["queries"])


def compute_p_at_1_by_feature() -> tuple[dict[str, float], int, int]:
    """Run the benchmark and aggregate P@1 per expected feature.

    Excludes 'hard' queries from the P@1 calculation — they exist to
    track the ceiling, not to regress the metric. Drill-in views still
    show them with their difficulty label.

    Returns:
        (p_at_1_by_feature, total_fixture_count, solvable_fixture_count)
    """
    manifest = load_manifest(HELP_DIR)
    queries = _load_queries()

    hits: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    solvable = 0

    for q in queries:
        if q.get("difficulty") == "hard":
            continue
        expected = q["expected"]
        totals[expected] += 1
        solvable += 1
        got = resolve_topic(q["query"], manifest)
        if got == expected:
            hits[expected] += 1

    p_at_1 = {feat: hits[feat] / totals[feat] for feat in totals}
    return p_at_1, len(queries), solvable


def write_cache() -> Path:
    """Compute scores and write the cache file. Returns the path written."""
    p_at_1, total, solvable = compute_p_at_1_by_feature()
    BENCHMARK_CACHE.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture_count": total,
        "solvable_fixture_count": solvable,
        "p_at_1_excludes_hard": True,
        "p_at_1_by_feature": p_at_1,
    }

    BENCHMARK_CACHE.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return BENCHMARK_CACHE


def main() -> int:
    path = write_cache()
    data = json.loads(path.read_text(encoding="utf-8"))
    scores: dict[str, float] = data["p_at_1_by_feature"]

    print(f"Wrote {path.relative_to(REPO_ROOT)}")
    print(
        f"  Fixtures: {data['fixture_count']} total, "
        f"{data['solvable_fixture_count']} solvable "
        f"(hard queries excluded from P@1)"
    )
    print(f"  Features scored: {len(scores)}")

    lowest = sorted(scores.items(), key=lambda kv: (kv[1], kv[0]))[:5]
    print()
    print("Lowest 5:")
    for name, score in lowest:
        print(f"  {name:<20} {score:>5.0%}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
