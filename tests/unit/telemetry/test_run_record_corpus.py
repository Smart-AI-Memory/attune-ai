"""Run-record corpus tests (docs/specs/run-record-corpus/ RC-1..RC-5).

Covers the canonical home-global run stream, the provenance fields,
suite isolation (the drift guard), rotation, and the ops-prune
non-interference assert.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from attune.models.telemetry import storage as storage_mod
from attune.models.telemetry.data_models import WorkflowRunRecord
from attune.models.telemetry.run_context import (
    TRIGGER_ENV,
    resolve_project_identity,
    resolve_run_trigger,
)
from attune.models.telemetry.storage import TelemetryStore
from attune.ops.runner import prune_old_runs
from attune.workflows.telemetry_mixin import TelemetryMixin


def _record(**overrides) -> WorkflowRunRecord:
    base = {
        "run_id": "r1",
        "workflow_name": "code-review",
        "started_at": "2026-07-19T12:00:00+00:00",
    }
    base.update(overrides)
    return WorkflowRunRecord(**base)


class TestCanonicalStream:
    """RC-1: default store routes run records home-global."""

    def test_default_store_resolves_under_attune_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.chdir(tmp_path)
        store = TelemetryStore()
        assert store.workflows_file == tmp_path / "home" / "telemetry" / "workflow_runs.jsonl"
        # Project-scoped files stay cwd-relative — only run records move.
        assert store.calls_file.parent.name == ".attune"
        assert not str(store.calls_file).startswith(str(tmp_path / "home"))

    def test_explicit_storage_dir_keeps_runs_local(self, tmp_path):
        store = TelemetryStore(storage_dir=str(tmp_path / "iso"))
        assert store.workflows_file == tmp_path / "iso" / "workflow_runs.jsonl"

    def test_log_workflow_creates_stream_and_appends(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.chdir(tmp_path)
        store = TelemetryStore()
        store.log_workflow(_record())
        store.log_workflow(_record(run_id="r2"))
        lines = store.workflows_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["workflow_name"] == "code-review"

    def test_suite_isolation_drift_guard(self):
        """The autouse ATTUNE_HOME fixture must redirect the default store.

        This is the RC-4 drift guard: if suite isolation regresses (env
        var dropped, singleton leak, resolution bypass), the default
        store points at the developer's real ``~/.attune`` and this
        fails loudly.
        """
        store = TelemetryStore()
        real_home_stream = Path.home() / ".attune" / "telemetry" / "workflow_runs.jsonl"
        assert store.workflows_file != real_home_stream
        assert os.environ.get("ATTUNE_HOME"), "suite must run with ATTUNE_HOME isolation"
        assert str(store.workflows_file).startswith(os.environ["ATTUNE_HOME"])


class TestProvenanceFields:
    """RC-3: trigger/project fields, additive compatibility."""

    def test_pre_rc3_record_loads_with_none_provenance(self):
        old = _record().to_dict()
        del old["trigger"]
        del old["project"]
        loaded = WorkflowRunRecord.from_dict(old)
        assert loaded.trigger is None
        assert loaded.project is None

    def test_resolve_run_trigger_defaults_manual(self, monkeypatch):
        monkeypatch.delenv(TRIGGER_ENV, raising=False)
        assert resolve_run_trigger() == "manual"

    def test_resolve_run_trigger_accepts_attune_rec(self, monkeypatch):
        monkeypatch.setenv(TRIGGER_ENV, "attune-rec")
        assert resolve_run_trigger() == "attune-rec"

    def test_resolve_run_trigger_rejects_junk(self, monkeypatch):
        monkeypatch.setenv(TRIGGER_ENV, "pytest-says-hi")
        assert resolve_run_trigger() == "manual"

    def test_project_identity_plain_repo(self, tmp_path):
        repo = tmp_path / "myproj"
        (repo / ".git").mkdir(parents=True)
        sub = repo / "src" / "pkg"
        sub.mkdir(parents=True)
        assert resolve_project_identity(sub) == "myproj"

    def test_project_identity_worktree_resolves_parent(self, tmp_path):
        main = tmp_path / "mainrepo"
        (main / ".git" / "worktrees" / "slug").mkdir(parents=True)
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'slug'}\n", encoding="utf-8"
        )
        assert resolve_project_identity(wt) == "mainrepo"

    def test_project_identity_outside_repo(self, tmp_path):
        assert resolve_project_identity(tmp_path) is None

    def test_emit_populates_provenance(self, tmp_path, monkeypatch):
        """RC-2/RC-3: the emit seam stamps trigger + project on records."""
        monkeypatch.setenv(TRIGGER_ENV, "attune-rec")
        repo = tmp_path / "emitproj"
        (repo / ".git").mkdir(parents=True)
        monkeypatch.chdir(repo)

        captured: list[WorkflowRunRecord] = []
        backend = SimpleNamespace(log_workflow=captured.append)
        wf = TelemetryMixin.__new__(TelemetryMixin)
        wf.name = "code-review"
        wf._run_id = "rid-1"
        wf._telemetry_backend = backend
        now = datetime.now(timezone.utc)
        result = SimpleNamespace(
            stages=[],
            started_at=now,
            completed_at=now,
            total_duration_ms=5,
            success=True,
            error=None,
            cost_report=SimpleNamespace(
                total_cost=0.0,
                baseline_cost=0.0,
                savings=0.0,
                savings_percent=0.0,
                by_tier={},
            ),
        )
        wf._emit_workflow_telemetry(result)
        assert len(captured) == 1
        assert captured[0].trigger == "attune-rec"
        assert captured[0].project == "emitproj"


class TestExecuteWrap:
    """RC-2: subclass ``execute`` overrides are wrapped to emit."""

    def test_override_is_wrapped(self):
        from attune.workflows.base import BaseWorkflow
        from attune.workflows.code_review import CodeReviewWorkflow

        # SDK-native override: wrapped by __init_subclass__.
        assert getattr(CodeReviewWorkflow.execute, "_emits_run_record", False) is True
        # Inherited mixin execute (no override): NOT wrapped — its own
        # epilogue emits inline, and the idempotence guard prevents any
        # double-record if a future override chains through super().
        assert getattr(BaseWorkflow.execute, "_emits_run_record", False) is False

    def test_emit_is_idempotent_per_result(self, tmp_path, monkeypatch):
        repo = tmp_path / "onceproj"
        (repo / ".git").mkdir(parents=True)
        monkeypatch.chdir(repo)
        captured: list[WorkflowRunRecord] = []
        backend = SimpleNamespace(log_workflow=captured.append)
        wf = TelemetryMixin.__new__(TelemetryMixin)
        wf.name = "code-review"
        wf._run_id = "rid-2"
        wf._telemetry_backend = backend
        now = datetime.now(timezone.utc)
        result = SimpleNamespace(
            stages=[],
            started_at=now,
            completed_at=now,
            total_duration_ms=1,
            success=True,
            error=None,
            cost_report=SimpleNamespace(
                total_cost=0.0,
                baseline_cost=0.0,
                savings=0.0,
                savings_percent=0.0,
                by_tier={},
            ),
        )
        wf._emit_workflow_telemetry(result)
        wf._emit_workflow_telemetry(result)  # second call must no-op
        assert len(captured) == 1


class TestRetention:
    """RC-5: rotation never deletes; ops prune never touches the stream."""

    def test_rotation_archives_past_size_guard(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(storage_mod, "_RUNS_ROTATE_BYTES", 64)
        store = TelemetryStore()
        store.workflows_file.parent.mkdir(parents=True, exist_ok=True)
        store.workflows_file.write_text("x" * 200 + "\n", encoding="utf-8")
        store.log_workflow(_record())
        archive = sorted((store.workflows_file.parent / "archive").glob("*.jsonl"))
        assert len(archive) == 1
        assert archive[0].read_text(encoding="utf-8").startswith("x" * 10)
        live = store.workflows_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(live) == 1  # fresh stream holds only the new record

    def test_ops_prune_never_touches_canonical_stream(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.chdir(tmp_path)
        store = TelemetryStore()
        store.log_workflow(_record())
        # Age the stream far past any retention window.
        old = datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()
        os.utime(store.workflows_file, (old, old))

        ops_runs = tmp_path / "home" / "ops" / "runs"
        wf_dir = ops_runs / "code-review"
        wf_dir.mkdir(parents=True)
        stale = wf_dir / "deadbeef0001.json"
        stale.write_text("{}", encoding="utf-8")
        os.utime(stale, (old, old))

        deleted = prune_old_runs(ops_runs, days=30)
        assert deleted == 1
        assert not stale.exists()
        assert store.workflows_file.exists()  # the corpus is not prunable


class TestReportShapedEmission:
    """RC-2 follow-up: orchestrator/agent-team workflows emit too.

    Their ``execute`` overrides return report objects
    (``HealthCheckReport``, ``OrchestratorResult``,
    ``SecureReleaseResult``) without the ``WorkflowResult`` surface;
    emission must degrade to a minimal record instead of dying on
    ``result.stages`` and silently recording nothing.
    """

    def _mixin(self, captured):
        wf = TelemetryMixin.__new__(TelemetryMixin)
        wf.name = "orchestrated-health-check"
        wf._run_id = "rid-report"
        wf._telemetry_backend = SimpleNamespace(log_workflow=captured.append)
        return wf

    def test_report_shaped_result_emits_fallback_record(self, tmp_path, monkeypatch):
        repo = tmp_path / "teamproj"
        (repo / ".git").mkdir(parents=True)
        monkeypatch.chdir(repo)
        captured: list[WorkflowRunRecord] = []
        wf = self._mixin(captured)
        report = SimpleNamespace(success=True, agents_executed=3)
        start = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 7, 19, 12, 0, 2, tzinfo=timezone.utc)
        wf._emit_workflow_telemetry(report, started_at=start, completed_at=end)
        assert len(captured) == 1
        rec = captured[0]
        assert rec.workflow_name == "orchestrated-health-check"
        assert rec.project == "teamproj"
        assert rec.trigger == "manual"
        assert rec.success is True
        assert rec.stages == []
        assert rec.total_cost == 0.0
        assert rec.total_duration_ms == 2000
        assert rec.started_at == start.isoformat()
        assert rec.completed_at == end.isoformat()

    def test_report_failure_and_error_string_preserved(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        captured: list[WorkflowRunRecord] = []
        wf = self._mixin(captured)
        report = SimpleNamespace(success=False, error="agent blew up")
        wf._emit_workflow_telemetry(report)
        assert captured[0].success is False
        assert captured[0].error == "agent blew up"

    def test_report_without_success_field_counts_as_success(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        captured: list[WorkflowRunRecord] = []
        wf = self._mixin(captured)
        wf._emit_workflow_telemetry(SimpleNamespace(agents_executed=1))
        assert captured[0].success is True
        assert captured[0].error is None

    def test_report_emission_is_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        captured: list[WorkflowRunRecord] = []
        wf = self._mixin(captured)
        report = SimpleNamespace(success=True)
        wf._emit_workflow_telemetry(report)
        wf._emit_workflow_telemetry(report)
        assert len(captured) == 1

    def test_service_path_emits_fallback_record(self, tmp_path, monkeypatch):
        from attune.workflows.services.telemetry_service import TelemetryService

        monkeypatch.chdir(tmp_path)
        captured: list[WorkflowRunRecord] = []
        svc = TelemetryService.__new__(TelemetryService)
        svc._workflow_name = "orchestrated-health-check"
        svc._provider = "anthropic"
        svc._run_id = "rid-svc"
        svc._backend = SimpleNamespace(log_workflow=captured.append)
        report = SimpleNamespace(success=True)
        svc.emit_workflow_record(report)
        svc.emit_workflow_record(report)  # idempotent on the ctx path too
        assert len(captured) == 1
        assert captured[0].workflow_name == "orchestrated-health-check"
        assert captured[0].providers_used == ["anthropic"]

    def test_orchestrator_family_execute_is_wrapped(self):
        from attune.workflows.documentation_orchestrator import (
            DocumentationOrchestrator,
        )
        from attune.workflows.orchestrated_health_check import (
            OrchestratedHealthCheckWorkflow,
        )
        from attune.workflows.secure_release import SecureReleasePipeline

        for cls in (
            OrchestratedHealthCheckWorkflow,
            DocumentationOrchestrator,
            SecureReleasePipeline,
        ):
            assert getattr(cls.execute, "_emits_run_record", False) is True, cls
