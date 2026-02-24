"""Tests for the SimplifyCodeWorkflow."""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.verification.defaults import DEFAULT_VERIFICATION_STRATEGIES
from attune.workflows.simplify_code import (
    SIMPLIFY_CATEGORIES,
    SIMPLIFY_FOCUS_AREAS,
    SimplifyCodeWorkflow,
)


class TestSimplifyCodeWorkflowInit:
    """Test workflow initialization and configuration."""

    def test_workflow_name(self) -> None:
        """Test workflow name is correct."""
        wf = SimplifyCodeWorkflow()
        assert wf.name == "simplify-code"

    def test_workflow_stages(self) -> None:
        """Test workflow has correct stages."""
        wf = SimplifyCodeWorkflow()
        assert wf.stages == ["scan", "analyze", "simplify", "review"]

    def test_default_min_complexity(self) -> None:
        """Test default min_complexity threshold."""
        wf = SimplifyCodeWorkflow()
        assert wf.min_complexity == 5

    def test_custom_min_complexity(self) -> None:
        """Test custom min_complexity."""
        wf = SimplifyCodeWorkflow(min_complexity=10)
        assert wf.min_complexity == 10

    def test_default_max_files(self) -> None:
        """Test default max_files."""
        wf = SimplifyCodeWorkflow()
        assert wf.max_files == 20

    def test_crew_not_initialized_on_init(self) -> None:
        """Test crew is not initialized eagerly."""
        wf = SimplifyCodeWorkflow()
        assert wf._crew is None
        assert wf._crew_available is False


class TestVerificationMapping:
    """Test verification strategy mapping."""

    def test_simplify_code_maps_to_run_tests(self) -> None:
        """Test simplify-code is mapped to run-tests strategy."""
        assert DEFAULT_VERIFICATION_STRATEGIES["simplify-code"] == "run-tests"


class TestScanStage:
    """Test the scan stage (AST complexity analysis)."""

    @pytest.mark.asyncio
    async def test_scan_identifies_complex_functions(
        self,
        tmp_path: Path,
    ) -> None:
        """Test scan finds functions above complexity threshold."""
        # Create a file with a complex function
        code = textwrap.dedent(
            """\
            def simple_func():
                return 1

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
        """
        )
        test_file = tmp_path / "test_code.py"
        test_file.write_text(code)

        wf = SimplifyCodeWorkflow(min_complexity=3)
        result, in_tok, out_tok = await wf._scan(
            {"path": str(tmp_path)},
            wf.tier_map["scan"],
        )

        assert result["files_scanned"] == 1
        assert result["total_hotspots"] >= 1

        # complex_func should be in hotspots
        func_names = [h["function"] for h in result["hotspots"]]
        assert "complex_func" in func_names

    @pytest.mark.asyncio
    async def test_scan_excludes_simple_functions(
        self,
        tmp_path: Path,
    ) -> None:
        """Test scan excludes functions below threshold."""
        code = textwrap.dedent(
            """\
            def simple():
                return 1

            def also_simple(x):
                return x + 1
        """
        )
        test_file = tmp_path / "simple.py"
        test_file.write_text(code)

        wf = SimplifyCodeWorkflow(min_complexity=5)
        result, _, _ = await wf._scan(
            {"path": str(tmp_path)},
            wf.tier_map["scan"],
        )

        assert result["total_hotspots"] == 0

    @pytest.mark.asyncio
    async def test_scan_skips_excluded_dirs(
        self,
        tmp_path: Path,
    ) -> None:
        """Test scan skips __pycache__ and venv dirs."""
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.py").write_text(
            "def f():\n    if True:\n        if True:\n            if True:\n                if True:\n                    if True:\n                        pass"
        )

        wf = SimplifyCodeWorkflow(min_complexity=3)
        result, _, _ = await wf._scan(
            {"path": str(tmp_path)},
            wf.tier_map["scan"],
        )

        assert result["files_scanned"] == 0

    @pytest.mark.asyncio
    async def test_scan_respects_max_files(
        self,
        tmp_path: Path,
    ) -> None:
        """Test scan limits files scanned."""
        for i in range(10):
            (tmp_path / f"file_{i}.py").write_text(f"def func_{i}():\n    return {i}")

        wf = SimplifyCodeWorkflow(max_files=3)
        result, _, _ = await wf._scan(
            {"path": str(tmp_path)},
            wf.tier_map["scan"],
        )

        assert result["files_scanned"] <= 3


class TestFunctionComplexity:
    """Test the static complexity calculator."""

    def test_simple_function(self) -> None:
        """Test baseline complexity for simple function."""
        code = "def f():\n    return 1"
        tree = ast.parse(code)
        func = tree.body[0]
        assert SimplifyCodeWorkflow._function_complexity(func) == 1

    def test_if_adds_complexity(self) -> None:
        """Test if statement adds complexity."""
        code = "def f(x):\n    if x:\n        return 1\n    return 0"
        tree = ast.parse(code)
        func = tree.body[0]
        assert SimplifyCodeWorkflow._function_complexity(func) == 2

    def test_nested_ifs(self) -> None:
        """Test nested ifs accumulate complexity."""
        code = textwrap.dedent(
            """\
            def f(x, y, z):
                if x:
                    if y:
                        if z:
                            return 1
                return 0
        """
        )
        tree = ast.parse(code)
        func = tree.body[0]
        assert SimplifyCodeWorkflow._function_complexity(func) == 4

    def test_loop_adds_complexity(self) -> None:
        """Test for/while loops add complexity."""
        code = textwrap.dedent(
            """\
            def f(items):
                for item in items:
                    while item > 0:
                        item -= 1
        """
        )
        tree = ast.parse(code)
        func = tree.body[0]
        assert SimplifyCodeWorkflow._function_complexity(func) == 3

    def test_boolean_operators(self) -> None:
        """Test and/or add complexity branches."""
        code = "def f(a, b, c):\n    if a and b and c:\n        return 1"
        tree = ast.parse(code)
        func = tree.body[0]
        # 1 base + 1 if + 2 extra bool ops (3 values - 1)
        assert SimplifyCodeWorkflow._function_complexity(func) == 4

    def test_except_handler(self) -> None:
        """Test except handler adds complexity."""
        code = textwrap.dedent(
            """\
            def f():
                try:
                    pass
                except ValueError:
                    pass
                except TypeError:
                    pass
        """
        )
        tree = ast.parse(code)
        func = tree.body[0]
        # 1 base + 2 except handlers
        assert SimplifyCodeWorkflow._function_complexity(func) == 3


class TestShouldSkipStage:
    """Test conditional stage skipping."""

    def test_review_skipped_when_few_findings(self) -> None:
        """Test review is skipped when below threshold."""
        wf = SimplifyCodeWorkflow(min_findings_for_review=3)
        wf._findings_count = 1
        should_skip, reason = wf.should_skip_stage("review", {})
        assert should_skip is True
        assert "below threshold" in reason

    def test_review_runs_when_enough_findings(self) -> None:
        """Test review runs when at or above threshold."""
        wf = SimplifyCodeWorkflow(min_findings_for_review=3)
        wf._findings_count = 5
        should_skip, reason = wf.should_skip_stage("review", {})
        assert should_skip is False

    def test_other_stages_never_skipped(self) -> None:
        """Test non-review stages are never skipped."""
        wf = SimplifyCodeWorkflow()
        for stage in ["scan", "analyze", "simplify"]:
            should_skip, _ = wf.should_skip_stage(stage, {})
            assert should_skip is False


class TestAnalyzeStage:
    """Test the analyze stage."""

    @pytest.mark.asyncio
    async def test_analyze_delegates_to_crew(self) -> None:
        """Test analyze uses RefactoringCrew when available."""
        wf = SimplifyCodeWorkflow()

        # Mock crew
        mock_finding = MagicMock()
        mock_finding.category.value = "simplify"
        mock_finding.to_dict.return_value = {
            "title": "Simplify conditional",
            "category": "simplify",
            "file_path": "/tmp/test.py",
        }

        mock_result = MagicMock()
        mock_result.findings = [mock_finding]

        mock_crew = AsyncMock()
        mock_crew.analyze.return_value = mock_result

        wf._crew = mock_crew
        wf._crew_available = True

        # Create a temp file for the analysis
        input_data = {
            "hotspots": [
                {
                    "file": __file__,
                    "function": "test_func",
                    "line": 1,
                    "end_line": 10,
                    "complexity": 8,
                    "loc": 10,
                },
            ],
        }

        result, _, _ = await wf._analyze(input_data, wf.tier_map["analyze"])

        assert result["crew_used"] is True
        assert result["findings_count"] >= 1
        mock_crew.analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_filters_non_simplify_categories(self) -> None:
        """Test analyze filters out non-simplify findings."""
        wf = SimplifyCodeWorkflow()

        # Mock crew with mixed categories
        simplify_finding = MagicMock()
        simplify_finding.category.value = "simplify"
        simplify_finding.to_dict.return_value = {"category": "simplify"}

        rename_finding = MagicMock()
        rename_finding.category.value = "rename"

        mock_result = MagicMock()
        mock_result.findings = [simplify_finding, rename_finding]

        mock_crew = AsyncMock()
        mock_crew.analyze.return_value = mock_result

        wf._crew = mock_crew
        wf._crew_available = True

        input_data = {
            "hotspots": [
                {
                    "file": __file__,
                    "function": "f",
                    "line": 1,
                    "end_line": 5,
                    "complexity": 6,
                    "loc": 5,
                },
            ],
        }

        result, _, _ = await wf._analyze(input_data, wf.tier_map["analyze"])

        # Only simplify finding should be kept
        assert result["findings_count"] == 1

    @pytest.mark.asyncio
    async def test_analyze_fallback_when_crew_unavailable(self) -> None:
        """Test LLM fallback when crew is not available."""
        wf = SimplifyCodeWorkflow()
        wf._crew = None
        wf._crew_available = False
        # Prevent _initialize_crew from actually loading the crew
        wf._initialize_crew = AsyncMock()

        # Mock _call_llm
        wf._call_llm = AsyncMock(
            return_value=(
                '[{"title": "Flatten nested if", "category": "simplify"}]',
                100,
                50,
            )
        )

        input_data = {
            "hotspots": [
                {
                    "file": "test.py",
                    "function": "f",
                    "line": 1,
                    "end_line": 10,
                    "complexity": 8,
                    "loc": 10,
                },
            ],
        }

        result, _, _ = await wf._analyze(input_data, wf.tier_map["analyze"])

        assert result["crew_used"] is False
        assert result["findings_count"] >= 1
        wf._call_llm.assert_called_once()


class TestSimplifyStage:
    """Test the simplify stage."""

    @pytest.mark.asyncio
    async def test_simplify_generates_before_after(self) -> None:
        """Test simplify generates before/after code via crew."""
        wf = SimplifyCodeWorkflow()

        mock_finding = MagicMock()
        mock_finding.title = "Flatten conditional"
        mock_finding.file_path = __file__
        mock_finding.start_line = 1
        mock_finding.category.value = "simplify"
        mock_finding.before_code = "if x:\n    if y:\n        return 1"
        mock_finding.after_code = "if x and y:\n    return 1"

        mock_crew = AsyncMock()
        mock_crew.generate_refactor.return_value = mock_finding

        wf._crew = mock_crew
        wf._crew_available = True

        input_data = {
            "findings": [
                {
                    "id": "test-1",
                    "title": "Flatten conditional",
                    "description": "Nested if",
                    "category": "simplify",
                    "severity": "medium",
                    "file_path": __file__,
                    "start_line": 1,
                    "end_line": 3,
                    "before_code": "if x:\n    if y:\n        return 1",
                },
            ],
        }

        with patch("attune.workflows.simplify_code.Path") as mock_path:
            mock_path.return_value.read_text.return_value = "code"
            result, _, _ = await wf._simplify(
                input_data,
                wf.tier_map["simplify"],
            )

        assert result["simplification_count"] >= 1
        simplification = result["simplifications"][0]
        assert "before" in simplification
        assert "after" in simplification


class TestReviewStage:
    """Test the review stage."""

    @pytest.mark.asyncio
    async def test_review_calls_llm(self) -> None:
        """Test review stage calls LLM for validation."""
        wf = SimplifyCodeWorkflow()
        wf._call_llm = AsyncMock(return_value=("All simplifications look correct.", 200, 50))

        input_data = {
            "simplifications": [
                {
                    "title": "Flatten conditional",
                    "file": "test.py",
                    "before": "if x:\n    if y:\n        return 1",
                    "after": "if x and y:\n    return 1",
                },
            ],
        }

        result, _, _ = await wf._review(
            input_data,
            wf.tier_map["review"],
        )

        assert "review" in result
        assert result["review"] == "All simplifications look correct."
        wf._call_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_no_simplifications(self) -> None:
        """Test review with empty simplifications."""
        wf = SimplifyCodeWorkflow()

        result, _, _ = await wf._review(
            {"simplifications": []},
            wf.tier_map["review"],
        )

        assert "No simplifications" in result["review"]


class TestSimplifyConstants:
    """Test module-level constants."""

    def test_focus_areas_are_simplification_related(self) -> None:
        """Test SIMPLIFY_FOCUS_AREAS are all simplification-related."""
        expected = ["simplify", "consolidate_conditional", "inline", "dead_code"]
        assert SIMPLIFY_FOCUS_AREAS == expected

    def test_categories_match_focus_areas(self) -> None:
        """Test SIMPLIFY_CATEGORIES matches SIMPLIFY_FOCUS_AREAS."""
        assert SIMPLIFY_CATEGORIES == set(SIMPLIFY_FOCUS_AREAS)


class TestRunStageRouting:
    """Test run_stage routing."""

    @pytest.mark.asyncio
    async def test_unknown_stage_raises(self) -> None:
        """Test unknown stage raises ValueError."""
        wf = SimplifyCodeWorkflow()
        with pytest.raises(ValueError, match="Unknown stage"):
            await wf.run_stage("nonexistent", wf.tier_map["scan"], {})
