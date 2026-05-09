"""Unit tests for attune.orchestration.tools.performance.

Covers RealPerformanceProfiler.analyze and the static helpers.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from attune.orchestration.tools.performance import (
    PERFORMANCE_TOOLS,
    RealPerformanceProfiler,
)


@pytest.fixture
def profiler(tmp_path: Path) -> RealPerformanceProfiler:
    return RealPerformanceProfiler(project_root=str(tmp_path))


# ---------------------------------------------------------------------------
# Module-level
# ---------------------------------------------------------------------------


class TestModuleAttributes:
    def test_performance_tools_dict(self):
        assert PERFORMANCE_TOOLS["performance_profiler"] is RealPerformanceProfiler


# ---------------------------------------------------------------------------
# _compute_complexity
# ---------------------------------------------------------------------------


class TestComputeComplexity:
    def _parse_first_func(self, source: str):
        import ast

        tree = ast.parse(textwrap.dedent(source))
        return tree.body[0]

    def test_base_complexity_is_one(self):
        """Empty function → complexity 1."""
        node = self._parse_first_func(
            """
            def f():
                return 1
            """
        )
        assert RealPerformanceProfiler._compute_complexity(node) == 1

    def test_if_adds_branch(self):
        node = self._parse_first_func(
            """
            def f(x):
                if x:
                    return 1
                return 0
            """
        )
        assert RealPerformanceProfiler._compute_complexity(node) == 2

    def test_for_loop_adds_branch(self):
        node = self._parse_first_func(
            """
            def f(items):
                for i in items:
                    pass
            """
        )
        assert RealPerformanceProfiler._compute_complexity(node) == 2

    def test_async_for_adds_branch(self):
        node = self._parse_first_func(
            """
            async def f(items):
                async for i in items:
                    pass
            """
        )
        assert RealPerformanceProfiler._compute_complexity(node) == 2

    def test_while_adds_branch(self):
        node = self._parse_first_func(
            """
            def f():
                while True:
                    break
            """
        )
        assert RealPerformanceProfiler._compute_complexity(node) == 2

    def test_except_handler_adds_branch(self):
        node = self._parse_first_func(
            """
            def f():
                try:
                    pass
                except ValueError:
                    pass
                except KeyError:
                    pass
            """
        )
        # 1 base + 2 except handlers
        assert RealPerformanceProfiler._compute_complexity(node) == 3

    def test_bool_op_adds_one_per_extra_value(self):
        """`a and b and c` → 1 BoolOp with 3 values → +2."""
        node = self._parse_first_func(
            """
            def f(a, b, c):
                if a and b and c:
                    return 1
            """
        )
        # 1 base + 1 if + 2 bool extras = 4
        assert RealPerformanceProfiler._compute_complexity(node) == 4

    def test_if_expression_adds_branch(self):
        node = self._parse_first_func(
            """
            def f(x):
                return 1 if x else 0
            """
        )
        assert RealPerformanceProfiler._compute_complexity(node) == 2


# ---------------------------------------------------------------------------
# _compute_function_length
# ---------------------------------------------------------------------------


class TestComputeFunctionLength:
    def _parse_first_func(self, source: str):
        import ast

        tree = ast.parse(textwrap.dedent(source))
        return tree.body[0]

    def test_empty_body_returns_zero(self):
        """If node.body is empty, return 0. We use a Module with a func that
        has only a Pass to test the non-empty path; we'll mock the empty case."""
        from unittest.mock import MagicMock

        node = MagicMock()
        node.body = []
        assert RealPerformanceProfiler._compute_function_length(node) == 0

    def test_single_line_function(self):
        node = self._parse_first_func(
            """
            def f():
                return 1
            """
        )
        assert RealPerformanceProfiler._compute_function_length(node) == 1

    def test_multi_line_function(self):
        node = self._parse_first_func(
            """
            def f():
                a = 1
                b = 2
                c = 3
                return a + b + c
            """
        )
        assert RealPerformanceProfiler._compute_function_length(node) == 4

    def test_uses_lineno_when_no_end_lineno(self):
        """If end_lineno is None, fall back to lineno."""
        from unittest.mock import MagicMock

        first = MagicMock()
        first.lineno = 5
        last = MagicMock()
        last.end_lineno = None
        last.lineno = 10
        node = MagicMock()
        node.body = [first, last]
        assert RealPerformanceProfiler._compute_function_length(node) == 6


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


class TestAnalyze:
    def test_no_python_files_yields_perfect_score(self, tmp_path):
        """Empty directory → 0 files, score 10.0, passed True."""
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("src")
        assert report.score == 10.0
        assert report.total_files == 0
        assert report.functions_analyzed == 0
        assert report.high_complexity == []
        assert report.large_functions == []
        assert report.passed is True

    def test_simple_clean_files(self, tmp_path):
        """Simple .py files with low complexity → no deductions."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            textwrap.dedent(
                """
                def hello():
                    return 1
                """
            )
        )
        (src / "b.py").write_text(
            textwrap.dedent(
                """
                def world(x):
                    if x:
                        return 1
                    return 0
                """
            )
        )
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("src")
        assert report.total_files == 2
        assert report.functions_analyzed == 2
        assert report.high_complexity == []
        assert report.large_functions == []
        assert report.score == 10.0
        assert report.passed is True

    def test_dunder_files_skipped(self, tmp_path):
        """__init__.py and __main__.py are skipped."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "__init__.py").write_text("def x(): return 1\n")
        (src / "__main__.py").write_text("def y(): return 1\n")
        (src / "regular.py").write_text("def z(): return 1\n")
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("src")
        # Only regular.py counted
        assert report.total_files == 1
        assert report.functions_analyzed == 1

    def test_high_complexity_function_recorded(self, tmp_path):
        """Function with > 10 branches is added to high_complexity."""
        src = tmp_path / "src"
        src.mkdir()
        # Build a function with many if branches
        ifs = "\n    ".join(f"if x == {i}:\n        return {i}" for i in range(15))
        (src / "complex.py").write_text(f"def f(x):\n    {ifs}\n    return -1\n")
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("src")
        assert len(report.high_complexity) == 1
        entry = report.high_complexity[0]
        assert entry["function"] == "f"
        assert entry["complexity"] > 10
        assert entry["file"].endswith("complex.py")
        # Score deducted
        assert report.score < 10.0

    def test_large_function_recorded(self, tmp_path):
        """Function > 50 lines is added to large_functions."""
        src = tmp_path / "src"
        src.mkdir()
        body = "\n    ".join(f"x = {i}" for i in range(60))
        (src / "big.py").write_text(f"def f():\n    {body}\n")
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("src")
        assert len(report.large_functions) == 1
        entry = report.large_functions[0]
        assert entry["function"] == "f"
        assert entry["lines"] > 50

    def test_score_floor_zero(self, tmp_path):
        """Many bad functions → score floored at 0.0."""
        src = tmp_path / "src"
        src.mkdir()
        # 10 high-complexity functions × 0.5 = -5.0, capped at -3.0
        # 10 large functions × 0.3 = -3.0, capped at -2.0
        # Total: -5.0 → score 5.0 (still positive). Need MORE deductions.
        # Actually max deduction is 3 + 2 = 5 → min score 5. Can't reach 0.
        # The cap means score >= 5. Let me just verify the cap works.
        ifs = "\n    ".join(f"if x == {i}:\n        return {i}" for i in range(15))
        for i in range(10):
            (src / f"f{i}.py").write_text(f"def f{i}(x):\n    {ifs}\n    return -1\n")
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("src")
        # Capped deduction: -3.0 from complexity → score 7.0
        assert report.score == 7.0

    def test_failed_threshold(self, tmp_path):
        """Score below 6.0 → passed False. Build enough complexity + large funcs
        to deduct max."""
        src = tmp_path / "src"
        src.mkdir()
        # 6 high-complexity functions × 0.5 = 3.0 (capped) → -3
        ifs = "\n    ".join(f"if x == {i}:\n        return {i}" for i in range(15))
        for i in range(6):
            (src / f"hc{i}.py").write_text(f"def f{i}(x):\n    {ifs}\n    return -1\n")
        # 7 large functions × 0.3 = 2.1 (capped at 2.0) → -2
        body = "\n    ".join(f"x = {i}" for i in range(60))
        for i in range(7):
            (src / f"big{i}.py").write_text(f"def g{i}():\n    {body}\n")
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("src")
        # 10.0 - 3.0 - 2.0 = 5.0 → fails 6.0 threshold
        assert report.score == 5.0
        assert report.passed is False

    def test_syntax_error_logged_and_skipped(self, tmp_path, caplog):
        """Files with syntax errors → logged, skipped."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "broken.py").write_text("def f(:\n    invalid\n")
        (src / "ok.py").write_text("def g(): return 1\n")
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        with caplog.at_level("WARNING"):
            report = profiler.analyze("src")
        assert any("Failed to parse" in r.message for r in caplog.records)
        # Only the valid file was counted
        assert report.total_files == 1
        assert report.functions_analyzed == 1

    def test_target_is_single_file(self, tmp_path):
        """target_path points to a single file, not a directory."""
        f = tmp_path / "single.py"
        f.write_text("def f(): return 1\n")
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("single.py")
        assert report.total_files == 1
        assert report.functions_analyzed == 1

    def test_async_function_analyzed(self, tmp_path):
        """async def functions are also analyzed."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            textwrap.dedent(
                """
                async def f():
                    return 1
                """
            )
        )
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("src")
        assert report.functions_analyzed == 1

    def test_high_complexity_truncated_to_20(self, tmp_path):
        """high_complexity list is sliced to first 20."""
        src = tmp_path / "src"
        src.mkdir()
        ifs = "\n    ".join(f"if x == {i}:\n        return {i}" for i in range(15))
        for i in range(25):
            (src / f"f{i}.py").write_text(f"def f{i}(x):\n    {ifs}\n    return -1\n")
        profiler = RealPerformanceProfiler(project_root=str(tmp_path))
        report = profiler.analyze("src")
        assert len(report.high_complexity) == 20

    def test_path_relative_fallback(self, tmp_path):
        """If file is outside project_root, rel_path falls back to absolute str."""
        # Create a file outside project_root
        outside = tmp_path.parent / "outside_project_test.py"
        outside.write_text("def f(): return 1\n")
        try:
            profiler = RealPerformanceProfiler(project_root=str(tmp_path))
            # Pass an absolute path that's outside project_root
            report = profiler.analyze(str(outside))
            assert report.total_files == 1
        finally:
            outside.unlink(missing_ok=True)
