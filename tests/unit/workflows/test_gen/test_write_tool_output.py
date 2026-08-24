"""#2213 regression: test-gen writes real files and reports them truthfully.

The workflow previously had no Write tool (subagents could only describe
tests), while the MCP handler surfaced ``tests_generated``/``output_path``
keys the workflow never produced. These tests pin the wiring: the
Write-capable options shape, the validated output_dir, and result
metadata counted from DISK (not from the model's own claims).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from attune.workflows.agent_sdk_adapter import AgentRunResult
from attune.workflows.test_gen.workflow import TestGenerationWorkflow


@pytest.fixture
def workflow():
    return TestGenerationWorkflow()


class TestResolveOutputDir:
    def test_default_for_directory_target(self, tmp_path):
        out = TestGenerationWorkflow._resolve_output_dir(str(tmp_path), None)
        assert out == tmp_path / "tests" / "generated"

    def test_default_for_file_target(self, tmp_path):
        target = tmp_path / "mod.py"
        target.write_text("x = 1\n")
        out = TestGenerationWorkflow._resolve_output_dir(str(target), None)
        assert out == tmp_path / "tests" / "generated"

    def test_relative_output_dir_anchors_inside(self, tmp_path):
        out = TestGenerationWorkflow._resolve_output_dir(str(tmp_path), "gen")
        assert out == (tmp_path / "gen").resolve()

    def test_outside_output_dir_rejected(self, tmp_path):
        outside = tmp_path.parent / "elsewhere"
        out = TestGenerationWorkflow._resolve_output_dir(str(tmp_path), str(outside))
        assert out is None

    def test_traversal_rejected(self, tmp_path):
        out = TestGenerationWorkflow._resolve_output_dir(str(tmp_path), "../escape")
        assert out is None


class TestExecuteReportsDiskTruth:
    def test_metadata_counts_files_written_this_run(self, workflow, tmp_path):
        out_dir = tmp_path / "tests" / "generated"
        out_dir.mkdir(parents=True)
        (out_dir / "test_preexisting.py").write_text("# old\n")

        async def fake_run(resolved_path, max_turns, depth="standard", output_dir=None):
            (output_dir / "test_mod.py").write_text("def test_ok():\n    assert True\n")
            return AgentRunResult(result_text="wrote tests")

        with patch.object(workflow, "_run_agent_gen", side_effect=fake_run):
            result = asyncio.run(workflow.execute(path=str(tmp_path)))

        assert result.success is True
        meta = result.metadata
        assert meta["output_path"] == str(out_dir)
        assert meta["tests_generated"] == 1  # preexisting file excluded
        assert meta["generated_files"] == [str(out_dir / "test_mod.py")]

    def test_no_files_written_reports_zero(self, workflow, tmp_path):
        with patch.object(workflow, "_run_agent_gen", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = AgentRunResult(result_text="prose only")
            result = asyncio.run(workflow.execute(path=str(tmp_path)))
        assert result.metadata["tests_generated"] == 0
        assert result.metadata["generated_files"] == []

    def test_outside_output_dir_is_an_error_result(self, workflow, tmp_path):
        result = asyncio.run(workflow.execute(path=str(tmp_path), output_dir="/somewhere/else"))
        assert result.success is False
        assert "output_dir" in result.error


class TestSdkOptionsShape:
    @patch("attune.workflows.test_gen.workflow.claude_agent_sdk")
    def test_write_tool_granted_and_guarded(self, mock_sdk, workflow, tmp_path):
        import claude_agent_sdk

        captured: dict = {}

        def capture_options(**kwargs):
            captured.update(kwargs)
            return claude_agent_sdk.ClaudeAgentOptions(**kwargs)

        async def fake_query(*args, **kwargs):
            if False:  # pragma: no cover - empty async generator
                yield None

        mock_sdk.query = lambda prompt, options: fake_query()
        mock_sdk.ClaudeAgentOptions = capture_options
        mock_sdk.AgentDefinition = claude_agent_sdk.AgentDefinition
        mock_sdk.ResultMessage = claude_agent_sdk.ResultMessage
        mock_sdk.HookMatcher = claude_agent_sdk.HookMatcher

        asyncio.run(
            workflow._run_agent_gen(str(tmp_path), 10, output_dir=tmp_path / "tests" / "generated")
        )

        assert "Write" in captured["allowed_tools"]
        assert captured["permission_mode"] == "acceptEdits"
        write_matchers = [m for m in captured["hooks"]["PreToolUse"] if m.matcher == "Write"]
        assert len(write_matchers) == 1
        writer = captured["agents"]["test-writer"]
        assert "Write" in writer.tools
        assert "Write tool" in writer.prompt

    @pytest.mark.asyncio
    async def test_scope_guard_denies_write_outside_output_dir(self, tmp_path):
        from attune.workflows.agent_sdk_adapter import make_edit_scope_guard

        out_dir = tmp_path / "tests" / "generated"
        guard = make_edit_scope_guard([out_dir])

        inside = await guard({"tool_input": {"file_path": str(out_dir / "test_a.py")}}, None, None)
        assert inside == {}

        outside = await guard({"tool_input": {"file_path": str(tmp_path / "evil.py")}}, None, None)
        decision = outside["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"


def _sync_guard_result(coro):
    return asyncio.run(coro)
