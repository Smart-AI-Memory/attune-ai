"""Tests for MCP workspace path containment.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.security.path_validation import _validate_file_path

# ---------------------------------------------------------------------------
# MCP handler workspace containment
# ---------------------------------------------------------------------------


class TestMCPWorkspaceContainment:
    """Test MCP handlers enforce workspace-scoped paths."""

    @pytest.fixture
    def server(self, tmp_path):
        from attune.mcp.server import AttuneMCPServer

        return AttuneMCPServer(workspace_root=str(tmp_path))

    @pytest.fixture
    def in_workspace_file(self, tmp_path):
        f = tmp_path / "src" / "app.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x = 1")
        return str(f)

    @pytest.mark.parametrize(
        "method_name,path_key",
        [
            ("_run_security_audit", "path"),
            ("_run_bug_predict", "path"),
            ("_run_code_review", "path"),
            ("_run_performance_audit", "path"),
        ],
    )
    @pytest.mark.asyncio
    async def test_blocks_absolute_path_outside_workspace(self, server, method_name, path_key):
        method = getattr(server, method_name)
        with pytest.raises(ValueError, match="outside allowed directory"):
            await method({path_key: "/home/other/repo/file.py"})

    @pytest.mark.asyncio
    async def test_release_notes_blocks_external_path(self, server):
        with pytest.raises(ValueError, match="outside allowed directory"):
            await server._run_release_notes({"path": "/home/other/repo"})

    @pytest.mark.asyncio
    async def test_auth_recommend_blocks_external_path(self, server):
        with pytest.raises(ValueError, match="outside allowed directory"):
            await server._get_auth_recommend({"file_path": "/home/other/app.py"})

    @pytest.mark.parametrize(
        "method_name,path_key,workflow_target",
        [
            (
                "_run_security_audit",
                "path",
                "attune.workflows.security_audit.SecurityAuditWorkflow",
            ),
            (
                "_run_bug_predict",
                "path",
                "attune.workflows.bug_predict.BugPredictionWorkflow",
            ),
            (
                "_run_code_review",
                "path",
                "attune.workflows.code_review.CodeReviewWorkflow",
            ),
            (
                "_run_performance_audit",
                "path",
                "attune.workflows.perf_audit.PerformanceAuditWorkflow",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_allows_in_workspace_path(
        self, server, in_workspace_file, method_name, path_key, workflow_target
    ):
        """Verify in-workspace paths pass validation.

        The workflow class is mocked at its SOURCE module (the handlers
        lazy-import it at call time): the earlier no-mock version of this
        test let the real SDK workflow spawn a `claude` CLI subprocess
        inside the xdist worker, which crashed workers across OS lanes
        (the windows-xdist-flakes crash class; broke main 2026-06-10).
        Path validation runs BEFORE the workflow import, so mocking the
        workflow preserves exactly what this test asserts.
        """
        fake_result = MagicMock(
            success=True,
            final_output={},
            cost_report=MagicMock(total_cost=0.0),
            provider="anthropic",
        )
        fake_workflow_cls = MagicMock(
            return_value=MagicMock(execute=AsyncMock(return_value=fake_result)),
        )
        method = getattr(server, method_name)
        with patch(workflow_target, fake_workflow_cls):
            try:
                await method({path_key: in_workspace_file})
            except ValueError as e:
                if "outside allowed directory" in str(e):
                    pytest.fail(f"In-workspace path was blocked: {e}")

        # Validation passed AND the validated path reached the workflow.
        execute = fake_workflow_cls.return_value.execute
        execute.assert_awaited_once()
        assert execute.await_args.kwargs["path"] == str(Path(in_workspace_file).resolve())

    @pytest.mark.asyncio
    async def test_blocks_traversal_outside_workspace(self, server):
        """Parent traversal must be caught."""
        with pytest.raises(ValueError, match="outside allowed directory"):
            await server._run_security_audit({"path": "../../etc/passwd"})


# ---------------------------------------------------------------------------
# Path validation error messages
# ---------------------------------------------------------------------------


class TestPathValidationMessages:
    """Test improved error messages from _validate_file_path."""

    def test_system_dir_message_unchanged(self):
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/etc/passwd")

    def test_workspace_message_shows_both_paths(self, tmp_path):
        allowed = str(tmp_path / "workspace")
        Path(allowed).mkdir(parents=True, exist_ok=True)
        with pytest.raises(ValueError, match="outside allowed directory") as exc_info:
            _validate_file_path("/tmp/other/file.py", allowed_dir=allowed)
        error_msg = str(exc_info.value)
        assert str(Path(allowed).resolve()) in error_msg

    def test_traversal_outside_workspace_blocked(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        with pytest.raises(ValueError, match="outside allowed directory"):
            _validate_file_path(
                str(workspace / ".." / ".." / "etc" / "passwd"),
                allowed_dir=str(workspace),
            )

    def test_in_workspace_path_passes(self, tmp_path):
        workspace = tmp_path / "workspace"
        target = workspace / "src" / "app.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1")
        result = _validate_file_path(str(target), allowed_dir=str(workspace))
        assert result == target.resolve()

    def test_error_includes_resolved_path(self, tmp_path):
        workspace = tmp_path / "ws"
        workspace.mkdir()
        outside = tmp_path / "outside" / "file.py"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("x = 1")
        with pytest.raises(ValueError) as exc_info:
            _validate_file_path(str(outside), allowed_dir=str(workspace))
        assert str(outside.resolve()) in str(exc_info.value)
