"""Engine tests (advanced-debugging-plugin T3/T4) — refusal rules and
the end-to-end pipeline with mocked seats and a fake Redis client.
"""

import json

import pytest

from attune.diagnosis import records_for_run
from attune.diagnosis.config import DiagnosisConfig
from attune.diagnosis.engine import DiagnosisSourceError, diagnose, find_source_run
from attune.models.telemetry.storage import TelemetryStore

_REPLY = (
    "HYPOTHESIS: the SDK subprocess lost auth\n"
    "CONFIDENCE: medium\n"
    "SUPPORTING: run-record\n"
    "CONTRADICTING: none\n"
)


def _stream(tmp_path, records):
    path = tmp_path / "workflow_runs.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def _failed(run_id="run-f", trigger="manual", success=False):
    return {
        "run_id": run_id,
        "workflow_name": "code-review",
        "started_at": "2026-07-20T12:00:00+00:00",
        "trigger": trigger,
        "project": "attune-ai",
        "success": success,
        "error": "ValueError in attune.ops.runner",
    }


def _invoke(recipe, brief):
    return 0, _REPLY


class _NoRedis:
    def execute_command(self, *args):
        raise ConnectionError("test: no redis")


class TestRefusals:
    def test_unknown_run_refused(self, tmp_path):
        stream = _stream(tmp_path, [_failed()])
        with pytest.raises(DiagnosisSourceError, match="not found"):
            diagnose("missing", run_stream=stream)

    def test_successful_run_refused(self, tmp_path):
        stream = _stream(tmp_path, [_failed(run_id="run-ok", success=True)])
        with pytest.raises(DiagnosisSourceError, match="succeeded"):
            diagnose("run-ok", run_stream=stream)

    def test_attune_heal_run_refused(self, tmp_path):
        stream = _stream(tmp_path, [_failed(run_id="run-h", trigger="attune-heal")])
        with pytest.raises(DiagnosisSourceError, match="self-record"):
            diagnose("run-h", run_stream=stream)


class TestFindSourceRun:
    def test_finds_by_id_newest_wins(self, tmp_path):
        older = _failed()
        newer = dict(_failed(), error="newer version of the record")
        stream = _stream(tmp_path, [older, newer])
        found = find_source_run("run-f", stream=stream)
        assert found is not None and found.error == "newer version of the record"

    def test_missing_stream_is_none(self, tmp_path):
        assert find_source_run("x", stream=tmp_path / "absent.jsonl") is None


class TestEndToEnd:
    def test_pipeline_persists_receipted_record(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        stream = _stream(tmp_path, [_failed()])
        store = TelemetryStore()

        record = diagnose(
            "run-f",
            DiagnosisConfig(),
            store=store,
            run_stream=stream,
            redis_client=_NoRedis(),
            invoke_seat=_invoke,
            repo_root=tmp_path,  # off-repo: git context degrades to None
        )

        # Priors degraded EXPLICITLY, never silently (RR-4)
        assert record.priors_degraded == "recall-failed: ConnectionError"
        assert record.prior_lessons == []
        # Observed evidence present; no prior-kind entries when degraded
        kinds = {e.kind for e in record.evidence}
        assert kinds == {"observed"}
        # Panel ran with mocked seats and produced ranked hypotheses
        assert record.hypotheses and record.hypotheses[0].confidence == "medium"
        assert record.panel["seats_invoked"]
        # Policy is data (dissent register)
        assert record.config_used["fix_proposal_threshold"] == "high"
        # Persisted to the isolated canonical stream and reloadable
        reloaded = records_for_run("run-f")
        assert [r.diagnosis_id for r in reloaded] == [record.diagnosis_id]

    def test_lessons_become_prior_kind_evidence(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        stream = _stream(tmp_path, [_failed()])

        class _Hit:
            def execute_command(self, *args):
                return [1, "k", ["name", "mapping-trap", "description", "main shadows"]]

        record = diagnose(
            "run-f",
            DiagnosisConfig(),
            store=TelemetryStore(),
            run_stream=stream,
            redis_client=_Hit(),
            invoke_seat=_invoke,
            repo_root=tmp_path,
        )
        assert record.prior_lessons == ["mapping-trap — main shadows"]
        priors = [e for e in record.evidence if e.kind == "prior"]
        observed = [e for e in record.evidence if e.kind == "observed"]
        assert priors and observed  # distinct kinds, both present (RR-4)


class TestCli:
    def test_cmd_diagnose_reports_refusal_as_exit_1(self, tmp_path, monkeypatch, capsys):
        from argparse import Namespace

        from attune.cli_commands.diagnosis_commands import cmd_diagnose

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        code = cmd_diagnose(Namespace(run_id="nope"))
        assert code == 1
        assert "cannot diagnose" in capsys.readouterr().out
