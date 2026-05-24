"""Regression tests for `read_telemetry_summary` field-name handling.

History: Home KPI tiles and the Daily activity table silently read zero
for months because `data.py` looked up `event.get("timestamp")` while
the UsageTracker writer has used `ts` since the v1.0 schema. This test
locks in the writer/reader field-name contract so the bug can't recur
silently — if anyone renames the field on either side without
coordinating, this test fails.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from attune.ops import data
from attune.ops.config import Config

# Frozen "today" for the by-day-window assertions below. Events in the
# fixtures are dated 2026-05-14; this anchors the rolling window to the
# same day so the assertions don't age out as wall-clock time advances.
# The production code path keeps using date.today() — the parameter
# only affects tests that pass it.
_FIXED_TODAY = date(2026, 5, 14)


def _write_jsonl(path, events):
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _config(tmp_path):
    """Build an ops Config rooted in ``tmp_path``.

    The fields not under test (project_root, etc.) get harmless
    defaults; only ``attune_home`` matters because that's where
    ``telemetry_path`` resolves to.
    """
    home = tmp_path / "attune_home"
    (home / "telemetry").mkdir(parents=True)
    return Config(
        project_root=tmp_path,
        attune_home=home,
        allow_run=False,
        specs_roots=(),
    )


def test_read_telemetry_summary_recognizes_ts_field(tmp_path):
    """An event with the canonical ``ts`` key feeds the by_day bucket.

    This is the field name the writer (UsageTracker._format_entry)
    emits today. Before the fix, the reader looked up ``timestamp``
    instead, so this event would land in totals but not by_day,
    breaking Home's Daily activity table.
    """
    cfg = _config(tmp_path)
    _write_jsonl(
        cfg.telemetry_path,
        [
            {
                "v": "1.0",
                "ts": "2026-05-14T12:00:00+00:00",
                "workflow": "code-review",
                "total_cost": 0.05,
            }
        ],
    )

    summary = data.read_telemetry_summary(cfg, today=_FIXED_TODAY)

    assert summary.total_requests == 1
    assert summary.total_cost == pytest.approx(0.05)
    assert summary.last_event_at == "2026-05-14T12:00:00+00:00"
    # The actual bug: by_day was empty even when events existed.
    assert summary.by_day == [("2026-05-14", 1, 0.05)]


def test_read_telemetry_summary_falls_back_to_legacy_timestamp(tmp_path):
    """A rotated archive with the old ``timestamp`` field still works.

    Defensive read: ``event.get("ts") or event.get("timestamp")``.
    Without this fallback, any archived usage.YYYY-MM-DD.jsonl from
    before the schema rename would silently fail to aggregate.
    """
    cfg = _config(tmp_path)
    _write_jsonl(
        cfg.telemetry_path,
        [
            {
                "timestamp": "2026-05-14T12:00:00+00:00",
                "workflow": "code-review",
                "total_cost": 0.05,
            }
        ],
    )

    summary = data.read_telemetry_summary(cfg, today=_FIXED_TODAY)

    assert summary.total_requests == 1
    assert summary.by_day == [("2026-05-14", 1, 0.05)]


def test_read_telemetry_summary_handles_both_fields_in_same_file(tmp_path):
    """Mixed-schema file (new + legacy events) aggregates correctly.

    Concretely covers the "we just rotated mid-day" case where the
    same file has both shapes from before and after a schema bump.
    """
    cfg = _config(tmp_path)
    _write_jsonl(
        cfg.telemetry_path,
        [
            {"ts": "2026-05-14T09:00:00+00:00", "workflow": "a", "total_cost": 0.01},
            {
                "timestamp": "2026-05-14T10:00:00+00:00",
                "workflow": "a",
                "total_cost": 0.02,
            },
            {"ts": "2026-05-15T11:00:00+00:00", "workflow": "b", "total_cost": 0.03},
        ],
    )

    summary = data.read_telemetry_summary(cfg, today=_FIXED_TODAY)

    assert summary.total_requests == 3
    assert summary.total_cost == pytest.approx(0.06)
    by_day = {row[0]: (row[1], row[2]) for row in summary.by_day}
    assert by_day["2026-05-14"] == (2, pytest.approx(0.03))
    assert by_day["2026-05-15"] == (1, pytest.approx(0.03))


def test_read_telemetry_summary_skips_event_with_no_timestamp(tmp_path):
    """An event missing both ``ts`` and ``timestamp`` still counts in
    totals but doesn't contribute to by_day (no date to bucket against)."""
    cfg = _config(tmp_path)
    _write_jsonl(
        cfg.telemetry_path,
        [{"workflow": "a", "total_cost": 0.01}],
    )

    summary = data.read_telemetry_summary(cfg, today=_FIXED_TODAY)

    assert summary.total_requests == 1
    assert summary.total_cost == pytest.approx(0.01)
    assert summary.by_day == []
    assert summary.last_event_at is None
