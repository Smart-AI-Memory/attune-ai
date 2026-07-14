"""Characterization tests for the two D-grade functions in ``ops/data.py``.

Pins the CURRENT behavior of :func:`attune.ops.data.read_telemetry_summary`
(radon D22, ~line 825) and :func:`attune.ops.data.spend_alarm` (radon D23,
~line 1221) so a later decomposition refactor has a behavior-preservation
receipt. These tests document what the code DOES today, quirks included —
they are not aspirational, and several of them exist specifically to pin a
surprising-but-intentional (or surprising-and-accidental) branch so a
refactor can't silently change it.

Some branch families are already covered by ``test_telemetry_summary.py``
(the ts/timestamp field-name regression) and ``test_spend_alarm.py`` (the
z-score / flat-multiplier / ceiling / source-precedence verdict shapes).
This file does not try to avoid all overlap with those — it is meant to
stand alone as a single characterization suite for the two functions —
but it focuses new coverage on branches those files don't already pin:
missing/unreadable files, malformed JSON, field-fallback edge cases
(``None`` vs missing, empty-string falsy fallback, last-line-wins
ordering), the workflow-registry canonical filter (success/failure/cap),
and the spend-alarm threshold *boundaries*, custom overrides, and the
``min_baseline_days`` guard against a ``statistics.stdev`` crash on a
single-point baseline.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from attune.ops import data
from attune.ops.config import Config

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path, lines: list[str]) -> None:
    """Write raw lines (already-serialized or intentionally malformed)."""
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_events(path, events: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _config(tmp_path) -> Config:
    """Build an ops Config rooted in ``tmp_path`` (mirrors test_telemetry_summary.py)."""
    home = tmp_path / "attune_home"
    (home / "telemetry").mkdir(parents=True)
    return Config(
        project_root=tmp_path,
        attune_home=home,
        allow_run=False,
        specs_roots=(),
    )


# Frozen "today" for read_telemetry_summary fixtures (matches
# test_telemetry_summary.py's convention so events dated 2026-05-14 stay
# inside the default 7-day recent-days window).
_TELEMETRY_TODAY = date(2026, 5, 14)

# Frozen "today" for spend_alarm fixtures (matches test_spend_alarm.py's
# convention).
_SPEND_TODAY = date(2026, 6, 20)


# ===========================================================================
# read_telemetry_summary
# ===========================================================================


def test_read_telemetry_summary_happy_path_full_shape(tmp_path, monkeypatch):
    """Main happy path: multiple workflows, multiple days, savings — pins
    the exact TelemetrySummary shape (rounding, sort order, last_event_at)."""
    cfg = _config(tmp_path)
    import attune.ops.data as _data_mod
    from attune.ops.data import WorkflowEntry

    canonical = [
        WorkflowEntry(name="code-review", description="", stages=1, tier_map={}),
        WorkflowEntry(name="security-audit", description="", stages=1, tier_map={}),
    ]

    def _fake_list_workflows() -> list[WorkflowEntry]:
        return canonical

    monkeypatch.setattr(_data_mod, "list_workflows", _fake_list_workflows)
    _write_events(
        cfg.telemetry_path,
        [
            {
                "workflow": "code-review",
                "ts": "2026-05-14T09:00:00+00:00",
                "total_cost": 1.5,
                "savings": 0.5,
            },
            {
                "workflow": "code-review",
                "ts": "2026-05-14T10:00:00+00:00",
                "total_cost": 0.5,
            },
            {
                "workflow": "security-audit",
                "ts": "2026-05-13T08:00:00+00:00",
                "total_cost": 3.0,
                "savings": 1.0,
            },
        ],
    )

    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)

    assert summary == data.TelemetrySummary(
        total_requests=3,
        total_cost=5.0,
        total_savings=1.5,
        by_workflow=[("security-audit", 1, 3.0), ("code-review", 2, 2.0)],
        by_day=[("2026-05-13", 1, 3.0), ("2026-05-14", 2, 2.0)],
        last_event_at="2026-05-13T08:00:00+00:00",
    )


def test_read_telemetry_summary_missing_file_returns_zeroed_summary(tmp_path):
    """No ``usage.jsonl`` at all -> the early-return zeroed summary, not an
    exception (the panel must render on a fresh install)."""
    cfg = _config(tmp_path)
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)
    assert summary == data.TelemetrySummary(0, 0.0, 0.0, [], [], None)


def test_read_telemetry_summary_unreadable_file_returns_zeroed_summary(tmp_path):
    """A path that exists but can't be opened as a file (here: it's a
    directory) hits the ``except OSError`` branch, not an unhandled crash."""
    cfg = _config(tmp_path)
    cfg.telemetry_path.mkdir()  # usage.jsonl is a directory, not a file
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)
    assert summary == data.TelemetrySummary(0, 0.0, 0.0, [], [], None)


def test_read_telemetry_summary_blank_and_malformed_lines_are_skipped(tmp_path):
    """Blank lines and lines that don't parse as JSON are silently
    dropped — they don't count toward ``total_requests`` at all."""
    cfg = _config(tmp_path)
    _write_jsonl(
        cfg.telemetry_path,
        [
            json.dumps({"ts": "2026-05-14T09:00:00+00:00", "workflow": "a", "total_cost": 0.01}),
            "",  # blank line
            "not valid json {{{",  # malformed
            json.dumps({"ts": "2026-05-14T10:00:00+00:00", "workflow": "a", "total_cost": 0.02}),
        ],
    )
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)
    assert summary.total_requests == 2
    assert summary.total_cost == pytest.approx(0.03)
    assert summary.by_day == [("2026-05-14", 2, 0.03)]


def test_read_telemetry_summary_cost_field_fallback_chain(tmp_path):
    """``total_cost`` wins; falls back to ``cost``; falls back to 0.0 when
    neither is present. Quirk: an EXPLICIT ``total_cost: null`` does NOT
    fall through to ``cost`` — ``dict.get(key, default)`` only applies the
    default when the key is absent, not when its value is ``None``, so
    ``None or 0.0`` short-circuits to 0.0 even though ``cost`` has a value."""
    cfg = _config(tmp_path)
    _write_events(
        cfg.telemetry_path,
        [
            {"ts": "2026-05-14T09:00:00+00:00", "workflow": "a", "total_cost": 1.0},
            {"ts": "2026-05-14T09:01:00+00:00", "workflow": "a", "cost": 2.0},
            {"ts": "2026-05-14T09:02:00+00:00", "workflow": "a"},
            {
                "ts": "2026-05-14T09:03:00+00:00",
                "workflow": "a",
                "total_cost": None,
                "cost": 5.0,
            },
        ],
    )
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)
    assert summary.total_requests == 4
    # 1.0 (total_cost) + 2.0 (cost fallback) + 0.0 (neither) + 0.0 (null
    # total_cost does NOT fall back to cost=5.0) == 3.0, not 8.0.
    assert summary.total_cost == pytest.approx(3.0)


def test_read_telemetry_summary_workflow_field_fallback_chain(tmp_path, monkeypatch):
    """``workflow`` wins; falls back to ``event_type``; falls back to
    ``"unknown"``. Quirk: an EMPTY-STRING ``workflow`` is falsy under the
    ``or`` chain, so it also falls through to ``event_type`` rather than
    being kept as the literal empty string."""
    cfg = _config(tmp_path)
    import attune.ops.data as _data_mod

    # Force the "show everything" fallback by making the registry lookup
    # raise, so this test isolates the workflow-name resolution logic from
    # the canonical-filter logic (covered separately below).
    def _raise():
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(_data_mod, "list_workflows", _raise)
    _write_events(
        cfg.telemetry_path,
        [
            {
                "ts": "2026-05-14T09:00:00+00:00",
                "workflow": "code-review",
                "total_cost": 1.0,
            },
            {
                "ts": "2026-05-14T09:01:00+00:00",
                "event_type": "audit_run",
                "total_cost": 2.0,
            },
            {"ts": "2026-05-14T09:02:00+00:00", "total_cost": 3.0},
            {
                "ts": "2026-05-14T09:03:00+00:00",
                "workflow": "",
                "event_type": "fallback-name",
                "total_cost": 4.0,
            },
        ],
    )
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)

    by_cost = {row[0]: row[2] for row in summary.by_workflow}
    assert by_cost == {
        "code-review": 1.0,
        "audit_run": 2.0,
        "unknown": 3.0,
        "fallback-name": 4.0,
    }


def test_read_telemetry_summary_ts_missing_entirely_still_counts_in_totals(tmp_path):
    """An event with neither ``ts`` nor ``timestamp`` still counts toward
    ``total_requests``/``total_cost`` but contributes nothing to ``by_day``
    and does not move ``last_event_at`` (the empty-string ts is falsy)."""
    cfg = _config(tmp_path)
    _write_events(
        cfg.telemetry_path,
        [
            {"ts": "2026-05-14T09:00:00+00:00", "workflow": "a", "total_cost": 0.01},
            {"timestamp": "2026-05-14T10:00:00+00:00", "workflow": "a", "total_cost": 0.02},
            {"workflow": "a", "total_cost": 0.03},  # neither field
        ],
    )
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)
    assert summary.total_requests == 3
    assert summary.total_cost == pytest.approx(0.06)
    assert summary.by_day == [("2026-05-14", 2, 0.03)]
    # last_event_at is "frozen" at the last event that HAD a truthy ts —
    # the trailing no-ts event does not reset it to None.
    assert summary.last_event_at == "2026-05-14T10:00:00+00:00"


def test_read_telemetry_summary_last_event_at_is_last_line_not_max_timestamp(tmp_path):
    """QUIRK: ``last_event_at`` tracks file/iteration order, not
    chronological order. An event with an EARLIER timestamp that appears
    LATER in the file wins over an event with a later timestamp that
    appears earlier."""
    cfg = _config(tmp_path)
    _write_events(
        cfg.telemetry_path,
        [
            {"ts": "2026-05-14T09:00:00+00:00", "workflow": "a", "total_cost": 1.0},
            {"ts": "2026-05-10T09:00:00+00:00", "workflow": "a", "total_cost": 1.0},
        ],
    )
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)
    assert summary.last_event_at == "2026-05-10T09:00:00+00:00"


def test_read_telemetry_summary_by_day_window_excludes_old_days_but_totals_include_them(
    tmp_path,
):
    """``recent_days`` (default 7) trims ``by_day`` to a rolling window, but
    ``total_requests``/``total_cost`` are NOT windowed — they're an
    all-time sum over the whole file."""
    cfg = _config(tmp_path)
    _write_events(
        cfg.telemetry_path,
        [
            # Outside the 7-day window relative to 2026-05-14 (cutoff is
            # 2026-05-07; this is 13 days before "today").
            {"ts": "2026-05-01T09:00:00+00:00", "workflow": "a", "total_cost": 5.0},
            {"ts": "2026-05-14T09:00:00+00:00", "workflow": "a", "total_cost": 2.0},
        ],
    )
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)
    assert summary.total_requests == 2
    assert summary.total_cost == pytest.approx(7.0)
    assert summary.by_day == [("2026-05-14", 1, 2.0)]


def test_read_telemetry_summary_canonical_filter_excludes_unregistered_workflows(
    tmp_path, monkeypatch
):
    """When the workflow registry resolves, ``by_workflow`` only surfaces
    canonical (currently-registered) workflow names — a stale test-fixture
    or removed-workflow name is dropped from the rollup, though it still
    counts toward the file-wide totals."""
    cfg = _config(tmp_path)
    import attune.ops.data as _data_mod
    from attune.ops.data import WorkflowEntry

    def _fake_list_workflows():
        return [WorkflowEntry(name="code-review", description="", stages=1, tier_map={})]

    monkeypatch.setattr(_data_mod, "list_workflows", _fake_list_workflows)
    _write_events(
        cfg.telemetry_path,
        [
            {
                "ts": "2026-05-14T09:00:00+00:00",
                "workflow": "code-review",
                "total_cost": 1.0,
            },
            {
                "ts": "2026-05-14T09:01:00+00:00",
                "workflow": "old-stub",
                "total_cost": 2.0,
            },
        ],
    )
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)

    assert summary.total_requests == 2
    assert summary.total_cost == pytest.approx(3.0)  # unfiltered total
    assert summary.by_workflow == [("code-review", 1, 1.0)]  # old-stub dropped


def test_read_telemetry_summary_registry_failure_falls_back_to_show_everything(
    tmp_path, monkeypatch
):
    """INTENTIONAL fallback: if introspecting the workflow registry raises,
    the canonical filter is disabled entirely (``canonical_names = None``)
    rather than hiding all data behind a broken registry call."""
    cfg = _config(tmp_path)
    import attune.ops.data as _data_mod

    def _raise():
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(_data_mod, "list_workflows", _raise)
    _write_events(
        cfg.telemetry_path,
        [
            {
                "ts": "2026-05-14T09:00:00+00:00",
                "workflow": "not-a-real-workflow",
                "total_cost": 1.0,
            }
        ],
    )
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)

    assert summary.by_workflow == [("not-a-real-workflow", 1, 1.0)]


def test_read_telemetry_summary_by_workflow_caps_at_top_20(tmp_path, monkeypatch):
    """``by_workflow`` is capped at the top 20 by cost (``heapq.nlargest``),
    dropping the lowest spenders when more than 20 distinct workflows have
    events, and returns them sorted descending by cost."""
    cfg = _config(tmp_path)
    import attune.ops.data as _data_mod

    def _raise():
        raise RuntimeError("registry unavailable")  # show-everything fallback

    monkeypatch.setattr(_data_mod, "list_workflows", _raise)
    events = [
        {
            "ts": "2026-05-14T09:00:00+00:00",
            "workflow": f"w{i:02d}",
            "total_cost": float(i),
        }
        for i in range(1, 23)  # w01..w22, costs 1.0..22.0
    ]
    _write_events(cfg.telemetry_path, events)
    summary = data.read_telemetry_summary(cfg, today=_TELEMETRY_TODAY)

    assert len(summary.by_workflow) == 20
    names = {row[0] for row in summary.by_workflow}
    assert "w01" not in names  # lowest two dropped
    assert "w02" not in names
    assert summary.by_workflow[0] == ("w22", 1, 22.0)  # sorted descending by cost


# ===========================================================================
# spend_alarm
# ===========================================================================


def test_spend_alarm_happy_path_full_shape_ok_day():
    """Main happy path: a mild day within a varied baseline — pins the
    exact SpendAlarm shape, including the verbatim ``detail`` text and the
    default source's CI-blindness suffix."""
    daily = {
        "2026-06-17": 4.0,
        "2026-06-18": 6.0,
        "2026-06-19": 5.0,
        "2026-06-20": 6.5,
    }
    alarm = data.spend_alarm(daily, today=_SPEND_TODAY)
    assert alarm == data.SpendAlarm(
        level="ok",
        triggered_by=(),
        today_cost=6.5,
        baseline_mean=5.0,
        baseline_days=3,
        method="zscore",
        z_score=1.5,
        month_to_date=21.5,
        monthly_ceiling=350.0,
        ceiling_pct=6.1,
        source="local",
        detail="today $6.50 within normal range (local telemetry only — CI spend not counted)",
    )


def test_spend_alarm_zscore_boundary_exact_threshold_alarms():
    """z_score == z_threshold (the ``>=`` boundary) alarms — the trigger is
    inclusive of the threshold, not strictly-greater."""
    daily = {
        "2026-06-17": 4.0,
        "2026-06-18": 6.0,
        "2026-06-19": 5.0,
        "2026-06-20": 8.0,  # (8.0 - 5.0) / 1.0 == 3.0 exactly
    }
    alarm = data.spend_alarm(daily, today=_SPEND_TODAY)
    assert alarm.z_score == 3.0
    assert alarm.level == "alarm"
    assert "daily_anomaly" in alarm.triggered_by


def test_spend_alarm_zscore_boundary_just_below_threshold_is_ok():
    """z_score just under z_threshold does not alarm."""
    daily = {
        "2026-06-17": 4.0,
        "2026-06-18": 6.0,
        "2026-06-19": 5.0,
        "2026-06-20": 7.99,  # z == 2.99
    }
    alarm = data.spend_alarm(daily, today=_SPEND_TODAY)
    assert alarm.z_score == 2.99
    assert alarm.level == "ok"
    assert alarm.triggered_by == ()


def test_spend_alarm_flat_multiplier_boundary_exact_ratio_is_ok():
    """QUIRK: the flat-history multiplier check uses strict ``>``, so
    today's spend exactly equal to ``baseline_mean * flat_multiplier``
    does NOT alarm — it must exceed the ratio, not merely meet it."""
    daily = {
        "2026-06-17": 5.0,
        "2026-06-18": 5.0,
        "2026-06-19": 5.0,
        "2026-06-20": 15.0,  # exactly 3x the flat $5/day baseline
    }
    alarm = data.spend_alarm(daily, today=_SPEND_TODAY)
    assert alarm.method == "multiplier"
    assert alarm.level == "ok"
    assert alarm.triggered_by == ()


def test_spend_alarm_ceiling_boundary_exact_fraction_alarms():
    """month_to_date exactly at ``ceiling_fraction`` of the ceiling alarms
    (the ``>=`` boundary, same inclusive convention as the z-score check)."""
    daily = {"2026-06-20": 1.0}
    alarm = data.spend_alarm(
        daily,
        today=_SPEND_TODAY,
        monthly_ceiling=350.0,
        ceiling_fraction=0.8,
        month_to_date=280.0,  # exactly 350 * 0.8
    )
    assert alarm.ceiling_pct == 80.0
    assert alarm.level == "alarm"
    assert "ceiling" in alarm.triggered_by


def test_spend_alarm_both_triggers_fire_together():
    """Daily-anomaly and ceiling triggers are independent and can both fire
    on the same verdict; ``detail`` joins both explanations with '; '."""
    daily = {
        "2026-06-17": 4.0,
        "2026-06-18": 6.0,
        "2026-06-19": 5.0,
        "2026-06-20": 8.0,  # z == 3.0, alarms
    }
    alarm = data.spend_alarm(
        daily,
        today=_SPEND_TODAY,
        monthly_ceiling=350.0,
        month_to_date=300.0,  # 300/350 ~= 85.7% >= 80%, alarms
    )
    assert alarm.level == "alarm"
    assert set(alarm.triggered_by) == {"daily_anomaly", "ceiling"}
    assert "; " in alarm.detail


def test_spend_alarm_zero_monthly_ceiling_disables_ceiling_check():
    """A ``monthly_ceiling`` of 0 (or negative) makes ``ceiling_pct`` 0.0
    and never trips the ceiling trigger, regardless of month-to-date."""
    daily = {"2026-06-20": 1.0}
    alarm = data.spend_alarm(daily, today=_SPEND_TODAY, monthly_ceiling=0.0, month_to_date=1000.0)
    assert alarm.ceiling_pct == 0.0
    assert "ceiling" not in alarm.triggered_by


def test_spend_alarm_min_baseline_days_one_avoids_stdev_crash_on_single_point():
    """QUIRK / defensive guard: ``statistics.stdev`` requires >= 2 data
    points and raises on a single value. When ``min_baseline_days`` is
    lowered to 1, a 1-day baseline enters the anomaly branch but the code
    guards with ``stdev = ... if baseline_days >= 2 else 0.0`` so it takes
    the flat-multiplier path instead of crashing."""
    daily = {"2026-06-19": 5.0, "2026-06-20": 20.0}  # single baseline day
    alarm = data.spend_alarm(daily, today=_SPEND_TODAY, min_baseline_days=1)
    assert alarm.baseline_days == 1
    assert alarm.method == "multiplier"
    assert alarm.level == "alarm"  # 20.0 > 5.0 * 3.0 flat multiplier


def test_spend_alarm_missing_today_key_defaults_to_zero_cost():
    """``daily`` with no entry for today's date yields ``today_cost == 0.0``
    rather than a KeyError, and a below-baseline "today" is not an
    anomaly (z_score negative, no trigger)."""
    daily = {"2026-06-17": 5.0, "2026-06-18": 6.0, "2026-06-19": 4.0}  # no 06-20
    alarm = data.spend_alarm(daily, today=_SPEND_TODAY)
    assert alarm.today_cost == 0.0
    assert alarm.z_score == -5.0
    assert alarm.level == "ok"
    assert alarm.triggered_by == ()


def test_spend_alarm_custom_z_threshold_overrides_default():
    """A caller-supplied ``z_threshold`` changes the trigger point: the
    same z_score of 1.5 is 'ok' at the default 3.0 bar but 'alarm' at a
    custom 1.0 bar."""
    daily = {
        "2026-06-17": 4.0,
        "2026-06-18": 6.0,
        "2026-06-19": 5.0,
        "2026-06-20": 6.5,  # z == 1.5
    }
    default_alarm = data.spend_alarm(daily, today=_SPEND_TODAY)
    assert default_alarm.level == "ok"

    strict_alarm = data.spend_alarm(daily, today=_SPEND_TODAY, z_threshold=1.0)
    assert strict_alarm.z_score == 1.5
    assert strict_alarm.level == "alarm"
    assert "daily_anomaly" in strict_alarm.triggered_by


def test_spend_alarm_rounding_of_verdict_fields():
    """``today_cost``/``month_to_date`` round to 4 decimals and
    ``ceiling_pct`` rounds to 1 decimal, regardless of input precision."""
    daily = {"2026-06-20": 1.23456789}
    alarm = data.spend_alarm(
        daily, today=_SPEND_TODAY, monthly_ceiling=350.0, month_to_date=12.3456789
    )
    assert alarm.today_cost == 1.2346
    assert alarm.month_to_date == 12.3457
    assert alarm.ceiling_pct == round(12.3456789 / 350.0 * 100, 1)
