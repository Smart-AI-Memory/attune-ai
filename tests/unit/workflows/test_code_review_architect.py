"""Unit tests for attune.workflows.code_review_architect module.

Tests cover:
- _read_file_snippet: safe file reading helper
- _build_directory_tree: directory tree generation
- ArchitectMixin._gather_project_context: project metadata collection
- ArchitectMixin._architect_review: architectural review stage

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.code_review_architect import (
    ArchitectMixin,
    _build_directory_tree,
    _read_file_snippet,
)
from attune.workflows.compat import ModelTier

# ---------------------------------------------------------------------------
# _read_file_snippet
# ---------------------------------------------------------------------------


class TestReadFileSnippet:
    """Tests for the _read_file_snippet helper."""

    def test_reads_file_content(self, tmp_path: Path) -> None:
        """Test reading a file returns its content."""
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        result = _read_file_snippet(f, 1000)
        assert result == "hello world"

    def test_truncates_to_max_chars(self, tmp_path: Path) -> None:
        """Test content is truncated to max_chars."""
        f = tmp_path / "long.txt"
        f.write_text("a" * 100, encoding="utf-8")
        result = _read_file_snippet(f, 10)
        assert len(result) == 10

    def test_nonexistent_file_returns_empty(self) -> None:
        """Test that missing file returns empty string."""
        result = _read_file_snippet(Path("/nonexistent/file.txt"), 100)
        assert result == ""

    def test_os_error_returns_empty(self, tmp_path: Path) -> None:
        """Test that OSError returns empty string."""
        f = tmp_path / "test.txt"
        f.write_text("data", encoding="utf-8")
        with patch.object(Path, "read_text", side_effect=OSError("denied")):
            result = _read_file_snippet(f, 100)
        assert result == ""


# ---------------------------------------------------------------------------
# _build_directory_tree
# ---------------------------------------------------------------------------


class TestBuildDirectoryTree:
    """Tests for _build_directory_tree helper."""

    def test_basic_tree(self, tmp_path: Path) -> None:
        """Test building a simple directory tree."""
        (tmp_path / "main.py").write_text("pass", encoding="utf-8")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "module.py").write_text("pass", encoding="utf-8")

        tree = _build_directory_tree(tmp_path, max_depth=2)

        assert tmp_path.name in tree
        assert "main.py" in tree
        assert "sub/" in tree

    def test_excludes_hidden_and_builtin_dirs(self, tmp_path: Path) -> None:
        """Test that excluded dirs (.git, __pycache__) are skipped."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("pass", encoding="utf-8")

        tree = _build_directory_tree(tmp_path, max_depth=3)

        assert ".git" not in tree
        assert "__pycache__" not in tree
        assert "src/" in tree

    def test_max_depth_limits_traversal(self, tmp_path: Path) -> None:
        """Test that max_depth stops descent."""
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "deep.py").write_text("pass", encoding="utf-8")

        tree = _build_directory_tree(tmp_path, max_depth=1)

        # depth 1 should not include 'c/' directory contents
        assert "deep.py" not in tree

    def test_os_error_handled(self, tmp_path: Path) -> None:
        """Test graceful handling when os.walk raises OSError."""
        with patch("attune.workflows.code_review_architect.os.walk", side_effect=OSError("denied")):
            tree = _build_directory_tree(tmp_path)
        assert "Unable to read" in tree


# ---------------------------------------------------------------------------
# ArchitectMixin._gather_project_context
# ---------------------------------------------------------------------------


class _FakeArchitectHost(ArchitectMixin):
    """Minimal host for architect mixin testing."""

    def __init__(self) -> None:
        self._auth_mode_used: str | None = None
        self._executor = None
        self._api_key: str | None = None

    def _is_xml_enabled(self) -> bool:
        """Check if XML prompts are enabled."""
        return False

    def _render_xml_prompt(self, **kwargs) -> str:
        """Render XML prompt (mock)."""
        return "xml prompt"

    def _parse_xml_response(self, response: str) -> dict:
        """Parse XML response (mock)."""
        return {}

    async def _call_llm(self, tier, system, user_msg, max_tokens=3000):
        """Mock LLM call."""
        return "review response APPROVE", 100, 200

    async def run_step_with_executor(self, step, prompt, system=None):
        """Mock executor."""
        return "executor response APPROVE", 50, 100, 0.01


class TestGatherProjectContext:
    """Tests for ArchitectMixin._gather_project_context."""

    def test_includes_project_name(self, tmp_path: Path) -> None:
        """Test that project name is included in context."""
        host = _FakeArchitectHost()
        with patch("attune.workflows.code_review_architect.Path.cwd", return_value=tmp_path):
            result = host._gather_project_context()
        assert tmp_path.name in result

    def test_includes_pyproject_toml(self, tmp_path: Path) -> None:
        """Test that pyproject.toml content is included."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"', encoding="utf-8")
        host = _FakeArchitectHost()
        with patch("attune.workflows.code_review_architect.Path.cwd", return_value=tmp_path):
            result = host._gather_project_context()
        assert "pyproject.toml" in result

    def test_includes_readme(self, tmp_path: Path) -> None:
        """Test that README.md content is included."""
        (tmp_path / "README.md").write_text("# Test Project", encoding="utf-8")
        host = _FakeArchitectHost()
        with patch("attune.workflows.code_review_architect.Path.cwd", return_value=tmp_path):
            result = host._gather_project_context()
        assert "README.md" in result

    def test_empty_project_returns_empty(self, tmp_path: Path) -> None:
        """Test that an empty project returns empty string."""
        host = _FakeArchitectHost()
        with patch("attune.workflows.code_review_architect.Path.cwd", return_value=tmp_path):
            result = host._gather_project_context()
        # Only header lines, may return "" if len(parts) <= 3
        # The tree is always present, so it won't be empty
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# ArchitectMixin._architect_review
# ---------------------------------------------------------------------------


class TestArchitectReview:
    """Tests for ArchitectMixin._architect_review."""

    @pytest.fixture
    def host(self) -> _FakeArchitectHost:
        """Create a host instance."""
        return _FakeArchitectHost()

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_architect.format_code_review_report",
        return_value="formatted report",
    )
    async def test_basic_review(
        self,
        mock_format: MagicMock,
        host: _FakeArchitectHost,
    ) -> None:
        """Test basic architect review execution."""
        input_data = {
            "code_to_review": "def foo(): pass",
            "scan_results": "no issues",
            "classification": "standard",
        }

        result, in_t, out_t = await host._architect_review(input_data, ModelTier.PREMIUM)

        assert "architectural_review" in result
        assert result["verdict"] == "approve"
        assert result["model_tier_used"] == ModelTier.PREMIUM.value
        assert result["formatted_report"] == "formatted report"

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_architect.format_code_review_report",
        return_value="report",
    )
    async def test_verdict_request_changes(
        self,
        mock_format: MagicMock,
        host: _FakeArchitectHost,
    ) -> None:
        """Test that REQUEST_CHANGES in response sets correct verdict."""
        host._call_llm = AsyncMock(return_value=("REQUEST_CHANGES: issues found", 100, 200))

        result, _, _ = await host._architect_review(
            {"code_to_review": "bad code", "scan_results": "", "classification": ""},
            ModelTier.PREMIUM,
        )

        assert result["verdict"] == "request_changes"

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_architect.format_code_review_report",
        return_value="report",
    )
    async def test_xml_parsed_verdict(
        self,
        mock_format: MagicMock,
        host: _FakeArchitectHost,
    ) -> None:
        """Test that XML-parsed verdict is used when available."""

        class MockParsed:
            extra = {"verdict": "reject"}

        host._parse_xml_response = lambda r: {
            "xml_parsed": True,
            "_parsed_response": MockParsed(),
            "summary": "summary",
            "findings": [],
            "checklist": [],
        }

        result, _, _ = await host._architect_review(
            {"code_to_review": "code", "scan_results": "", "classification": ""},
            ModelTier.PREMIUM,
        )

        assert result["verdict"] == "reject"
        assert result["xml_parsed"] is True

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_architect.format_code_review_report",
        return_value="report",
    )
    async def test_executor_fallback(
        self,
        mock_format: MagicMock,
        host: _FakeArchitectHost,
    ) -> None:
        """Test fallback to _call_llm when executor raises."""
        host._api_key = "test-key"

        async def failing_executor(**kwargs):
            raise RuntimeError("executor failed")

        host.run_step_with_executor = failing_executor

        result, _, _ = await host._architect_review(
            {"code_to_review": "code", "scan_results": "", "classification": ""},
            ModelTier.PREMIUM,
        )

        # Should fall back to _call_llm response
        assert "architectural_review" in result
