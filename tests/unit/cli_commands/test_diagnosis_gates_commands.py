"""Tests for the diagnose and gates-check CLI command handlers.

Both handlers lazy-import their engines at call time, so the engine
seams are patched at their source modules and the handlers exercised
through the real argparse ``Namespace`` contract: exit codes and the
rendered stdout are the receipts.
"""

from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

import pytest

from attune.cli_commands.diagnosis_commands import cmd_diagnose
from attune.cli_commands.gates_commands import cmd_gates_check
from attune.models.telemetry.data_models import DiagnosisRecord


def _record(**overrides: object) -> DiagnosisRecord:
    base: dict[str, object] = {
        "diagnosis_id": "d1",
        "source_run_id": "r1",
        "workflow_name": "code-review",
        "created_at": "2026-07-30T12:00:00+00:00",
        "symptom": "boom",
    }
    base.update(overrides)
    return DiagnosisRecord(**base)  # type: ignore[arg-type]


class TestCmdDiagnose:
    def test_success_renders_receipted_summary(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import attune.diagnosis.engine as engine_mod

        seen: list[tuple[str, str]] = []

        def _fake_diagnose(run_id: str, origin: str = "operational") -> DiagnosisRecord:
            seen.append((run_id, origin))
            return _record(
                prior_lessons=["lesson-a", "lesson-b"],
                panel={"seats_invoked": ["codex"], "absences": [], "invocations": 3},
                synthesis="Root cause: stale mapping.",
                dissent=["codex disagrees on scope"],
            )

        monkeypatch.setattr(engine_mod, "diagnose", _fake_diagnose)
        rc = cmd_diagnose(Namespace(run_id="r1", origin="dogfood"))

        assert rc == 0
        assert seen == [("r1", "dogfood")]
        out = capsys.readouterr().out
        assert "diagnosis d1 for run r1" in out
        assert "workflow: code-review" in out
        assert "symptom:  boom" in out
        assert "priors:   2 lesson(s) recalled" in out
        assert "panel:    1 seat(s), 0 absent, 3 invocation(s)" in out
        assert "Root cause: stale mapping." in out
        assert "1 unresolved dissent line(s) retained" in out
        assert "persisted to the canonical diagnosis stream" in out

    def test_origin_defaults_when_absent(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import attune.diagnosis.engine as engine_mod

        seen: list[str] = []

        def _fake_diagnose(run_id: str, origin: str = "unset") -> DiagnosisRecord:
            seen.append(origin)
            return _record(priors_degraded="recall-failed: ConnectionError")

        monkeypatch.setattr(engine_mod, "diagnose", _fake_diagnose)
        rc = cmd_diagnose(Namespace(run_id="r1"))

        assert rc == 0
        assert seen == ["operational"]
        out = capsys.readouterr().out
        # Degraded priors render the reason, not a lesson count.
        assert "priors:   degraded (recall-failed: ConnectionError)" in out

    def test_source_error_exits_1(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import attune.diagnosis.engine as engine_mod

        def _fail(run_id: str, origin: str = "operational") -> DiagnosisRecord:
            raise engine_mod.DiagnosisSourceError("run r1 not found in any stream")

        monkeypatch.setattr(engine_mod, "diagnose", _fail)
        rc = cmd_diagnose(Namespace(run_id="r1"))

        assert rc == 1
        assert "cannot diagnose: run r1 not found" in capsys.readouterr().out

    def test_unexpected_error_exits_2(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import attune.diagnosis.engine as engine_mod

        def _explode(run_id: str, origin: str = "operational") -> DiagnosisRecord:
            raise RuntimeError("panel melted")

        monkeypatch.setattr(engine_mod, "diagnose", _explode)
        rc = cmd_diagnose(Namespace(run_id="r1"))

        assert rc == 2
        assert "diagnosis failed unexpectedly: RuntimeError: panel melted" in (
            capsys.readouterr().out
        )


def _receipt(
    state: str = "PASS",
    *,
    waived: bool = False,
    findings: list[str] | None = None,
    proposed_disposition: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        state=state,
        waived=waived,
        gate_id="G5-brand",
        target="docs/page.md",
        phase="tasks",
        receipt_id="rcpt-1",
        findings=findings or [],
        proposed_disposition=proposed_disposition,
    )


def _gates_args(**overrides: object) -> Namespace:
    base: dict[str, object] = {
        "phase": "tasks",
        "spec": "my-spec",
        "tier": None,
        "changed": None,
    }
    base.update(overrides)
    return Namespace(**base)


class TestCmdGatesCheck:
    def _patch(
        self,
        monkeypatch: pytest.MonkeyPatch,
        receipts: list[SimpleNamespace],
        code: int,
    ) -> list[tuple]:
        import attune.gates.lifecycle as lifecycle_mod

        calls: list[tuple] = []

        def _fake_run_boundary(phase: str, spec: str, **kwargs: object) -> list[SimpleNamespace]:
            calls.append((phase, spec, kwargs))
            return receipts

        monkeypatch.setattr(lifecycle_mod, "run_boundary", _fake_run_boundary)
        monkeypatch.setattr(lifecycle_mod, "exit_code", lambda _receipts: code)
        return calls

    def test_no_applicable_gates(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        calls = self._patch(monkeypatch, [], code=0)
        rc = cmd_gates_check(_gates_args())

        assert rc == 0
        assert "no gates applicable at the tasks boundary for my-spec" in (capsys.readouterr().out)
        # ``changed: None`` normalizes to an empty list at the seam.
        assert calls[0][2]["changed_paths"] == []

    def test_receipts_rendered_with_findings_and_disposition(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        receipts = [
            _receipt(
                "PASS",
                waived=True,
                findings=["stale claim in docs/page.md"],
                proposed_disposition="re-run projector",
            )
        ]
        self._patch(monkeypatch, receipts, code=0)
        rc = cmd_gates_check(_gates_args(changed=["docs/page.md"]))

        assert rc == 0
        out = capsys.readouterr().out
        assert "[PASS (waived)] G5-brand — docs/page.md @ tasks (rcpt-1)" in out
        assert "    - stale claim in docs/page.md" in out
        assert "    → re-run projector" in out
        assert "BLOCKED" not in out
        assert "CHAIR_REQUIRED" not in out

    def test_hard_block_exits_2(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._patch(monkeypatch, [_receipt("BLOCKED")], code=2)
        rc = cmd_gates_check(_gates_args())

        assert rc == 2
        assert "BLOCKED: this boundary cannot advance (G5 hard block)." in (capsys.readouterr().out)

    def test_soft_block_exits_1(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._patch(monkeypatch, [_receipt("CHAIR_REQUIRED")], code=1)
        rc = cmd_gates_check(_gates_args())

        assert rc == 1
        assert "CHAIR_REQUIRED: proceed only with an explicit chair acknowledgment" in (
            capsys.readouterr().out
        )
