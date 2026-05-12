"""Tests for `attune.memory.security.query.AuditQueryMixin`.

Strategy: real `AuditLogger` instances against a `tmp_path` log
file. The mixin requires `self.log_path`; constructing the real
host class exercises the mixin in its production context with
no mock surface to drift away from.

Covers:
- Public API: AuditQueryMixin.query() — every filter argument,
  combinations, limit enforcement, malformed-line handling.
- Edge cases: missing log file, empty file, unicode user_ids,
  empty/None timestamps, mixed Z/+00:00 timezone suffixes,
  multi-event partial matches under date filter.
- Helper: `_apply_custom_filters` — every comparison operator
  (gt/gte/lt/lte/ne/default), nested-key access, missing keys,
  non-numeric operands.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from attune.memory.security.audit_logger import AuditLogger
from attune.memory.security.query import _apply_custom_filters

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def logger(tmp_path: Path) -> AuditLogger:
    """Real AuditLogger writing to a tmp_path-isolated log file."""
    return AuditLogger(
        log_dir=str(tmp_path),
        log_filename="audit.jsonl",
        enable_rotation=False,
    )


def _write_events(logger: AuditLogger, events: list[dict[str, Any]]) -> None:
    """Append JSONL events directly to the logger's log file.

    Bypasses AuditLogger's own write path so tests don't depend on
    its serialization layer — we want to assert query semantics
    against arbitrary on-disk content.
    """
    logger.log_path.parent.mkdir(parents=True, exist_ok=True)
    with logger.log_path.open("a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def _ts(*, year: int = 2026, month: int = 5, day: int = 12, hour: int = 12) -> str:
    """ISO timestamp helper for test event timestamps."""
    return datetime(year, month, day, hour, tzinfo=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# query() — file-presence edge cases
# ---------------------------------------------------------------------------


class TestQueryFileEdgeCases:
    def test_missing_log_file_returns_empty(self, logger: AuditLogger) -> None:
        # AuditLogger.__init__ creates the log dir but not the file.
        # If the file is missing, query() should return [], not raise.
        if logger.log_path.exists():
            logger.log_path.unlink()
        assert logger.query() == []

    def test_empty_log_file_returns_empty(self, logger: AuditLogger) -> None:
        logger.log_path.write_text("", encoding="utf-8")
        assert logger.query() == []

    def test_log_with_only_blank_lines_returns_empty(self, logger: AuditLogger) -> None:
        logger.log_path.write_text("\n\n\n", encoding="utf-8")
        # Blank lines parse to JSON failures (json.loads("") raises);
        # they should be skipped, returning [].
        assert logger.query() == []


# ---------------------------------------------------------------------------
# query() — simple filter behaviors
# ---------------------------------------------------------------------------


class TestQueryFilters:
    def test_no_filters_returns_all_events(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "llm_request", "timestamp": _ts()},
                {"event_type": "store_pattern", "timestamp": _ts()},
            ],
        )
        results = logger.query()
        assert len(results) == 2

    def test_filter_by_event_type(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "llm_request", "user_id": "alice"},
                {"event_type": "store_pattern", "user_id": "alice"},
                {"event_type": "llm_request", "user_id": "bob"},
            ],
        )
        results = logger.query(event_type="llm_request")
        assert len(results) == 2
        assert all(e["event_type"] == "llm_request" for e in results)

    def test_filter_by_user_id(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "llm_request", "user_id": "alice"},
                {"event_type": "llm_request", "user_id": "bob"},
            ],
        )
        results = logger.query(user_id="alice")
        assert len(results) == 1
        assert results[0]["user_id"] == "alice"

    def test_filter_by_status(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "x", "status": "success"},
                {"event_type": "x", "status": "failed"},
                {"event_type": "x", "status": "blocked"},
            ],
        )
        results = logger.query(status="blocked")
        assert len(results) == 1
        assert results[0]["status"] == "blocked"

    def test_filter_combination_applies_AND(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "x", "user_id": "alice", "status": "success"},
                {"event_type": "x", "user_id": "alice", "status": "failed"},
                {"event_type": "y", "user_id": "alice", "status": "success"},
            ],
        )
        results = logger.query(event_type="x", status="success")
        assert len(results) == 1
        assert results[0]["user_id"] == "alice"

    def test_filter_with_no_matches_returns_empty(self, logger: AuditLogger) -> None:
        _write_events(logger, [{"event_type": "llm_request"}])
        assert logger.query(event_type="never_logged") == []

    def test_unicode_user_id_filter(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "x", "user_id": "用户@例.com"},
                {"event_type": "x", "user_id": "alice"},
            ],
        )
        results = logger.query(user_id="用户@例.com")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# query() — date range filtering (includes the Class 1 bug fix)
# ---------------------------------------------------------------------------


class TestQueryDateFilters:
    def test_filter_by_start_date(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "x", "timestamp": _ts(day=10)},
                {"event_type": "x", "timestamp": _ts(day=15)},
                {"event_type": "x", "timestamp": _ts(day=20)},
            ],
        )
        cutoff = datetime(2026, 5, 14, tzinfo=timezone.utc)
        results = logger.query(start_date=cutoff)
        assert len(results) == 2

    def test_filter_by_end_date(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "x", "timestamp": _ts(day=10)},
                {"event_type": "x", "timestamp": _ts(day=15)},
                {"event_type": "x", "timestamp": _ts(day=20)},
            ],
        )
        cutoff = datetime(2026, 5, 16, tzinfo=timezone.utc)
        results = logger.query(end_date=cutoff)
        assert len(results) == 2

    def test_filter_by_date_range(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "x", "timestamp": _ts(day=10)},
                {"event_type": "x", "timestamp": _ts(day=15)},
                {"event_type": "x", "timestamp": _ts(day=20)},
            ],
        )
        results = logger.query(
            start_date=datetime(2026, 5, 12, tzinfo=timezone.utc),
            end_date=datetime(2026, 5, 18, tzinfo=timezone.utc),
        )
        assert len(results) == 1
        # Day 15 falls inside the [12, 18] window.

    def test_Z_suffix_timestamp_parses(self, logger: AuditLogger) -> None:
        # Older audit producers wrote `2026-05-12T12:00:00Z` rather
        # than the +00:00 form. The replace("Z", "+00:00") bridges
        # both shapes on Python 3.10.
        _write_events(
            logger,
            [{"event_type": "x", "timestamp": "2026-05-12T12:00:00Z"}],
        )
        results = logger.query(
            start_date=datetime(2026, 5, 11, tzinfo=timezone.utc),
        )
        assert len(results) == 1

    def test_malformed_timestamp_is_skipped_not_aborted(
        self,
        logger: AuditLogger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Class 1 bug fix verification.

        Before the fix, a single line with a malformed `timestamp`
        raised ValueError from datetime.fromisoformat. The
        ValueError propagated to the outer except clause, logged
        once, and the function returned whatever results had
        accumulated so far — silently truncating the result set.

        After the fix, the malformed line is skipped and iteration
        continues; the caller gets the complete matching set.
        """
        _write_events(
            logger,
            [
                {"event_type": "x", "timestamp": _ts(day=10)},
                {"event_type": "x", "timestamp": "not-a-timestamp"},
                {"event_type": "x", "timestamp": _ts(day=20)},
            ],
        )
        with caplog.at_level(logging.WARNING):
            results = logger.query(
                start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        assert len(results) == 2, (
            "the third (good) event must be reached after the bad "
            "timestamp; pre-fix this returned 1 result, not 2"
        )
        assert any("malformed timestamp" in r.message for r in caplog.records)

    def test_empty_string_timestamp_skipped(
        self,
        logger: AuditLogger,
    ) -> None:
        # event.get("timestamp", "") returns "" if absent; the empty
        # string must be skipped, not raised on.
        _write_events(
            logger,
            [
                {"event_type": "x"},  # no timestamp at all
                {"event_type": "x", "timestamp": _ts(day=15)},
            ],
        )
        results = logger.query(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert len(results) == 1

    def test_null_timestamp_skipped(self, logger: AuditLogger) -> None:
        # JSON `null` deserializes to None; .replace() on None raises
        # AttributeError, which the fix also catches.
        _write_events(
            logger,
            [
                {"event_type": "x", "timestamp": None},
                {"event_type": "x", "timestamp": _ts(day=15)},
            ],
        )
        results = logger.query(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert len(results) == 1


# ---------------------------------------------------------------------------
# query() — limit and malformed-line handling
# ---------------------------------------------------------------------------


class TestQueryLimitAndRobustness:
    def test_limit_caps_results(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [{"event_type": "x", "n": i} for i in range(10)],
        )
        results = logger.query(limit=3)
        assert len(results) == 3

    def test_filtered_lines_dont_count_against_limit(self, logger: AuditLogger) -> None:
        # 10 events: 5 match, 5 don't. limit=4 means we get 4
        # matches even though we read past 4 lines.
        events: list[dict[str, Any]] = []
        for i in range(10):
            events.append({"event_type": "match" if i % 2 == 0 else "skip", "n": i})
        _write_events(logger, events)
        results = logger.query(event_type="match", limit=4)
        assert len(results) == 4

    def test_malformed_json_line_skipped(
        self,
        logger: AuditLogger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        logger.log_path.parent.mkdir(parents=True, exist_ok=True)
        with logger.log_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({"event_type": "good"}) + "\n")
            f.write("{not valid json\n")
            f.write(json.dumps({"event_type": "good"}) + "\n")
        with caplog.at_level(logging.WARNING):
            results = logger.query()
        assert len(results) == 2
        assert any("malformed audit log line" in r.message for r in caplog.records)

    def test_io_error_returns_partial_results_not_raise(
        self,
        logger: AuditLogger,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Outer except handler: I/O errors on the log file must not
        crash the query. Documented behavior is graceful degradation —
        log the error, return whatever accumulated.

        Simulating a real I/O failure cross-platform: replace
        log_path with a directory after exists() check passes.
        open() then raises IsADirectoryError, which the outer
        Exception handler catches.
        """
        log_dir_as_file = tmp_path / "audit-as-dir"
        log_dir_as_file.mkdir()
        logger.log_path = log_dir_as_file
        with caplog.at_level(logging.ERROR):
            results = logger.query()
        assert results == []
        assert any("Failed to query audit logs" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _apply_custom_filters — comparison-operator dispatch
# ---------------------------------------------------------------------------


class TestApplyCustomFilters:
    def test_default_equality_match(self) -> None:
        assert _apply_custom_filters({"status": "ok"}, {"status": "ok"})

    def test_default_equality_mismatch(self) -> None:
        assert not _apply_custom_filters({"status": "ok"}, {"status": "bad"})

    def test_gt_operator(self) -> None:
        event = {"score": 10}
        assert _apply_custom_filters(event, {"score__gt": 5})
        assert not _apply_custom_filters(event, {"score__gt": 10})  # not strict
        assert not _apply_custom_filters(event, {"score__gt": 15})

    def test_gte_operator(self) -> None:
        event = {"score": 10}
        assert _apply_custom_filters(event, {"score__gte": 10})
        assert _apply_custom_filters(event, {"score__gte": 5})
        assert not _apply_custom_filters(event, {"score__gte": 11})

    def test_lt_operator(self) -> None:
        event = {"score": 10}
        assert _apply_custom_filters(event, {"score__lt": 11})
        assert not _apply_custom_filters(event, {"score__lt": 10})  # not strict

    def test_lte_operator(self) -> None:
        event = {"score": 10}
        assert _apply_custom_filters(event, {"score__lte": 10})
        assert _apply_custom_filters(event, {"score__lte": 11})
        assert not _apply_custom_filters(event, {"score__lte": 9})

    def test_ne_operator(self) -> None:
        event = {"status": "ok"}
        assert _apply_custom_filters(event, {"status__ne": "bad"})
        assert not _apply_custom_filters(event, {"status__ne": "ok"})

    def test_nested_key_access(self) -> None:
        event = {"security": {"pii_detected": 7}}
        assert _apply_custom_filters(event, {"security__pii_detected": 7})
        assert not _apply_custom_filters(event, {"security__pii_detected": 8})

    def test_nested_key_with_operator(self) -> None:
        event = {"security": {"pii_detected": 7}}
        assert _apply_custom_filters(event, {"security__pii_detected__gt": 5})
        assert not _apply_custom_filters(event, {"security__pii_detected__gt": 10})

    def test_missing_nested_key_returns_false(self) -> None:
        event = {"security": {}}
        assert not _apply_custom_filters(event, {"security__pii_detected__gt": 0})

    def test_missing_top_level_key_returns_false(self) -> None:
        # event has no "security" key at all.
        assert not _apply_custom_filters({}, {"security__pii_detected": 5})

    def test_non_numeric_value_rejected_by_gt(self) -> None:
        # gt/gte/lt/lte explicitly guard with isinstance(current,
        # int | float). String operands return False rather than
        # raising TypeError mid-iteration.
        event = {"name": "alice"}
        assert not _apply_custom_filters(event, {"name__gt": "alpha"})
        assert not _apply_custom_filters(event, {"name__lt": "zzz"})

    def test_multiple_filters_combined_AND(self) -> None:
        event = {"a": 1, "b": 2}
        assert _apply_custom_filters(event, {"a": 1, "b": 2})
        assert not _apply_custom_filters(event, {"a": 1, "b": 3})

    def test_empty_filters_passes(self) -> None:
        # An event always matches an empty filter dict.
        assert _apply_custom_filters({"anything": "here"}, {})


# ---------------------------------------------------------------------------
# query() — custom-filter integration with the rest of the pipeline
# ---------------------------------------------------------------------------


class TestQueryWithCustomFilters:
    def test_nested_custom_filter_via_query(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "llm_request",
                    "security": {"pii_detected": 0},
                },
                {
                    "event_type": "llm_request",
                    "security": {"pii_detected": 8},
                },
            ],
        )
        results = logger.query(security__pii_detected__gt=5)
        assert len(results) == 1
        assert results[0]["security"]["pii_detected"] == 8

    def test_custom_filter_combines_with_named_filters(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "llm_request",
                    "user_id": "alice",
                    "security": {"pii_detected": 10},
                },
                {
                    "event_type": "store_pattern",
                    "user_id": "alice",
                    "security": {"pii_detected": 10},
                },
            ],
        )
        results = logger.query(
            event_type="llm_request",
            security__pii_detected__gt=5,
        )
        assert len(results) == 1
        assert results[0]["event_type"] == "llm_request"
