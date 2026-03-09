"""Progressive test generation workflow with tier escalation.

This module implements test generation with automatic escalation from cheap
to capable to premium tiers based on test quality metrics.
"""

import ast
import logging
import subprocess
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.workflows.progressive.core import (
    EscalationConfig,
    FailureAnalysis,
    ProgressiveWorkflowResult,
    Tier,
    TierResult,
)
from attune.workflows.progressive.workflow import ProgressiveWorkflow

logger = logging.getLogger(__name__)


class ProgressiveTestGenWorkflow(ProgressiveWorkflow):
    """Test generation workflow with progressive tier escalation.

    Generates tests for Python functions using a cost-efficient progressive
    approach:
    1. Start with cheap tier (gpt-4o-mini) for volume
    2. Escalate failed tests to capable tier (claude-3-5-sonnet)
    3. Escalate persistent failures to premium tier (claude-opus-4)

    Quality metrics tracked:
    - Syntax errors (AST parsing)
    - Test execution (pass/fail)
    - Code coverage
    - Assertion depth

    Example:
        >>> config = EscalationConfig(enabled=True, max_cost=10.00)
        >>> workflow = ProgressiveTestGenWorkflow(config)
        >>> result = workflow.execute(target_file="app.py")
        >>> print(result.generate_report())

    """

    def __init__(self, config: EscalationConfig | None = None):
        """Initialize progressive test generation workflow.

        .. deprecated:: 5.3.0
            Use :class:`ParallelTestGenerationWorkflow` via
            ``attune workflow run test-gen-parallel``.
            Will be removed in v6.0.0.

        Args:
            config: Escalation configuration (uses defaults if None)

        """
        warnings.warn(
            "ProgressiveTestGenWorkflow is deprecated since v5.3.0. "
            "Use ParallelTestGenerationWorkflow via 'attune workflow run test-gen-parallel' instead. "
            "Will be removed in v6.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(config)
        self.target_file: Path | None = None

    def execute(self, target_file: str, **kwargs) -> ProgressiveWorkflowResult:
        """Generate tests for target file with progressive escalation.

        Args:
            target_file: Path to Python file to generate tests for
            **kwargs: Additional parameters

        Returns:
            Complete workflow results with progression history

        Raises:
            FileNotFoundError: If target_file doesn't exist
            BudgetExceededError: If cost exceeds budget
            UserCancelledError: If user declines approval

        Example:
            >>> result = workflow.execute(target_file="src/app.py")
            >>> print(f"Generated {len(result.final_result.generated_items)} tests")

        """
        self.target_file = Path(target_file)

        if not self.target_file.exists():
            raise FileNotFoundError(f"Target file not found: {target_file}")

        logger.info(f"Generating tests for {target_file}")

        # Parse target file to extract functions
        functions = self._parse_functions(self.target_file)

        if not functions:
            logger.warning(f"No functions found in {target_file}")
            return self._create_empty_result("test-gen")

        logger.info(f"Found {len(functions)} functions to test")

        # Execute with progressive escalation
        return self._execute_progressive(items=functions, workflow_name="test-gen", **kwargs)

    def _parse_functions(self, file_path: Path) -> list[dict[str, Any]]:
        """Parse Python file to extract function definitions.

        Args:
            file_path: Path to Python file

        Returns:
            List of function metadata dicts with keys:
            - name: Function name
            - lineno: Line number
            - args: List of argument names
            - docstring: Function docstring (if present)
            - code: Full function source code

        Example:
            >>> functions = workflow._parse_functions(Path("app.py"))
            >>> print(functions[0]["name"])
            'calculate_total'

        """
        try:
            source = file_path.read_text()
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return []

        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Extract function info
                func_info = {
                    "name": node.name,
                    "lineno": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "docstring": ast.get_docstring(node) or "",
                    "code": ast.unparse(node),  # Python 3.9+
                    "file": str(file_path),
                }
                functions.append(func_info)

        return functions

    def _execute_tier_impl(
        self,
        tier: Tier,
        items: list[Any],
        context: dict[str, Any] | None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Execute test generation at specific tier.

        Args:
            tier: Which tier to execute at
            items: Functions to generate tests for
            context: Context from previous tier (if escalating)
            **kwargs: Additional parameters

        Returns:
            List of generated test items with quality scores

        Note:
            This is a placeholder implementation. In production, this would
            call the actual LLM API to generate tests.

        """
        logger.info(f"Generating {len(items)} tests at {tier.value} tier")

        # Build prompt for this tier (prepared for future LLM integration)
        base_task = self._build_test_gen_task(items)
        _prompt = self.meta_orchestrator.build_tier_prompt(tier, base_task, context)

        # TODO(llm-integration): Call LLM API with _prompt
        # Deferred: Requires LLM API integration (tracked in P2B debt register)
        # For now, returns simulated test generation results
        generated_tests = self._simulate_test_generation(tier, items)

        return generated_tests

    def _build_test_gen_task(self, functions: list[dict[str, Any]]) -> str:
        """Build task description for test generation.

        Args:
            functions: List of function metadata

        Returns:
            Task description string

        Example:
            >>> task = workflow._build_test_gen_task([{"name": "foo", ...}])
            >>> print(task)
            'Generate pytest tests for 1 functions from app.py'

        """
        file_name = self.target_file.name if self.target_file else "module"
        func_names = [f["name"] for f in functions]

        task = f"Generate pytest tests for {len(functions)} function(s) from {file_name}"

        if len(func_names) <= 3:
            task += f": {', '.join(func_names)}"

        return task

    def _simulate_test_generation(
        self,
        tier: Tier,
        functions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Simulate test generation (placeholder for LLM integration).

        In production, this would call the LLM API. For now, it generates
        mock test data with varying quality based on tier.

        Args:
            tier: Which tier is generating
            functions: Functions to generate tests for

        Returns:
            List of generated test items with quality metrics

        Note:
            This is temporary scaffolding. Real implementation will:
            1. Call LLM API with tier-appropriate model
            2. Parse generated test code
            3. Validate syntax
            4. Execute tests
            5. Calculate coverage

        """
        generated_tests = []

        # Quality thresholds per tier (prepared for future LLM integration)
        _base_quality = {
            Tier.CHEAP: 70,
            Tier.CAPABLE: 85,
            Tier.PREMIUM: 95,
        }[tier]

        for func in functions:
            # Generate mock test code
            test_code = self._generate_mock_test(func)

            # Analyze test quality
            analysis = self._analyze_generated_test(test_code, func)

            # Calculate quality score
            quality_score = analysis.calculate_quality_score()

            generated_tests.append(
                {
                    "function_name": func["name"],
                    "test_code": test_code,
                    "quality_score": quality_score,
                    "passed": analysis.test_pass_rate > 0.5,
                    "coverage": analysis.coverage_percent,
                    "assertions": analysis.assertion_depth,
                    "confidence": analysis.confidence_score,
                    "syntax_errors": [str(e) for e in analysis.syntax_errors],
                    "error": "" if not analysis.syntax_errors else str(analysis.syntax_errors[0]),
                },
            )

        return generated_tests

    def _generate_mock_test(self, func: dict[str, Any]) -> str:
        """Generate mock test code (placeholder).

        Args:
            func: Function metadata

        Returns:
            Generated test code as string

        """
        func_name = func["name"]
        args = func["args"]

        # Generate simple test template
        test_code = f'''def test_{func_name}():
    """Test {func_name} function."""
    # Arrange
    {self._generate_test_setup(args)}

    # Act
    result = {func_name}({", ".join(args)})

    # Assert
    assert result is not None
'''

        return test_code

    def _generate_test_setup(self, args: list[str]) -> str:
        """Generate test setup code for arguments.

        Args:
            args: List of argument names

        Returns:
            Setup code as string

        """
        if not args:
            return "pass"

        setup_lines = []
        for arg in args:
            # Simple type inference based on name
            if "count" in arg or "num" in arg or "index" in arg:
                setup_lines.append(f"{arg} = 1")
            elif "name" in arg or "text" in arg or "message" in arg:
                setup_lines.append(f'{arg} = "test"')
            elif "items" in arg or "list" in arg:
                setup_lines.append(f"{arg} = []")
            else:
                setup_lines.append(f'{arg} = "value"')

        return "\n    ".join(setup_lines)

    def _analyze_generated_test(self, test_code: str, func: dict[str, Any]) -> FailureAnalysis:
        """Analyze quality of generated test.

        Args:
            test_code: Generated test code
            func: Original function metadata

        Returns:
            Failure analysis with quality metrics

        """
        analysis = FailureAnalysis()

        # 1. Check syntax
        try:
            ast.parse(test_code)
        except SyntaxError as e:
            analysis.syntax_errors.append(e)
            return analysis  # Can't proceed with invalid syntax

        # 2. Count assertions
        try:
            tree = ast.parse(test_code)
            assertion_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Assert))
            analysis.assertion_depth = assertion_count
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to count assertions: {e}")
            analysis.assertion_depth = 0

        # 3. Simulate test execution (placeholder)
        # In production, would actually run the test
        analysis.test_pass_rate = 0.8  # Mock: 80% pass rate

        # 4. Simulate coverage (placeholder)
        # In production, would use coverage.py
        analysis.coverage_percent = 75.0  # Mock: 75% coverage

        # 5. Estimate confidence (placeholder)
        # In production, would parse from LLM response
        analysis.confidence_score = 0.85  # Mock: 85% confidence

        return analysis

    def _create_empty_result(self, workflow_name: str) -> ProgressiveWorkflowResult:
        """Create empty result when no functions found.

        Args:
            workflow_name: Name of workflow

        Returns:
            Empty workflow result

        """
        empty_result = TierResult(
            tier=Tier.CHEAP,
            model=self._get_model_for_tier(Tier.CHEAP),
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[],
            failure_analysis=FailureAnalysis(),
            cost=0.0,
            duration=0.0,
        )

        task_id = f"{workflow_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        return ProgressiveWorkflowResult(
            workflow_name=workflow_name,
            task_id=task_id,
            tier_results=[empty_result],
            final_result=empty_result,
            total_cost=0.0,
            total_duration=0.0,
            success=False,
        )


def execute_test_file(test_file: Path) -> dict[str, Any]:
    """Execute a test file using pytest.

    Args:
        test_file: Path to test file

    Returns:
        Dict with execution results:
        - passed: Number of tests passed
        - failed: Number of tests failed
        - pass_rate: Percentage passed (0.0-1.0)
        - output: pytest output

    Example:
        >>> result = execute_test_file(Path("test_app.py"))
        >>> print(f"Pass rate: {result['pass_rate']:.1%}")

    """
    try:
        result = subprocess.run(
            ["pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Parse pytest output to get pass/fail counts
        # This is a simple parser - production would be more robust
        output = result.stdout + result.stderr

        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        total = passed + failed

        pass_rate = passed / total if total > 0 else 0.0

        return {
            "passed": passed,
            "failed": failed,
            "total": total,
            "pass_rate": pass_rate,
            "output": output,
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "pass_rate": 0.0,
            "output": "Test execution timed out",
            "returncode": -1,
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to execute tests: {e}")
        return {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "pass_rate": 0.0,
            "output": str(e),
            "returncode": -1,
        }


def calculate_coverage(test_file: Path, source_file: Path) -> float:
    """Calculate code coverage for a test file.

    Args:
        test_file: Path to test file
        source_file: Path to source file being tested

    Returns:
        Coverage percentage (0.0-100.0)

    Example:
        >>> coverage = calculate_coverage(
        ...     Path("test_app.py"),
        ...     Path("app.py")
        ... )
        >>> print(f"Coverage: {coverage:.1f}%")

    """
    try:
        # Run pytest with coverage
        result = subprocess.run(
            [
                "pytest",
                str(test_file),
                f"--cov={source_file.stem}",
                "--cov-report=term-missing",
                "--no-cov-on-fail",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=source_file.parent,
        )

        output = result.stdout + result.stderr

        # Parse coverage percentage from output
        # Look for line like: "app.py    85%"
        for line in output.split("\n"):
            if source_file.name in line and "%" in line:
                # Extract percentage
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        try:
                            return float(part.rstrip("%"))
                        except ValueError:
                            pass

        return 0.0

    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to calculate coverage: {e}")
        return 0.0
