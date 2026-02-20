#!/usr/bin/env python3
"""Automated Test Suite for Sonnet 4.5 → Opus 4.5 Fallback

Runs comprehensive tests across multiple workflows and generates a
detailed performance and cost savings report.

Usage:
    python tests/test_fallback_suite.py
    python tests/test_fallback_suite.py --quick       # Fast test
    python tests/test_fallback_suite.py --full        # Comprehensive test

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

# Load .env file first
try:
    from dotenv import load_dotenv

    load_dotenv()  # Load environment variables from .env
except ImportError:
    pass  # dotenv not installed, continue anyway

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime

from attune.models.empathy_executor import EmpathyLLMExecutor
from attune.models.fallback import SONNET_TO_OPUS_FALLBACK, ResilientExecutor

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None


@dataclass
class TestResult:
    """Result from a single test scenario."""

    scenario_name: str
    workflow_type: str
    expected_model: str  # "sonnet" or "opus"
    actual_model: str
    success: bool
    fallback_triggered: bool
    duration_ms: int
    cost: float
    error: str | None = None


@dataclass
class TestReport:
    """Comprehensive test report."""

    test_run_id: str
    started_at: str
    completed_at: str
    duration_seconds: float

    # Test execution
    total_tests: int
    passed_tests: int
    failed_tests: int

    # Model usage
    sonnet_only: int
    opus_fallback: int
    fallback_rate: float

    # Cost analysis
    total_cost: float
    baseline_opus_cost: float
    savings: float
    savings_percent: float

    # Results by scenario
    results: list[TestResult]

    # Performance
    avg_duration_ms: float
    total_duration_ms: int


class FallbackTestSuite:
    """Automated test suite for Sonnet → Opus fallback."""

    def __init__(self, verbose: bool = True):
        """Initialize test suite.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.console = Console() if RICH_AVAILABLE else None
        self.start_time = datetime.utcnow()
        self.test_run_id = f"fallback_test_{int(time.time())}"
        self.results: list[TestResult] = []

    def _print(self, message: str, style: str | None = None) -> None:
        """Print message with optional rich styling."""
        if self.console and style:
            self.console.print(message, style=style)
        else:
            print(message)

    async def run_test_scenario(
        self,
        scenario_name: str,
        workflow_type: str,
        prompt: str,
        expected_model: str = "sonnet",
    ) -> TestResult:
        """Run a single test scenario.

        Args:
            scenario_name: Name of the test scenario
            workflow_type: Type of workflow (code_review, test_gen, etc.)
            prompt: Test prompt
            expected_model: Expected model to handle this ("sonnet" or "opus")

        Returns:
            TestResult with outcome
        """
        if self.verbose:
            self._print(f"  Testing: {scenario_name}...", "cyan")

        start_time = time.time()

        try:
            # Get API key from environment (Option 2: explicit passing)
            import os

            api_key = os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not found in environment. "
                    "Please set it in your .env file or export it."
                )

            # Create executor with fallback (explicitly pass API key)
            base_executor = EmpathyLLMExecutor(
                provider="anthropic",
                api_key=api_key,  # Explicitly pass the API key
            )
            executor = ResilientExecutor(
                executor=base_executor,
                fallback_policy=SONNET_TO_OPUS_FALLBACK,
            )

            # Execute
            response = await executor.run(
                task_type=workflow_type,
                prompt=prompt,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Determine actual model used
            actual_model = "opus" if response.metadata.get("fallback_used") else "sonnet"
            fallback_triggered = response.metadata.get("fallback_used", False)

            # Get cost (estimate if not available)
            cost = response.metadata.get("cost", 0.0)
            if cost == 0.0:
                # Estimate based on model
                input_tokens = response.metadata.get("input_tokens", 1000)
                output_tokens = response.metadata.get("output_tokens", 500)
                if actual_model == "sonnet":
                    cost = (input_tokens * 0.003 / 1000) + (output_tokens * 0.015 / 1000)
                else:
                    cost = (input_tokens * 0.015 / 1000) + (output_tokens * 0.075 / 1000)

            # Check if response indicates success (handle different response formats)
            success = True
            if hasattr(response, "success"):
                # Check if response is successful (has content and no error)
                success = bool(response.content and not response.metadata.get("error"))
            elif hasattr(response, "content"):
                success = bool(response.content)  # Has content = success
            else:
                success = True  # If we got a response, assume success

            result = TestResult(
                scenario_name=scenario_name,
                workflow_type=workflow_type,
                expected_model=expected_model,
                actual_model=actual_model,
                success=success,
                fallback_triggered=fallback_triggered,
                duration_ms=duration_ms,
                cost=cost,
            )

            if self.verbose:
                status = "✅" if success else "❌"
                model_icon = "🔵" if actual_model == "sonnet" else "🟣"
                self._print(
                    f"    {status} {model_icon} {actual_model.upper()} ({duration_ms}ms, ${cost:.4f})",
                    "green" if success else "red",
                )

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            result = TestResult(
                scenario_name=scenario_name,
                workflow_type=workflow_type,
                expected_model=expected_model,
                actual_model="error",
                success=False,
                fallback_triggered=False,
                duration_ms=duration_ms,
                cost=0.0,
                error=str(e),
            )

            if self.verbose:
                self._print(f"    ❌ ERROR: {e}", "red")

            return result

    async def run_quick_tests(self) -> list[TestResult]:
        """Run quick test suite (5-10 tests)."""
        self._print("\n🚀 Running Quick Test Suite", "bold cyan")
        self._print("=" * 60, "cyan")

        tests = [
            # Simple tasks (should use Sonnet)
            (
                "Simple code generation",
                "code_generation",
                "Write a Python function to calculate factorial",
                "sonnet",
            ),
            (
                "Basic code review",
                "code_review",
                "Review this code: def add(a, b): return a + b",
                "sonnet",
            ),
            (
                "Test generation",
                "test_generation",
                "Generate pytest tests for a function that reverses a string",
                "sonnet",
            ),
            # Moderate tasks (likely Sonnet, may fallback)
            (
                "Security review",
                "code_review",
                "Review for security: def query(sql): db.execute(sql)",
                "sonnet",
            ),
            (
                "Documentation",
                "documentation",
                "Document this function: def process_data(items): return [x*2 for x in items]",
                "sonnet",
            ),
        ]

        results = []
        for scenario_name, workflow_type, prompt, expected in tests:
            result = await self.run_test_scenario(scenario_name, workflow_type, prompt, expected)
            results.append(result)
            await asyncio.sleep(0.5)  # Rate limiting

        return results

    async def run_full_tests(self) -> list[TestResult]:
        """Run comprehensive test suite (15-20 tests)."""
        self._print("\n🔬 Running Full Test Suite", "bold cyan")
        self._print("=" * 60, "cyan")

        tests = [
            # Tier 1: Simple tasks (should use Sonnet)
            (
                "Hello world generation",
                "code_generation",
                "Write a hello world program in Python",
                "sonnet",
            ),
            (
                "Simple function",
                "code_generation",
                "Write a function to check if a number is even",
                "sonnet",
            ),
            (
                "Basic review",
                "code_review",
                "Review: def greet(name): print(f'Hello {name}')",
                "sonnet",
            ),
            (
                "Simple test",
                "test_generation",
                "Generate test for: def square(x): return x * x",
                "sonnet",
            ),
            # Tier 2: Moderate complexity (should use Sonnet)
            (
                "Algorithm explanation",
                "documentation",
                "Explain quicksort algorithm with code example",
                "sonnet",
            ),
            (
                "Bug fix suggestion",
                "code_review",
                "Find bug: items = [1,2,3]; print(items[5])",
                "sonnet",
            ),
            (
                "Refactoring suggestion",
                "refactoring",
                "Refactor: def f(x): if x>0: if x>10: if x>100: return True",
                "sonnet",
            ),
            (
                "SQL injection check",
                "code_review",
                "Security review: def login(user, pwd): query = f'SELECT * FROM users WHERE name={user}'",
                "sonnet",
            ),
            # Tier 3: Complex tasks (may trigger Opus fallback)
            (
                "Architecture analysis",
                "architecture_review",
                "Analyze this distributed system for race conditions: System A locks X then Y, System B locks Y then X",
                "opus",
            ),
            (
                "Complex refactoring",
                "refactoring",
                "Refactor this legacy code to use dependency injection, SOLID principles, and design patterns",
                "opus",
            ),
            (
                "Performance optimization",
                "performance_audit",
                "Optimize this O(n²) algorithm for large datasets with millions of records",
                "opus",
            ),
            (
                "Security deep dive",
                "security_audit",
                "Comprehensive security audit including timing attacks, side channels, and crypto vulnerabilities",
                "opus",
            ),
            # Tier 4: Edge cases
            (
                "Empty input",
                "code_generation",
                "",
                "sonnet",
            ),
            (
                "Very long prompt",
                "documentation",
                "Explain " + "machine learning " * 100,
                "sonnet",
            ),
            (
                "Special characters",
                "code_review",
                "Review: def test(): return '\\n\\t\\'\\\"'",
                "sonnet",
            ),
        ]

        results = []
        for scenario_name, workflow_type, prompt, expected in tests:
            result = await self.run_test_scenario(scenario_name, workflow_type, prompt, expected)
            results.append(result)
            await asyncio.sleep(0.5)  # Rate limiting

        return results

    def generate_report(self, results: list[TestResult]) -> TestReport:
        """Generate comprehensive test report.

        Args:
            results: List of test results

        Returns:
            TestReport with analysis
        """
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()

        # Calculate metrics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests

        sonnet_only = sum(1 for r in results if r.actual_model == "sonnet")
        opus_fallback = sum(1 for r in results if r.actual_model == "opus")
        fallback_rate = (opus_fallback / total_tests * 100) if total_tests > 0 else 0

        total_cost = sum(r.cost for r in results)

        # Calculate baseline (all Opus) cost
        baseline_opus_cost = sum(
            r.cost * 5 if r.actual_model == "sonnet" else r.cost for r in results
        )

        savings = baseline_opus_cost - total_cost
        savings_percent = (savings / baseline_opus_cost * 100) if baseline_opus_cost > 0 else 0

        avg_duration = sum(r.duration_ms for r in results) / total_tests if total_tests > 0 else 0
        total_duration_ms = sum(r.duration_ms for r in results)

        return TestReport(
            test_run_id=self.test_run_id,
            started_at=self.start_time.isoformat(),
            completed_at=end_time.isoformat(),
            duration_seconds=duration,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            sonnet_only=sonnet_only,
            opus_fallback=opus_fallback,
            fallback_rate=fallback_rate,
            total_cost=total_cost,
            baseline_opus_cost=baseline_opus_cost,
            savings=savings,
            savings_percent=savings_percent,
            results=results,
            avg_duration_ms=avg_duration,
            total_duration_ms=total_duration_ms,
        )

    def print_report(self, report: TestReport) -> None:
        """Print formatted test report.

        Args:
            report: Test report to display
        """
        if RICH_AVAILABLE and self.console:
            self._print_rich_report(report)
        else:
            self._print_plain_report(report)

    def _print_rich_report(self, report: TestReport) -> None:
        """Print rich formatted report."""
        console = self.console
        if not console:
            return

        console.print("\n" + "=" * 80, style="cyan")
        console.print(
            "🎯 SONNET 4.5 → OPUS 4.5 FALLBACK TEST REPORT", style="bold cyan", justify="center"
        )
        console.print("=" * 80, style="cyan")

        # Test execution summary
        exec_table = Table(title="Test Execution Summary", show_header=True)
        exec_table.add_column("Metric", style="cyan")
        exec_table.add_column("Value", style="green", justify="right")

        exec_table.add_row("Total Tests", str(report.total_tests))
        exec_table.add_row("Passed", f"[green]{report.passed_tests}[/green]")
        exec_table.add_row("Failed", f"[red]{report.failed_tests}[/red]")
        exec_table.add_row(
            "Success Rate",
            f"{(report.passed_tests / report.total_tests * 100):.1f}%",
        )
        exec_table.add_row("Duration", f"{report.duration_seconds:.1f}s")
        exec_table.add_row("Avg Test Duration", f"{report.avg_duration_ms:.0f}ms")

        console.print(exec_table)

        # Model usage
        usage_text = Text()
        usage_text.append(
            f"Sonnet Only: {report.sonnet_only} ({(report.sonnet_only / report.total_tests * 100):.1f}%)\n",
            style="blue bold",
        )
        usage_text.append(
            f"Opus Fallback: {report.opus_fallback} ({report.fallback_rate:.1f}%)\n",
            style="magenta bold",
        )

        fallback_style = (
            "green"
            if report.fallback_rate < 5
            else ("yellow" if report.fallback_rate < 15 else "red")
        )
        usage_text.append(
            f"\nFallback Rate: {report.fallback_rate:.1f}%", style=f"{fallback_style} bold"
        )

        console.print(Panel(usage_text, title="Model Usage Distribution", border_style="blue"))

        # Cost analysis
        cost_text = Text()
        cost_text.append(f"Actual Cost: ${report.total_cost:.4f}\n")
        cost_text.append(f"Baseline (all Opus): ${report.baseline_opus_cost:.4f}\n")
        cost_text.append(
            f"\nSavings: ${report.savings:.4f} ({report.savings_percent:.1f}%)\n",
            style="green bold",
        )
        cost_text.append(f"Projected Annual Savings: ${report.savings * 365:.2f}", style="green")

        console.print(Panel(cost_text, title="Cost Savings Analysis", border_style="green"))

        # Detailed results table
        results_table = Table(title="Test Results by Scenario", show_header=True)
        results_table.add_column("Scenario", style="cyan")
        results_table.add_column("Type", style="blue")
        results_table.add_column("Model", style="magenta")
        results_table.add_column("Status", justify="center")
        results_table.add_column("Duration", justify="right")
        results_table.add_column("Cost", justify="right")

        for result in report.results:
            status_icon = "✅" if result.success else "❌"
            model_display = "🔵 Sonnet" if result.actual_model == "sonnet" else "🟣 Opus"

            results_table.add_row(
                result.scenario_name[:30],
                result.workflow_type[:15],
                model_display,
                status_icon,
                f"{result.duration_ms}ms",
                f"${result.cost:.4f}",
            )

        console.print(results_table)

        # Recommendations
        if report.fallback_rate < 5:
            rec_text = Text()
            rec_text.append("✅ Excellent Performance!\n", style="green bold")
            rec_text.append(f"Sonnet handles {100 - report.fallback_rate:.1f}% of tasks.\n")
            rec_text.append(
                f"Cost savings: ${report.savings:.4f} ({report.savings_percent:.1f}%)\n"
            )
            rec_text.append("\nRecommendation: Continue current strategy.")
            console.print(Panel(rec_text, title="Assessment", border_style="green"))
        elif report.fallback_rate < 15:
            rec_text = Text()
            rec_text.append("⚠️  Moderate Fallback Rate\n", style="yellow bold")
            rec_text.append(f"{report.fallback_rate:.1f}% of tasks need Opus.\n")
            rec_text.append("\nRecommendation: Monitor fallback patterns.")
            console.print(Panel(rec_text, title="Assessment", border_style="yellow"))
        else:
            rec_text = Text()
            rec_text.append("❌ High Fallback Rate\n", style="red bold")
            rec_text.append(f"{report.fallback_rate:.1f}% of tasks need Opus.\n")
            rec_text.append("\nRecommendation: Consider using Opus directly for complex tasks.")
            console.print(Panel(rec_text, title="Assessment", border_style="red"))

        console.print("\n" + "=" * 80, style="cyan")

    def _print_plain_report(self, report: TestReport) -> None:
        """Print plain text report."""
        print("\n" + "=" * 80)
        print("SONNET 4.5 → OPUS 4.5 FALLBACK TEST REPORT")
        print("=" * 80)

        print("\nTest Execution:")
        print(f"  Total Tests: {report.total_tests}")
        print(f"  Passed: {report.passed_tests}")
        print(f"  Failed: {report.failed_tests}")
        print(f"  Duration: {report.duration_seconds:.1f}s")

        print("\nModel Usage:")
        print(
            f"  Sonnet Only: {report.sonnet_only} ({(report.sonnet_only / report.total_tests * 100):.1f}%)"
        )
        print(f"  Opus Fallback: {report.opus_fallback} ({report.fallback_rate:.1f}%)")

        print("\nCost Analysis:")
        print(f"  Actual Cost: ${report.total_cost:.4f}")
        print(f"  Baseline (all Opus): ${report.baseline_opus_cost:.4f}")
        print(f"  Savings: ${report.savings:.4f} ({report.savings_percent:.1f}%)")

        print("\n" + "=" * 80)

    def save_report(
        self, report: TestReport, output_path: str = "fallback_test_report.json"
    ) -> None:
        """Save report to JSON file.

        Args:
            report: Test report
            output_path: Path to save report
        """
        report_dict = asdict(report)

        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2, default=str)

        self._print(f"\n📄 Report saved to: {output_path}", "green")

    async def run(self, test_type: str = "quick") -> TestReport:
        """Run test suite and generate report.

        Args:
            test_type: "quick" or "full"

        Returns:
            TestReport
        """
        self._print("\n🧪 Sonnet 4.5 → Opus 4.5 Fallback Test Suite", "bold magenta")
        self._print(f"Test ID: {self.test_run_id}", "dim")
        self._print(f"Started: {self.start_time.isoformat()}", "dim")

        # Run tests
        if test_type == "full":
            results = await self.run_full_tests()
        else:
            results = await self.run_quick_tests()

        self.results = results

        # Generate report
        report = self.generate_report(results)

        # Display report
        self.print_report(report)

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"fallback_test_report_{timestamp}.json"
        self.save_report(report, report_path)

        return report


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Automated test suite for Sonnet 4.5 → Opus 4.5 fallback"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test suite (5-10 tests, ~30s)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full test suite (15-20 tests, ~2min)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (only show final report)",
    )

    args = parser.parse_args()

    # Determine test type
    if args.full:
        test_type = "full"
    else:
        test_type = "quick"  # Default

    # Create suite
    suite = FallbackTestSuite(verbose=not args.quiet)

    # Run tests
    report = await suite.run(test_type=test_type)

    # Exit code based on results
    if report.failed_tests > 0:
        return 1

    if report.fallback_rate > 20:
        print("\n⚠️  Warning: High fallback rate detected!")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
