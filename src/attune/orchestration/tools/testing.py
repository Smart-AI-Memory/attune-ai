"""Testing tools — coverage analysis, test generation, and validation.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from attune.utils.coverage import detect_coverage_targets

from ._shared import _validate_file_path

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

        Coverage targets are detected from the project's ``pyproject.toml``
        via :func:`attune.utils.coverage.detect_coverage_targets`, so this
        works against any project layout (src/, flat, or hatch wheel
        packages), not just attune-ai itself.

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

                # Detect coverage targets from the project's pyproject.toml
                # so this works on any project, not just attune-ai. Falls back
                # to ``["src"]`` for the conventional layout.
                cov_packages = detect_coverage_targets(self.project_root)

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
                "Coverage report not found. Run 'pytest --cov=<your-package> "
                "--cov-report=json' first.",
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
                        },
                    )
                    missing_lines[filepath] = file_data["missing_lines"]

            logger.info(
                f"Coverage analysis complete: {total_coverage:.1f}% "
                f"({len(uncovered_files)} files below 80%)",
            )

            return CoverageReport(
                total_coverage=total_coverage,
                files_analyzed=len(files),
                uncovered_files=uncovered_files,
                missing_lines=missing_lines,
            )

        except Exception as e:  # noqa: BLE001
            logger.error(f"Coverage analysis failed: {e}")
            raise RuntimeError(f"Coverage analysis failed: {e}") from e


class RealTestGenerator:
    """Generates actual test code using LLM."""

    def __init__(
        self,
        project_root: str = ".",
        output_dir: str = "tests/generated",
        api_key: str | None = None,
        use_llm: bool = True,
    ):
        """Initialize test generator.

        Args:
            project_root: Project root directory
            output_dir: Directory for generated tests (relative to project_root)
            api_key: Anthropic API key (or uses env var)
            use_llm: Whether to use LLM for intelligent test generation

        """
        self.project_root = Path(project_root).resolve()
        self.output_dir = self.project_root / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key
        self.use_llm = use_llm

        # Initialize LLM client if needed
        self._llm = None
        if use_llm:
            self._initialize_llm()

    def _initialize_llm(self):
        """Initialize Anthropic LLM client."""
        try:
            import os

            from anthropic import Anthropic

            # Try to load .env file
            try:
                from dotenv import load_dotenv

                load_dotenv()
            except ImportError:
                pass  # python-dotenv not required

            api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning(
                    "No Anthropic API key found. Set ANTHROPIC_API_KEY environment variable "
                    "or create .env file with ANTHROPIC_API_KEY=your_key_here. "
                    "Falling back to basic templates.",
                )
                self.use_llm = False
                return

            self._llm = Anthropic(api_key=api_key)
            logger.info("✓ LLM client initialized successfully with Claude")

        except ImportError as e:
            logger.warning(f"Required package not installed: {e}. Falling back to templates")
            self.use_llm = False
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to initialize LLM: {e}. Falling back to templates")
            self.use_llm = False

    def generate_tests_for_file(self, source_file: str, missing_lines: list[int]) -> Path:
        """Generate tests for uncovered code in a file.

        Args:
            source_file: Path to source file
            missing_lines: Line numbers without coverage

        Returns:
            Path to generated test file

        Raises:
            RuntimeError: If test generation fails

        """
        logger.info(f"Generating tests for {source_file} (lines: {missing_lines[:5]}...)")

        # Read source file
        source_path = Path(source_file)
        if not source_path.exists():
            source_path = self.project_root / source_file

        # Resolve to absolute path for relative_to() to work correctly
        source_path = source_path.resolve()

        try:
            source_code = source_path.read_text()
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Cannot read source file: {e}") from e

        # Create unique test name from full path to avoid collisions
        relative_path = source_path.relative_to(self.project_root)
        parts_str = "_".join(relative_path.parts)
        test_name = f"test_{parts_str.replace('.py', '')}_generated.py"
        test_path = self.output_dir / test_name

        # Generate tests using LLM or template
        if self.use_llm and self._llm:
            test_code = self._generate_llm_tests(source_file, source_code, missing_lines)
        else:
            test_code = self._generate_basic_test_template(source_file, source_code, missing_lines)

        # Write test file
        validated_path = _validate_file_path(str(test_path))
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        validated_path.write_text(test_code)

        logger.info(f"Generated test file: {test_path}")
        return test_path

    def _generate_llm_tests(
        self,
        source_file: str,
        source_code: str,
        missing_lines: list[int],
    ) -> str:
        """Generate tests using LLM (Claude).

        Args:
            source_file: Source file path
            source_code: Source file content
            missing_lines: Uncovered line numbers

        Returns:
            Generated test code

        Raises:
            RuntimeError: If LLM generation fails

        """
        logger.info(f"Using LLM to generate intelligent tests for {source_file}")

        # Extract API signatures using AST
        api_docs = self._extract_api_docs(source_code)

        # Extract module path
        module_path = source_file.replace("/", ".").replace(".py", "")

        # Create prompt for Claude with full context
        prompt = f"""Generate comprehensive pytest tests for the following Python code.

**Source File:** `{source_file}`
**Module Path:** `{module_path}`
**Uncovered Lines:** {missing_lines[:20]}

{api_docs}

**Full Source Code:**
```python
{source_code}
```

**CRITICAL Requirements - API Accuracy:**
1. **READ THE SOURCE CODE CAREFULLY** - Extract exact API signatures from:
   - Dataclass definitions (@dataclass) - use EXACT parameter names
   - Function signatures - match parameter names and types
   - Class __init__ methods - use correct constructor arguments

2. **DO NOT GUESS** parameter names - if you see:
   ```python
   @dataclass
   class Foo:
       bar: str  # Parameter name is 'bar', NOT 'bar_name'
   ```
   Then use: `Foo(bar="value")` NOT `Foo(bar_name="value")`

3. **Computed Properties** - Do NOT pass @property values to constructors:
   - If source has `@property def total(self): return self.a + self.b`
   - Then DO NOT use `Foo(total=10)` - it's computed from `a` and `b`

**Test Requirements:**
1. Write complete, runnable pytest tests
2. Focus on covering uncovered lines: {missing_lines[:10]}
3. Include:
   - Test class with descriptive name
   - Test methods for key functions/classes
   - Proper imports from the actual module path
   - Mock external dependencies (database, API calls, etc.)
   - Edge cases (empty inputs, None, zero, negative numbers)
   - Error handling tests (invalid input, exceptions)
4. Follow pytest best practices
5. Use clear, descriptive test method names
6. Add docstrings explaining what each test validates

**Output Format:**
Return ONLY the Python test code, starting with imports. No markdown, no explanations.
"""

        try:
            # Try Sonnet models only (Capable tier) - do NOT downgrade.
            # Stable alias only: it never retires and always routes to the
            # latest Sonnet checkpoint. The old claude-3-5-sonnet-2024xxxx
            # dated snapshots were retired by Anthropic 2025-10-28.
            models_to_try = [
                "claude-sonnet-5",  # Sonnet 5 (stable alias)
            ]

            response = None
            last_error = None

            for model_name in models_to_try:
                try:
                    response = self._llm.messages.create(
                        model=model_name,
                        max_tokens=12000,  # Increased to prevent truncation on large files
                        temperature=0.3,  # Lower temperature for consistent code
                        messages=[{"role": "user", "content": prompt}],
                    )
                    logger.info(f"✓ Using Sonnet model: {model_name}")
                    break
                except Exception as e:  # noqa: BLE001
                    last_error = e
                    logger.debug(f"Model {model_name} not available: {e}")
                    continue

            if response is None:
                error_msg = f"All Sonnet models unavailable. Last error: {last_error}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            test_code = response.content[0].text

            # Clean up markdown if present
            if "```python" in test_code:
                test_code = test_code.split("```python")[1].split("```")[0].strip()
            elif "```" in test_code:
                test_code = test_code.split("```")[1].split("```")[0].strip()

            logger.info(f"✓ LLM generated {len(test_code)} chars of test code")
            return test_code

        except Exception as e:  # noqa: BLE001
            logger.error(f"LLM test generation failed: {e}, falling back to template")
            return self._generate_basic_test_template(source_file, source_code, missing_lines)

    def _extract_api_docs(self, source_code: str) -> str:
        """Extract API signatures from source code using AST.

        Args:
            source_code: Python source code

        Returns:
            Formatted API documentation for LLM prompt

        """
        try:
            import sys
            from pathlib import Path

            # Add scripts to path
            scripts_dir = Path(__file__).parent.parent.parent.parent / "scripts"
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))

            from ast_api_extractor import extract_api_signatures, format_api_docs

            classes, functions = extract_api_signatures(source_code)
            return format_api_docs(classes, functions)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"AST extraction failed: {e}, proceeding without API docs")
            return "# API extraction failed - use source code carefully"

    def _generate_basic_test_template(
        self,
        source_file: str,
        source_code: str,
        missing_lines: list[int],
    ) -> str:
        """Generate basic test template.

        IMPORTANT: Placeholder tests use pytest.skip() to prevent false greens.
        Tests must be implemented before they will pass.

        Args:
            source_file: Source file path
            source_code: Source file content
            missing_lines: Uncovered line numbers

        Returns:
            Test code as string

        """
        # Extract module name
        module_path = source_file.replace("/", ".").replace(".py", "")
        first_line = missing_lines[0] if missing_lines else 0

        template = f'''"""Auto-generated tests for {source_file}.

Coverage gaps on lines: {missing_lines[:10]}

WARNING: This file contains placeholder tests that are skipped by default.
You must implement the actual test logic before they will run.

To allow placeholder tests temporarily, set ATTUNE_ALLOW_PLACEHOLDER_TESTS=1
"""

import os
import pytest


# Check if placeholder tests are allowed (for development only)
ALLOW_PLACEHOLDERS = os.getenv("ATTUNE_ALLOW_PLACEHOLDER_TESTS", "").lower() in ("1", "true")


class TestGeneratedCoverage:
    """Tests to improve coverage for {source_file}."""

    def test_module_imports(self):
        """Test that module can be imported."""
        try:
            import {module_path}
            assert {module_path} is not None
        except ImportError as e:
            pytest.fail(f"Module import failed: {{e}}")

    @pytest.mark.skipif(not ALLOW_PLACEHOLDERS, reason="Placeholder test - implement actual logic")
    def test_placeholder_for_lines_{first_line}(self):
        """Placeholder test for uncovered code.

        TODO: Implement actual test logic for lines {missing_lines[:5]}

        This test is SKIPPED by default to prevent false positive coverage.
        Implement the test logic, then remove the @pytest.mark.skipif decorator.
        """
        pytest.fail(
            "PLACEHOLDER: Implement test logic for lines {missing_lines[:5]}. "
            "Remove @pytest.mark.skipif when done."
        )
'''
        return template


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
                f"tests_passed={tests_passed}",
            )

            return {
                "all_passed": tests_passed,
                "passed_count": passed,
                "failed_count": failed,
                "output": result.stdout[:1000],  # Limit output
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("Test validation timed out after 5 minutes") from None
        except Exception as e:  # noqa: BLE001
            logger.error(f"Test validation failed: {e}")
            raise RuntimeError(f"Test validation failed: {e}") from e


TESTING_TOOLS = {
    "coverage_analyzer": RealCoverageAnalyzer,
    "test_generator": RealTestGenerator,
    "test_validator": RealTestValidator,
}
