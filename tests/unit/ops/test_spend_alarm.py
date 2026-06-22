"""Tests for the spend anomaly alarm — R6 of docs/specs/usage-signals/.

Covers the pure :func:`spend_alarm` verdict (z-score path, the explicit
flat-history/stddev==0 multiplier fallback, ceiling approach, insufficient
data), the local :func:`read_daily_spend` ts-bucketing reader, the
:func:`build_spend_alarm` source-precedence builder, and the home-page
panel render.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from attune.ops import data

# --------------------------------------------------------------------------
# spend_alarm — pure verdict
# --------------------------------------------------------------------------

TODAY = date(2026, 6, 20)


def test_spend_alarm_zscore_flags_outlier():
    """A spike many sigma above a varied baseline flags via z-score."""
    daily = {
        "2026-06-15": 4.0,
        "2026-06-16": 6.0,
        "2026-06-17": 5.0,
        "2026-06-18": 7.0,
        "2026-06-19": 5.0,
        "2026-06-20": 1200.0,  # the $1,200-night
    }
    alarm = data.spend_alarm(daily, today=TODAY)
    assert alarm.level == "alarm"
    assert "daily_anomaly" in alarm.triggered_by
    assert alarm.method == "zscore"
    assert alarm.z_score is not None and alarm.z_score >= 3.0
    assert alarm.today_cost == 1200.0


def test_spend_alarm_zscore_normal_day_is_ok():
    """A typical day within the varied baseline is ``ok``."""
    daily = {
        "2026-06-15": 4.0,
        "2026-06-16": 6.0,
        "2026-06-17": 5.0,
        "2026-06-18": 7.0,
        "2026-06-19": 5.0,
        "2026-06-20": 6.0,
    }
    alarm = data.spend_alarm(daily, today=TODAY)
    assert alarm.level == "ok"
    assert alarm.triggered_by == ()
    assert alarm.method == "zscore"


def test_spend_alarm_flat_history_multiplier_flags():
    """REQUIRED branch: stddev == 0 (all baseline days equal) falls back to
    the multiplier rule. A z-score is undefined with zero variance, so
    ``today > baseline_mean * flat_multiplier`` stands in."""
    daily = {
        "2026-06-17": 5.0,
        "2026-06-18": 5.0,
        "2026-06-19": 5.0,  # flat baseline, zero variance
        "2026-06-20": 20.0,  # 4x the flat $5/day baseline (> 3x)
    }
    alarm = data.spend_alarm(daily, today=TODAY)
    assert alarm.method == "multiplier"
    assert alarm.level == "alarm"
    assert "daily_anomaly" in alarm.triggered_by
    assert alarm.z_score is None  # no z-score in the flat-history branch
    assert "x the flat" in alarm.detail


def test_spend_alarm_flat_history_within_multiplier_is_ok():
    """Flat baseline, today below the multiplier threshold → ``ok``."""
    daily = {
        "2026-06-17": 5.0,
        "2026-06-18": 5.0,
        "2026-06-19": 5.0,
        "2026-06-20": 10.0,  # 2x — under the 3x flat multiplier
    }
    alarm = data.spend_alarm(daily, today=TODAY)
    assert alarm.method == "multiplier"
    assert alarm.level == "ok"
    assert alarm.triggered_by == ()


def test_spend_alarm_insufficient_baseline():
    """Fewer than min_baseline_days active prior days → no anomaly judgment."""
    daily = {
        "2026-06-19": 5.0,  # only one prior active day (< min 3)
        "2026-06-20": 50.0,  # a spike, but kept under the ceiling
    }
    alarm = data.spend_alarm(daily, today=TODAY)
    assert alarm.level == "insufficient_data"
    assert alarm.method == "none"
    assert "need 3" in alarm.detail


def test_spend_alarm_ceiling_fires_without_baseline():
    """The ceiling trigger is independent of baseline history: a fresh
    install whose month-to-date already exceeds 80% of the ceiling alarms
    even with insufficient daily history."""
    daily = {"2026-06-20": 50.0}
    alarm = data.spend_alarm(daily, today=TODAY, monthly_ceiling=350.0, month_to_date=300.0)
    assert alarm.level == "alarm"
    assert "ceiling" in alarm.triggered_by
    assert "daily_anomaly" not in alarm.triggered_by
    assert alarm.month_to_date == 300.0
    assert alarm.ceiling_pct == pytest.approx(300.0 / 350.0 * 100, abs=0.1)


def test_spend_alarm_ceiling_just_under_threshold_is_ok():
    """Month-to-date below 80% of the ceiling does not trip the gauge."""
    daily = {"2026-06-20": 10.0}
    alarm = data.spend_alarm(daily, today=TODAY, monthly_ceiling=350.0, month_to_date=200.0)
    # 200/350 ≈ 57% < 80% → no ceiling trigger (and no baseline → insufficient)
    assert "ceiling" not in alarm.triggered_by
    assert alarm.level == "insufficient_data"


def test_spend_alarm_month_to_date_summed_from_window_when_not_given():
    """Without an explicit month_to_date, MTD sums the current-month days
    present in ``daily`` (the local-source path)."""
    daily = {
        "2026-05-31": 100.0,  # prior month — excluded from MTD
        "2026-06-01": 10.0,
        "2026-06-20": 5.0,
    }
    alarm = data.spend_alarm(daily, today=TODAY)
    assert alarm.month_to_date == pytest.approx(15.0)


def test_spend_alarm_local_source_notes_ci_blindness():
    daily = {"2026-06-20": 1.0}
    alarm = data.spend_alarm(daily, today=TODAY, source="local")
    assert alarm.source == "local"
    assert "CI spend not counted" in alarm.detail


def test_spend_alarm_account_source_no_blindness_note():
    daily = {"2026-06-20": 1.0}
    alarm = data.spend_alarm(daily, today=TODAY, source="account")
    assert alarm.source == "account"
    assert "CI spend not counted" not in alarm.detail


# --------------------------------------------------------------------------
# read_daily_spend — local usage.jsonl reader
# --------------------------------------------------------------------------


def test_read_daily_spend_buckets_by_ts(tmp_path, monkeypatch):
    """Events keyed by ``ts`` (v1.0 schema) bucket correctly — the field
    discipline that keeps Home from reading zero (#867 class)."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "h"))
    from attune.ops.config import build_config

    home = tmp_path / "h"
    (home / "telemetry").mkdir(parents=True)
    (home / "telemetry" / "usage.jsonl").write_text(
        '{"workflow": "x", "total_cost": 0.40, "ts": "2026-06-20T10:00:00+00:00"}\n'
        '{"workflow": "y", "total_cost": 0.10, "ts": "2026-06-20T12:00:00+00:00"}\n'
        '{"workflow": "z", "total_cost": 1.00, "ts": "2026-06-19T09:00:00+00:00"}\n',
        encoding="utf-8",
    )
    cfg = build_config(project_root=tmp_path, trusted_hosts=("test",))
    daily = data.read_daily_spend(cfg, today=TODAY)
    assert daily["2026-06-20"] == pytest.approx(0.50)
    assert daily["2026-06-19"] == pytest.approx(1.00)


def test_read_daily_spend_legacy_timestamp_fallback(tmp_path, monkeypatch):
    """Archived events using the legacy ``timestamp`` key still bucket."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "h"))
    from attune.ops.config import build_config

    home = tmp_path / "h"
    (home / "telemetry").mkdir(parents=True)
    (home / "telemetry" / "usage.jsonl").write_text(
        '{"workflow": "x", "cost": 0.25, "timestamp": "2026-06-20T10:00:00+00:00"}\n',
        encoding="utf-8",
    )
    cfg = build_config(project_root=tmp_path, trusted_hosts=("test",))
    daily = data.read_daily_spend(cfg, today=TODAY)
    assert daily["2026-06-20"] == pytest.approx(0.25)


def test_read_daily_spend_window_excludes_old_events(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "h"))
    from attune.ops.config import build_config

    home = tmp_path / "h"
    (home / "telemetry").mkdir(parents=True)
    (home / "telemetry" / "usage.jsonl").write_text(
        '{"total_cost": 1.0, "ts": "2026-06-20T10:00:00+00:00"}\n'
        '{"total_cost": 9.0, "ts": "2026-01-01T10:00:00+00:00"}\n',  # far outside 35d
        encoding="utf-8",
    )
    cfg = build_config(project_root=tmp_path, trusted_hosts=("test",))
    daily = data.read_daily_spend(cfg, days=35, today=TODAY)
    assert "2026-06-20" in daily
    assert "2026-01-01" not in daily


def test_read_daily_spend_missing_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "h"))
    from attune.ops.config import build_config

    cfg = build_config(project_root=tmp_path, trusted_hosts=("test",))
    assert data.read_daily_spend(cfg, today=TODAY) == {}


# --------------------------------------------------------------------------
# build_spend_alarm — source precedence
# --------------------------------------------------------------------------


@dataclass
class _FakeCostSummary:
    by_day: list
    month_to_date_usd: float


def test_build_spend_alarm_prefers_account_source(tmp_path, monkeypatch):
    """When a cost summary with by_day is present, the alarm uses the
    account-level series (which sees CI) and reports source=account."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "h"))
    from attune.ops.config import build_config

    cfg = build_config(project_root=tmp_path, trusted_hosts=("test",))
    summary = _FakeCostSummary(
        by_day=[
            (date(2026, 6, 17), 5.0),
            (date(2026, 6, 18), 5.0),
            (date(2026, 6, 19), 5.0),
            (date(2026, 6, 20), 1200.0),
        ],
        month_to_date_usd=1300.0,
    )
    alarm = data.build_spend_alarm(cfg, summary, today=TODAY)
    assert alarm.source == "account"
    assert alarm.level == "alarm"
    assert alarm.month_to_date == 1300.0  # from the summary, not summed window


def test_build_spend_alarm_falls_back_to_local(tmp_path, monkeypatch):
    """No cost summary → read local usage.jsonl, source=local."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "h"))
    from attune.ops.config import build_config

    home = tmp_path / "h"
    (home / "telemetry").mkdir(parents=True)
    (home / "telemetry" / "usage.jsonl").write_text(
        '{"total_cost": 2.0, "ts": "2026-06-20T10:00:00+00:00"}\n',
        encoding="utf-8",
    )
    cfg = build_config(project_root=tmp_path, trusted_hosts=("test",))
    alarm = data.build_spend_alarm(cfg, None, today=TODAY)
    assert alarm.source == "local"
    assert alarm.today_cost == pytest.approx(2.0)


def test_build_spend_alarm_empty_summary_falls_back_to_local(tmp_path, monkeypatch):
    """A cost summary with an empty by_day still falls back to local."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "h"))
    from attune.ops.config import build_config

    cfg = build_config(project_root=tmp_path, trusted_hosts=("test",))
    summary = _FakeCostSummary(by_day=[], month_to_date_usd=0.0)
    alarm = data.build_spend_alarm(cfg, summary, today=TODAY)
    assert alarm.source == "local"


# --------------------------------------------------------------------------
# Home page render
# --------------------------------------------------------------------------


def test_home_renders_spend_alarm_panel(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    pytest.importorskip("jinja2")
    from fastapi.testclient import TestClient

    from attune.ops.config import build_config
    from attune.ops.server import create_app

    home = tmp_path / "attune-home"
    (home / "telemetry").mkdir(parents=True)
    # A populated local log so the panel renders with real numbers (no
    # admin key in the test env → local source).
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).date().isoformat()
    (home / "telemetry" / "usage.jsonl").write_text(
        f'{{"workflow": "x", "total_cost": 1.5, "ts": "{today}T10:00:00+00:00"}}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("ATTUNE_HOME", str(home))
    config = build_config(project_root=tmp_path, trusted_hosts=("testserver", "test"))
    app = create_app(config)
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "API spend watch" in resp.text
    assert "spend-alarm" in resp.text
