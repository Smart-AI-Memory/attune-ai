"""Testing tools — coverage analysis, test generation, and validation.

RealTestGenerator extracted to test_generation.py; re-exported here.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .test_generation import RealTestGenerator

logger = logging.getLogger(__name__)


@dataclass
class CoverageReport:
    """Coverage analysis report from pytest-cov."""

    total_coverage: float
    files_analyzed: int
    uncovered_files: list[dict[str, Any]]
    missing_lines: dict[str, list[int]]


class RealCoverageAnalyzer:
    """Runs real pytest coverage analysis."""

    def __init__(self, project_root: str = "."):
        """Initialize coverage analyzer.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root).resolve()

    def analyze(self, use_existing: bool = True) -> CoverageReport:
        """Run coverage analysis on all project packages.

        Analyzes coverage for: attune, attune_llm_toolkit,
        attune_software_plugin

        Args:
            use_existing: Use existing coverage.json if available (default: True)

        Returns:
            CoverageReport with results

        Raises:
            RuntimeError: If coverage analysis fails
        """
        logger.info("Running coverage analysis on all packages")

        coverage_file = self.project_root / "coverage.json"

        # Check if we can use existing coverage data
        if use_existing and coverage_file.exists():
            import time

            file_age = time.time() - coverage_file.stat().st_mtime
            # Use existing file if less than 1 hour old
            if file_age < 3600:
                logger.info(f"Using existing coverage data (age: {file_age / 60:.1f} minutes)")
            else:
                logger.info("Existing coverage data is stale, regenerating")
                use_existing = False

        if not use_existing or not coverage_file.exists():
            try:
                # Run pytest with coverage on test suite
                logger.info("Running test suite to generate coverage (may take 2-5 minutes)")

                # Use actual package names (match pyproject.toml configuration)
                cov_packages = [
                    "attune",
                    "attune_llm_toolkit",
                    "attune_software_plugin",
                ]

                cmd = [
                    "pytest",
                    "tests/",  # Run all tests to measure coverage
                    "--cov-report=json",
                    "--cov-report=term-missing",
                    "-q",
                    "--tb=no",
                    "--maxfail=50",  # Continue despite failures
                ]

                # Add --cov for each package
                for pkg in cov_packages:
                    cmd.append(f"--cov={pkg}")

                _result = subprocess.run(  # Result not needed, only coverage.json
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=600,  # Increased to 10 minutes
                )

            except subprocess.TimeoutExpired:
                logger.warning("Coverage generation timed out, checking for partial results")
                # Fall through to use whatever coverage.json exists

        # Read coverage.json
        if not coverage_file.exists():
            raise RuntimeError(
                "Coverage report not found. Run 'pytest --cov=src --cov-report=json' first."
            )

        try:
            with coverage_file.open() as f:
                coverage_data = json.load(f)

            # Parse results
            total_coverage = coverage_data["totals"]["percent_covered"]
            files = coverage_data.get("files", {})

            # Identify low coverage files
            uncovered_files = []
            missing_lines = {}

            for filepath, file_data in files.items():
                file_coverage = file_data["summary"]["percent_covered"]
                if file_coverage < 80:  # Below target
                    uncovered_files.append(
                        {
                            "path": filepath,
                            "coverage": file_coverage,
                            "missing_lines": file_data["missing_lines"],
                        }
                    )
                    missing_lines[filepath] = file_data["missing_lines"]

            logger.info(
                f"Coverage analysis complete: {total_coverage:.1f}% "
                f"({len(uncovered_files)} files below 80%)"
            )

            return CoverageReport(
                total_coverage=total_coverage,
                files_analyzed=len(files),
                uncovered_files=uncovered_files,
                missing_lines=missing_lines,
            )

        except Exception as e:
            logger.error(f"Coverage analysis failed: {e}")
            raise RuntimeError(f"Coverage analysis failed: {e}") from e


class RealTestValidator:
    """Validates generated tests by running them."""

    def __init__(self, project_root: str = "."):
        """Initialize test validator.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root).resolve()

    def validate_tests(self, test_files: list[Path]) -> dict[str, Any]:
        """Run tests and measure coverage improvement.

        Args:
            test_files: List of test file paths

        Returns:
            Validation results dict

        Raises:
            RuntimeError: If validation fails
        """
        logger.info(f"Validating {len(test_files)} generated test files")

        try:
            # Run tests
            test_paths = [str(t) for t in test_files]
            cmd = ["pytest"] + test_paths + ["-v", "--tb=short"]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            tests_passed = result.returncode == 0
            output_lines = result.stdout.split("\n")

            # Count passed/failed
            passed = sum(1 for line in output_lines if " PASSED" in line)
            failed = sum(1 for line in output_lines if " FAILED" in line)

            logger.info(
                f"Validation complete: {passed} passed, {failed} failed, "
                f"tests_passed={tests_passed}"
            )

            return {
                "all_passed": tests_passed,
                "passed_count": passed,
                "failed_count": failed,
                "output": result.stdout[:1000],  # Limit output
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("Test validation timed out after 5 minutes")
        except Exception as e:
            logger.error(f"Test validation failed: {e}")
            raise RuntimeError(f"Test validation failed: {e}") from e


TESTING_TOOLS = {
    "coverage_analyzer": RealCoverageAnalyzer,
    "test_generator": RealTestGenerator,
    "test_validator": RealTestValidator,
}
