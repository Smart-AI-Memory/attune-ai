"""Test Generation Workflow.

Main workflow orchestration for test generation.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from pathlib import Path
from typing import Any

from ..base import BaseWorkflow, ModelTier
from ..context import WorkflowContext
from ..services import ParsingService, PromptService
from .ast_analyzer import ASTFunctionAnalyzer
from .config import DEFAULT_SKIP_PATTERNS
from .test_templates import (
    generate_test_for_class,
    generate_test_for_function,
)


class TestGenerationWorkflow(BaseWorkflow):
    """Generate tests targeting areas with historical bugs.

    Prioritizes test generation for files that have historically
    been bug-prone and have low test coverage.

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.
    """

    name = "test-gen"
    description = "Generate tests for modules with low coverage (sequential, single module)"
    stages = ["identify", "analyze", "generate", "review"]
    tier_map = {
        "identify": ModelTier.CHEAP,
        "analyze": ModelTier.CAPABLE,
        "generate": ModelTier.CAPABLE,
        "review": ModelTier.PREMIUM,
    }

    def __init__(
        self,
        patterns_dir: str = "./patterns",
        min_tests_for_review: int = 10,
        write_tests: bool = False,
        output_dir: str = "tests/generated",
        enable_auth_strategy: bool = True,
        **kwargs: Any,
    ):
        """Initialize test generation workflow.

        Args:
            patterns_dir: Directory containing learned patterns
            min_tests_for_review: Minimum tests generated to trigger premium review
            write_tests: If True, write generated tests to output_dir
            output_dir: Directory to write generated test files
            enable_auth_strategy: Enable intelligent auth routing (default: True)
            **kwargs: Additional arguments passed to BaseWorkflow

        """
        # Opt in to post-simplification by default for test generation
        kwargs.setdefault("enable_post_simplification", True)
        super().__init__(**kwargs)
        self.patterns_dir = patterns_dir
        self.min_tests_for_review = min_tests_for_review
        self.write_tests = write_tests
        self.output_dir = output_dir
        self.enable_auth_strategy = enable_auth_strategy
        self._test_count: int = 0
        self._bug_hotspots: list[str] = []
        self._auth_mode_used: str | None = None
        self._load_bug_hotspots()

    def _load_bug_hotspots(self) -> None:
        """Load files with historical bugs from pattern library."""
        debugging_file = Path(self.patterns_dir) / "debugging.json"
        if debugging_file.exists():
            try:
                with open(debugging_file) as fh:
                    data = json.load(fh)
                    patterns = data.get("patterns", [])
                    # Extract files from bug patterns
                    files = set()
                    for p in patterns:
                        for file_entry in p.get("files_affected", []):
                            if file_entry is None:
                                continue
                            files.add(str(file_entry))
                    self._bug_hotspots = list(files)
            except (json.JSONDecodeError, OSError):
                pass

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for test generation.

        Args:
            xml_config: Optional XML prompt configuration dict.

        Returns:
            WorkflowContext with prompt and parsing services.

        """
        return WorkflowContext(
            prompt=PromptService("test-gen", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Downgrade review stage if few tests generated.

        Args:
            stage_name: Name of the stage to check
            input_data: Current workflow data

        Returns:
            Tuple of (should_skip, reason)

        """
        if stage_name == "review":
            if self._test_count < self.min_tests_for_review:
                # Downgrade to CAPABLE
                self.tier_map["review"] = ModelTier.CAPABLE
                return False, None
        return False, None

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Route to specific stage implementation."""
        if stage_name == "identify":
            return await self._identify(input_data, tier)
        if stage_name == "analyze":
            return await self._analyze(input_data, tier)
        if stage_name == "generate":
            return await self._generate(input_data, tier)
        if stage_name == "review":
            return await self._review(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    async def _identify(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Identify files needing tests.

        Finds files with low coverage, historical bugs, or
        no existing tests.

        Configurable options via input_data:
            max_files_to_scan: Maximum files to scan before stopping (default: 1000)
            max_file_size_kb: Skip files larger than this (default: 200)
            max_candidates: Maximum candidates to return (default: 50)
            skip_patterns: List of directory patterns to skip (default: DEFAULT_SKIP_PATTERNS)
            include_all_files: Include files with priority=0 (default: False)
        """
        target_path = input_data.get("path", ".")
        file_types = input_data.get("file_types", [".py"])

        # === AUTH STRATEGY INTEGRATION ===
        if self.enable_auth_strategy:
            try:
                import logging
                from pathlib import Path

                from attune.models import (
                    count_lines_of_code,
                    get_auth_strategy,
                    get_module_size_category,
                )

                logger = logging.getLogger(__name__)

                # Calculate total LOC for the project/path
                target = Path(target_path)
                total_lines = 0
                if target.is_file():
                    total_lines = count_lines_of_code(target)
                elif target.is_dir():
                    # Estimate total lines for directory
                    for py_file in target.rglob("*.py"):
                        try:
                            total_lines += count_lines_of_code(py_file)
                        except Exception:
                            pass

                if total_lines > 0:
                    strategy = get_auth_strategy()
                    recommended_mode = strategy.get_recommended_mode(total_lines)
                    self._auth_mode_used = recommended_mode.value

                    size_category = get_module_size_category(total_lines)
                    logger.info(
                        f"Test generation target: {target_path} "
                        f"({total_lines:,} LOC, {size_category})",
                    )
                    logger.info(f"Recommended auth mode: {recommended_mode.value}")

                    cost_estimate = strategy.estimate_cost(total_lines, recommended_mode)
                    if recommended_mode.value == "subscription":
                        logger.info(f"Cost: {cost_estimate['quota_cost']}")
                    else:
                        logger.info(f"Cost: ~${cost_estimate['monetary_cost']:.4f}")

            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Auth strategy detection failed: {e}")

        # Parse configurable limits with sensible defaults
        max_files_to_scan = input_data.get("max_files_to_scan", 1000)
        max_file_size_kb = input_data.get("max_file_size_kb", 200)
        max_candidates = input_data.get("max_candidates", 50)
        skip_patterns = input_data.get("skip_patterns", DEFAULT_SKIP_PATTERNS)
        include_all_files = input_data.get("include_all_files", False)

        target = Path(target_path)
        candidates: list[dict] = []

        # Track project scope for enterprise reporting
        total_source_files = 0
        existing_test_files = 0

        # Track scan summary for debugging/visibility
        # Use separate counters for type safety
        scan_counts = {
            "files_scanned": 0,
            "files_too_large": 0,
            "files_read_error": 0,
            "files_excluded_by_pattern": 0,
        }
        early_exit_reason: str | None = None

        max_file_size_bytes = max_file_size_kb * 1024
        scan_limit_reached = False

        if target.exists():
            for ext in file_types:
                if scan_limit_reached:
                    break

                for file_path in target.rglob(f"*{ext}"):
                    # Check if we've hit the scan limit
                    if scan_counts["files_scanned"] >= max_files_to_scan:
                        early_exit_reason = f"max_files_to_scan ({max_files_to_scan}) reached"
                        scan_limit_reached = True
                        break

                    # Skip non-code directories using configurable patterns
                    file_str = str(file_path)
                    if any(skip in file_str for skip in skip_patterns):
                        scan_counts["files_excluded_by_pattern"] += 1
                        continue

                    # Count test files separately for scope awareness
                    if "test_" in file_str or "_test." in file_str or "/tests/" in file_str:
                        existing_test_files += 1
                        continue

                    # Check file size before reading
                    try:
                        file_size = file_path.stat().st_size
                        if file_size > max_file_size_bytes:
                            scan_counts["files_too_large"] += 1
                            continue
                    except OSError:
                        scan_counts["files_read_error"] += 1
                        continue

                    # Count source files and increment scan counter
                    total_source_files += 1
                    scan_counts["files_scanned"] += 1

                    try:
                        content = file_path.read_text(errors="ignore")
                        lines = len(content.splitlines())

                        # Check if in bug hotspots
                        is_hotspot = any(hotspot in file_str for hotspot in self._bug_hotspots)

                        # Check for existing tests
                        test_file = self._find_test_file(file_path)
                        has_tests = test_file.exists() if test_file else False

                        # Calculate priority
                        priority = 0
                        if is_hotspot:
                            priority += 50
                        if not has_tests:
                            priority += 30
                        if lines > 100:
                            priority += 10
                        if lines > 300:
                            priority += 10

                        # Include if priority > 0 OR include_all_files is set
                        if priority > 0 or include_all_files:
                            candidates.append(
                                {
                                    "file": file_str,
                                    "lines": lines,
                                    "is_hotspot": is_hotspot,
                                    "has_tests": has_tests,
                                    "priority": priority,
                                },
                            )
                    except OSError:
                        scan_counts["files_read_error"] += 1
                        continue

        # Sort by priority
        candidates.sort(key=lambda x: -x["priority"])

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(candidates)) // 4

        # Calculate scope metrics for enterprise reporting
        analyzed_count = min(max_candidates, len(candidates))
        coverage_pct = (analyzed_count / len(candidates) * 100) if candidates else 100

        return (
            {
                "candidates": candidates[:max_candidates],
                "total_candidates": len(candidates),
                "hotspot_count": sum(1 for c in candidates if c["is_hotspot"]),
                "untested_count": sum(1 for c in candidates if not c["has_tests"]),
                # Scope awareness fields for enterprise reporting
                "total_source_files": total_source_files,
                "existing_test_files": existing_test_files,
                "large_project_warning": len(candidates) > 100,
                "analysis_coverage_percent": coverage_pct,
                # Scan summary for debugging/visibility
                "scan_summary": {**scan_counts, "early_exit_reason": early_exit_reason},
                # Pass through config for subsequent stages
                "config": {
                    "max_files_to_analyze": input_data.get("max_files_to_analyze", 20),
                    "max_functions_per_file": input_data.get("max_functions_per_file", 30),
                    "max_classes_per_file": input_data.get("max_classes_per_file", 15),
                    "max_files_to_generate": input_data.get("max_files_to_generate", 15),
                    "max_functions_to_generate": input_data.get("max_functions_to_generate", 8),
                    "max_classes_to_generate": input_data.get("max_classes_to_generate", 4),
                },
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    def _find_test_file(self, source_file: Path) -> Path | None:
        """Find corresponding test file for a source file."""
        name = source_file.stem
        parent = source_file.parent

        # Check common test locations
        possible = [
            parent / f"test_{name}.py",
            parent / "tests" / f"test_{name}.py",
            parent.parent / "tests" / f"test_{name}.py",
        ]

        for p in possible:
            if p.exists():
                return p

        return possible[0]  # Return expected location even if doesn't exist

    async def _analyze(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Analyze code structure for test generation.

        Examines functions, classes, and patterns to determine
        what tests should be generated.

        Uses config from _identify stage for limits:
            max_files_to_analyze: Maximum files to analyze (default: 20)
            max_functions_per_file: Maximum functions per file (default: 30)
            max_classes_per_file: Maximum classes per file (default: 15)
        """
        # Get config from previous stage or use defaults
        config = input_data.get("config", {})
        max_files_to_analyze = config.get("max_files_to_analyze", 20)
        max_functions_per_file = config.get("max_functions_per_file", 30)
        max_classes_per_file = config.get("max_classes_per_file", 15)

        candidates = input_data.get("candidates", [])[:max_files_to_analyze]
        analysis: list[dict] = []
        parse_errors: list[str] = []  # Track files that failed to parse

        for candidate in candidates:
            file_path = Path(candidate["file"])
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(errors="ignore")

                # Extract testable items with configurable limits and error tracking
                functions, func_error = self._extract_functions(
                    content,
                    candidate["file"],
                    max_functions_per_file,
                )
                classes, class_error = self._extract_classes(
                    content,
                    candidate["file"],
                    max_classes_per_file,
                )

                # Track parse errors for visibility
                if func_error:
                    parse_errors.append(func_error)
                if class_error and class_error != func_error:
                    parse_errors.append(class_error)

                analysis.append(
                    {
                        "file": candidate["file"],
                        "priority": candidate["priority"],
                        "functions": functions,
                        "classes": classes,
                        "function_count": len(functions),
                        "class_count": len(classes),
                        "test_suggestions": self._generate_suggestions(functions, classes),
                    },
                )
            except OSError:
                continue

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(analysis)) // 4

        return (
            {
                "analysis": analysis,
                "total_functions": sum(a["function_count"] for a in analysis),
                "total_classes": sum(a["class_count"] for a in analysis),
                "parse_errors": parse_errors,  # Expose errors for debugging
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    def _extract_functions(
        self,
        content: str,
        file_path: str = "",
        max_functions: int = 30,
    ) -> tuple[list[dict], str | None]:
        """Extract function definitions from Python code using AST analysis.

        Args:
            content: Python source code
            file_path: File path for error reporting
            max_functions: Maximum functions to extract (configurable)

        Returns:
            Tuple of (functions list, error message or None)

        """
        analyzer = ASTFunctionAnalyzer()
        functions, _ = analyzer.analyze(content, file_path)

        result = []
        for sig in functions[:max_functions]:
            if not sig.name.startswith("_") or sig.name.startswith("__"):
                result.append(
                    {
                        "name": sig.name,
                        "params": [(p[0], p[1], p[2]) for p in sig.params],
                        "param_names": [p[0] for p in sig.params],
                        "is_async": sig.is_async,
                        "return_type": sig.return_type,
                        "raises": list(sig.raises),
                        "has_side_effects": sig.has_side_effects,
                        "complexity": sig.complexity,
                        "docstring": sig.docstring,
                    },
                )
        return result, analyzer.last_error

    def _extract_classes(
        self,
        content: str,
        file_path: str = "",
        max_classes: int = 15,
    ) -> tuple[list[dict], str | None]:
        """Extract class definitions from Python code using AST analysis.

        Args:
            content: Python source code
            file_path: File path for error reporting
            max_classes: Maximum classes to extract (configurable)

        Returns:
            Tuple of (classes list, error message or None)

        """
        analyzer = ASTFunctionAnalyzer()
        _, classes = analyzer.analyze(content, file_path)

        result = []
        for sig in classes[:max_classes]:
            # Skip enums - they don't need traditional class tests
            if sig.is_enum:
                continue

            methods = [
                {
                    "name": m.name,
                    "params": [(p[0], p[1], p[2]) for p in m.params],
                    "is_async": m.is_async,
                    "raises": list(m.raises),
                }
                for m in sig.methods
                if not m.name.startswith("_") or m.name == "__init__"
            ]
            result.append(
                {
                    "name": sig.name,
                    "init_params": [(p[0], p[1], p[2]) for p in sig.init_params],
                    "methods": methods,
                    "base_classes": sig.base_classes,
                    "docstring": sig.docstring,
                    "is_dataclass": sig.is_dataclass,
                    "required_init_params": sig.required_init_params,
                },
            )
        return result, analyzer.last_error

    def _generate_suggestions(self, functions: list[dict], classes: list[dict]) -> list[str]:
        """Generate test suggestions based on code structure."""
        suggestions = []

        for func in functions[:5]:
            if func["params"]:
                suggestions.append(f"Test {func['name']} with valid inputs")
                suggestions.append(f"Test {func['name']} with edge cases")
            if func["is_async"]:
                suggestions.append(f"Test {func['name']} async behavior")

        for cls in classes[:3]:
            suggestions.append(f"Test {cls['name']} initialization")
            suggestions.append(f"Test {cls['name']} methods")

        return suggestions

    async def _generate(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Generate test cases.

        Creates test code targeting identified functions
        and classes, focusing on edge cases.

        Uses config from _identify stage for limits:
            max_files_to_generate: Maximum files to generate tests for (default: 15)
            max_functions_to_generate: Maximum functions per file (default: 8)
            max_classes_to_generate: Maximum classes per file (default: 4)
        """
        # Get config from previous stages or use defaults
        config = input_data.get("config", {})
        max_files_to_generate = config.get("max_files_to_generate", 15)
        max_functions_to_generate = config.get("max_functions_to_generate", 8)
        max_classes_to_generate = config.get("max_classes_to_generate", 4)

        analysis = input_data.get("analysis", [])
        generated_tests: list[dict] = []

        for item in analysis[:max_files_to_generate]:
            file_path = item["file"]
            module_name = Path(file_path).stem

            tests = []
            for func in item.get("functions", [])[:max_functions_to_generate]:
                test_code = generate_test_for_function(module_name, func)
                tests.append(
                    {
                        "target": func["name"],
                        "type": "function",
                        "code": test_code,
                    },
                )

            for cls in item.get("classes", [])[:max_classes_to_generate]:
                test_code = generate_test_for_class(module_name, cls)
                tests.append(
                    {
                        "target": cls["name"],
                        "type": "class",
                        "code": test_code,
                    },
                )

            if tests:
                generated_tests.append(
                    {
                        "source_file": file_path,
                        "test_file": f"test_{module_name}.py",
                        "tests": tests,
                        "test_count": len(tests),
                    },
                )

        self._test_count = sum(t["test_count"] for t in generated_tests)

        # Write tests to files if enabled (via input_data or instance config)
        write_tests = input_data.get("write_tests", self.write_tests)
        output_dir = input_data.get("output_dir", self.output_dir)
        written_files: list[str] = []

        if write_tests and generated_tests:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            for test_item in generated_tests:
                test_filename = test_item["test_file"]
                test_file_path = output_path / test_filename

                # Combine all test code for this file
                combined_code = []
                imports_added = set()

                for test in test_item["tests"]:
                    code = test["code"]
                    # Extract and dedupe imports
                    for line in code.split("\n"):
                        if line.startswith("import ") or line.startswith("from "):
                            if line not in imports_added:
                                imports_added.add(line)
                        elif line.strip():
                            combined_code.append(line)

                # Write the combined test file
                final_code = "\n".join(sorted(imports_added)) + "\n\n" + "\n".join(combined_code)
                test_file_path.write_text(final_code)
                written_files.append(str(test_file_path))
                test_item["written_to"] = str(test_file_path)

        input_tokens = len(str(input_data)) // 4
        output_tokens = sum(len(str(t)) for t in generated_tests) // 4

        return (
            {
                "generated_tests": generated_tests,
                "total_tests_generated": self._test_count,
                "written_files": written_files,
                "tests_written": len(written_files) > 0,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )


def main():
    """CLI entry point for test generation workflow."""
    import asyncio

    async def run():
        workflow = TestGenerationWorkflow()
        result = await workflow.execute(path=".", file_types=[".py"])

        print("\nTest Generation Results")
        print("=" * 50)
        print(f"Provider: {result.provider}")
        print(f"Success: {result.success}")
        print(f"Tests Generated: {result.final_output.get('total_tests', 0)}")
        print("\nCost Report:")
        print(f"  Total Cost: ${result.cost_report.total_cost:.4f}")
        savings = result.cost_report.savings
        pct = result.cost_report.savings_percent
        print(f"  Savings: ${savings:.4f} ({pct:.1f}%)")

    asyncio.run(run())
