"""Tests for scripts/help_aggregator_prototype.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "help_aggregator_prototype.py"


@pytest.fixture
def agg():
    """Load the aggregator script as a module."""
    spec = importlib.util.spec_from_file_location("_help_aggregator_proto", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_help_aggregator_proto"] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("_help_aggregator_proto", None)


def _make_row(agg_mod, **overrides):
    """Build a FeatureRow with sensible defaults, overriding any field."""
    defaults = {
        "name": "alpha",
        "kinds_present": agg_mod.EXPECTED_KINDS,
        "is_stale": False,
        "stored_hash": "abc",
        "current_hash": "abc",
        "matched_files": ["src/alpha.py"],
        "p_at_1": 0.90,
    }
    defaults.update(overrides)
    return agg_mod.FeatureRow(**defaults)


class TestFeatureRowProperties:
    def test_kind_count_matches_len(self, agg):
        row = _make_row(agg, kinds_present=frozenset({"concept", "task"}))
        assert row.kind_count == 2

    def test_is_complete_true_when_all_kinds_present(self, agg):
        row = _make_row(agg, kinds_present=agg.EXPECTED_KINDS)
        assert row.is_complete is True

    def test_is_complete_false_when_kinds_missing(self, agg):
        row = _make_row(agg, kinds_present=frozenset({"concept"}))
        assert row.is_complete is False

    def test_missing_kinds_returns_difference(self, agg):
        partial = frozenset({"concept", "task", "reference"})
        row = _make_row(agg, kinds_present=partial)
        assert row.missing_kinds == agg.EXPECTED_KINDS - partial

    def test_needs_attention_when_stale(self, agg):
        row = _make_row(agg, is_stale=True)
        assert row.needs_attention is True

    def test_needs_attention_when_incomplete(self, agg):
        row = _make_row(agg, kinds_present=frozenset({"concept"}))
        assert row.needs_attention is True

    def test_needs_attention_when_low_p_at_1(self, agg):
        row = _make_row(agg, p_at_1=0.50)
        assert row.needs_attention is True

    def test_needs_attention_false_when_ok(self, agg):
        row = _make_row(agg, p_at_1=0.90)
        assert row.needs_attention is False

    def test_needs_attention_false_when_p_at_1_missing(self, agg):
        row = _make_row(agg, p_at_1=None)
        assert row.needs_attention is False

    def test_severity_stale_is_zero(self, agg):
        row = _make_row(agg, is_stale=True)
        assert row.severity == 0

    def test_severity_incomplete_is_one(self, agg):
        row = _make_row(agg, kinds_present=frozenset({"concept"}))
        assert row.severity == 1

    def test_severity_low_p_at_1_is_two(self, agg):
        row = _make_row(agg, p_at_1=0.50)
        assert row.severity == 2

    def test_severity_ok_is_three(self, agg):
        row = _make_row(agg, p_at_1=0.95)
        assert row.severity == 3


class TestScanKinds:
    def test_missing_dir_returns_empty(self, agg, tmp_path):
        assert agg._scan_kinds(tmp_path / "does-not-exist") == frozenset()

    def test_returns_file_stems(self, agg, tmp_path):
        (tmp_path / "concept.md").write_text("x")
        (tmp_path / "task.md").write_text("x")
        (tmp_path / "reference.md").write_text("x")
        (tmp_path / "not-md.txt").write_text("x")
        assert agg._scan_kinds(tmp_path) == frozenset({"concept", "task", "reference"})

    def test_empty_dir_returns_empty_frozenset(self, agg, tmp_path):
        assert agg._scan_kinds(tmp_path) == frozenset()


class TestLoadBenchmarks:
    def test_missing_file_returns_empty_dict(self, agg, tmp_path, monkeypatch):
        monkeypatch.setattr(agg, "BENCHMARK_CACHE", tmp_path / "latest.json")
        assert agg._load_benchmarks() == {}

    def test_malformed_json_returns_empty_dict(self, agg, tmp_path, monkeypatch):
        cache = tmp_path / "latest.json"
        cache.write_text("not json{", encoding="utf-8")
        monkeypatch.setattr(agg, "BENCHMARK_CACHE", cache)
        assert agg._load_benchmarks() == {}

    def test_valid_payload(self, agg, tmp_path, monkeypatch):
        cache = tmp_path / "latest.json"
        cache.write_text(
            '{"p_at_1_by_feature": {"alpha": 0.9, "beta": 0.75}}',
            encoding="utf-8",
        )
        monkeypatch.setattr(agg, "BENCHMARK_CACHE", cache)
        result = agg._load_benchmarks()
        assert result == {"alpha": 0.9, "beta": 0.75}

    def test_non_dict_p_at_1_returns_empty_dict(self, agg, tmp_path, monkeypatch):
        cache = tmp_path / "latest.json"
        cache.write_text('{"p_at_1_by_feature": ["bogus"]}', encoding="utf-8")
        monkeypatch.setattr(agg, "BENCHMARK_CACHE", cache)
        assert agg._load_benchmarks() == {}

    def test_filters_non_numeric_values(self, agg, tmp_path, monkeypatch):
        cache = tmp_path / "latest.json"
        cache.write_text(
            '{"p_at_1_by_feature": {"alpha": 0.9, "bad": "oops", "beta": 1}}',
            encoding="utf-8",
        )
        monkeypatch.setattr(agg, "BENCHMARK_CACHE", cache)
        result = agg._load_benchmarks()
        assert result == {"alpha": 0.9, "beta": 1.0}
        assert "bad" not in result


class TestLoadQueries:
    def test_missing_file_returns_empty_list(self, agg, tmp_path, monkeypatch):
        monkeypatch.setattr(agg, "FIXTURES", tmp_path / "missing.yaml")
        assert agg._load_queries() == []

    def test_valid_fixtures(self, agg, tmp_path, monkeypatch):
        fixtures = tmp_path / "queries.yaml"
        fixtures.write_text(
            "queries:\n"
            "  - id: q1\n    query: find bugs\n    expected: bug-predict\n"
            "  - id: q2\n    query: review code\n    expected: code-quality\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(agg, "FIXTURES", fixtures)
        result = agg._load_queries()
        assert len(result) == 2
        assert result[0]["id"] == "q1"
        assert result[1]["expected"] == "code-quality"


class TestFmtP1:
    def test_none_returns_dash(self, agg):
        assert agg._fmt_p1(None) == "  -  "

    def test_value_formats_as_percent(self, agg):
        assert agg._fmt_p1(0.75).strip() == "75%"

    def test_zero_formats_as_zero_percent(self, agg):
        assert agg._fmt_p1(0.0).strip() == "0%"


class TestDrillIn:
    def test_unknown_feature_returns_1(self, agg, tmp_path, monkeypatch, capsys):
        """Feature not in manifest — drill_in should return exit code 1."""

        # load_manifest is called at module scope, so we stub it
        class _Manifest:
            features: dict = {"alpha": object(), "beta": object()}

        monkeypatch.setattr(agg, "load_manifest", lambda _d: _Manifest())

        result = agg.drill_in("not-a-feature")
        out = capsys.readouterr().out

        assert result == 1
        assert "not-a-feature" in out
        assert "Known features" in out
