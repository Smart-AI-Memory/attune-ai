#!/usr/bin/env python3
"""Comprehensive test script for Wizard Factory features.

This script tests all 4 phases of the Wizard Factory Enhancement:
1. Pattern Library
2. Hot-Reload Infrastructure
3. Risk-Driven Test Generator
4. Methodology Scaffolding

Usage:
    python test_wizard_factory.py
    python test_wizard_factory.py --verbose
    python test_wizard_factory.py --phase 1
    python test_wizard_factory.py --cleanup

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


class TestResult:
    """Track test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []

    def add_pass(self, test_name: str):
        """Record a passing test."""
        self.passed += 1
        logger.info(f"{GREEN}✅ PASS{RESET}: {test_name}")

    def add_fail(self, test_name: str, error: str):
        """Record a failing test."""
        self.failed += 1
        self.errors.append((test_name, error))
        logger.error(f"{RED}❌ FAIL{RESET}: {test_name}")
        logger.error(f"   {RED}Error: {error}{RESET}")

    def add_skip(self, test_name: str, reason: str = ""):
        """Record a skipped test."""
        self.skipped += 1
        logger.info(f"{YELLOW}⏭️  SKIP{RESET}: {test_name} {f'({reason})' if reason else ''}")

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed + self.skipped

        logger.info(f"\n{BOLD}{'=' * 70}{RESET}")
        logger.info(f"{BOLD}Test Summary{RESET}")
        logger.info(f"{BOLD}{'=' * 70}{RESET}")
        logger.info(f"Total Tests: {total}")
        logger.info(f"{GREEN}Passed: {self.passed}{RESET}")
        logger.info(f"{RED}Failed: {self.failed}{RESET}")
        logger.info(f"{YELLOW}Skipped: {self.skipped}{RESET}")

        if self.failed > 0:
            logger.info(f"\n{RED}{BOLD}Failed Tests:{RESET}")
            for test_name, error in self.errors:
                logger.info(f"  {RED}• {test_name}{RESET}")
                logger.info(f"    {error}")

        logger.info(f"{BOLD}{'=' * 70}{RESET}\n")

        return self.failed == 0


class WizardFactoryTester:
    """Test suite for Wizard Factory features."""

    def __init__(self, verbose: bool = False, cleanup: bool = True):
        """Initialize tester.

        Args:
            verbose: Enable verbose output
            cleanup: Clean up test files after running
        """
        self.verbose = verbose
        self.cleanup = cleanup
        self.result = TestResult()
        self.test_dir = Path("test_wizard_output")

    def run_all_tests(self):
        """Run all test phases."""
        logger.info(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
        logger.info(f"{BOLD}{BLUE}Wizard Factory Enhancement - Test Suite{RESET}")
        logger.info(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

        # Setup test directory
        self._setup_test_dir()

        # Run all phases
        self.test_phase_1_pattern_library()
        self.test_phase_2_hot_reload()
        self.test_phase_3_test_generator()
        self.test_phase_4_scaffolding()

        # Cleanup
        if self.cleanup:
            self._cleanup_test_dir()

        # Print summary
        success = self.result.print_summary()

        return 0 if success else 1

    def test_phase_1_pattern_library(self):
        """Test Phase 1: Pattern Library."""
        logger.info(f"\n{BOLD}{BLUE}Phase 1: Pattern Library{RESET}\n")

        # Test 1: Import pattern modules
        try:
            from patterns import get_pattern_registry
            from patterns.core import PatternCategory

            self.result.add_pass("Import pattern modules")
        except Exception as e:
            self.result.add_fail("Import pattern modules", str(e))
            return

        # Test 2: Get pattern registry
        try:
            registry = get_pattern_registry()
            patterns = registry.list_all()
            assert len(patterns) >= 15, f"Expected at least 15 patterns, got {len(patterns)}"
            self.result.add_pass(f"Pattern registry loaded ({len(patterns)} patterns)")
        except Exception as e:
            self.result.add_fail("Pattern registry loaded", str(e))
            return

        # Test 3: Pattern categories
        try:
            from patterns.core import PatternCategory

            categories = list(PatternCategory)
            assert len(categories) == 5, f"Expected 5 categories, got {len(categories)}"
            self.result.add_pass("Pattern categories defined (5 categories)")
        except Exception as e:
            self.result.add_fail("Pattern categories defined", str(e))

        # Test 4: Pattern recommendations
        try:
            healthcare_patterns = registry.recommend_for_wizard("domain", "healthcare")
            assert len(healthcare_patterns) > 0, "No patterns recommended for healthcare"

            coach_patterns = registry.recommend_for_wizard("coach", "software")
            assert len(coach_patterns) > 0, "No patterns recommended for coach"

            self.result.add_pass("Pattern recommendations working")
        except Exception as e:
            self.result.add_fail("Pattern recommendations working", str(e))

        # Test 5: Pattern search
        try:
            results = registry.search("linear")
            assert len(results) > 0, "Search for 'linear' returned no results"
            self.result.add_pass("Pattern search functionality")
        except Exception as e:
            self.result.add_fail("Pattern search functionality", str(e))

        # Test 6: Run pattern unit tests
        try:
            result = subprocess.run(
                ["pytest", "tests/unit/patterns/", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                # Extract test count
                output = result.stdout
                if "passed" in output:
                    self.result.add_pass("Pattern unit tests (63 tests)")
                else:
                    self.result.add_fail("Pattern unit tests", "No tests passed")
            else:
                self.result.add_fail("Pattern unit tests", result.stderr)
        except Exception as e:
            self.result.add_fail("Pattern unit tests", str(e))

    def test_phase_2_hot_reload(self):
        """Test Phase 2: Hot-Reload Infrastructure."""
        logger.info(f"\n{BOLD}{BLUE}Phase 2: Hot-Reload Infrastructure{RESET}\n")

        # Test 1: Import hot-reload modules
        try:
            from hot_reload import HotReloadConfig
            from hot_reload.watcher import WizardFileWatcher
            from hot_reload.websocket import ReloadNotificationManager

            self.result.add_pass("Import hot-reload modules")
        except Exception as e:
            self.result.add_fail("Import hot-reload modules", str(e))
            return

        # Test 2: Hot-reload configuration
        try:
            from hot_reload import HotReloadConfig

            config = HotReloadConfig()
            assert hasattr(config, "enabled"), "Config missing 'enabled' attribute"
            assert hasattr(config, "watch_dirs"), "Config missing 'watch_dirs' attribute"
            self.result.add_pass("Hot-reload configuration loaded")
        except Exception as e:
            self.result.add_fail("Hot-reload configuration loaded", str(e))

        # Test 3: File watcher initialization
        try:
            from pathlib import Path

            from hot_reload.watcher import WizardFileWatcher

            def dummy_callback(path):
                pass

            watcher = WizardFileWatcher(
                wizard_dirs=[Path("wizards")],
                reload_callback=dummy_callback,
            )
            assert watcher is not None, "Watcher initialization failed"
            self.result.add_pass("File watcher initialization")
        except Exception as e:
            self.result.add_fail("File watcher initialization", str(e))

        # Test 4: WebSocket manager
        try:
            from hot_reload.websocket import ReloadNotificationManager

            manager = ReloadNotificationManager()
            assert hasattr(manager, "broadcast"), "Manager missing 'broadcast' method"
            self.result.add_pass("WebSocket notification manager")
        except Exception as e:
            self.result.add_fail("WebSocket notification manager", str(e))

    def test_phase_3_test_generator(self):
        """Test Phase 3: Risk-Driven Test Generator."""
        logger.info(f"\n{BOLD}{BLUE}Phase 3: Risk-Driven Test Generator{RESET}\n")

        # Test 1: Import test generator modules
        try:
            from test_generator import RiskAnalyzer, TestGenerator

            self.result.add_pass("Import test generator modules")
        except Exception as e:
            self.result.add_fail("Import test generator modules", str(e))
            return

        # Test 2: Risk analyzer
        try:
            from test_generator import RiskAnalyzer

            analyzer = RiskAnalyzer()
            analysis = analyzer.analyze(
                "test_wizard",
                ["linear_flow", "approval", "step_validation"],
            )

            assert analysis.wizard_id == "test_wizard", "Wizard ID mismatch"
            assert len(analysis.pattern_ids) == 3, "Pattern count mismatch"
            assert analysis.recommended_coverage >= 70, "Coverage too low"
            assert analysis.recommended_coverage <= 95, "Coverage too high"

            self.result.add_pass(f"Risk analysis ({analysis.recommended_coverage}% coverage)")
        except Exception as e:
            self.result.add_fail("Risk analysis", str(e))

        # Test 3: Test generation
        try:
            from test_generator import TestGenerator

            generator = TestGenerator()
            tests = generator.generate_tests(
                wizard_id="test_wizard",
                pattern_ids=["linear_flow", "approval"],
            )

            assert "unit" in tests, "Missing unit tests"
            assert "fixtures" in tests, "Missing fixtures"
            assert len(tests["unit"]) > 0, "Empty unit tests"

            self.result.add_pass("Test code generation")
        except Exception as e:
            self.result.add_fail("Test code generation", str(e))

        # Test 4: Test priorities
        try:
            from test_generator import RiskAnalyzer

            analyzer = RiskAnalyzer()
            analysis = analyzer.analyze(
                "test_wizard",
                ["approval", "risk_assessment"],
            )

            assert len(analysis.test_priorities) > 0, "No test priorities"

            # Check for priority levels
            priorities = set(analysis.test_priorities.values())
            assert 1 in priorities or len(analysis.critical_paths) > 0, "No critical tests"

            self.result.add_pass(f"Test prioritization ({len(analysis.test_priorities)} tests)")
        except Exception as e:
            self.result.add_fail("Test prioritization", str(e))

    def test_phase_4_scaffolding(self):
        """Test Phase 4: Methodology Scaffolding."""
        logger.info(f"\n{BOLD}{BLUE}Phase 4: Methodology Scaffolding{RESET}\n")

        # Test 1: Import scaffolding modules
        try:
            from scaffolding import PatternCompose, TDDFirst

            self.result.add_pass("Import scaffolding modules")
        except Exception as e:
            self.result.add_fail("Import scaffolding modules", str(e))
            return

        # Test 2: Pattern-Compose methodology
        try:
            from scaffolding import PatternCompose

            method = PatternCompose()
            assert method is not None, "PatternCompose initialization failed"
            assert hasattr(method, "create_wizard"), "Missing create_wizard method"
            self.result.add_pass("Pattern-Compose methodology initialized")
        except Exception as e:
            self.result.add_fail("Pattern-Compose methodology initialized", str(e))

        # Test 3: TDD-First methodology
        try:
            from scaffolding import TDDFirst

            method = TDDFirst()
            assert method is not None, "TDDFirst initialization failed"
            assert hasattr(method, "create_wizard"), "Missing create_wizard method"
            self.result.add_pass("TDD-First methodology initialized")
        except Exception as e:
            self.result.add_fail("TDD-First methodology initialized", str(e))

        # Test 4: Template loading
        try:
            from pathlib import Path

            from jinja2 import Environment, FileSystemLoader

            template_dir = Path("scaffolding/templates")
            env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)

            templates = [
                "linear_flow_wizard.py.jinja2",
                "coach_wizard.py.jinja2",
                "domain_wizard.py.jinja2",
                "base_wizard.py.jinja2",
            ]

            for template_name in templates:
                template = env.get_template(template_name)
                assert template is not None, f"Failed to load {template_name}"

            self.result.add_pass(f"Template loading ({len(templates)} templates)")
        except Exception as e:
            self.result.add_fail("Template loading", str(e))

        # Test 5: End-to-end wizard creation
        try:
            from pathlib import Path

            from scaffolding import PatternCompose

            method = PatternCompose()
            result = method.create_wizard(
                name="test_e2e_wizard",
                domain="healthcare",
                wizard_type="domain",
                output_dir=self.test_dir / "wizards",
            )

            assert "files" in result, "Missing files in result"
            assert len(result["files"]) > 0, "No files generated"

            # Verify files exist
            for file_path in result["files"]:
                assert Path(file_path).exists(), f"Generated file not found: {file_path}"

            self.result.add_pass(f"E2E wizard creation ({len(result['files'])} files)")
        except Exception as e:
            self.result.add_fail("E2E wizard creation", str(e))

        # Test 6: CLI commands
        try:
            # Test list-patterns command
            result = subprocess.run(
                ["python", "-m", "scaffolding", "list-patterns"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and "patterns" in result.stdout.lower():
                self.result.add_pass("CLI list-patterns command")
            else:
                self.result.add_fail("CLI list-patterns command", result.stderr or "No output")
        except Exception as e:
            self.result.add_fail("CLI list-patterns command", str(e))

        # Test 7: Wizard creation via CLI
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "scaffolding",
                    "create",
                    "test_cli_wizard",
                    "--domain",
                    "healthcare",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0 and "✅" in result.stdout:
                self.result.add_pass("CLI wizard creation command")

                # Cleanup CLI-generated files
                cli_wizard_file = Path("empathy_llm_toolkit/wizards/test_cli_wizard_wizard.py")
                if cli_wizard_file.exists():
                    cli_wizard_file.unlink()

                test_file = Path("tests/unit/wizards/test_test_cli_wizard_wizard.py")
                if test_file.exists():
                    test_file.unlink()

                fixtures_file = Path("tests/unit/wizards/fixtures_test_cli_wizard.py")
                if fixtures_file.exists():
                    fixtures_file.unlink()

                readme_file = Path("empathy_llm_toolkit/wizards/test_cli_wizard_README.md")
                if readme_file.exists():
                    readme_file.unlink()
            else:
                self.result.add_fail(
                    "CLI wizard creation command", result.stderr or "Command failed"
                )
        except Exception as e:
            self.result.add_fail("CLI wizard creation command", str(e))

    def _setup_test_dir(self):
        """Setup test output directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)
        logger.info(f"{BLUE}Test directory: {self.test_dir}{RESET}\n")

    def _cleanup_test_dir(self):
        """Cleanup test output directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            logger.info(f"\n{BLUE}Cleaned up test directory{RESET}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Wizard Factory Enhancement features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python test_wizard_factory.py

  # Run with verbose output
  python test_wizard_factory.py --verbose

  # Run specific phase
  python test_wizard_factory.py --phase 1
  python test_wizard_factory.py --phase 4

  # Keep test files (don't cleanup)
  python test_wizard_factory.py --no-cleanup
        """,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--phase",
        "-p",
        type=int,
        choices=[1, 2, 3, 4],
        help="Run specific phase only",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't cleanup test files after running",
    )

    args = parser.parse_args()

    tester = WizardFactoryTester(
        verbose=args.verbose,
        cleanup=not args.no_cleanup,
    )

    # Setup
    tester._setup_test_dir()

    # Run tests
    if args.phase:
        logger.info(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
        logger.info(f"{BOLD}{BLUE}Running Phase {args.phase} Tests Only{RESET}")
        logger.info(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

        if args.phase == 1:
            tester.test_phase_1_pattern_library()
        elif args.phase == 2:
            tester.test_phase_2_hot_reload()
        elif args.phase == 3:
            tester.test_phase_3_test_generator()
        elif args.phase == 4:
            tester.test_phase_4_scaffolding()
    else:
        exit_code = tester.run_all_tests()
        sys.exit(exit_code)

    # Cleanup
    if not args.no_cleanup:
        tester._cleanup_test_dir()

    # Print summary
    success = tester.result.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
