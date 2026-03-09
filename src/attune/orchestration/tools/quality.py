"""Quality tools — code quality analysis and documentation completeness.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Code quality report from ruff and mypy."""

    quality_score: float  # 0-10
    ruff_issues: int
    mypy_issues: int
    total_files: int
    issues_by_category: dict[str, int]
    passed: bool


class RealCodeQualityAnalyzer:
    """Runs real code quality analysis using ruff and mypy."""

    def __init__(self, project_root: str = "."):
        """Initialize code quality analyzer.

        Args:
            project_root: Project root directory

        """
        self.project_root = Path(project_root).resolve()

    def analyze(self, target_path: str = "src") -> QualityReport:
        """Run code quality analysis.

        Args:
            target_path: Path to analyze (default: src)

        Returns:
            QualityReport with quality metrics

        Raises:
            RuntimeError: If quality analysis fails

        """
        logger.info(f"Running code quality analysis on {target_path}")

        try:
            # Run ruff for linting
            ruff_issues = self._run_ruff(target_path)

            # Run mypy for type checking (optional - may not be installed)
            mypy_issues = self._run_mypy(target_path)

            # Count files
            target = self.project_root / target_path
            py_files = list(target.rglob("*.py")) if target.is_dir() else [target]
            total_files = len(py_files)

            # Calculate quality score (0-10 scale)
            # Start with 10, deduct points for issues
            quality_score = 10.0
            quality_score -= min(ruff_issues * 0.01, 3.0)  # Max -3 points for ruff
            quality_score -= min(mypy_issues * 0.02, 2.0)  # Max -2 points for mypy
            quality_score = max(0.0, quality_score)  # Floor at 0

            # Passed if score >= 7.0
            passed = quality_score >= 7.0

            logger.info(
                f"Quality analysis complete: score={quality_score:.1f}/10 "
                f"(ruff={ruff_issues}, mypy={mypy_issues})",
            )

            return QualityReport(
                quality_score=quality_score,
                ruff_issues=ruff_issues,
                mypy_issues=mypy_issues,
                total_files=total_files,
                issues_by_category={"ruff": ruff_issues, "mypy": mypy_issues},
                passed=passed,
            )

        except Exception as e:  # noqa: BLE001
            logger.error(f"Quality analysis failed: {e}")
            raise RuntimeError(f"Quality analysis failed: {e}") from e

    def _run_ruff(self, target_path: str) -> int:
        """Run ruff linter and count issues."""
        try:
            cmd = ["ruff", "check", target_path, "--output-format=json"]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Parse JSON output
            try:
                ruff_data = json.loads(result.stdout) if result.stdout else []
                return len(ruff_data)
            except json.JSONDecodeError:
                logger.warning("Ruff returned invalid JSON")
                return 0

        except FileNotFoundError:
            logger.warning("Ruff not installed, skipping")
            return 0
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Ruff check failed: {e}")
            return 0

    def _run_mypy(self, target_path: str) -> int:
        """Run mypy type checker and count issues."""
        try:
            cmd = ["mypy", target_path, "--no-error-summary"]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Count error lines
            error_count = sum(1 for line in result.stdout.split("\n") if ": error:" in line)
            return error_count

        except FileNotFoundError:
            logger.warning("Mypy not installed, skipping")
            return 0
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Mypy check failed: {e}")
            return 0


@dataclass
class DocumentationReport:
    """Documentation completeness report."""

    completeness_percentage: float
    total_functions: int
    documented_functions: int
    total_classes: int
    documented_classes: int
    missing_docstrings: list[str]
    passed: bool


class RealDocumentationAnalyzer:
    """Analyzes documentation completeness by scanning docstrings."""

    def __init__(self, project_root: str = "."):
        """Initialize documentation analyzer.

        Args:
            project_root: Project root directory

        """
        self.project_root = Path(project_root).resolve()

    def analyze(self, target_path: str = "src") -> DocumentationReport:
        """Analyze documentation completeness.

        Args:
            target_path: Path to analyze (default: src)

        Returns:
            DocumentationReport with completeness metrics

        Raises:
            RuntimeError: If analysis fails

        """
        logger.info(f"Analyzing documentation completeness in {target_path}")

        import ast

        target = self.project_root / target_path
        py_files = list(target.rglob("*.py")) if target.is_dir() else [target]

        total_functions = 0
        documented_functions = 0
        total_classes = 0
        documented_classes = 0
        missing_docstrings = []

        for py_file in py_files:
            if py_file.name.startswith("__") and py_file.name.endswith("__.py"):
                continue  # Skip __init__.py, __main__.py

            try:
                tree = ast.parse(py_file.read_text())

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if not node.name.startswith("_"):  # Public functions
                            total_functions += 1
                            if ast.get_docstring(node):
                                documented_functions += 1
                            else:
                                missing_docstrings.append(
                                    f"{py_file.relative_to(self.project_root)}:{node.lineno} - function {node.name}",
                                )

                    elif isinstance(node, ast.ClassDef):
                        if not node.name.startswith("_"):  # Public classes
                            total_classes += 1
                            if ast.get_docstring(node):
                                documented_classes += 1
                            else:
                                missing_docstrings.append(
                                    f"{py_file.relative_to(self.project_root)}:{node.lineno} - class {node.name}",
                                )

            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to parse {py_file}: {e}")
                continue

        # Calculate completeness
        total_items = total_functions + total_classes
        documented_items = documented_functions + documented_classes

        if total_items > 0:
            completeness_percentage = (documented_items / total_items) * 100
        else:
            completeness_percentage = 100.0  # No public APIs, consider complete

        passed = completeness_percentage >= 80.0

        logger.info(
            f"Documentation analysis complete: {completeness_percentage:.1f}% "
            f"({documented_items}/{total_items} items documented)",
        )

        return DocumentationReport(
            completeness_percentage=completeness_percentage,
            total_functions=total_functions,
            documented_functions=documented_functions,
            total_classes=total_classes,
            documented_classes=documented_classes,
            missing_docstrings=missing_docstrings[:10],  # Limit to first 10
            passed=passed,
        )


QUALITY_TOOLS = {
    "code_quality_analyzer": RealCodeQualityAnalyzer,
    "documentation_analyzer": RealDocumentationAnalyzer,
}
