"""Tests for RealPerformanceProfiler AST-based analysis.

Verifies that the performance profiler correctly identifies high-complexity
functions and oversized functions through static analysis.

Generated with XML-enhanced task prompts.
"""

import textwrap

import pytest

from attune.orchestration.real_tools import RealPerformanceProfiler

# ---------------------------------------------------------------------------
# Task 4.1: Analyze simple file — clean code scores high
# ---------------------------------------------------------------------------


class TestAnalyzeSimpleFile:
    """Test profiler on simple, clean code."""

    def test_analyze_simple_file_scores_high(self, tmp_path: str) -> None:
        """Clean code with low complexity should score near 10.0."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        simple_code = textwrap.dedent(
            """\
            def add(a: int, b: int) -> int:
                return a + b

            def greet(name: str) -> str:
                return f"Hello, {name}"

            def multiply(x: float, y: float) -> float:
                return x * y
        """,
        )
        (src_dir / "simple.py").write_text(simple_code)

        profiler = RealPerformanceProfiler(str(tmp_path))
        report = profiler.analyze("src")

        assert report.score == pytest.approx(10.0)
        assert report.total_files == 1
        assert report.functions_analyzed == 3
        assert report.high_complexity == []
        assert report.large_functions == []
        assert report.passed is True


# ---------------------------------------------------------------------------
# Task 4.2: Detect high complexity
# ---------------------------------------------------------------------------


class TestDetectHighComplexity:
    """Test that high cyclomatic complexity functions are flagged."""

    def test_detect_high_complexity(self, tmp_path: str) -> None:
        """Function with many branches should be flagged as high complexity."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create a function with complexity > 10
        complex_code = textwrap.dedent(
            """\
            def classify(value: int) -> str:
                if value < 0:
                    return "negative"
                elif value == 0:
                    return "zero"
                elif value == 1:
                    return "one"
                elif value == 2:
                    return "two"
                elif value == 3:
                    return "three"
                elif value == 4:
                    return "four"
                elif value == 5:
                    return "five"
                elif value == 6:
                    return "six"
                elif value == 7:
                    return "seven"
                elif value == 8:
                    return "eight"
                elif value == 9:
                    return "nine"
                else:
                    return "large"
        """,
        )
        (src_dir / "complex.py").write_text(complex_code)

        profiler = RealPerformanceProfiler(str(tmp_path))
        report = profiler.analyze("src")

        assert len(report.high_complexity) >= 1
        flagged = report.high_complexity[0]
        assert flagged["function"] == "classify"
        assert flagged["complexity"] > 10


# ---------------------------------------------------------------------------
# Task 4.3: Detect large function
# ---------------------------------------------------------------------------


class TestDetectLargeFunction:
    """Test that oversized functions are flagged."""

    def test_detect_large_function(self, tmp_path: str) -> None:
        """Function exceeding 50 lines should be flagged."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Generate a 60-line function
        lines = ["def big_function() -> None:"]
        for i in range(60):
            lines.append(f"    x_{i} = {i}")
        large_code = "\n".join(lines) + "\n"
        (src_dir / "large.py").write_text(large_code)

        profiler = RealPerformanceProfiler(str(tmp_path))
        report = profiler.analyze("src")

        assert len(report.large_functions) >= 1
        flagged = report.large_functions[0]
        assert flagged["function"] == "big_function"
        assert flagged["lines"] > 50


# ---------------------------------------------------------------------------
# Task 4.4: Empty directory returns perfect score
# ---------------------------------------------------------------------------


class TestEmptyDirectory:
    """Test profiler on empty directory."""

    def test_empty_directory_scores_perfect(self, tmp_path: str) -> None:
        """Empty directory should return score 10.0, passed=True."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        profiler = RealPerformanceProfiler(str(tmp_path))
        report = profiler.analyze("src")

        assert report.score == pytest.approx(10.0)
        assert report.total_files == 0
        assert report.functions_analyzed == 0
        assert report.passed is True


# ---------------------------------------------------------------------------
# Task 4.5: Strategy no longer returns placeholder
# ---------------------------------------------------------------------------


class TestStrategyUsesRealProfiler:
    """Test that base strategy uses RealPerformanceProfiler instead of placeholder."""

    def test_strategy_no_longer_returns_placeholder(self, tmp_path: str) -> None:
        """Verify the performance_optimizer branch no longer returns placeholder: True."""
        # Read the source of the base strategy to confirm no placeholder
        from pathlib import Path

        strategy_path = Path(__file__).resolve().parent.parent.parent / (
            "src/attune/orchestration/_strategies/base.py"
        )
        source = strategy_path.read_text()

        # The old placeholder code had this exact string
        assert '"placeholder": True' not in source
        assert "Performance analysis not yet implemented" not in source

        # Verify RealPerformanceProfiler is imported and used
        assert "RealPerformanceProfiler" in source

    def test_real_tools_registry_includes_profiler(self) -> None:
        """Verify performance_profiler is in the REAL_TOOLS registry."""
        from attune.orchestration.real_tools import REAL_TOOLS

        assert "performance_profiler" in REAL_TOOLS
        assert REAL_TOOLS["performance_profiler"] is RealPerformanceProfiler
