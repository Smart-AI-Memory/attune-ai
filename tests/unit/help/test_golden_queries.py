"""Benchmark resolve_topic() against hand-crafted golden queries.

Follows the attune-rag pattern: every query has an expected feature
and a difficulty bucket (easy/medium/hard). Easy queries MUST pass.
Medium queries SHOULD pass and a regression fails the test. Hard
queries document the corpus ceiling and are xfail-by-default so they
surface as XPASS if a future retriever upgrade starts handling them.

The test emits a P@1 summary on every run so you can watch the
numbers move over time.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from attune.help.manifest import load_manifest, resolve_topic

FIXTURES = Path(__file__).parent / "fixtures" / "golden_queries.yaml"


def _load_queries() -> list[dict]:
    data = yaml.safe_load(FIXTURES.read_text(encoding="utf-8"))
    return list(data["queries"])


def _manifest():
    return load_manifest(Path(__file__).resolve().parents[3] / ".help")


def _run_query(query: str) -> str | None:
    return resolve_topic(query, _manifest())


@pytest.fixture(scope="module")
def benchmark_summary():
    """Collect per-difficulty hit rates across all queries in one pass."""
    results: dict[str, dict[str, int]] = {
        "easy": {"hits": 0, "total": 0, "fails": []},
        "medium": {"hits": 0, "total": 0, "fails": []},
        "hard": {"hits": 0, "total": 0, "fails": []},
    }
    manifest = _manifest()
    for q in _load_queries():
        got = resolve_topic(q["query"], manifest)
        bucket = results[q["difficulty"]]
        bucket["total"] += 1
        if got == q["expected"]:
            bucket["hits"] += 1
        else:
            bucket["fails"].append(
                f"{q['id']} {q['query']!r} -> {got!r} (expected {q['expected']!r})"
            )
    return results


def test_p_at_1_summary(benchmark_summary, capsys):
    """Always-pass informational test — prints P@1 by difficulty."""
    lines = ["P@1 by difficulty:"]
    for bucket_name in ("easy", "medium", "hard"):
        r = benchmark_summary[bucket_name]
        if r["total"] == 0:
            continue
        rate = r["hits"] / r["total"]
        lines.append(f"  {bucket_name:6s}: {r['hits']}/{r['total']} ({rate:.0%})")
        for f in r["fails"]:
            lines.append(f"    MISS {f}")
    # Print to stdout so pytest -s shows the summary
    print("\n".join(lines))


@pytest.mark.parametrize("query", [q for q in _load_queries() if q["difficulty"] == "easy"])
def test_easy_queries_resolve(query):
    """Easy queries are synonyms of the feature name and must always pass.

    A regression here means the resolver or manifest broke — stop and fix.
    """
    got = _run_query(query["query"])
    assert got == query["expected"], (
        f"easy query {query['id']!r}: {query['query']!r} resolved to "
        f"{got!r}, expected {query['expected']!r}"
    )


@pytest.mark.parametrize("query", [q for q in _load_queries() if q["difficulty"] == "medium"])
def test_medium_queries_resolve(query):
    """Medium queries are paraphrases of descriptions and should resolve.

    A failure here is a signal to improve the feature's description or
    tags in .help/features.yaml, NOT a blocker — so we run them but
    allow xfail on a per-query basis via the skip mechanism below.
    """
    got = _run_query(query["query"])
    assert got == query["expected"], (
        f"medium query {query['id']!r}: {query['query']!r} resolved to "
        f"{got!r}, expected {query['expected']!r}. Consider adding "
        f"the query keyword as a tag on {query['expected']!r}."
    )


@pytest.mark.parametrize("query", [q for q in _load_queries() if q["difficulty"] == "hard"])
def test_hard_queries_document_ceiling(query):
    """Hard queries track the resolver ceiling — expected to fail today.

    An XPASS here is good news: the resolver has improved. When a hard
    query starts passing reliably, reclassify it to medium to make
    regressions detectable.
    """
    got = _run_query(query["query"])
    if got != query["expected"]:
        pytest.xfail(
            f"hard query {query['id']!r}: {query['query']!r} resolved "
            f"to {got!r}, expected {query['expected']!r}"
        )
    assert got == query["expected"]
