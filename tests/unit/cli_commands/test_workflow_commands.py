"""Tests for CLI workflow commands (list, info, run).

Tests for src/attune/cli_commands/workflow_commands.py which provides
cmd_workflow_list, cmd_workflow_info, and cmd_workflow_run.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import types
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _disable_spend_gate(monkeypatch):
    """Disable the spend gate for these pre-gate tests.

    These exercise workflow-run dispatch, not the gate; without this
    the gate (collaboration-gates) would block every non-TTY run.
    The gate has dedicated tests in ``test_workflow_spend_gate.py``.
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
    """Create a SimpleNamespace args object with sensible defaults for cmd_workflow_run."""
    defaults = {
        "name": "test-workflow",
        "input": None,
        "path": None,
        "target": None,
        "json": False,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_workflow_class(
    docstring: str = "A test workflow.",
    input_schema: dict | None = None,
    execute_return: dict | None = None,
    execute_side_effect: Exception | None = None,
    is_async: bool = False,
) -> type:
    """Build a mock workflow class with configurable behaviour."""
    if execute_return is None:
        execute_return = {"status": "ok"}

    if is_async:

        async def _execute(self, **kwargs):
            if execute_side_effect:
                raise execute_side_effect
            return execute_return

    else:

        def _execute(self, **kwargs):
            if execute_side_effect:
                raise execute_side_effect
            return execute_return

    cls = type("MockWorkflow", (), {"__doc__": docstring, "execute": _execute})
    if input_schema is not None:
        cls.input_schema = input_schema
    return cls


# ===========================================================================
# cmd_workflow_list
# ===========================================================================


class TestCmdWorkflowList:
    """Tests for cmd_workflow_list.

    cmd_workflow_list calls list_workflows() which returns list[dict].
    """

    @patch("attune.workflows.list_workflows")
    def test_list_empty_workflows_returns_zero(self, mock_list, capsys):
        """Test listing when no workflows are registered."""
        mock_list.return_value = []

        from attune.cli_commands.workflow_commands import cmd_workflow_list

        args = types.SimpleNamespace()
        result = cmd_workflow_list(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No workflows registered." in captured.out

    @patch("attune.workflows.list_workflows")
    def test_list_single_workflow_shows_name_and_description(self, mock_list, capsys):
        """Test listing a single workflow shows its name and first docstring line."""
        mock_list.return_value = [
            {
                "name": "code-review",
                "description": "Automated code review.",
                "engine": "native",
            },
        ]

        from attune.cli_commands.workflow_commands import cmd_workflow_list

        result = cmd_workflow_list(types.SimpleNamespace())

        assert result == 0
        captured = capsys.readouterr()
        assert "code-review" in captured.out
        assert "Automated code review." in captured.out

    @patch("attune.workflows.list_workflows")
    def test_list_multiple_workflows_sorted_alphabetically(self, mock_list, capsys):
        """Test workflows are listed in alphabetical order."""
        mock_list.return_value = [
            {"name": "zeta-workflow", "description": "Zeta", "engine": "native"},
            {"name": "alpha-workflow", "description": "Alpha", "engine": "native"},
            {"name": "mid-workflow", "description": "Mid", "engine": "native"},
        ]

        from attune.cli_commands.workflow_commands import cmd_workflow_list

        result = cmd_workflow_list(types.SimpleNamespace())

        assert result == 0
        captured = capsys.readouterr()
        # alpha should appear before mid, which appears before zeta
        alpha_idx = captured.out.index("alpha-workflow")
        mid_idx = captured.out.index("mid-workflow")
        zeta_idx = captured.out.index("zeta-workflow")
        assert alpha_idx < mid_idx < zeta_idx

    @patch("attune.workflows.list_workflows")
    def test_list_shows_total_count(self, mock_list, capsys):
        """Test that the total workflow count is displayed."""
        mock_list.return_value = [
            {"name": "wf-1", "description": "First", "engine": "native"},
            {"name": "wf-2", "description": "Second", "engine": "native"},
        ]

        from attune.cli_commands.workflow_commands import cmd_workflow_list

        cmd_workflow_list(types.SimpleNamespace())

        captured = capsys.readouterr()
        assert "Total: 2 workflows" in captured.out

    @patch("attune.workflows.list_workflows")
    def test_list_displays_header_and_footer(self, mock_list, capsys):
        """Test that header, separator lines and usage hint are printed."""
        mock_list.return_value = [
            {"name": "demo", "description": "Demo", "engine": "native"},
        ]

        from attune.cli_commands.workflow_commands import cmd_workflow_list

        cmd_workflow_list(types.SimpleNamespace())

        captured = capsys.readouterr()
        assert "Available Workflows" in captured.out
        assert "-" * 60 in captured.out
        assert "attune workflow run" in captured.out

    @patch("attune.workflows.list_workflows")
    def test_list_shows_sdk_tag(self, mock_list, capsys):
        """Test that SDK engine tag is displayed."""
        mock_list.return_value = [
            {"name": "security-audit", "description": "Security", "engine": "sdk"},
        ]

        from attune.cli_commands.workflow_commands import cmd_workflow_list

        cmd_workflow_list(types.SimpleNamespace())

        captured = capsys.readouterr()
        assert "[SDK]" in captured.out

    @patch("attune.workflows.list_workflows")
    def test_list_shows_api_tag(self, mock_list, capsys):
        """Test that API engine tag is displayed."""
        mock_list.return_value = [
            {"name": "security-audit", "description": "Security", "engine": "api"},
        ]

        from attune.cli_commands.workflow_commands import cmd_workflow_list

        cmd_workflow_list(types.SimpleNamespace())

        captured = capsys.readouterr()
        assert "[API]" in captured.out


# ===========================================================================
# cmd_workflow_info
# ===========================================================================


class TestCmdWorkflowInfo:
    """Tests for cmd_workflow_info.

    cmd_workflow_info calls get_workflow(name) which returns a class
    or raises KeyError.
    """

    @patch("attune.workflows.get_workflow")
    def test_info_found_returns_zero(self, mock_get, capsys):
        """Test that a found workflow returns 0."""
        mock_get.return_value = _make_workflow_class("Code review workflow.")

        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = types.SimpleNamespace(name="code-review")
        result = cmd_workflow_info(args)

        assert result == 0

    @patch("attune.workflows.get_workflow")
    def test_info_not_found_returns_one(self, mock_get, capsys):
        """Test that a missing workflow returns 1."""
        mock_get.side_effect = KeyError("Unknown workflow: nonexistent")

        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = types.SimpleNamespace(name="nonexistent")
        result = cmd_workflow_info(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Workflow not found: nonexistent" in captured.out

    @patch("attune.workflows.get_workflow")
    def test_info_shows_docstring(self, mock_get, capsys):
        """Test that the workflow docstring is printed."""
        mock_get.return_value = _make_workflow_class("My workflow does wonderful things.")

        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = types.SimpleNamespace(name="my-wf")
        cmd_workflow_info(args)

        captured = capsys.readouterr()
        assert "My workflow does wonderful things." in captured.out

    @patch("attune.workflows.get_workflow")
    def test_info_shows_input_schema_when_present(self, mock_get, capsys):
        """Test that input_schema is printed as JSON when the attribute exists."""
        schema = {"type": "object", "properties": {"path": {"type": "string"}}}
        mock_get.return_value = _make_workflow_class("Workflow.", input_schema=schema)

        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = types.SimpleNamespace(name="my-wf")
        cmd_workflow_info(args)

        captured = capsys.readouterr()
        assert "Input Schema:" in captured.out
        assert '"type": "object"' in captured.out
        assert '"path"' in captured.out

    @patch("attune.workflows.get_workflow")
    def test_info_omits_schema_when_absent(self, mock_get, capsys):
        """Test that Input Schema section is skipped when class has no input_schema."""
        mock_get.return_value = _make_workflow_class("Workflow.")

        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = types.SimpleNamespace(name="my-wf")
        cmd_workflow_info(args)

        captured = capsys.readouterr()
        assert "Input Schema:" not in captured.out

    @patch("attune.workflows.get_workflow")
    def test_info_workflow_without_docstring(self, mock_get, capsys):
        """Test info for a workflow class whose __doc__ is None."""
        mock_get.return_value = _make_workflow_class(docstring=None)

        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = types.SimpleNamespace(name="no-doc")
        result = cmd_workflow_info(args)

        # Should still succeed
        assert result == 0


# ===========================================================================
# cmd_workflow_run
# ===========================================================================


class TestCmdWorkflowRunNotFound:
    """Tests for cmd_workflow_run when workflow is not found."""

    @patch("attune.workflows.get_workflow")
    def test_run_not_found_returns_cli_error(self, mock_get, capsys):
        """A nonexistent workflow is a CLI-level error → exit 3."""
        mock_get.side_effect = KeyError("Unknown workflow: missing-workflow")

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="missing-workflow")
        result = cmd_workflow_run(args)

        assert result == 3
        captured = capsys.readouterr()
        assert "Workflow not found: missing-workflow" in captured.out


class TestCmdWorkflowRunInputParsing:
    """Tests for JSON input parsing in cmd_workflow_run."""

    @patch("attune.workflows.get_workflow")
    def test_run_valid_json_input(self, mock_get, capsys):
        """Test that valid JSON input is parsed and passed to execute."""
        call_kwargs = {}

        class TrackingWorkflow:
            """Tracking workflow."""

            def execute(self, **kwargs):
                call_kwargs.update(kwargs)
                return {"done": True}

        mock_get.return_value = TrackingWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="track", input='{"key": "value", "count": 42}')
        result = cmd_workflow_run(args)

        assert result == 0
        assert call_kwargs["key"] == "value"
        assert call_kwargs["count"] == 42

    @patch("attune.workflows.get_workflow")
    def test_run_invalid_json_returns_cli_error(self, mock_get, capsys):
        """Invalid JSON input is a CLI-level error → exit 3."""
        mock_get.return_value = _make_workflow_class()

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf", input="{not valid json")
        result = cmd_workflow_run(args)

        assert result == 3
        captured = capsys.readouterr()
        assert "Invalid JSON input" in captured.out

    @patch("attune.workflows.get_workflow")
    def test_run_empty_json_object_input(self, mock_get, capsys):
        """Test that '{}' is accepted as valid empty JSON input."""
        mock_get.return_value = _make_workflow_class()

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf", input="{}")
        result = cmd_workflow_run(args)

        assert result == 0

    @patch("attune.workflows.get_workflow")
    def test_run_no_input_uses_empty_dict(self, mock_get, capsys):
        """Test that when args.input is None, an empty dict is used."""
        call_kwargs = {}

        class TrackingWorkflow:
            """Tracking."""

            def execute(self, **kwargs):
                call_kwargs.update(kwargs)
                return {"status": "ok"}

        mock_get.return_value = TrackingWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="track", input=None)
        result = cmd_workflow_run(args)

        assert result == 0
        # No extra keys should be in kwargs (path and target are None)
        assert "key" not in call_kwargs


class TestCmdWorkflowRunPathValidation:
    """Tests for path validation in cmd_workflow_run."""

    @patch("attune.security.path_validation._validate_file_path")
    @patch("attune.workflows.get_workflow")
    def test_run_valid_path_is_validated_and_passed(
        self,
        mock_get,
        mock_validate,
        capsys,
        tmp_path,
    ):
        """Test that a valid path is validated and included in input_data."""
        call_kwargs = {}
        valid_path = tmp_path / "src"
        mock_validate.return_value = valid_path

        class TrackingWorkflow:
            """Tracking."""

            def execute(self, **kwargs):
                call_kwargs.update(kwargs)
                return {"status": "ok"}

        mock_get.return_value = TrackingWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="track", path=str(valid_path))
        result = cmd_workflow_run(args)

        assert result == 0
        mock_validate.assert_called_once_with(str(valid_path))
        assert call_kwargs["path"] == str(valid_path)

    @patch("attune.security.path_validation._validate_file_path")
    @patch("attune.workflows.get_workflow")
    def test_run_path_traversal_rejected(self, mock_get, mock_validate, capsys):
        """Path traversal is a CLI-level error → exit 3."""
        mock_validate.side_effect = ValueError("Cannot write to system directory: /etc")
        mock_get.return_value = _make_workflow_class()

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf", path="../../../etc/passwd")
        result = cmd_workflow_run(args)

        assert result == 3
        captured = capsys.readouterr()
        assert "Invalid path" in captured.out
        assert "Cannot write to system directory" in captured.out

    @patch("attune.security.path_validation._validate_file_path")
    @patch("attune.workflows.get_workflow")
    def test_run_null_byte_path_rejected(self, mock_get, mock_validate, capsys):
        """Null bytes in path are a CLI-level error → exit 3."""
        mock_validate.side_effect = ValueError("path contains null bytes")
        mock_get.return_value = _make_workflow_class()

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf", path="config\x00.json")
        result = cmd_workflow_run(args)

        assert result == 3
        captured = capsys.readouterr()
        assert "Invalid path" in captured.out

    @patch("attune.security.path_validation._validate_file_path")
    @patch("attune.workflows.get_workflow")
    def test_run_system_directory_path_rejected(self, mock_get, mock_validate, capsys):
        """System directory paths are a CLI-level error → exit 3."""
        mock_validate.side_effect = ValueError("Cannot write to system directory: /sys")
        mock_get.return_value = _make_workflow_class()

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf", path="/sys/kernel/debug")
        result = cmd_workflow_run(args)

        assert result == 3
        captured = capsys.readouterr()
        assert "Invalid path" in captured.out


class TestCmdWorkflowRunTarget:
    """Tests for target argument handling in cmd_workflow_run."""

    @patch("attune.workflows.get_workflow")
    def test_run_target_passed_in_input_data(self, mock_get, capsys):
        """Test that args.target is added to input_data."""
        call_kwargs = {}

        class TrackingWorkflow:
            """Tracking."""

            def execute(self, **kwargs):
                call_kwargs.update(kwargs)
                return {"status": "ok"}

        mock_get.return_value = TrackingWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="track", target="src/attune/config.py")
        result = cmd_workflow_run(args)

        assert result == 0
        assert call_kwargs["target"] == "src/attune/config.py"

    @patch("attune.workflows.get_workflow")
    def test_run_no_target_omits_key(self, mock_get, capsys):
        """Test that when target is None, it is not included in input_data."""
        call_kwargs = {}

        class TrackingWorkflow:
            """Tracking."""

            def execute(self, **kwargs):
                call_kwargs.update(kwargs)
                return {"status": "ok"}

        mock_get.return_value = TrackingWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="track", target=None)
        result = cmd_workflow_run(args)

        assert result == 0
        assert "target" not in call_kwargs


class TestCmdWorkflowRunDiscoveryFlags:
    """Characterization pins (D-block batch 2): the discovery-sweep
    flags map into input_data exactly as today — set only when truthy,
    absent otherwise."""

    @staticmethod
    def _run_tracking(args_kwargs: dict) -> dict:
        call_kwargs: dict = {}

        class TrackingWorkflow:
            """Tracking."""

            def execute(self, **kwargs):
                call_kwargs.update(kwargs)
                return {"status": "ok"}

        with patch("attune.workflows.get_workflow", return_value=TrackingWorkflow):
            from attune.cli_commands.workflow_commands import cmd_workflow_run

            assert cmd_workflow_run(_make_args(**args_kwargs)) == 0
        return call_kwargs

    def test_verbose_flag_sets_input_key(self, capsys):
        call_kwargs = self._run_tracking({"verbose": True})
        assert call_kwargs["verbose"] is True

    def test_source_flag_sets_input_key(self, capsys):
        call_kwargs = self._run_tracking({"source": "git"})
        assert call_kwargs["source"] == "git"

    def test_depth_flag_sets_input_key(self, capsys):
        call_kwargs = self._run_tracking({"depth": "quick"})
        assert call_kwargs["depth"] == "quick"

    def test_absent_flags_omit_keys(self, capsys):
        call_kwargs = self._run_tracking({})
        for key in ("verbose", "no_llm", "source", "depth", "output_format"):
            assert key not in call_kwargs


class TestCmdWorkflowRunSyncExecution:
    """Tests for synchronous workflow execution."""

    @patch("attune.workflows.get_workflow")
    def test_run_sync_workflow_dict_result_formatted(self, mock_get, capsys):
        """Test that a dict result from a sync workflow is formatted correctly."""
        mock_get.return_value = _make_workflow_class(execute_return={"score": 95, "issues": 2})

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf")
        result = cmd_workflow_run(args)

        assert result == 0
        captured = capsys.readouterr()
        # Voice layer replaces "Workflow completed" with personality-driven messaging
        assert "issues: 2" in captured.out
        assert "95" in captured.out

    @patch("attune.workflows.get_workflow")
    def test_run_sync_workflow_non_dict_result(self, mock_get, capsys):
        """Test that a non-dict result is printed with Result: prefix."""
        mock_get.return_value = _make_workflow_class(execute_return="All tests passed")

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf")
        result = cmd_workflow_run(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "All tests passed" in captured.out

    @patch("attune.workflows.get_workflow")
    def test_run_sync_workflow_none_result(self, mock_get, capsys):
        """Test that a None result is handled without error."""

        class NoneWorkflow:
            """Returns None."""

            def execute(self, **kwargs):
                return None

        mock_get.return_value = NoneWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf")
        result = cmd_workflow_run(args)

        assert result == 0
        captured = capsys.readouterr()
        # Voice layer handles None result gracefully
        assert "Running workflow: wf" in captured.out


class TestCmdWorkflowRunAsyncExecution:
    """Tests for async workflow execution."""

    @patch("attune.workflows.get_workflow")
    def test_run_async_workflow_succeeds(self, mock_get, capsys):
        """Test that an async workflow is executed correctly via asyncio.run."""
        mock_get.return_value = _make_workflow_class(
            docstring="Async workflow.",
            execute_return={"async_result": True},
            is_async=True,
        )

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="async-wf")
        result = cmd_workflow_run(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "async_result: True" in captured.out

    @patch("attune.workflows.get_workflow")
    def test_run_async_workflow_with_input(self, mock_get, capsys):
        """Test that input_data is passed to async workflow execute."""
        received_kwargs = {}

        class AsyncWorkflow:
            """Async with input."""

            async def execute(self, **kwargs):
                received_kwargs.update(kwargs)
                return {"processed": True}

        mock_get.return_value = AsyncWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="async-wf", input='{"query": "test"}')
        result = cmd_workflow_run(args)

        assert result == 0
        assert received_kwargs["query"] == "test"


class TestCmdWorkflowRunJsonOutput:
    """Tests for JSON output mode in cmd_workflow_run."""

    @patch("attune.workflows.get_workflow")
    def test_run_json_output_mode_dict(self, mock_get, capsys):
        """Test that --json flag outputs result as JSON."""
        mock_get.return_value = _make_workflow_class(execute_return={"status": "ok", "count": 5})

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf", json=True)
        result = cmd_workflow_run(args)

        assert result == 0
        captured = capsys.readouterr()
        # The running header is printed first, then JSON
        lines = captured.out.strip().split("\n")
        # Find the JSON block (starts with '{')
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith("{"):
                in_json = True
            if in_json:
                json_lines.append(line)

        json_text = "\n".join(json_lines)
        parsed = json.loads(json_text)
        assert parsed["status"] == "ok"
        assert parsed["count"] == 5

    @patch("attune.workflows.get_workflow")
    def test_run_json_output_mode_non_dict(self, mock_get, capsys):
        """Test JSON output with a non-dict result uses default=str."""
        mock_get.return_value = _make_workflow_class(execute_return="plain string result")

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf", json=True)
        result = cmd_workflow_run(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "plain string result" in captured.out

    @patch("attune.workflows.get_workflow")
    def test_run_non_json_output_does_not_dump_json(self, mock_get, capsys):
        """Test that without --json, output is formatted, not raw JSON."""
        mock_get.return_value = _make_workflow_class(execute_return={"key": "val"})

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf", json=False)
        result = cmd_workflow_run(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "key: val" in captured.out


class TestCmdWorkflowRunExceptionHandling:
    """Tests for exception handling in cmd_workflow_run.

    An uncaught exception from ``execute()`` is the exit-2 "unplanned
    failure" branch: the traceback goes to stderr, the voiced summary
    to stdout.
    """

    @patch("attune.workflows.get_workflow")
    def test_run_workflow_raises_runtime_error(self, mock_get, capsys):
        """A RuntimeError during execute is an unplanned failure → exit 2."""
        mock_get.return_value = _make_workflow_class(
            execute_side_effect=RuntimeError("Something broke"),
        )

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf")
        result = cmd_workflow_run(args)

        assert result == 2
        captured = capsys.readouterr()
        assert "Something went wrong" in captured.out
        assert "Something broke" in captured.out
        # Traceback is printed to stderr per the exit-2 contract.
        assert "Traceback (most recent call last):" in captured.err

    @patch("attune.workflows.get_workflow")
    def test_run_workflow_raises_value_error(self, mock_get, capsys):
        """A ValueError during execute is an unplanned failure → exit 2."""
        mock_get.return_value = _make_workflow_class(
            execute_side_effect=ValueError("Invalid value"),
        )

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf")
        result = cmd_workflow_run(args)

        assert result == 2
        captured = capsys.readouterr()
        assert "Something went wrong" in captured.out

    @patch("attune.workflows.get_workflow")
    def test_run_workflow_raises_key_error(self, mock_get, capsys):
        """A KeyError during execute is an unplanned failure → exit 2."""
        mock_get.return_value = _make_workflow_class(
            execute_side_effect=KeyError("missing_key"),
        )

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf")
        result = cmd_workflow_run(args)

        assert result == 2
        captured = capsys.readouterr()
        assert "Something went wrong" in captured.out

    @patch("attune.workflows.get_workflow")
    def test_run_async_workflow_raises_exception(self, mock_get, capsys):
        """An exception from an async workflow is an unplanned failure → exit 2."""
        mock_get.return_value = _make_workflow_class(
            execute_side_effect=ConnectionError("API unreachable"),
            is_async=True,
        )

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="wf")
        result = cmd_workflow_run(args)

        assert result == 2
        captured = capsys.readouterr()
        assert "Something went wrong" in captured.out
        assert "API unreachable" in captured.out


class TestCmdWorkflowRunCombinedInputs:
    """Tests for combining JSON input with path and target."""

    @patch("attune.security.path_validation._validate_file_path")
    @patch("attune.workflows.get_workflow")
    def test_run_json_input_plus_path_and_target(
        self,
        mock_get,
        mock_validate,
        capsys,
        tmp_path,
    ):
        """Test that JSON input, validated path, and target are all merged."""
        call_kwargs = {}
        validated = tmp_path / "project"
        mock_validate.return_value = validated

        class TrackingWorkflow:
            """Tracking."""

            def execute(self, **kwargs):
                call_kwargs.update(kwargs)
                return {"merged": True}

        mock_get.return_value = TrackingWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(
            name="track",
            input='{"severity": "high"}',
            path=str(validated),
            target="main.py",
        )
        result = cmd_workflow_run(args)

        assert result == 0
        assert call_kwargs["severity"] == "high"
        assert call_kwargs["path"] == str(validated)
        assert call_kwargs["target"] == "main.py"

    @patch("attune.workflows.get_workflow")
    def test_run_no_optional_args(self, mock_get, capsys):
        """Test execution with no input, path, or target."""
        call_kwargs = {}

        class TrackingWorkflow:
            """Tracking."""

            def execute(self, **kwargs):
                call_kwargs.update(kwargs)
                return {}

        mock_get.return_value = TrackingWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="track", input=None, path=None, target=None)
        result = cmd_workflow_run(args)

        assert result == 0
        # No path or target should be in kwargs
        assert "path" not in call_kwargs
        assert "target" not in call_kwargs


class TestCmdWorkflowRunOutputHeader:
    """Tests for the running header message."""

    @patch("attune.workflows.get_workflow")
    def test_run_prints_running_header(self, mock_get, capsys):
        """Test that the 'Running workflow' header is always printed."""
        mock_get.return_value = _make_workflow_class()

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="my-workflow")
        cmd_workflow_run(args)

        captured = capsys.readouterr()
        assert "Running workflow: my-workflow" in captured.out


class TestCmdWorkflowRunCheapFlag:
    """Tests for --cheap flag wiring.

    When ``args.cheap`` is True, ``cmd_workflow_run`` must set
    ``ATTUNE_AGENT_MODEL_DEFAULT=haiku`` in the process environment
    BEFORE the workflow is instantiated, so that any subagent the
    workflow spawns sees the override via ``get_subagent_model``.

    IMPORTANT: ``cmd_workflow_run`` does a raw ``os.environ[k] = v``
    write, which pytest's ``monkeypatch`` cannot track or roll back.
    Each test uses ``try/finally`` to pop the env var so it doesn't
    leak to sibling tests on the same xdist worker (sibling assertions
    like ``get_subagent_model(...) is None`` would silently fail).
    """

    @patch("attune.workflows.get_workflow")
    def test_cheap_flag_sets_env_var(self, mock_get, monkeypatch, capsys):
        """args.cheap=True sets ATTUNE_AGENT_MODEL_DEFAULT=haiku."""
        import os

        monkeypatch.delenv("ATTUNE_AGENT_MODEL_DEFAULT", raising=False)
        mock_get.return_value = _make_workflow_class()

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        args = _make_args(name="bug-predict", cheap=True)
        try:
            cmd_workflow_run(args)
            assert os.environ.get("ATTUNE_AGENT_MODEL_DEFAULT") == "haiku"
            captured = capsys.readouterr()
            assert "--cheap mode" in captured.out
        finally:
            # SUT does a raw env write monkeypatch can't track — pop it.
            os.environ.pop("ATTUNE_AGENT_MODEL_DEFAULT", None)

    @patch("attune.workflows.get_workflow")
    def test_no_cheap_flag_leaves_env_unchanged(self, mock_get, monkeypatch, capsys):
        """Without --cheap, env var is not set by cmd_workflow_run."""
        import os

        monkeypatch.delenv("ATTUNE_AGENT_MODEL_DEFAULT", raising=False)
        mock_get.return_value = _make_workflow_class()

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        # Note: _make_args doesn't include 'cheap' by default, so the
        # getattr(args, "cheap", False) fallback in cmd_workflow_run
        # must return False here.
        args = _make_args(name="bug-predict")
        try:
            cmd_workflow_run(args)
            assert "ATTUNE_AGENT_MODEL_DEFAULT" not in os.environ
            captured = capsys.readouterr()
            assert "--cheap mode" not in captured.out
        finally:
            # Defense in depth — even if the assertion above doesn't fire,
            # ensure nothing leaks if a future refactor changes behavior.
            os.environ.pop("ATTUNE_AGENT_MODEL_DEFAULT", None)
