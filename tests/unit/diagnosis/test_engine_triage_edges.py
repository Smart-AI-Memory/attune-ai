"""Edge coverage for engine source-run resolution and triage plumbing.

Targets ``find_source_run``'s malformed-stream defenses and ops-store
fallback (``_source_from_ops_record``), and ``run_triage``'s board
posting plus the manual ``main()`` entry point. All keyless: the
diagnose step is always stubbed and ``ATTUNE_HOME`` is redirected to
tmp so no real corpus is read or written.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from attune.diagnosis.engine import _source_from_ops_record, find_source_run
from attune.diagnosis.triage import main, run_triage, select_failed_runs
from attune.models.telemetry.data_models import DiagnosisHypothesis, DiagnosisRecord


def _run_line(run_id: str, *, success: bool = False, **extra: object) -> str:
    data: dict[str, object] = {
        "run_id": run_id,
        "workflow_name": "code-review",
        "started_at": "2026-07-20T12:00:00+00:00",
        "trigger": "manual",
        "success": success,
        "error": "boom",
    }
    data.update(extra)
    return json.dumps(data)


def _diagnosis(diagnosis_id: str, source: str) -> DiagnosisRecord:
    return DiagnosisRecord(
        diagnosis_id=diagnosis_id,
        source_run_id=source,
        workflow_name="code-review",
        created_at="2026-07-20T12:00:00+00:00",
        symptom="boom",
        hypotheses=[DiagnosisHypothesis(statement="stale mapping", confidence="high")],
    )


@pytest.fixture
def attune_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "attune-home"
    home.mkdir()
    monkeypatch.setenv("ATTUNE_HOME", str(home))
    return home


class TestFindSourceRunStreamEdges:
    def test_unreadable_stream_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stream = tmp_path / "runs.jsonl"
        stream.write_text(_run_line("r1") + "\n", encoding="utf-8")

        def _boom(self: Path, *args: object, **kwargs: object) -> str:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "read_text", _boom)
        assert find_source_run("r1", stream=stream) is None

    def test_invalid_json_line_containing_id_skipped(self, tmp_path: Path) -> None:
        stream = tmp_path / "runs.jsonl"
        stream.write_text('{"run_id": "r1" broken\n', encoding="utf-8")
        assert find_source_run("r1", stream=stream) is None

    def test_matching_line_with_missing_fields_skipped(self, tmp_path: Path) -> None:
        # run_id matches but required record fields are absent, so
        # from_dict raises and the line is skipped, not fatal.
        stream = tmp_path / "runs.jsonl"
        stream.write_text(json.dumps({"run_id": "r1"}) + "\n", encoding="utf-8")
        assert find_source_run("r1", stream=stream) is None


class TestOpsRecordFallback:
    def _write_ops_run(self, home: Path, run_id: str, data: object) -> Path:
        runs_dir = home / "ops" / "runs" / "2026-07-30"
        runs_dir.mkdir(parents=True, exist_ok=True)
        target = runs_dir / f"{run_id}.json"
        content = data if isinstance(data, str) else json.dumps(data)
        target.write_text(content, encoding="utf-8")
        return target

    def test_no_ops_store_returns_none(self, attune_home: Path) -> None:
        assert _source_from_ops_record("abc123") is None

    def test_invalid_json_skipped(self, attune_home: Path) -> None:
        self._write_ops_run(attune_home, "abc123", "{broken")
        assert _source_from_ops_record("abc123") is None

    def test_non_dict_payload_skipped(self, attune_home: Path) -> None:
        self._write_ops_run(attune_home, "abc123", [1, 2])
        assert _source_from_ops_record("abc123") is None

    def test_completed_run_synthesized(self, attune_home: Path) -> None:
        self._write_ops_run(
            attune_home,
            "abc123",
            {
                "workflow": "code-review",
                "started_at": "2026-07-30T10:00:00+00:00",
                "trigger": "manual",
                "status": "completed",
                "exit_code": 0,
            },
        )
        record = _source_from_ops_record("abc123")
        assert record is not None
        assert record.run_id == "abc123"
        assert record.workflow_name == "code-review"
        assert record.success is True
        assert "exit 0" in (record.error or "")

    def test_failed_run_uses_sdk_stderr(self, attune_home: Path) -> None:
        self._write_ops_run(
            attune_home,
            "abc123",
            {
                "workflow": "code-review",
                "started_at": "2026-07-30T10:00:00+00:00",
                "status": "failed",
                "exit_code": 1,
                "sdk_stderr": "Traceback: boom",
                "trigger": 42,  # non-str trigger normalizes to None
            },
        )
        record = _source_from_ops_record("abc123")
        assert record is not None
        assert record.success is False
        assert record.error == "Traceback: boom"
        assert record.trigger is None

    def test_find_source_run_falls_back_to_ops(self, attune_home: Path) -> None:
        # No canonical stream under ATTUNE_HOME — the ops record is
        # the only source, and the default-stream path must reach it.
        self._write_ops_run(
            attune_home,
            "abc123",
            {
                "workflow": "code-review",
                "started_at": "2026-07-30T10:00:00+00:00",
                "status": "failed",
                "exit_code": 1,
            },
        )
        record = find_source_run("abc123")
        assert record is not None
        assert record.workflow_name == "code-review"


class TestSelectFailedRunsEdges:
    def test_malformed_lines_skipped(self, tmp_path: Path) -> None:
        stream = tmp_path / "runs.jsonl"
        stream.write_text(
            "\n".join(
                [
                    "",  # blank
                    "{not json",
                    json.dumps({"run_id": "r-missing-fields", "success": False}),
                    json.dumps({"run_id": 42, "success": False}),
                    _run_line("r-good"),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        selected = select_failed_runs(stream, limit=5, already_diagnosed=lambda _rid: False)
        assert [r.run_id for r in selected] == ["r-good"]

    def test_unreadable_stream_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stream = tmp_path / "runs.jsonl"
        stream.write_text(_run_line("r1") + "\n", encoding="utf-8")

        def _boom(self: Path, *args: object, **kwargs: object) -> str:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "read_text", _boom)
        assert select_failed_runs(stream, limit=5, already_diagnosed=lambda _rid: False) == []

    def test_default_diagnosed_predicate_reads_store(
        self, attune_home: Path, tmp_path: Path
    ) -> None:
        # No already_diagnosed injected: the default predicate queries
        # the (empty, ATTUNE_HOME-redirected) diagnosis store.
        stream = tmp_path / "runs.jsonl"
        stream.write_text(_run_line("r1") + "\n", encoding="utf-8")
        selected = select_failed_runs(stream, limit=5)
        assert [r.run_id for r in selected] == ["r1"]


class _FakeBoard:
    posts: list[tuple[str, str, str, str]] = []

    def post_message(self, thread: str, author: str, kind: str, body: str) -> None:
        _FakeBoard.posts.append((thread, author, kind, body))


class _ExplodingBoard:
    def __init__(self) -> None:
        raise RuntimeError("board down")


class TestRunTriageBoardPost:
    def test_digest_posted_with_date_stamped_thread(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import attune.roundtable as roundtable

        _FakeBoard.posts = []
        monkeypatch.setattr(roundtable, "Board", _FakeBoard)
        stream = tmp_path / "runs.jsonl"
        stream.write_text(_run_line("r1") + "\n", encoding="utf-8")

        digest = run_triage(
            stream=stream,
            diagnose_fn=lambda run_id, config: _diagnosis("d1", run_id),
            now=datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc),
        )

        assert len(_FakeBoard.posts) == 1
        thread, author, kind, body = _FakeBoard.posts[0]
        assert thread == "routine-failed-run-triage-2026-07-30"
        assert (author, kind) == ("moderator", "synthesis")
        assert body == digest
        assert "1 run(s) diagnosed" in digest

    def test_board_failure_never_loses_digest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import attune.roundtable as roundtable

        monkeypatch.setattr(roundtable, "Board", _ExplodingBoard)
        stream = tmp_path / "runs.jsonl"
        stream.write_text(_run_line("r1") + "\n", encoding="utf-8")

        digest = run_triage(
            stream=stream,
            diagnose_fn=lambda run_id, config: _diagnosis("d1", run_id),
        )
        assert "1 run(s) diagnosed" in digest

    def test_no_diagnoses_skips_board(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import attune.roundtable as roundtable

        _FakeBoard.posts = []
        monkeypatch.setattr(roundtable, "Board", _FakeBoard)
        stream = tmp_path / "runs.jsonl"
        stream.write_text("", encoding="utf-8")

        run_triage(stream=stream, diagnose_fn=lambda run_id, config: _diagnosis("d1", run_id))
        assert _FakeBoard.posts == []


class TestMainEntryPoint:
    def test_dry_run_prints_batch_without_diagnosing(
        self,
        attune_home: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        stream_dir = attune_home / "telemetry"
        stream_dir.mkdir(parents=True)
        (stream_dir / "workflow_runs.jsonl").write_text(_run_line("r1") + "\n", encoding="utf-8")

        rc = main(["--dry-run"])

        assert rc == 0
        out = capsys.readouterr().out
        assert "would diagnose 1 run(s):" in out
        assert "- r1 (code-review): boom" in out

    def test_dry_run_with_empty_corpus(
        self, attune_home: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(["--dry-run"])
        assert rc == 0
        assert "would diagnose 0 run(s):" in capsys.readouterr().out

    def test_limit_overrides_batch_cap_and_digest_printed(
        self,
        attune_home: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        import attune.diagnosis.triage as triage_mod

        seen_caps: list[int] = []

        def _fake_run_triage(config: object) -> str:
            seen_caps.append(config.triage_batch_max)
            return "DIGEST-SENTINEL"

        monkeypatch.setattr(triage_mod, "run_triage", _fake_run_triage)
        rc = main(["--limit", "2"])

        assert rc == 0
        assert seen_caps == [2]
        assert "DIGEST-SENTINEL" in capsys.readouterr().out
