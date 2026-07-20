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


class TestHealRunRecord:
    """The engine emits its own heal-stamped canonical run record
    (advanced-debugging-plugin v1.1 backlog (a)) — without it the
    mining exclusion guards an empty set.
    """

    def _diagnose(self, tmp_path, store, **overrides):
        kwargs = {
            "store": store,
            "run_stream": _stream(tmp_path, [_failed()]),
            "redis_client": _NoRedis(),
            "invoke_seat": _invoke,
            "repo_root": tmp_path,
        }
        kwargs.update(overrides)
        return diagnose("run-f", DiagnosisConfig(), **kwargs)

    def _heal_records(self, store):
        if not store.workflows_file.is_file():
            return []
        lines = store.workflows_file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def test_successful_diagnosis_emits_heal_stamped_run_record(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.delenv("ATTUNE_RUN_TRIGGER", raising=False)
        store = TelemetryStore()
        self._diagnose(tmp_path, store)

        records = self._heal_records(store)
        assert len(records) == 1
        (rec,) = records
        assert rec["trigger"] == "attune-heal"
        assert rec["workflow_name"] == "diagnose"
        assert rec["success"] is True
        assert rec["run_id"] != "run-f"
        assert rec["started_at"] and rec["completed_at"]
        assert rec["total_duration_ms"] >= 0

    def test_heal_trigger_is_constant_not_env_resolved(self, tmp_path, monkeypatch):
        # Even a launcher stamping "manual" cannot un-heal the record:
        # a diagnosis run is a self-record by construction.
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.setenv("ATTUNE_RUN_TRIGGER", "manual")
        store = TelemetryStore()
        self._diagnose(tmp_path, store)
        assert self._heal_records(store)[0]["trigger"] == "attune-heal"

    def test_refusal_emits_no_run_record(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        store = TelemetryStore()
        stream = _stream(tmp_path, [_failed(run_id="run-ok", success=True)])
        with pytest.raises(DiagnosisSourceError):
            diagnose("run-ok", DiagnosisConfig(), store=store, run_stream=stream)
        assert self._heal_records(store) == []

    def test_engine_failure_emits_no_run_record(self, tmp_path, monkeypatch):
        # RC-2 precedent: a run that raises without producing a result
        # emits nothing — not a run.
        import attune.diagnosis.engine as engine_mod

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        store = TelemetryStore()

        def _boom(*args, **kwargs):
            raise RuntimeError("panel exploded")

        monkeypatch.setattr(engine_mod, "convene_panel", _boom)
        with pytest.raises(RuntimeError, match="panel exploded"):
            self._diagnose(tmp_path, store)
        assert self._heal_records(store) == []

    def test_emission_failure_never_fails_the_diagnosis(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        store = TelemetryStore()

        def _disk_full(record):
            raise OSError("disk full")

        monkeypatch.setattr(store, "log_workflow", _disk_full)
        record = self._diagnose(tmp_path, store)
        # Diagnosis persisted and returned despite the emission failure
        assert records_for_run("run-f")
        assert record.source_run_id == "run-f"

    def test_mining_excludes_and_counts_the_heal_record(self, tmp_path, monkeypatch):
        # Live-fire the exclusion end-to-end: the record the engine
        # just emitted is what dropped_attune_heal counts.
        from attune.models.telemetry import run_context
        from attune.pipeline_learner.corpus import load_corpus

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.setattr(run_context, "resolve_project_identity", lambda start=None: "proj-x")
        store = TelemetryStore()
        self._diagnose(tmp_path, store)

        records, stats = load_corpus("proj-x", paths=[store.workflows_file])
        assert stats.dropped_attune_heal == 1
        assert records == [] and stats.eligible == 0


class TestCli:
    def test_cmd_diagnose_reports_refusal_as_exit_1(self, tmp_path, monkeypatch, capsys):
        from argparse import Namespace

        from attune.cli_commands.diagnosis_commands import cmd_diagnose

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        code = cmd_diagnose(Namespace(run_id="nope"))
        assert code == 1
        assert "cannot diagnose" in capsys.readouterr().out
