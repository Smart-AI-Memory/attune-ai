"""Tests for the discovery-sweep source reader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.curator.sources import sweep as sweep_source


def _write_sweep(attune_home_dir: Path, scope_digest: str, payload: dict) -> None:
    results = attune_home_dir / "ops" / "sweep-results"
    results.mkdir(parents=True, exist_ok=True)
    (results / f"{scope_digest}.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def attune_home_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    return tmp_path


def test_empty_results_dir_returns_empty(tmp_path, attune_home_tmp):
    summary = sweep_source.read(project_root=tmp_path)
    assert summary.source_id == "sweep"
    assert summary.items == []
    assert len(summary.state_hash) == 16


def test_emits_queue_and_questions_skips_rejected(tmp_path, attune_home_tmp):
    _write_sweep(
        attune_home_tmp,
        "abc123",
        {
            "queue": [
                {
                    "source": "bug-predict",
                    "severity": "high",
                    "title": "race condition in foo",
                    "description": "...",
                    "file": "src/a.py",
                    "line": 12,
                    "confidence": 0.8,
                },
            ],
            "questions": [
                {
                    "finding": {
                        "source": "security-audit",
                        "severity": "medium",
                        "title": "weak token check",
                        "description": "...",
                        "file": "src/b.py",
                        "line": 30,
                        "confidence": 0.5,
                    },
                    "reason": "LOW_CONFIDENCE",
                    "next_step": "review",
                },
            ],
            "rejected": [
                {
                    "finding": {
                        "source": "bug-predict",
                        "severity": "low",
                        "title": "noise",
                        "description": "...",
                        "file": "src/c.py",
                    },
                    "rule": "SEVERITY_BELOW_THRESHOLD",
                },
            ],
        },
    )
    summary = sweep_source.read(project_root=tmp_path)
    buckets = {item.metadata["bucket"] for item in summary.items}
    assert buckets == {"queue", "questions"}
    assert len(summary.items) == 2


def test_malformed_file_skipped(tmp_path, attune_home_tmp):
    results = attune_home_tmp / "ops" / "sweep-results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "bad.json").write_text("not-json", encoding="utf-8")
    _write_sweep(
        attune_home_tmp,
        "good",
        {
            "queue": [
                {"source": "bug-predict", "severity": "high", "title": "x"},
            ]
        },
    )
    summary = sweep_source.read(project_root=tmp_path)
    assert len(summary.items) == 1


def test_state_hash_deterministic(tmp_path, attune_home_tmp):
    _write_sweep(
        attune_home_tmp,
        "abc",
        {"queue": [{"source": "x", "severity": "high", "title": "t"}]},
    )
    a = sweep_source.read(project_root=tmp_path).state_hash
    b = sweep_source.read(project_root=tmp_path).state_hash
    assert a == b


def test_caps_at_50_items(tmp_path, attune_home_tmp):
    findings = [
        {"source": "bug-predict", "severity": "info", "title": f"f-{i}"} for i in range(100)
    ]
    _write_sweep(attune_home_tmp, "big", {"queue": findings})
    summary = sweep_source.read(project_root=tmp_path)
    assert len(summary.items) == 50
