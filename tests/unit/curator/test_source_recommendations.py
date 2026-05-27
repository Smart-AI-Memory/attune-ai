"""Tests for the recommendations source reader."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.curator.sources import recommendations as rec_source


def _write_run(
    attune_home_dir: Path,
    workflow: str,
    run_id: str,
    *,
    recommendations: list[dict] | None = None,
    mtime_offset_hours: float = 0.0,
) -> Path:
    runs_dir = attune_home_dir / "ops" / "runs" / workflow
    runs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "workflow": workflow,
        "recommendations": recommendations or [],
    }
    path = runs_dir / f"{run_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    if mtime_offset_hours:
        target = time.time() + mtime_offset_hours * 3600
        os.utime(path, (target, target))
    return path


@pytest.fixture
def attune_home_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    return tmp_path


def test_missing_runs_dir_returns_empty(tmp_path, attune_home_tmp):
    summary = rec_source.read(project_root=tmp_path)
    assert summary.source_id == "recommendations"
    assert summary.items == []
    assert len(summary.state_hash) == 16


def test_emits_one_item_per_recommendation(tmp_path, attune_home_tmp):
    _write_run(
        attune_home_tmp,
        "code-review",
        "r1",
        recommendations=[
            {"kind": "open", "label": "Review fix", "url": "/runs/r1/view"},
            {"kind": "run", "label": "Re-run", "workflow": "code-review"},
        ],
    )
    summary = rec_source.read(project_root=tmp_path)
    assert len(summary.items) == 2
    ids = {item.item_id for item in summary.items}
    assert ids == {"rec:code-review:r1:0", "rec:code-review:r1:1"}


def test_old_runs_excluded(tmp_path, attune_home_tmp):
    _write_run(
        attune_home_tmp,
        "code-review",
        "old",
        recommendations=[{"kind": "open", "label": "stale"}],
        mtime_offset_hours=-48,  # 2 days old
    )
    _write_run(
        attune_home_tmp,
        "code-review",
        "fresh",
        recommendations=[{"kind": "open", "label": "fresh"}],
    )
    summary = rec_source.read(project_root=tmp_path)
    ids = {item.item_id for item in summary.items}
    assert "rec:code-review:fresh:0" in ids
    assert "rec:code-review:old:0" not in ids


def test_runs_without_recommendations_skipped(tmp_path, attune_home_tmp):
    _write_run(attune_home_tmp, "code-review", "r1", recommendations=[])
    summary = rec_source.read(project_root=tmp_path)
    assert summary.items == []


def test_state_hash_deterministic(tmp_path, attune_home_tmp):
    _write_run(
        attune_home_tmp,
        "code-review",
        "r1",
        recommendations=[{"kind": "open", "label": "x"}],
    )
    a = rec_source.read(project_root=tmp_path).state_hash
    b = rec_source.read(project_root=tmp_path).state_hash
    assert a == b


def test_malformed_record_skipped(tmp_path, attune_home_tmp):
    runs_dir = attune_home_tmp / "ops" / "runs" / "code-review"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "bad.json").write_text("not-json", encoding="utf-8")
    _write_run(
        attune_home_tmp,
        "code-review",
        "good",
        recommendations=[{"kind": "open", "label": "g"}],
    )
    summary = rec_source.read(project_root=tmp_path)
    assert len(summary.items) == 1
    assert summary.items[0].item_id == "rec:code-review:good:0"


def test_since_param_overrides_default(tmp_path, attune_home_tmp):
    _write_run(
        attune_home_tmp,
        "code-review",
        "old",
        recommendations=[{"kind": "open", "label": "x"}],
        mtime_offset_hours=-48,
    )
    # since=72h ago — pulls in the 48h-old record.
    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
    summary = rec_source.read(project_root=tmp_path, since=cutoff)
    assert len(summary.items) == 1
