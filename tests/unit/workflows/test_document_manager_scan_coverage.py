"""Coverage-completing tests for DocumentManagerWorkflow.

Targets the uncovered surface: ``default_context()`` and the
``_scan_codebase`` helper across all its branches — nonexistent path,
single file (success + read error), full directory scan (README,
pyproject, src modules, directory listing), the per-file read-error
sub-branches, and the outer scan failure.

Real files under ``tmp_path`` drive the happy paths; targeted
``read_text`` / ``iterdir`` failures drive the error branches.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from attune.workflows.context import WorkflowContext
from attune.workflows.document_manager import DocumentManagerWorkflow


@pytest.fixture
def workflow() -> DocumentManagerWorkflow:
    return DocumentManagerWorkflow()


@pytest.mark.unit
class TestDefaultContext:
    """default_context() classmethod."""

    def test_returns_configured_context(self):
        ctx = DocumentManagerWorkflow.default_context()
        assert isinstance(ctx, WorkflowContext)
        assert ctx.prompt is not None
        assert ctx.parsing is not None

    def test_accepts_xml_config(self):
        ctx = DocumentManagerWorkflow.default_context(xml_config={"foo": "bar"})
        assert isinstance(ctx, WorkflowContext)


@pytest.mark.unit
class TestScanCodebase:
    """_scan_codebase across all branches."""

    def test_nonexistent_path(self, workflow):
        result = workflow._scan_codebase(Path("/no/such/path/here"))
        assert "Path does not exist" in result

    def test_single_file(self, workflow, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("def foo():\n    return 1\n", encoding="utf-8")
        result = workflow._scan_codebase(f)
        assert "File: mod.py" in result
        assert "def foo" in result

    def test_single_file_read_error(self, workflow, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n", encoding="utf-8")
        with patch.object(Path, "read_text", side_effect=OSError("denied")):
            result = workflow._scan_codebase(f)
        assert "Error reading file" in result

    def test_full_directory_scan(self, workflow, tmp_path):
        (tmp_path / "README.md").write_text("# Project\nintro\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        src = tmp_path / "src"
        src.mkdir()
        (src / "core.py").write_text('"""Core module docstring."""\n\nx = 1\n', encoding="utf-8")
        (tmp_path / "subpkg").mkdir()
        (tmp_path / "notes.txt").write_text("notes\n", encoding="utf-8")
        (tmp_path / ".hidden").write_text("skip me\n", encoding="utf-8")

        result = workflow._scan_codebase(tmp_path)

        assert "README.md (excerpt)" in result
        assert "pyproject.toml (excerpt)" in result
        assert "Key Python Modules" in result
        assert "Core module docstring" in result
        assert "Directory Structure" in result
        assert "subpkg/ (directory)" in result
        assert "notes.txt" in result
        # Hidden entries are skipped.
        assert ".hidden" not in result

    def test_directory_read_errors_are_tolerated(self, workflow, tmp_path):
        # README, pyproject, and a src module all exist but reading raises.
        (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        src = tmp_path / "src"
        src.mkdir()
        (src / "core.py").write_text("x = 1\n", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("denied")):
            result = workflow._scan_codebase(tmp_path)

        # Read failures are swallowed; the structure section still renders.
        assert "Directory Structure" in result
        assert "README.md (excerpt)" not in result  # excerpt block skipped on error

    def test_outer_exception_returns_error_string(self, workflow, tmp_path):
        with patch.object(Path, "iterdir", side_effect=RuntimeError("boom")):
            result = workflow._scan_codebase(tmp_path)
        assert "Error scanning directory" in result
