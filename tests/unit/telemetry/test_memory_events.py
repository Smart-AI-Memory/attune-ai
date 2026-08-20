"""Behavioral tests for the src-side memory-events writer.

QA pass (test-quality-program #1569): 76% → target ~100% on
``attune.telemetry.memory_events`` — the rotation branch, the
session-id cap, the consent gate, and the never-raises contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.telemetry.memory_events import _MAX_BYTES, log_memory_event


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated ATTUNE_HOME with the consent env vars cleared."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("ATTUNE_MEMORY_TELEMETRY", raising=False)
    return tmp_path


def _events_file(home: Path) -> Path:
    return home / "telemetry" / "memory_events.jsonl"


def _lines(home: Path) -> list[dict]:
    return [
        json.loads(line) for line in _events_file(home).read_text(encoding="utf-8").splitlines()
    ]


class TestAppend:
    def test_record_shape_and_key_order(self, home: Path) -> None:
        log_memory_event("memory_feedback", verdict="rejected", count=2)
        (record,) = _lines(home)
        assert list(record) == ["v", "ts", "event", "verdict", "count"]
        assert record["v"] == "1.0"
        assert record["event"] == "memory_feedback"
        assert record["verdict"] == "rejected"
        assert record["count"] == 2
        assert record["ts"].endswith("Z")

    def test_reserved_keys_cannot_be_clobbered_by_fields(self, home: Path) -> None:
        """Regression: library review checkpoint-1 R2 hit (forms form_events
        sibling class) — **fields must not overwrite v/ts/event/session_id."""
        log_memory_event(
            "memory_feedback",
            session_id="real",
            v="FORGED",
            ts="1970-01-01T00:00:00Z",
            verdict="keep",
        )
        (record,) = _lines(home)
        assert record["v"] == "1.0"
        assert record["ts"] != "1970-01-01T00:00:00Z"
        assert record["event"] == "memory_feedback"
        assert record["session_id"] == "real"
        assert record["verdict"] == "keep"

    def test_lines_are_compact_json(self, home: Path) -> None:
        log_memory_event("memory_feedback", source="review")
        raw = _events_file(home).read_text(encoding="utf-8")
        assert raw.endswith("\n")
        assert ", " not in raw and ": " not in raw  # compact separators

    def test_session_id_recorded_and_capped_at_64(self, home: Path) -> None:
        log_memory_event("memory_feedback", session_id="s" * 100)
        (record,) = _lines(home)
        assert record["session_id"] == "s" * 64

    def test_no_session_id_key_when_absent(self, home: Path) -> None:
        log_memory_event("memory_feedback")
        (record,) = _lines(home)
        assert "session_id" not in record

    def test_non_json_field_serialized_via_str(self, home: Path) -> None:
        log_memory_event("memory_feedback", cwd=Path("/tmp/proj"))
        (record,) = _lines(home)
        assert record["cwd"] == str(Path("/tmp/proj"))

    def test_appends_preserve_existing_lines(self, home: Path) -> None:
        log_memory_event("memory_feedback", n=1)
        log_memory_event("memory_feedback", n=2)
        assert [r["n"] for r in _lines(home)] == [1, 2]


class TestConsentGate:
    def test_do_not_track_disables(self, home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DO_NOT_TRACK", "1")
        log_memory_event("memory_feedback")
        assert not _events_file(home).exists()

    def test_falsey_do_not_track_still_records(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DO_NOT_TRACK", "0")
        log_memory_event("memory_feedback")
        assert _events_file(home).exists()

    def test_memory_telemetry_env_disables(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_MEMORY_TELEMETRY", "off")
        log_memory_event("memory_feedback")
        assert not _events_file(home).exists()


class TestRotation:
    def test_huge_file_rotates_to_dated_sibling(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("attune.telemetry.memory_events._MAX_BYTES", 10)
        path = _events_file(home)
        path.parent.mkdir(parents=True)
        path.write_text('{"event":"old-line-well-over-ten-bytes"}\n', encoding="utf-8")
        log_memory_event("memory_feedback", fresh=True)
        rotated = list(path.parent.glob("memory_events.*.jsonl"))
        assert len(rotated) == 1
        assert "old-line" in rotated[0].read_text(encoding="utf-8")
        (record,) = _lines(home)  # live file holds only the new event
        assert record["fresh"] is True

    def test_rotation_counter_avoids_collision(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from datetime import datetime, timezone

        monkeypatch.setattr("attune.telemetry.memory_events._MAX_BYTES", 10)
        path = _events_file(home)
        path.parent.mkdir(parents=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        occupied = path.with_name(f"memory_events.{stamp}.jsonl")
        occupied.write_text("taken\n", encoding="utf-8")
        path.write_text('{"event":"old-line-well-over-ten-bytes"}\n', encoding="utf-8")
        log_memory_event("memory_feedback")
        counter_file = path.with_name(f"memory_events.{stamp}.1.jsonl")
        assert counter_file.exists()
        assert "old-line" in counter_file.read_text(encoding="utf-8")
        assert occupied.read_text(encoding="utf-8") == "taken\n"

    def test_small_file_never_rotates(self, home: Path) -> None:
        log_memory_event("memory_feedback", n=1)
        log_memory_event("memory_feedback", n=2)
        assert list(_events_file(home).parent.glob("memory_events.*.jsonl")) == []
        assert _MAX_BYTES == 5 * 1024 * 1024  # backstop, not an expected path

    def test_rotation_oserror_still_appends(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("attune.telemetry.memory_events._MAX_BYTES", 10)
        path = _events_file(home)
        path.parent.mkdir(parents=True)
        path.write_text('{"event":"old-line-well-over-ten-bytes"}\n', encoding="utf-8")

        def deny(self: Path, target: Path) -> None:
            raise OSError("rename denied")

        monkeypatch.setattr(Path, "replace", deny)
        log_memory_event("memory_feedback", fresh=True)
        records = _lines(home)  # rotation failed silently; append landed
        assert records[-1]["fresh"] is True
        assert len(records) == 2


class TestNeverRaises:
    def test_unwritable_telemetry_dir_swallowed(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A FILE squatting on the telemetry dir path → mkdir raises →
        swallowed; the caller must never see an exception."""
        (home / "telemetry").parent.mkdir(parents=True, exist_ok=True)
        (home / "telemetry").write_text("not a dir", encoding="utf-8")
        log_memory_event("memory_feedback")  # must not raise
        assert (home / "telemetry").is_file()
