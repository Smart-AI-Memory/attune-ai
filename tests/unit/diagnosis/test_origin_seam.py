"""D18 origin-tag + closure seam — contract tests.

Real store round-trips against a tmp stream file; no Redis, no LLM.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.diagnosis.annotate import retag_origin
from attune.diagnosis.store import load_diagnoses
from attune.models.telemetry.data_models import DiagnosisRecord

NOW = (datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc) + timedelta(hours=1)).isoformat()


def _record(diagnosis_id: str, **overrides) -> DiagnosisRecord:
    base = {
        "diagnosis_id": diagnosis_id,
        "source_run_id": f"run-{diagnosis_id}",
        "workflow_name": "code-review",
        "created_at": NOW,
    }
    base.update(overrides)
    return DiagnosisRecord(**base)


def _write_stream(path: Path, *records: DiagnosisRecord) -> Path:
    path.write_text(
        "".join(json.dumps(r.to_dict()) + "\n" for r in records),
        encoding="utf-8",
    )
    return path


class TestOriginField:
    def test_default_is_operational(self):
        assert _record("aaa").origin == "operational"

    def test_legacy_record_without_origin_loads_operational(self, tmp_path):
        raw = _record("bbb").to_dict()
        raw.pop("origin")
        stream = tmp_path / "s.jsonl"
        stream.write_text(json.dumps(raw) + "\n", encoding="utf-8")
        records, stats = load_diagnoses(stream)
        assert stats.eligible == 1
        assert records[0].origin == "operational"


class TestLastWinsDedupe:
    def test_reappended_record_supersedes(self, tmp_path):
        stream = _write_stream(
            tmp_path / "s.jsonl",
            _record("ccc", status="open"),
            _record("ccc", status="open", origin="live-fire"),
        )
        records, stats = load_diagnoses(stream)
        assert len(records) == 1
        assert records[0].origin == "live-fire"
        assert stats.eligible == 1
        assert stats.dropped_superseded == 1

    def test_distinct_ids_all_kept(self, tmp_path):
        stream = _write_stream(tmp_path / "s.jsonl", _record("d1"), _record("d2"))
        records, stats = load_diagnoses(stream)
        assert {r.diagnosis_id for r in records} == {"d1", "d2"}
        assert stats.dropped_superseded == 0


class TestRetagOrigin:
    def test_round_trip_retag(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        stream = tmp_path / "telemetry" / "diagnosis_records.jsonl"
        stream.parent.mkdir(parents=True)
        _write_stream(stream, _record("eee"))
        updated = retag_origin("eee", "dogfood")
        assert updated is not None and updated.origin == "dogfood"
        records, stats = load_diagnoses()
        assert records[0].origin == "dogfood"
        assert stats.dropped_superseded == 1

    def test_unknown_id_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        assert retag_origin("nope", "dogfood") is None

    def test_invalid_origin_raises(self):
        with pytest.raises(ValueError, match="D18 vocabulary"):
            retag_origin("any", "test-run")


class TestSourceFilter:
    def test_non_operational_records_excluded_from_briefing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        stream = tmp_path / "telemetry" / "diagnosis_records.jsonl"
        stream.parent.mkdir(parents=True)
        _write_stream(
            stream,
            _record("op1"),
            _record("lf1", origin="live-fire"),
            _record("df1", origin="dogfood"),
        )
        from attune.curator.sources import diagnoses as source

        summary = source.read(project_root=tmp_path)
        ids = [str(i.item_id) for i in summary.items]
        assert ids == ["diagnosis:op1"]
