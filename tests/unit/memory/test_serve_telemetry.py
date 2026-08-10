"""Tests for curated serve telemetry (memory-status-integrity P3 task 2).

Hermetic: ``ATTUNE_HOME`` is monkeypatched to ``tmp_path`` so nothing
touches the real telemetry sink, and every failure path must FAIL OPEN.
"""

from __future__ import annotations

import json
from pathlib import Path

from attune.memory.serve_telemetry import (
    CURATED_RECALL_EVENT,
    MAX_STEMS_PER_EVENT,
    log_curated_recall,
)


def _events_file(tmp_path: Path) -> Path:
    return tmp_path / "telemetry" / "memory_events.jsonl"


def _read_records(tmp_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in _events_file(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class TestLogCuratedRecall:
    def test_writes_a_well_formed_record(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        monkeypatch.delenv("DO_NOT_TRACK", raising=False)
        ok = log_curated_recall(["project_a", "feedback_b"], "personal_query", session_id="s1")
        assert ok is True
        records = _read_records(tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["event"] == CURATED_RECALL_EVENT
        assert rec["v"] == "1.0"
        assert rec["ts"].endswith("Z")
        assert rec["surface"] == "personal_query"
        assert rec["stems"] == ["project_a", "feedback_b"]
        assert rec["entries"] == 2
        assert rec["session_id"] == "s1"

    def test_appends_share_one_stream(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        log_curated_recall(["a"], "personal_query")
        log_curated_recall(["b"], "recall_digest")
        surfaces = [r["surface"] for r in _read_records(tmp_path)]
        assert surfaces == ["personal_query", "recall_digest"]

    def test_stems_only_never_content(self, tmp_path, monkeypatch) -> None:
        """The event is a counter, not a copy — nothing but the envelope
        fields and stems may appear in the record."""
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        log_curated_recall(["project_a"], "personal_query")
        rec = _read_records(tmp_path)[0]
        assert set(rec) == {"v", "ts", "event", "surface", "stems", "entries"}

    def test_do_not_track_disables(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        monkeypatch.setenv("DO_NOT_TRACK", "1")
        assert log_curated_recall(["a"], "personal_query") is False
        assert not _events_file(tmp_path).exists()

    def test_telemetry_off_switch_disables(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        monkeypatch.setenv("ATTUNE_MEMORY_TELEMETRY", "0")
        assert log_curated_recall(["a"], "personal_query") is False
        assert not _events_file(tmp_path).exists()

    def test_empty_or_blank_stems_write_nothing(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        assert log_curated_recall([], "personal_query") is False
        assert log_curated_recall(["", ""], "personal_query") is False
        assert not _events_file(tmp_path).exists()

    def test_stem_cap_is_enforced(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        log_curated_recall([f"s{i}" for i in range(200)], "personal_query")
        rec = _read_records(tmp_path)[0]
        assert rec["entries"] == MAX_STEMS_PER_EVENT

    def test_session_id_truncated(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        log_curated_recall(["a"], "personal_query", session_id="x" * 200)
        assert len(_read_records(tmp_path)[0]["session_id"]) == 64

    def test_unwritable_home_fails_open(self, tmp_path, monkeypatch) -> None:
        """ATTUNE_HOME pointing at a FILE makes mkdir fail — must degrade
        to False, never raise into the recall path."""
        blocker = tmp_path / "not_a_dir"
        blocker.write_text("x", encoding="utf-8")
        monkeypatch.setenv("ATTUNE_HOME", str(blocker))
        assert log_curated_recall(["a"], "personal_query") is False


class TestSurfaceWiring:
    def test_personal_query_emits_served_stems(self, tmp_path, monkeypatch) -> None:
        from unittest.mock import patch

        from attune.memory.personal import PersonalMemory
        from tests.unit.memory.test_personal_memory import _make_fake_rag

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        root = tmp_path / "global"
        (root / "topic").mkdir(parents=True)
        (root / "topic" / "project_served.md").write_text(
            "---\nname: project_served\ndescription: d\nmetadata:\n  type: project\n---\n\nBody.\n",
            encoding="utf-8",
        )
        pm = PersonalMemory(global_root=root)
        fake = _make_fake_rag(
            [{"path": "topic/project_served.md", "summary": "d", "excerpt": "", "score": 0.9}]
        )
        with patch("attune.memory.personal._load_rag", return_value=fake):
            hits = pm.query("served")
        assert hits, "fixture must produce at least one hit"
        recs = [r for r in _read_records(tmp_path) if r["event"] == CURATED_RECALL_EVENT]
        assert recs and recs[-1]["surface"] == "personal_query"
        assert "project_served" in recs[-1]["stems"]

    def test_recall_digest_fetch_emits_node_names(self, tmp_path, monkeypatch) -> None:
        from attune.memory.recall_digest import fetch_digest_nodes

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))

        class _Client:
            def fcall(self, fn, numkeys, count):
                return [json.dumps({"name": "node_a", "type": "project"})]

        nodes = fetch_digest_nodes(count=1, client=_Client())
        assert nodes[0]["name"] == "node_a"
        recs = [r for r in _read_records(tmp_path) if r["event"] == CURATED_RECALL_EVENT]
        assert recs and recs[-1]["surface"] == "recall_digest"
        assert recs[-1]["stems"] == ["node_a"]
