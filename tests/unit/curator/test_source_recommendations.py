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


def test_runs_dir_iterdir_oserror_returns_empty(tmp_path, attune_home_tmp, monkeypatch):
    """If iterdir on runs_dir raises, reader returns empty (caps the
    error before any workflow-dir traversal)."""
    from pathlib import Path

    (attune_home_tmp / "ops" / "runs").mkdir(parents=True, exist_ok=True)

    def boom(self):  # noqa: ANN001
        raise OSError("simulated")

    monkeypatch.setattr(Path, "iterdir", boom)
    summary = rec_source.read(project_root=tmp_path)
    assert summary.items == []


def test_workflow_glob_oserror_skips_dir(tmp_path, attune_home_tmp, monkeypatch):
    """If a workflow_dir.glob raises, that dir is skipped but others proceed."""
    from pathlib import Path

    _write_run(
        attune_home_tmp,
        "code-review",
        "good",
        recommendations=[{"kind": "open", "label": "x"}],
    )
    # Make a second workflow dir whose glob will raise.
    _write_run(
        attune_home_tmp,
        "bad-workflow",
        "x",
        recommendations=[{"kind": "open", "label": "y"}],
    )

    original_glob = Path.glob

    def selective_boom(self, pattern):  # noqa: ANN001
        if self.name == "bad-workflow":
            raise OSError("simulated")
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", selective_boom)
    summary = rec_source.read(project_root=tmp_path)
    ids = {item.item_id for item in summary.items}
    # Good workflow's recs still surface; bad-workflow's are skipped.
    assert any("code-review:good" in i for i in ids)
    assert not any("bad-workflow" in i for i in ids)


def test_stat_oserror_on_record_skips_silently(tmp_path, attune_home_tmp, monkeypatch):
    """A stat() failure on a record path should skip that file, not crash."""
    from pathlib import Path

    _write_run(
        attune_home_tmp,
        "code-review",
        "r1",
        recommendations=[{"kind": "open", "label": "x"}],
    )

    original_stat = Path.stat

    def selective_boom(self, *a, **kw):  # noqa: ANN001
        if self.name == "r1.json":
            raise OSError("simulated stat fail")
        return original_stat(self, *a, **kw)

    monkeypatch.setattr(Path, "stat", selective_boom)
    summary = rec_source.read(project_root=tmp_path)
    assert summary.source_id == "recommendations"
    assert summary.items == []


def test_tmp_record_files_skipped(tmp_path, attune_home_tmp):
    """Atomic-replace temp suffixes (.tmp) are skipped on read."""
    runs_dir = attune_home_tmp / "ops" / "runs" / "code-review"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "abc.json.tmp").write_text(
        json.dumps({"run_id": "abc", "recommendations": [{"kind": "open", "label": "x"}]}),
        encoding="utf-8",
    )
    summary = rec_source.read(project_root=tmp_path)
    assert summary.items == []


def test_non_dict_payload_skipped(tmp_path, attune_home_tmp):
    """A JSON record whose top-level isn't a dict produces zero items."""
    runs_dir = attune_home_tmp / "ops" / "runs" / "code-review"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "r1.json").write_text('["not", "dict"]', encoding="utf-8")
    summary = rec_source.read(project_root=tmp_path)
    assert summary.items == []


def test_non_dict_recommendation_entries_skipped(tmp_path, attune_home_tmp):
    """recommendations: [<string>, ...] entries get skipped (non-dict)."""
    _write_run(
        attune_home_tmp,
        "code-review",
        "r1",
        recommendations=[
            "not-a-dict",  # type: ignore[list-item]
            {"kind": "open", "label": "valid"},
        ],
    )
    summary = rec_source.read(project_root=tmp_path)
    # Only the valid one surfaces.
    assert len(summary.items) == 1


def test_max_items_cap_truncates(tmp_path, attune_home_tmp):
    """When a single run carries >50 recommendations, the per-file
    extension still respects the global cap on the next iteration."""
    # Spread 60 recs across two runs to force the post-extend truncation
    # plus the outer break.
    _write_run(
        attune_home_tmp,
        "wf-a",
        "r1",
        recommendations=[{"kind": "open", "label": f"a{i}"} for i in range(30)],
    )
    _write_run(
        attune_home_tmp,
        "wf-b",
        "r2",
        recommendations=[{"kind": "open", "label": f"b{i}"} for i in range(30)],
    )
    summary = rec_source.read(project_root=tmp_path)
    assert len(summary.items) == 50
