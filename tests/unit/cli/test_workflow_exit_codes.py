"""Exit-code contract for ``attune workflow run``.

Table-driven coverage of the four exit codes defined by the
workflow-failure-exit-propagation spec. Each case names the branch it
covers so a future refactor that collapses a code can't pass silently.

Contract (docs/specs/workflow-failure-exit-propagation/decisions.md):

- ``0`` — workflow ran AND ``WorkflowResult.success is True``
- ``1`` — workflow ran AND ``WorkflowResult.success is False``
- ``2`` — workflow ran AND raised an uncaught exception (traceback to
  stderr)
- ``3`` — CLI-level error (workflow not found / bad path / bad JSON)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import types
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from attune.workflows.data_classes import CostReport, WorkflowResult


@pytest.fixture(autouse=True)
def _disable_spend_gate(monkeypatch):
    """Disable the spend gate so these exit-code-contract tests run the
    workflow (the gate, collaboration-gates, would otherwise block a
    non-TTY run before execution). The gate must not change exit-code
    semantics for non-gated runs; with it off, behavior is unchanged.
    """
    monkeypatch.setenv("ATTUNE_SPEND_GATE", "off")
    # Auth-evidence for the pre-gate auth pre-flight (setup-friction
    # F1/F4): CI runners have no ~/.claude and an empty key, and these
    # tests target dispatch, not auth.
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-evidence")  # pragma: allowlist secret


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(**kwargs) -> types.SimpleNamespace:
    """Args namespace with cmd_workflow_run defaults."""
    defaults = {
        "name": "test-wf",
        "input": None,
        "path": None,
        "target": None,
        "json": False,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_result(*, success: bool, error: str | None = None) -> WorkflowResult:
    """Build a real WorkflowResult with the given success flag."""
    now = datetime.now(timezone.utc)
    return WorkflowResult(
        success=success,
        stages=[],
        final_output={"formatted_report": "done"},
        cost_report=CostReport(
            total_cost=0.0,
            baseline_cost=0.0,
            savings=0.0,
            savings_percent=0.0,
        ),
        started_at=now,
        completed_at=now,
        total_duration_ms=10,
        error=error,
    )


def _workflow_returning(result: WorkflowResult) -> type:
    """Workflow class whose execute() returns the given result."""

    def execute(self, **kwargs):
        return result

    return type("ReturningWorkflow", (), {"execute": execute})


def _workflow_raising(exc: Exception) -> type:
    """Workflow class whose execute() raises the given exception."""

    def execute(self, **kwargs):
        raise exc

    return type("RaisingWorkflow", (), {"execute": execute})


# ---------------------------------------------------------------------------
# The contract, table-driven
# ---------------------------------------------------------------------------


class TestWorkflowRunExitCodes:
    """Each branch of the exit-code contract, named explicitly."""

    @patch("attune.workflows.get_workflow")
    def test_success_returns_zero(self, mock_get, capsys):
        """Branch: workflow ran AND success is True → exit 0."""
        mock_get.return_value = _workflow_returning(_make_result(success=True))

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="ok-wf")) == 0

    @patch("attune.workflows.get_workflow")
    def test_planned_failure_returns_one(self, mock_get, capsys):
        """Branch: workflow ran AND success is False → exit 1."""
        mock_get.return_value = _workflow_returning(
            _make_result(success=False, error="analysis found blocking issues"),
        )

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="failing-wf")) == 1

    @patch("attune.workflows.get_workflow")
    def test_unplanned_failure_returns_two_with_traceback(self, mock_get, capsys):
        """Branch: execute() raised an uncaught exception → exit 2, traceback to stderr."""
        mock_get.return_value = _workflow_raising(RuntimeError("boom"))

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="crashing-wf")) == 2
        captured = capsys.readouterr()
        assert "Traceback (most recent call last):" in captured.err
        assert "boom" in captured.err

    @patch("attune.workflows.get_workflow")
    def test_not_found_returns_cli_error(self, mock_get, capsys):
        """Branch: CLI-level error (workflow not found) → exit 3."""
        mock_get.side_effect = KeyError("Unknown workflow: nope")

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="nope")) == 3

    @patch("attune.security.path_validation._validate_file_path")
    @patch("attune.workflows.get_workflow")
    def test_bad_path_returns_cli_error(self, mock_get, mock_validate, capsys):
        """Branch: CLI-level error (bad path) → exit 3, before execute()."""
        mock_validate.side_effect = ValueError("Cannot write to system directory: /etc")
        mock_get.return_value = _workflow_returning(_make_result(success=True))

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="wf", path="/etc/passwd")) == 3

    @patch("attune.workflows.get_workflow")
    def test_bad_json_returns_cli_error(self, mock_get, capsys):
        """Branch: CLI-level error (bad JSON input) → exit 3, before execute()."""
        mock_get.return_value = _workflow_returning(_make_result(success=True))

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="wf", input="{not json")) == 3


class TestWorkflowRunExitCodesAsync:
    """The success / planned-failure / unplanned branches for async execute()."""

    @staticmethod
    def _async_returning(result: WorkflowResult) -> type:
        async def execute(self, **kwargs):
            return result

        return type("AsyncReturningWorkflow", (), {"execute": execute})

    @staticmethod
    def _async_raising(exc: Exception) -> type:
        async def execute(self, **kwargs):
            raise exc

        return type("AsyncRaisingWorkflow", (), {"execute": execute})

    @patch("attune.workflows.get_workflow")
    def test_async_success_returns_zero(self, mock_get, capsys):
        """Branch: async workflow, success is True → exit 0."""
        mock_get.return_value = self._async_returning(_make_result(success=True))

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="async-ok")) == 0

    @patch("attune.workflows.get_workflow")
    def test_async_planned_failure_returns_one(self, mock_get, capsys):
        """Branch: async workflow, success is False → exit 1."""
        mock_get.return_value = self._async_returning(_make_result(success=False))

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="async-fail")) == 1

    @patch("attune.workflows.get_workflow")
    def test_async_unplanned_failure_returns_two(self, mock_get, capsys):
        """Branch: async workflow raised → exit 2."""
        mock_get.return_value = self._async_raising(ConnectionError("unreachable"))

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="async-crash")) == 2


class TestLegacyDictResultsExitZero:
    """Workflows returning plain dict/str/None (no ``success`` field) keep
    exiting 0 — the contract only trips exit 1 on an explicit
    ``success is False``."""

    @pytest.mark.parametrize(
        "value",
        [{"status": "ok"}, "all good", None, {"success": True}],
        ids=["dict", "string", "none", "dict-success-true"],
    )
    @patch("attune.workflows.get_workflow")
    def test_legacy_result_exits_zero(self, mock_get, value, capsys):
        """Branch: result without a falsey ``success`` attribute → exit 0."""
        mock_get.return_value = _workflow_returning(value)

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        assert cmd_workflow_run(_make_args(name="legacy-wf")) == 0


class TestJsonModeThreadsExitCode:
    """``--json`` threads exit_code + sdk_error_kind into stdout JSON,
    while ``$?`` (the return value) stays authoritative."""

    @patch("attune.workflows.get_workflow")
    def test_json_success_includes_exit_code_zero(self, mock_get, capsys):
        """Dict final_output gets exit_code/sdk_error_kind injected; return is 0."""
        import json

        result = _make_result(success=True)
        result.final_output = '{"score": 95}'
        mock_get.return_value = _workflow_returning(result)

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="wf", json=True))
        assert rc == 0
        out = capsys.readouterr().out
        block = out[out.index("{") :]
        parsed = json.loads(block)
        assert parsed["score"] == 95
        assert parsed["exit_code"] == 0
        assert parsed["sdk_error_kind"] is None

    @patch("attune.workflows.get_workflow")
    def test_json_planned_failure_includes_exit_code_one_and_kind(self, mock_get, capsys):
        """Failed run threads exit_code=1 and the sdk_error_kind metadata."""
        import json

        result = _make_result(success=False, error="quota reached")
        result.final_output = '{"findings": []}'
        result.metadata = {"sdk_error_kind": "api_quota"}
        mock_get.return_value = _workflow_returning(result)

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="wf", json=True))
        assert rc == 1
        out = capsys.readouterr().out
        block = out[out.index("{") :]
        parsed = json.loads(block)
        assert parsed["exit_code"] == 1
        assert parsed["sdk_error_kind"] == "api_quota"

    @patch("attune.workflows.get_workflow")
    def test_json_malformed_object_output_falls_back_to_envelope(self, mock_get, capsys):
        """A final_output that looks like JSON but won't parse falls back
        to the envelope instead of crashing."""
        import json

        result = _make_result(success=True)
        # Starts with '{' (so the coercer tries to parse) but is invalid.
        result.final_output = "{not valid json"
        mock_get.return_value = _workflow_returning(result)

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="wf", json=True))
        assert rc == 0
        out = capsys.readouterr().out
        block = out[out.index("{") :]
        parsed = json.loads(block)
        assert parsed["exit_code"] == 0
        assert parsed["success"] is True

    @patch("attune.workflows.get_workflow")
    def test_json_non_dict_output_wrapped_in_envelope(self, mock_get, capsys):
        """Non-dict result is wrapped so contract fields are always present."""
        import json

        # A legacy workflow that returns a bare string (no WorkflowResult).
        mock_get.return_value = _workflow_returning("plain text report")

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="wf", json=True))
        assert rc == 0
        out = capsys.readouterr().out
        block = out[out.index("{") :]
        parsed = json.loads(block)
        assert parsed["exit_code"] == 0
        assert parsed["success"] is True
        assert parsed["sdk_error_kind"] is None
        assert parsed["result"] == "plain text report"


class TestOnResultHookGuard:
    """The optional on_result hook must never alter the exit code."""

    def test_on_result_failure_does_not_change_exit_code(self):
        from attune.cli_commands._exit_codes import run_workflow_with_exit_code

        def _boom(_result):
            raise RuntimeError("hook blew up")

        rc = run_workflow_with_exit_code(
            _workflow_returning(_make_result(success=True)),
            {},
            name="ok-wf",
            json_mode=False,
            print_result=lambda _r: None,
            on_result=_boom,
        )
        assert rc == 0  # success exit code preserved despite the hook raising

    def test_on_result_receives_result_on_success(self):
        from attune.cli_commands._exit_codes import run_workflow_with_exit_code

        seen = []
        result = _make_result(success=True)
        rc = run_workflow_with_exit_code(
            _workflow_returning(result),
            {},
            name="ok-wf",
            json_mode=False,
            print_result=lambda _r: None,
            on_result=seen.append,
        )
        assert rc == 0
        assert seen == [result]
