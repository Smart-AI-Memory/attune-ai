"""Edge coverage for the diagnosis store and priors recall.

Targets the drop-counting paths in ``attune.diagnosis.store`` (every
``DiagnosisLoadStats`` counter, unreadable stream, last-wins
supersede) and the degrade paths in ``attune.diagnosis.priors``
(missing redis package, client construction from ``REDIS_URL``,
transport failure, and FT.SEARCH reply-shape defenses). All keyless
and network-free.
"""

from __future__ import annotations

import json
import sys
from datetime import timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from attune.diagnosis.priors import (
    _parse_search_reply,
    extract_error_terms,
    recall_priors,
)
from attune.diagnosis.store import (
    _parse_created_at,
    load_diagnoses,
    records_for_run,
)
from attune.pipeline_learner.corpus import FIXTURE_NAMES

_ELIGIBLE_AT = "2026-07-21T00:00:00+00:00"


def _record_line(
    diagnosis_id: str = "d1",
    *,
    source_run_id: str = "r1",
    workflow_name: str = "code-review",
    created_at: str = _ELIGIBLE_AT,
    symptom: str = "boom",
    **extra: object,
) -> str:
    data: dict[str, object] = {
        "diagnosis_id": diagnosis_id,
        "source_run_id": source_run_id,
        "workflow_name": workflow_name,
        "created_at": created_at,
        "symptom": symptom,
    }
    data.update(extra)
    return json.dumps(data)


class TestParseCreatedAt:
    def test_non_string(self) -> None:
        assert _parse_created_at(None) is None
        assert _parse_created_at(12345) is None
        assert _parse_created_at("") is None

    def test_invalid_iso(self) -> None:
        assert _parse_created_at("not-a-date") is None

    def test_naive_timestamp_gets_utc(self) -> None:
        parsed = _parse_created_at("2026-07-21T00:00:00")
        assert parsed is not None
        assert parsed.tzinfo is timezone.utc


class TestLoadDiagnosesDrops:
    def test_every_drop_counter_fires(self, tmp_path: Path) -> None:
        fixture_name = sorted(FIXTURE_NAMES)[0]
        stream = tmp_path / "diagnosis_records.jsonl"
        stream.write_text(
            "\n".join(
                [
                    _record_line("d-good"),
                    "",  # blank — skipped entirely, not counted
                    "{not json",  # malformed JSON
                    json.dumps([1, 2]),  # not a dict
                    json.dumps({"workflow_name": "", "created_at": _ELIGIBLE_AT}),
                    _record_line("d-fix", workflow_name=fixture_name),
                    _record_line("d-old", created_at="2026-01-01T00:00:00+00:00"),
                    # Required fields missing -> from_dict raises TypeError.
                    json.dumps({"workflow_name": "w", "created_at": _ELIGIBLE_AT}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        records, stats = load_diagnoses(stream)

        assert [r.diagnosis_id for r in records] == ["d-good"]
        assert stats.total_lines == 7  # blank line never counted
        assert stats.eligible == 1
        assert stats.dropped_malformed == 4
        assert stats.dropped_fixture == 1
        assert stats.dropped_pre_cutover == 1
        assert stats.dropped_superseded == 0

    def test_last_wins_supersede_counted(self, tmp_path: Path) -> None:
        stream = tmp_path / "diagnosis_records.jsonl"
        stream.write_text(
            _record_line("d1", symptom="first")
            + "\n"
            + _record_line("d1", symptom="second")
            + "\n",
            encoding="utf-8",
        )
        records, stats = load_diagnoses(stream)
        assert len(records) == 1
        assert records[0].symptom == "second"
        assert stats.eligible == 1
        assert stats.dropped_superseded == 1

    def test_missing_file(self, tmp_path: Path) -> None:
        records, stats = load_diagnoses(tmp_path / "absent.jsonl")
        assert records == []
        assert stats.total_lines == 0

    def test_unreadable_stream_degrades(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stream = tmp_path / "diagnosis_records.jsonl"
        stream.write_text(_record_line() + "\n", encoding="utf-8")

        def _boom(self: Path, *args: object, **kwargs: object) -> str:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "read_text", _boom)
        records, stats = load_diagnoses(stream)
        assert records == []
        assert stats.total_lines == 0

    def test_records_for_run_filters(self, tmp_path: Path) -> None:
        stream = tmp_path / "diagnosis_records.jsonl"
        stream.write_text(
            _record_line("d1", source_run_id="r1")
            + "\n"
            + _record_line("d2", source_run_id="r2")
            + "\n",
            encoding="utf-8",
        )
        matched = records_for_run("r2", stream)
        assert [r.diagnosis_id for r in matched] == ["d2"]


class TestExtractErrorTermsFallback:
    def test_fallback_respects_limit(self) -> None:
        # No error-shape pattern matches terse lowercase prose, so the
        # stopword-filtered plain-word fallback supplies terms and must
        # stop at the limit.
        text = "gadget frobnicator melted badly quickly slowly loudly"
        terms = extract_error_terms(text, limit=3)
        assert terms == ["gadget", "frobnicator", "melted"]


class _FakeRedisClient:
    def __init__(self, reply: object = None, error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.commands: list[tuple] = []

    def execute_command(self, *args: object) -> object:
        self.commands.append(args)
        if self.error is not None:
            raise self.error
        return self.reply


class TestRecallPriorsClientConstruction:
    def test_redis_package_missing_degrades(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A None entry in sys.modules makes ``import redis`` raise
        # ImportError without touching the real package.
        monkeypatch.setitem(sys.modules, "redis", None)
        result = recall_priors(["ValueError"])
        assert result.lessons == []
        assert result.degraded == "redis-package-not-installed"

    def test_client_built_from_redis_url_and_transport_error_degrades(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen_urls: list[str] = []
        failing = _FakeRedisClient(error=ConnectionError("down"))

        class _FakeRedis:
            @staticmethod
            def from_url(url: str, **kwargs: object) -> _FakeRedisClient:
                seen_urls.append(url)
                return failing

        monkeypatch.setitem(sys.modules, "redis", SimpleNamespace(Redis=_FakeRedis))
        monkeypatch.setenv("REDIS_URL", "redis://example.invalid:7000/3")

        result = recall_priors(["ValueError", "path|traversal"])
        assert seen_urls == ["redis://example.invalid:7000/3"]
        assert result.degraded == "recall-failed: ConnectionError"
        # Pipe characters inside a term are sanitized before OR-joining.
        assert failing.commands[0][2] == "ValueError|path traversal"

    def test_no_terms_short_circuits(self) -> None:
        assert recall_priors([]).degraded == "no-terms-extracted"


class TestParseSearchReply:
    def test_non_list_reply(self) -> None:
        assert _parse_search_reply("nope") == []

    def test_too_short_reply(self) -> None:
        assert _parse_search_reply([0]) == []

    def test_non_list_fields_entry_skipped(self) -> None:
        raw = [1, "key:a", "not-a-field-list"]
        assert _parse_search_reply(raw) == []

    def test_empty_name_and_description_skipped(self) -> None:
        raw = [1, "key:a", ["name", "", "description", ""]]
        assert _parse_search_reply(raw) == []

    def test_bytes_fields_decoded(self) -> None:
        raw = [1, b"key:a", [b"name", b"lesson-x", b"description", b"why it fires"]]
        assert _parse_search_reply(raw) == ["lesson-x — why it fires"]

    def test_name_only_entry_stripped(self) -> None:
        raw = [1, "key:a", ["name", "lesson-x", "description", ""]]
        assert _parse_search_reply(raw) == ["lesson-x"]
