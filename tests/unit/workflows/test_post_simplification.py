"""Tests for the PostSimplificationMixin integration."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.post_simplification_mixin import (
    CODE_GENERATING_WORKFLOWS,
    PostSimplificationMixin,
)


class TestPostSimplificationMixinInit:
    """Test mixin initialization."""

    def test_default_disabled(self) -> None:
        """Test post-simplification is disabled by default."""
        mixin = PostSimplificationMixin()
        assert mixin._enable_post_simplification is False

    def test_init_enables(self) -> None:
        """Test _init_post_simplification sets flags."""
        mixin = PostSimplificationMixin()
        mixin._init_post_simplification(
            enable_post_simplification=True,
            simplification_min_complexity=8,
        )
        assert mixin._enable_post_simplification is True
        assert mixin._simplification_min_complexity == 8

    def test_init_default_complexity(self) -> None:
        """Test default min_complexity is 5."""
        mixin = PostSimplificationMixin()
        mixin._init_post_simplification(enable_post_simplification=True)
        assert mixin._simplification_min_complexity == 5


class TestCodeGeneratingWorkflowsConstant:
    """Test the CODE_GENERATING_WORKFLOWS constant."""

    def test_contains_expected_workflows(self) -> None:
        """Test CODE_GENERATING_WORKFLOWS has expected entries."""
        assert "refactor-plan" in CODE_GENERATING_WORKFLOWS
        assert "test-gen" in CODE_GENERATING_WORKFLOWS

    def test_is_frozenset(self) -> None:
        """Test CODE_GENERATING_WORKFLOWS is immutable."""
        assert isinstance(CODE_GENERATING_WORKFLOWS, frozenset)


class TestRunPostSimplification:
    """Test the _run_post_simplification method."""

    @pytest.mark.asyncio
    async def test_noop_when_disabled(self) -> None:
        """Test returns result unchanged when disabled."""
        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = False

        mock_result = MagicMock()
        returned = await mixin._run_post_simplification(mock_result, {})
        assert returned is mock_result

    @pytest.mark.asyncio
    async def test_noop_when_result_failed(self) -> None:
        """Test returns result unchanged when execution failed."""
        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True

        mock_result = MagicMock()
        mock_result.success = False
        returned = await mixin._run_post_simplification(mock_result, {})
        assert returned is mock_result

    @pytest.mark.asyncio
    async def test_noop_when_no_path(self) -> None:
        """Test returns result unchanged when no path in kwargs."""
        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True

        mock_result = MagicMock()
        mock_result.success = True
        returned = await mixin._run_post_simplification(mock_result, {})
        assert returned is mock_result

    @pytest.mark.asyncio
    async def test_scans_when_enabled(self, tmp_path: Path) -> None:
        """Test runs scan when enabled with valid path."""
        # Create a complex Python file
        code = textwrap.dedent(
            """\
            def complex_func(x, y, z):
                if x > 0:
                    if y > 0:
                        if z > 0:
                            for i in range(x):
                                if i % 2 == 0:
                                    try:
                                        return i
                                    except ValueError:
                                        pass
                return None
        """,
        )
        (tmp_path / "complex.py").write_text(code)

        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True
        mixin._simplification_min_complexity = 3

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = {}

        returned = await mixin._run_post_simplification(
            mock_result,
            {"path": str(tmp_path)},
        )

        assert returned is mock_result
        assert mixin._simplification_result is not None
        assert mixin._simplification_result["hotspots_found"] >= 1

    @pytest.mark.asyncio
    async def test_attaches_metadata_to_final_output(
        self,
        tmp_path: Path,
    ) -> None:
        """Test attaches simplification metadata to result."""
        code = textwrap.dedent(
            """\
            def nested(a, b, c, d, e):
                if a:
                    if b:
                        if c:
                            if d:
                                if e:
                                    return 1
                return 0
        """,
        )
        (tmp_path / "nested.py").write_text(code)

        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True
        mixin._simplification_min_complexity = 3

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = {"existing_key": "value"}

        await mixin._run_post_simplification(
            mock_result,
            {"path": str(tmp_path)},
        )

        assert "_simplification" in mock_result.final_output

    @pytest.mark.asyncio
    async def test_no_hotspots_for_simple_code(self, tmp_path: Path) -> None:
        """Test no hotspots found for simple code."""
        (tmp_path / "simple.py").write_text("def f():\n    return 1\n")

        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True
        mixin._simplification_min_complexity = 5

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = {}

        await mixin._run_post_simplification(
            mock_result,
            {"path": str(tmp_path)},
        )

        assert mixin._simplification_result is not None
        assert mixin._simplification_result["hotspots_found"] == 0

    @pytest.mark.asyncio
    async def test_handles_import_error_gracefully(self) -> None:
        """Test graceful degradation when SimplifyCodeWorkflow unavailable."""
        import builtins

        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True

        mock_result = MagicMock()
        mock_result.success = True

        original_import = builtins.__import__

        def mock_import(name: str, *args: object, **kwargs: object) -> object:
            if "simplify_code" in name:
                raise ImportError("not available")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            # Should not raise
            returned = await mixin._run_post_simplification(
                mock_result,
                {"path": "/some/path"},
            )
            assert returned is mock_result

    @pytest.mark.asyncio
    async def test_empty_path_string_returns_early(self) -> None:
        """Test an empty-string path (falsy but present) skips scanning.

        ``kwargs.get("path", ".")`` only falls back to the default when
        the key is absent; an explicit empty string is falsy and should
        hit the early return distinct from the "no path in kwargs" case.
        """
        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True

        mock_result = MagicMock()
        mock_result.success = True

        returned = await mixin._run_post_simplification(
            mock_result,
            {"path": ""},
        )

        assert returned is mock_result
        assert mixin._simplification_result is None

    @pytest.mark.asyncio
    async def test_skips_file_with_syntax_error(self, tmp_path: Path) -> None:
        """Test a file that fails ast.parse is skipped, not fatal."""
        (tmp_path / "broken.py").write_text("def bad(:\n    pass\n")
        (tmp_path / "ok.py").write_text("def f():\n    return 1\n")

        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True
        mixin._simplification_min_complexity = 3

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = {}

        returned = await mixin._run_post_simplification(
            mock_result,
            {"path": str(tmp_path)},
        )

        assert returned is mock_result
        assert mixin._simplification_result is not None
        # Only the syntactically-valid file counts toward files_scanned.
        assert mixin._simplification_result["files_scanned"] == 1

    @pytest.mark.asyncio
    async def test_real_import_error_is_caught(self, tmp_path: Path) -> None:
        """Test an ImportError raised by the module's own ``import ast``
        (not an unrelated import) is caught and swallowed.
        """
        import builtins

        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = {}

        original_import = builtins.__import__

        def mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "ast":
                raise ImportError("ast unavailable")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            returned = await mixin._run_post_simplification(
                mock_result,
                {"path": str(tmp_path)},
            )

        assert returned is mock_result
        # Scan never happened; result stays unset.
        assert mixin._simplification_result is None

    @pytest.mark.asyncio
    async def test_type_error_from_bad_path_type_is_caught(self) -> None:
        """Test a non-str/PathLike path (TypeError from Path()) is
        caught by the data-error branch, not raised.
        """
        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = {}

        returned = await mixin._run_post_simplification(
            mock_result,
            {"path": 123},
        )

        assert returned is mock_result
        assert mixin._simplification_result is None

    @pytest.mark.asyncio
    async def test_generic_exception_during_scan_is_caught(
        self,
        tmp_path: Path,
    ) -> None:
        """Test an unexpected exception during the scan (not ImportError
        or a data-shape error) is caught by the catch-all branch.
        """
        mixin = PostSimplificationMixin()
        mixin._enable_post_simplification = True

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = {}

        with patch("pathlib.Path.rglob", side_effect=RuntimeError("boom")):
            returned = await mixin._run_post_simplification(
                mock_result,
                {"path": str(tmp_path)},
            )

        assert returned is mock_result
        assert mixin._simplification_result is None


class TestRefactorPlanOptIn:
    """Test that RefactorPlanWorkflow opts in to simplification."""

    def test_refactor_plan_enables_simplification(self) -> None:
        """Test RefactorPlanWorkflow sets enable_post_simplification."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf._enable_post_simplification is True

    def test_refactor_plan_can_disable_simplification(self) -> None:
        """Test RefactorPlanWorkflow simplification can be disabled."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow(enable_post_simplification=False)
        assert wf._enable_post_simplification is False


class TestBaseWorkflowIntegration:
    """Test BaseWorkflow integration with PostSimplificationMixin."""

    def test_base_workflow_default_disabled(self) -> None:
        """Test BaseWorkflow has post-simplification disabled by default."""
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        wf = SimplifyCodeWorkflow()
        assert wf._enable_post_simplification is False

    def test_base_workflow_can_enable(self) -> None:
        """Test BaseWorkflow can enable post-simplification."""
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        wf = SimplifyCodeWorkflow(enable_post_simplification=True)
        assert wf._enable_post_simplification is True
