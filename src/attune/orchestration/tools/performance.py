"""Performance tools — static complexity and function-length analysis.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Performance profiling report from AST-based analysis."""

    score: float  # 0-10
    total_files: int
    functions_analyzed: int
    high_complexity: list[dict[str, Any]]  # Functions with cyclomatic complexity > 10
    large_functions: list[dict[str, Any]]  # Functions with > 50 lines
    passed: bool


class RealPerformanceProfiler:
    """Runs real performance profiling via AST-based static analysis.

    Analyzes Python files for:
    - Cyclomatic complexity (counting if/for/while/try/except branches)
    - Function length (line count)

    Scoring: Starts at 10.0, deducts for high-complexity and oversized functions.
    Passing threshold: score >= 6.0.
    """

    def __init__(self, project_root: str = "."):
        """Initialize performance profiler.

        Args:
            project_root: Project root directory

        """
        self.project_root = Path(project_root).resolve()

    def analyze(self, target_path: str = "src") -> PerformanceReport:
        """Run performance analysis on Python files.

        Args:
            target_path: Path to analyze (default: src)

        Returns:
            PerformanceReport with complexity metrics

        Raises:
            RuntimeError: If analysis fails

        """
        import ast

        logger.info(f"Running performance analysis on {target_path}")

        target = self.project_root / target_path
        py_files = list(target.rglob("*.py")) if target.is_dir() else [target]

        total_files = 0
        functions_analyzed = 0
        high_complexity: list[dict[str, Any]] = []
        large_functions: list[dict[str, Any]] = []

        for py_file in py_files:
            if py_file.name.startswith("__") and py_file.name.endswith("__.py"):
                continue

            try:
                source = py_file.read_text()
                tree = ast.parse(source)
                total_files += 1
            except (
                SyntaxError,
                OSError,
                ValueError,
            ) as e:  # ast.parse: null bytes -> ValueError, not SyntaxError
                logger.warning(f"Failed to parse {py_file}: {e}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    functions_analyzed += 1
                    func_name = node.name
                    try:
                        rel_path = str(py_file.relative_to(self.project_root))
                    except ValueError:
                        rel_path = str(py_file)

                    # Cyclomatic complexity: count branching nodes
                    complexity = self._compute_complexity(node)
                    if complexity > 10:
                        high_complexity.append(
                            {
                                "file": rel_path,
                                "line": node.lineno,
                                "function": func_name,
                                "complexity": complexity,
                            },
                        )

                    # Function length
                    func_lines = self._compute_function_length(node)
                    if func_lines > 50:
                        large_functions.append(
                            {
                                "file": rel_path,
                                "line": node.lineno,
                                "function": func_name,
                                "lines": func_lines,
                            },
                        )

        # Scoring: start at 10.0
        score = 10.0
        score -= min(len(high_complexity) * 0.5, 3.0)  # Max -3 for complexity
        score -= min(len(large_functions) * 0.3, 2.0)  # Max -2 for large functions
        score = max(score, 0.0)
        passed = score >= 6.0

        logger.info(
            f"Performance analysis complete: score={score:.1f}, "
            f"files={total_files}, functions={functions_analyzed}, "
            f"high_complexity={len(high_complexity)}, large_functions={len(large_functions)}",
        )

        return PerformanceReport(
            score=score,
            total_files=total_files,
            functions_analyzed=functions_analyzed,
            high_complexity=high_complexity[:20],  # Limit to first 20
            large_functions=large_functions[:20],
            passed=passed,
        )

    @staticmethod
    def _compute_complexity(node: Any) -> int:
        """Count branching nodes for cyclomatic complexity.

        Args:
            node: AST function node

        Returns:
            Approximate cyclomatic complexity (1 + number of branches)

        """
        import ast

        complexity = 1  # Base complexity
        for child in ast.walk(node):
            if (
                isinstance(child, ast.If | ast.IfExp)
                or isinstance(child, ast.For | ast.AsyncFor)
                or isinstance(child, ast.While)
                or isinstance(child, ast.ExceptHandler)
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each `and`/`or` adds a branch
                complexity += len(child.values) - 1
        return complexity

    @staticmethod
    def _compute_function_length(node: Any) -> int:
        """Compute function body line count.

        Args:
            node: AST function node

        Returns:
            Number of lines in the function body

        """
        if not node.body:
            return 0
        first_line = node.body[0].lineno
        last_line = node.body[-1].end_lineno or node.body[-1].lineno
        return last_line - first_line + 1


PERFORMANCE_TOOLS = {
    "performance_profiler": RealPerformanceProfiler,
}
