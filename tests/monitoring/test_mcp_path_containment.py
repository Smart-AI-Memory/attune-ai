"""Tests for MCP workspace path containment.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.security.path_validation import _validate_file_path

# ---------------------------------------------------------------------------
# MCP handler workspace containment
# ---------------------------------------------------------------------------


class TestMCPWorkspaceContainment:
    """Test MCP handlers enforce workspace-scoped paths."""

    @pytest.fixture
    def server(self, tmp_path):
        from attune.mcp.server import EmpathyMCPServer

        return EmpathyMCPServer(workspace_root=str(tmp_path))

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
    async def test_release_prep_blocks_external_path(self, server):
        with pytest.raises(ValueError, match="outside allowed directory"):
            await server._run_release_prep({"path": "/home/other/repo"})

    @pytest.mark.asyncio
    async def test_auth_recommend_blocks_external_path(self, server):
        with pytest.raises(ValueError, match="outside allowed directory"):
            await server._get_auth_recommend({"file_path": "/home/other/app.py"})

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
    async def test_allows_in_workspace_path(self, server, in_workspace_file, method_name, path_key):
        """Verify in-workspace paths pass validation."""
        method = getattr(server, method_name)
        # Path validation should pass; workflow execution will
        # fail because we're not mocking the workflow — that's OK.
        try:
            await method({path_key: in_workspace_file})
        except ValueError as e:
            if "outside allowed directory" in str(e):
                pytest.fail(f"In-workspace path was blocked: {e}")
        except Exception:
            # Workflow execution errors are expected (no LLM)
            pass

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
