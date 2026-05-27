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
