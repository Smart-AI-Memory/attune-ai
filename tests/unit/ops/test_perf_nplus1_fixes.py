"""Regression tests for the 11.5.0 post-release perf fixes.

Pins the N+1 eliminations the self-review flagged: one
``list_features`` pass per help-home request, one TTL-cached corpus
walk shared by ``coverage_gaps`` / ``recently_regenerated``, and the
``(mtime, size)``-keyed cache for the unbounded ``usage.jsonl``
aggregation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from attune.ops import data, help_data
from attune.ops.config import Config


@pytest.fixture(autouse=True)
def _fresh_caches():
    help_data._clear_records_cache()
    help_data._clear_staleness_cache()
    data._clear_telemetry_summary_cache()
    yield
    help_data._clear_records_cache()
    help_data._clear_staleness_cache()
    data._clear_telemetry_summary_cache()


def _make_corpus(root, features=("alpha", "beta"), kinds=("concept", "task")):
    for feat in features:
        d = root / ".help" / "templates" / feat
        d.mkdir(parents=True)
        for kind in kinds:
            (d / f"{kind}.md").write_text(
                f"---\ngenerated_at: 2026-08-0{1 + len(feat) % 5}\n---\n\n# {feat} {kind}\n",
                encoding="utf-8",
            )


def _cfg(tmp_path) -> Config:
    return Config(project_root=tmp_path, attune_home=tmp_path / ".attune")


class TestRecordWalkCache:
    def test_gaps_and_recent_share_one_corpus_walk(self, tmp_path):
        """Back-to-back coverage_gaps + recently_regenerated must not
        double the per-template file reads (the flagged N+1)."""
        _make_corpus(tmp_path)
        cfg = _cfg(tmp_path)
        calls = 0
        real = help_data.get_template

        def counting(config, feature, kind):
            nonlocal calls
            calls += 1
            return real(config, feature, kind)

        with patch.object(help_data, "get_template", side_effect=counting):
            help_data.coverage_gaps(cfg)
            help_data.recently_regenerated(cfg, limit=5)
        assert calls == 4, f"expected ONE walk (4 templates), got {calls} reads"

    def test_cache_scoped_per_corpus_root(self, tmp_path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        _make_corpus(a, features=("only-a",), kinds=("concept",))
        _make_corpus(b, features=("only-b",), kinds=("concept",))
        recs_a = help_data._all_template_records(_cfg(a))
        recs_b = help_data._all_template_records(_cfg(b))
        assert [r.feature for r in recs_a] == ["only-a"]
        assert [r.feature for r in recs_b] == ["only-b"]


class TestFeaturesReuse:
    def test_featured_and_recent_reuse_passed_features(self, tmp_path):
        """With ``features=`` supplied, list_features is NOT recomputed."""
        _make_corpus(tmp_path)
        cfg = _cfg(tmp_path)
        features = help_data.list_features(cfg)
        with patch.object(help_data, "list_features", side_effect=AssertionError("recomputed")):
            help_data.featured_topics(cfg, features=features)
            help_data.recently_regenerated(cfg, limit=5, features=features)


class TestTelemetrySummaryCache:
    def _write_events(self, path, n=3):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for _ in range(n):
                f.write(
                    json.dumps(
                        {"total_cost": 1.0, "workflow": "code-review", "ts": "2026-08-08T00:00:00"}
                    )
                    + "\n"
                )

    def test_unchanged_file_parsed_once(self, tmp_path):
        cfg = _cfg(tmp_path)
        self._write_events(cfg.telemetry_path)
        calls = 0
        real = data._parse_usage_event

        def counting(line):
            nonlocal calls
            calls += 1
            return real(line)

        with patch.object(data, "_parse_usage_event", side_effect=counting):
            first = data.read_telemetry_summary(cfg)
            second = data.read_telemetry_summary(cfg)
        assert first.total_requests == 3
        assert second is first, "unchanged file must serve the cached summary"
        assert calls == 3, "second call must not re-parse the file"

    def test_append_invalidates_cache(self, tmp_path):
        cfg = _cfg(tmp_path)
        self._write_events(cfg.telemetry_path)
        first = data.read_telemetry_summary(cfg)
        assert first.total_requests == 3
        self._write_events(cfg.telemetry_path, n=2)
        # mtime granularity guard: force a distinct identity.
        st = cfg.telemetry_path.stat()
        os.utime(cfg.telemetry_path, ns=(st.st_atime_ns, st.st_mtime_ns + 1))
        second = data.read_telemetry_summary(cfg)
        assert second.total_requests == 5

    def test_today_change_invalidates_cache(self, tmp_path):
        from datetime import date

        cfg = _cfg(tmp_path)
        self._write_events(cfg.telemetry_path)
        d1 = data.read_telemetry_summary(cfg, today=date(2026, 8, 8))
        d2 = data.read_telemetry_summary(cfg, today=date(2026, 8, 9))
        assert d1 is not d2, "different rolling-window anchors must not share a cache entry"
