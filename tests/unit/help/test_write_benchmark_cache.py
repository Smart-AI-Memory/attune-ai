"""Tests for scripts/write_benchmark_cache.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "write_benchmark_cache.py"


@pytest.fixture
def bench():
    """Load the benchmark writer script as a module."""
    spec = importlib.util.spec_from_file_location("_write_benchmark_cache", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_write_benchmark_cache"] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("_write_benchmark_cache", None)


def _write_queries_yaml(path: Path, queries: list[dict]) -> None:
    lines = ["queries:"]
    for q in queries:
        lines.append(f"  - id: {q['id']}")
        lines.append(f"    query: {q['query']}")
        lines.append(f"    expected: {q['expected']}")
        if "difficulty" in q:
            lines.append(f"    difficulty: {q['difficulty']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestLoadQueries:
    def test_returns_list_from_fixture(self, bench, tmp_path, monkeypatch):
        fixtures = tmp_path / "queries.yaml"
        _write_queries_yaml(
            fixtures,
            [
                {"id": "q1", "query": "a", "expected": "alpha"},
                {"id": "q2", "query": "b", "expected": "beta"},
            ],
        )
        monkeypatch.setattr(bench, "FIXTURES", fixtures)
        result = bench._load_queries()
        assert len(result) == 2
        assert result[0]["id"] == "q1"


class TestComputePAt1ByFeature:
    def test_perfect_score(self, bench, tmp_path, monkeypatch):
        """All queries hit — every feature scores 1.0."""
        fixtures = tmp_path / "queries.yaml"
        _write_queries_yaml(
            fixtures,
            [
                {"id": "q1", "query": "find bug", "expected": "alpha"},
                {"id": "q2", "query": "review code", "expected": "beta"},
            ],
        )
        monkeypatch.setattr(bench, "FIXTURES", fixtures)
        monkeypatch.setattr(bench, "load_manifest", lambda _d: object())
        # resolve_topic always returns the expected feature -> perfect score
        monkeypatch.setattr(
            bench, "resolve_topic", lambda q, m: {"find bug": "alpha", "review code": "beta"}[q]
        )

        scores, total, solvable = bench.compute_p_at_1_by_feature()

        assert scores == {"alpha": 1.0, "beta": 1.0}
        assert total == 2
        assert solvable == 2

    def test_hard_queries_excluded(self, bench, tmp_path, monkeypatch):
        """Hard queries count in 'total' but not in P@1 or 'solvable'."""
        fixtures = tmp_path / "queries.yaml"
        _write_queries_yaml(
            fixtures,
            [
                {"id": "e1", "query": "easy", "expected": "alpha", "difficulty": "easy"},
                {"id": "h1", "query": "hard", "expected": "alpha", "difficulty": "hard"},
            ],
        )
        monkeypatch.setattr(bench, "FIXTURES", fixtures)
        monkeypatch.setattr(bench, "load_manifest", lambda _d: object())
        monkeypatch.setattr(bench, "resolve_topic", lambda q, m: "alpha")

        scores, total, solvable = bench.compute_p_at_1_by_feature()

        assert scores == {"alpha": 1.0}
        assert total == 2
        assert solvable == 1

    def test_partial_hit_rate(self, bench, tmp_path, monkeypatch):
        """Two queries for same feature, one hits -> score 0.5."""
        fixtures = tmp_path / "queries.yaml"
        _write_queries_yaml(
            fixtures,
            [
                {"id": "q1", "query": "match", "expected": "alpha"},
                {"id": "q2", "query": "miss", "expected": "alpha"},
            ],
        )
        monkeypatch.setattr(bench, "FIXTURES", fixtures)
        monkeypatch.setattr(bench, "load_manifest", lambda _d: object())
        monkeypatch.setattr(
            bench, "resolve_topic", lambda q, m: "alpha" if q == "match" else "beta"
        )

        scores, total, solvable = bench.compute_p_at_1_by_feature()

        assert scores == {"alpha": 0.5}
        assert total == 2
        assert solvable == 2

    def test_empty_fixtures_returns_empty(self, bench, tmp_path, monkeypatch):
        fixtures = tmp_path / "queries.yaml"
        fixtures.write_text("queries: []\n", encoding="utf-8")
        monkeypatch.setattr(bench, "FIXTURES", fixtures)
        monkeypatch.setattr(bench, "load_manifest", lambda _d: object())
        monkeypatch.setattr(bench, "resolve_topic", lambda q, m: None)

        scores, total, solvable = bench.compute_p_at_1_by_feature()
        assert scores == {}
        assert total == 0
        assert solvable == 0


class TestWriteCache:
    def test_writes_expected_schema(self, bench, tmp_path, monkeypatch):
        cache = tmp_path / "benchmarks" / "latest.json"
        monkeypatch.setattr(bench, "BENCHMARK_CACHE", cache)
        monkeypatch.setattr(
            bench,
            "compute_p_at_1_by_feature",
            lambda: ({"alpha": 0.9, "beta": 0.75}, 12, 10),
        )

        path = bench.write_cache()

        assert path == cache
        assert cache.exists()
        payload = json.loads(cache.read_text(encoding="utf-8"))
        assert payload["p_at_1_by_feature"] == {"alpha": 0.9, "beta": 0.75}
        assert payload["fixture_count"] == 12
        assert payload["solvable_fixture_count"] == 10
        assert payload["p_at_1_excludes_hard"] is True
        assert "generated_at" in payload

    def test_creates_parent_directory(self, bench, tmp_path, monkeypatch):
        """write_cache should mkdir the benchmarks dir if missing."""
        cache = tmp_path / "new-nested-dir" / "latest.json"
        assert not cache.parent.exists()
        monkeypatch.setattr(bench, "BENCHMARK_CACHE", cache)
        monkeypatch.setattr(
            bench,
            "compute_p_at_1_by_feature",
            lambda: ({}, 0, 0),
        )

        bench.write_cache()

        assert cache.parent.is_dir()
        assert cache.exists()

    def test_payload_is_sorted(self, bench, tmp_path, monkeypatch):
        """JSON output uses sort_keys=True — top-level keys should be sorted."""
        cache = tmp_path / "latest.json"
        monkeypatch.setattr(bench, "BENCHMARK_CACHE", cache)
        monkeypatch.setattr(
            bench,
            "compute_p_at_1_by_feature",
            lambda: ({"zebra": 0.1, "alpha": 1.0}, 2, 2),
        )

        bench.write_cache()
        text = cache.read_text(encoding="utf-8")

        # Top-level keys should appear alphabetically
        assert text.index('"fixture_count"') < text.index('"generated_at"')
        assert text.index('"p_at_1_by_feature"') < text.index('"p_at_1_excludes_hard"')
        # Trailing newline
        assert text.endswith("\n")
