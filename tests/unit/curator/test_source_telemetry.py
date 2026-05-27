"""Tests for the telemetry source reader."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.curator.sources import telemetry as telemetry_source


def _write_events(attune_home_dir: Path, events: list[dict]) -> None:
    tel_dir = attune_home_dir / "telemetry"
    tel_dir.mkdir(parents=True, exist_ok=True)
    path = tel_dir / "usage.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")


@pytest.fixture
def attune_home_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    return tmp_path


def test_missing_usage_file_returns_empty(tmp_path, attune_home_tmp):
    summary = telemetry_source.read(project_root=tmp_path)
    assert summary.source_id == "telemetry"
    assert summary.items == []


def test_cost_spike_fires_above_two_sigma(tmp_path, attune_home_tmp):
    now = datetime.now(timezone.utc)
    today_iso = now.isoformat()
    # Realistic varied prior days (~$0.05-0.15 range), today at $5.00.
    prior_costs = [0.05, 0.08, 0.12, 0.06, 0.10, 0.15]
    prior_events = [
        {
            "ts": (now - timedelta(days=d + 1)).isoformat(),
            "workflow": "code-review",
            "total_cost": cost,
        }
        for d, cost in enumerate(prior_costs)
    ]
    today_event = {"ts": today_iso, "workflow": "code-review", "total_cost": 5.00}
    _write_events(attune_home_tmp, prior_events + [today_event])

    summary = telemetry_source.read(project_root=tmp_path)
    spike_items = [i for i in summary.items if i.metadata["kind"] == "cost_spike"]
    assert len(spike_items) == 1
    assert spike_items[0].metadata["workflow"] == "code-review"


def test_no_spike_when_sample_too_small(tmp_path, attune_home_tmp):
    now = datetime.now(timezone.utc)
    # Only one prior day → samples < 3, skip the workflow.
    events = [
        {
            "ts": (now - timedelta(days=1)).isoformat(),
            "workflow": "code-review",
            "total_cost": 0.01,
        },
        {"ts": now.isoformat(), "workflow": "code-review", "total_cost": 5.0},
    ]
    _write_events(attune_home_tmp, events)
    summary = telemetry_source.read(project_root=tmp_path)
    assert not any(i.metadata["kind"] == "cost_spike" for i in summary.items)


def test_error_event_in_last_hour_surfaces(tmp_path, attune_home_tmp):
    now = datetime.now(timezone.utc)
    events = [
        {
            "ts": (now - timedelta(minutes=10)).isoformat(),
            "workflow": "code-review",
            "status": 500,
            "error": "boom",
        },
    ]
    _write_events(attune_home_tmp, events)
    summary = telemetry_source.read(project_root=tmp_path)
    err_items = [i for i in summary.items if i.metadata["kind"] == "error"]
    assert len(err_items) == 1
    assert err_items[0].metadata["status"] == "500"


def test_old_error_excluded(tmp_path, attune_home_tmp):
    now = datetime.now(timezone.utc)
    events = [
        {
            "ts": (now - timedelta(hours=3)).isoformat(),
            "workflow": "code-review",
            "status": 500,
            "error": "ancient",
        },
    ]
    _write_events(attune_home_tmp, events)
    summary = telemetry_source.read(project_root=tmp_path)
    assert not any(i.metadata["kind"] == "error" for i in summary.items)


def test_caps_items_at_ten(tmp_path, attune_home_tmp):
    now = datetime.now(timezone.utc)
    events = [
        {
            "ts": (now - timedelta(minutes=i)).isoformat(),
            "workflow": f"wf-{i}",
            "status": 500,
            "error": "err",
        }
        for i in range(20)
    ]
    _write_events(attune_home_tmp, events)
    summary = telemetry_source.read(project_root=tmp_path)
    assert len(summary.items) <= 10


def test_no_recent_events_returns_empty(tmp_path, attune_home_tmp):
    """If usage.jsonl exists but every event is older than the cutoff,
    return the canonical empty summary."""
    long_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    _write_events(
        attune_home_tmp,
        [{"ts": long_ago, "workflow": "code-review", "total_cost": 0.05}],
    )
    summary = telemetry_source.read(project_root=tmp_path)
    assert summary.items == []


def test_malformed_and_empty_lines_skipped(tmp_path, attune_home_tmp):
    """Empty lines and lines that fail json.loads are silently skipped."""
    telemetry_dir = attune_home_tmp / "telemetry"
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    valid = {"ts": now.isoformat(), "workflow": "code-review", "total_cost": 0.05}
    with (telemetry_dir / "usage.jsonl").open("w", encoding="utf-8") as fh:
        fh.write("\n")
        fh.write("not-json\n")
        fh.write("[1, 2, 3]\n")  # not a dict
        fh.write(json.dumps(valid) + "\n")
    summary = telemetry_source.read(project_root=tmp_path)
    # The lone valid event has no error / no spike — no items but no crash.
    assert summary.source_id == "telemetry"


def test_event_without_ts_skipped(tmp_path, attune_home_tmp):
    """An event missing both 'ts' and 'timestamp' falls through the
    cutoff filter."""
    _write_events(
        attune_home_tmp,
        [{"workflow": "code-review", "total_cost": 1.0}],
    )
    summary = telemetry_source.read(project_root=tmp_path)
    assert summary.items == []


def test_usage_jsonl_oserror_returns_empty(tmp_path, attune_home_tmp, monkeypatch):
    """An OSError while reading usage.jsonl collapses to empty summary."""
    telemetry_dir = attune_home_tmp / "telemetry"
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    (telemetry_dir / "usage.jsonl").write_text(
        json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "workflow": "code-review",
                "total_cost": 0.05,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    real_open = Path.open

    def boom(self, *args, **kwargs):  # noqa: ANN001
        if self.name == "usage.jsonl":
            raise OSError("simulated read failure")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", boom)
    summary = telemetry_source.read(project_root=tmp_path)
    assert summary.items == []


def test_cost_spike_zero_variance_skipped(tmp_path, attune_home_tmp):
    """Six identical prior days (variance=0) + spike today produces no
    cost-spike item. Documents the z-score-on-zero-variance behaviour
    (see CLAUDE.md lesson)."""
    now = datetime.now(timezone.utc)
    prior_events = [
        {
            "ts": (now - timedelta(days=d + 1)).isoformat(),
            "workflow": "flat-workflow",
            "total_cost": 0.01,
        }
        for d in range(6)
    ]
    today = {"ts": now.isoformat(), "workflow": "flat-workflow", "total_cost": 5.00}
    _write_events(attune_home_tmp, prior_events + [today])
    summary = telemetry_source.read(project_root=tmp_path)
    assert not any(i.metadata.get("kind") == "cost_spike" for i in summary.items)


def test_cost_below_two_sigma_skipped(tmp_path, attune_home_tmp):
    """A spike that's < 2σ above the prior mean is filtered out."""
    now = datetime.now(timezone.utc)
    prior_costs = [0.05, 0.08, 0.12, 0.06, 0.10, 0.15]
    prior_events = [
        {
            "ts": (now - timedelta(days=d + 1)).isoformat(),
            "workflow": "code-review",
            "total_cost": cost,
        }
        for d, cost in enumerate(prior_costs)
    ]
    # Today's cost is only slightly above mean — well under 2σ.
    today = {"ts": now.isoformat(), "workflow": "code-review", "total_cost": 0.12}
    _write_events(attune_home_tmp, prior_events + [today])
    summary = telemetry_source.read(project_root=tmp_path)
    assert not any(i.metadata.get("kind") == "cost_spike" for i in summary.items)


def test_integer_status_in_5xx_range_fires_error_without_error_field(tmp_path, attune_home_tmp):
    """An integer 500-599 status (no 'error' key) hits the int-status
    branch of _is_error."""
    now = datetime.now(timezone.utc)
    _write_events(
        attune_home_tmp,
        [
            {
                "ts": (now - timedelta(seconds=30)).isoformat(),
                "workflow": "code-review",
                "status": 502,  # int, no 'error' field
            }
        ],
    )
    summary = telemetry_source.read(project_root=tmp_path)
    errors = [i for i in summary.items if i.metadata["kind"] == "error"]
    assert len(errors) == 1
    assert errors[0].metadata["status"] == "502"


def test_string_status_in_4xx_range_fires_error(tmp_path, attune_home_tmp):
    """Status field present as a digit-string (e.g. '503') fires the
    error path."""
    now = datetime.now(timezone.utc)
    _write_events(
        attune_home_tmp,
        [
            {
                "ts": (now - timedelta(seconds=30)).isoformat(),
                "workflow": "code-review",
                "status": "503",
            }
        ],
    )
    summary = telemetry_source.read(project_root=tmp_path)
    errors = [i for i in summary.items if i.metadata["kind"] == "error"]
    assert len(errors) == 1


def test_string_status_non_error_ignored(tmp_path, attune_home_tmp):
    """A '200' status string doesn't fire the error path."""
    now = datetime.now(timezone.utc)
    _write_events(
        attune_home_tmp,
        [
            {
                "ts": (now - timedelta(seconds=30)).isoformat(),
                "workflow": "code-review",
                "status": "200",
            }
        ],
    )
    summary = telemetry_source.read(project_root=tmp_path)
    assert summary.items == []


def test_safe_float_coerces_bad_values():
    """Direct unit test of _safe_float — bad inputs collapse to 0.0."""
    import attune.curator.sources.telemetry as tmod

    assert tmod._safe_float("not-a-number") == 0.0
    assert tmod._safe_float(None) == 0.0
    assert tmod._safe_float(3.14) == 3.14


def test_parse_iso_helpers():
    """_parse_iso returns None on bad input; coerces naive to UTC."""
    import attune.curator.sources.telemetry as tmod

    assert tmod._parse_iso("bad") is None
    naive_dt = tmod._parse_iso("2026-05-26T12:00:00")
    assert naive_dt is not None and naive_dt.tzinfo is not None
