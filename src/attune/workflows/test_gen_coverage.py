"""Autonomous Test Generation Coverage Analysis (Phase 3).

Coverage-guided iterative test improvement targeting uncovered lines.
Extracted from autonomous_test_gen.py for maintainability.

Contains:
- TestGenCoverageMixin: Coverage analysis, uncovered line extraction, and
  coverage-targeted generation

Expected attributes on the host class:
    target_coverage: float
    _get_example_tests: method (from TestGenPromptMixin)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

from attune.config import _validate_file_path

logger = logging.getLogger(__name__)


class TestGenCoverageMixin:
    """Mixin providing Phase 3 coverage-guided generation for test generation."""

    # Class-level defaults for expected attributes
    target_coverage: float = 0.80

    def _run_coverage_analysis(self, test_file: Path, source_file: Path) -> object:
        """Run coverage analysis on tests.

        Args:
            test_file: Path to test file
            source_file: Path to source file being tested

        Returns:
            CoverageResult with coverage metrics and missing lines
        """
        from .autonomous_test_gen import CoverageResult

        try:
            # Run pytest with coverage (result intentionally unused - we read coverage from file)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(test_file),
                    f"--cov={source_file.parent}",
                    "--cov-report=term-missing",
                    "--cov-report=json",
                    "-v",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=Path.cwd(),
            )

            # Parse coverage from JSON report
            coverage_json_path = Path(".coverage.json")
            if not coverage_json_path.exists():
                logger.warning("Coverage JSON not generated")
                return CoverageResult(
                    coverage=0.0, missing_lines=[], total_statements=0, covered_statements=0
                )

            with open(coverage_json_path) as f:
                coverage_data = json.load(f)

            # Find coverage for our specific source file
            source_key = str(source_file)
            file_coverage = None
            for key in coverage_data.get("files", {}).keys():
                if source_file.name in key or source_key in key:
                    file_coverage = coverage_data["files"][key]
                    break

            if not file_coverage:
                logger.warning(f"No coverage data found for {source_file}")
                return CoverageResult(
                    coverage=0.0, missing_lines=[], total_statements=0, covered_statements=0
                )

            # Extract metrics
            total_statements = file_coverage["summary"]["num_statements"]
            covered_statements = file_coverage["summary"]["covered_lines"]
            coverage_pct = file_coverage["summary"]["percent_covered"] / 100.0
            missing_lines = file_coverage["missing_lines"]

            logger.info(
                f"Coverage: {coverage_pct:.1%} ({covered_statements}/{total_statements} statements)"
            )

            return CoverageResult(
                coverage=coverage_pct,
                missing_lines=missing_lines,
                total_statements=total_statements,
                covered_statements=covered_statements,
            )

        except subprocess.TimeoutExpired:
            logger.error("Coverage analysis timeout")
            return CoverageResult(
                coverage=0.0, missing_lines=[], total_statements=0, covered_statements=0
            )
        except Exception as e:
            logger.error(f"Coverage analysis error: {e}", exc_info=True)
            return CoverageResult(
                coverage=0.0, missing_lines=[], total_statements=0, covered_statements=0
            )

    def _extract_uncovered_lines(self, source_file: Path, missing_lines: list[int]) -> str:
        """Extract source code for uncovered lines.

        Args:
            source_file: Path to source file
            missing_lines: List of uncovered line numbers

        Returns:
            Formatted string with uncovered code sections
        """
        if not missing_lines:
            return "No uncovered lines"

        try:
            source_lines = source_file.read_text().split("\n")

            # Group consecutive lines into ranges
            ranges = []
            start = missing_lines[0]
            end = start

            for line_num in missing_lines[1:]:
                if line_num == end + 1:
                    end = line_num
                else:
                    ranges.append((start, end))
                    start = line_num
                    end = start
            ranges.append((start, end))

            # Extract code for each range with context
            uncovered_sections = []
            for start, end in ranges[:10]:  # Limit to 10 ranges
                context_start = max(0, start - 3)
                context_end = min(len(source_lines), end + 2)

                section = []
                section.append(f"Lines {start}-{end}:")
                for i in range(context_start, context_end):
                    line_marker = ">>>" if start <= i + 1 <= end else "   "
                    section.append(f"{line_marker} {i + 1:4d}: {source_lines[i]}")

                uncovered_sections.append("\n".join(section))

            return "\n\n".join(uncovered_sections)

        except Exception as e:
            logger.error(f"Error extracting uncovered lines: {e}")
            return f"Error extracting lines: {e}"

    def _generate_with_coverage_target(
        self,
        module_name: str,
        module_path: str,
        source_file: Path,
        source_code: str,
        test_file: Path,
        initial_test_content: str,
    ) -> str | None:
        """Generate tests iteratively until coverage target met (Phase 3).

        Process:
        1. Start with initial tests
        2. Run coverage analysis
        3. If target not met, identify uncovered lines
        4. Ask Claude to add tests for uncovered code
        5. Repeat until target coverage reached or max iterations

        Args:
            module_name: Name of module being tested
            module_path: Python import path
            source_file: Path to source file
            source_code: Source code content
            test_file: Path to test file
            initial_test_content: Initial test content from Phase 1/2

        Returns:
            Final test content with improved coverage or None if failed
        """
        import os

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not set")
            return None

        logger.info(
            f"📊 Phase 3: Coverage-guided generation enabled (target: {self.target_coverage:.0%})"
        )

        test_content = initial_test_content
        max_coverage_iterations = 5
        coverage_result = None

        for iteration in range(max_coverage_iterations):
            logger.info(
                f"📈 Coverage iteration {iteration + 1}/{max_coverage_iterations} for {module_name}"
            )

            # Write current tests
            validated_test = _validate_file_path(str(test_file))
            validated_test.write_text(test_content)

            # Run coverage analysis
            coverage_result = self._run_coverage_analysis(test_file, source_file)

            logger.info(
                f"Current coverage: {coverage_result.coverage:.1%}, target: {self.target_coverage:.0%}"
            )

            # Check if target reached
            if coverage_result.coverage >= self.target_coverage:
                logger.info(f"✅ Coverage target reached: {coverage_result.coverage:.1%}")
                return test_content

            # Not enough progress
            if iteration > 0 and coverage_result.coverage <= 0.05:
                logger.warning("⚠️  Coverage not improving, stopping")
                break

            # Identify uncovered code
            uncovered_code = self._extract_uncovered_lines(
                source_file, coverage_result.missing_lines
            )

            # Ask Claude to add tests for uncovered lines
            refinement_prompt = f"""Current coverage: {coverage_result.coverage:.1%}
Target coverage: {self.target_coverage:.0%}
Missing: {len(coverage_result.missing_lines)} lines

UNCOVERED CODE:
{uncovered_code[:3000]}

Please ADD tests to cover these specific uncovered lines. Requirements:
1. Focus ONLY on the uncovered lines shown above
2. Add new test methods to the existing test classes
3. Return the COMPLETE test file with additions (not just new tests)
4. Use appropriate mocking for external dependencies
5. Keep existing tests intact - just add new ones

Return ONLY the complete Python test file with additions, no explanations."""

            # Build conversation with caching
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are an expert Python test engineer. Examples:",
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": self._get_example_tests(),
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": f"Source code:\n```python\n{source_code}\n```",
                            "cache_control": {"type": "ephemeral"},
                        },
                        {"type": "text", "text": f"Current tests:\n```python\n{test_content}\n```"},
                        {"type": "text", "text": refinement_prompt},
                    ],
                }
            ]

            # Call LLM for coverage improvement
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=40000,  # Very generous total budget for coverage improvement
                    thinking={
                        "type": "enabled",
                        "budget_tokens": 20000,
                    },  # Thorough thinking for coverage gaps
                    messages=messages,
                    timeout=900.0,  # 15 minutes timeout for coverage-guided iterations
                )

                refined_content = None
                for block in response.content:
                    if block.type == "text":
                        refined_content = block.text.strip()
                        break

                if not refined_content:
                    logger.warning(f"No content in coverage refinement iteration {iteration + 1}")
                    break

                # Clean up
                if refined_content.startswith("```python"):
                    refined_content = refined_content[len("```python") :].strip()
                if refined_content.endswith("```"):
                    refined_content = refined_content[:-3].strip()

                test_content = refined_content
                logger.info(f"🔄 Coverage iteration {iteration + 1} complete, retrying analysis...")

            except Exception as e:
                logger.error(f"Coverage refinement error on iteration {iteration + 1}: {e}")
                break

        # Return best attempt
        final_coverage = coverage_result.coverage if coverage_result else 0.0
        logger.info(f"Coverage-guided generation complete: final coverage ~{final_coverage:.1%}")
        return test_content
