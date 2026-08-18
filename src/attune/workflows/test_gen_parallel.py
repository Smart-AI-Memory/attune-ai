"""Parallel Behavioral Test Generation & Completion Workflow.

Uses multi-tier LLM orchestration to generate AND complete tests in parallel.
This dramatically accelerates achieving 99.9% test coverage.

Key Features:
- Parallel template generation (cheap tier - fast)
- Parallel test completion (capable tier - quality)
- Batch processing of 10-50 modules simultaneously
- Automatic validation and fixing

Usage:
    empathy workflow run test-gen-parallel --top 200 --parallel 10

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import ast
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.context import TokenBudgetAllocator
from attune.security.path_validation import _validate_file_path

from ..workflows.base import BaseWorkflow, ModelTier, WorkflowResult
from ..workflows.context import WorkflowContext
from ..workflows.data_classes import WorkflowStage
from ..workflows.services import ParsingService, PromptService


@dataclass
class TestGenerationTask:
    """Tracks the state of a single test generation task.

    Attributes:
        module_path: Source module being tested.
        coverage: Current test coverage percentage.
        output_path: Destination path for the generated test file.
        status: Lifecycle state -- one of ``pending``,
            ``generated``, ``completed``, or ``error``.

    """

    module_path: str
    coverage: float
    output_path: str
    status: str = "pending"  # pending, generated, completed, error


class ParallelTestGenerationWorkflow(BaseWorkflow):
    """Generate and complete behavioral tests in parallel using multi-tier LLMs.

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.

    Uses extended thinking for better test planning and completion.
    """

    name = "parallel-test-generation"
    description = "Batch-generate tests for 10-50 modules in parallel"
    stages = ["discover", "generate_templates", "complete_tests", "validate"]
    tier_map = {
        "discover": ModelTier.CHEAP,
        "generate_templates": ModelTier.CHEAP,
        "complete_tests": ModelTier.CAPABLE,
        "validate": ModelTier.CHEAP,
    }

    # Enable extended thinking for complex test generation
    _use_thinking = True
    _thinking_budget = 10000

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for parallel test generation.

        Args:
            xml_config: Optional XML prompt configuration dict.

        Returns:
            WorkflowContext with prompt and parsing services.

        """
        return WorkflowContext(
            prompt=PromptService("parallel-test-generation", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    def discover_low_coverage_modules(self, top_n: int = 200) -> list[tuple[str, float]]:
        """Find modules with lowest test coverage.

        Runs ``coverage json`` to get per-file coverage data, then
        returns the files with the lowest coverage sorted ascending.
        Skips files with fewer than 30 statements.

        Args:
            top_n: Maximum number of modules to return.

        Returns:
            List of (file_path, coverage_percent) tuples sorted by
            coverage ascending.  Empty list if coverage data is
            unavailable.

        """
        try:
            # Get coverage data
            import subprocess
            import tempfile

            with tempfile.TemporaryDirectory(prefix="attune-cov-") as tmpdir:
                cov_path = Path(tmpdir) / "coverage_batch.json"
                subprocess.run(
                    ["coverage", "json", "-o", str(cov_path)],
                    capture_output=True,
                    check=True,
                )
                with open(cov_path) as f:
                    data = json.load(f)

            coverage_by_file = []
            for file_path, info in data.get("files", {}).items():
                if file_path.startswith("src/"):
                    coverage_pct = info["summary"]["percent_covered"]
                    total_lines = info["summary"]["num_statements"]

                    # Skip very small files
                    if total_lines > 30:
                        coverage_by_file.append((file_path, coverage_pct, total_lines))

            # Sort by coverage (lowest first), then by size (largest first)
            sorted_modules = sorted(coverage_by_file, key=lambda x: (x[1], -x[2]))

            return [(path, cov) for path, cov, _ in sorted_modules[:top_n]]

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Coverage data is optional; return empty list
            self.logger.warning(f"Could not get coverage data: {e}")
            return []

    def analyze_module_structure(self, file_path: str) -> dict[str, Any]:
        """Analyze a Python module's AST to extract classes and functions.

        Args:
            file_path: Path to the Python source file.

        Returns:
            Dict with ``file``, ``classes`` (name, methods, line),
            and ``functions`` (name, line) keys.  Includes an
            ``error`` key instead if parsing fails.

        """
        try:
            source = Path(file_path).read_text(encoding="utf-8")
            tree = ast.parse(source)

            classes = []
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [
                        n.name
                        for n in node.body
                        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
                    ]
                    classes.append({"name": node.name, "methods": methods, "line": node.lineno})
                elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                    functions.append({"name": node.name, "line": node.lineno})

            return {"file": file_path, "classes": classes, "functions": functions}

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation when AST parsing fails
            return {"file": file_path, "error": str(e)}

    async def generate_test_template_with_ai(
        self,
        module_path: str,
        structure: dict[str, Any],
    ) -> str:
        """Generate a pytest test skeleton using the cheap LLM tier.

        Args:
            module_path: Path to the source module.
            structure: Module structure dict from
                ``analyze_module_structure``.

        Returns:
            Generated Python test code as a string with TODO
            markers where test logic is needed.

        """
        prompt = f"""Generate a behavioral test template for this module:

File: {module_path}
Structure: {json.dumps(structure, indent=2)}

Generate a pytest test file with:
1. Proper imports
2. Test classes for each class in the module
3. Test methods for key functionality
4. TODO markers where test logic is needed
5. Proper async/await for async methods

Output ONLY the Python code, no explanations."""

        content, _in_tokens, _out_tokens = await self._call_llm(
            tier=ModelTier.CHEAP,
            system="You are a test generation assistant. Output ONLY Python code.",
            user_message=prompt,
        )

        return content

    async def complete_test_with_ai(self, template: str, module_path: str) -> str:
        """Complete a test template using the capable LLM tier.

        Reads the source module and fills in TODO markers with
        realistic test data, mocking, and assertions.

        Args:
            template: Skeleton test code with TODO placeholders.
            module_path: Path to the source module being tested.

        Returns:
            Completed Python test code as a string.

        """
        source_code = Path(module_path).read_text(encoding="utf-8")
        # Budget ≈ the retired 5000-char slice; an oversized module
        # degrades to its AST skeleton (every signature and docstring
        # survives) instead of losing all functions past the cap.
        source_context = TokenBudgetAllocator().fit_source(source_code, token_limit=1250)

        prompt = f"""Complete this behavioral test implementation.

MODULE SOURCE CODE:
```python
{source_context}
```

TEST TEMPLATE:
```python
{template}
```

Complete ALL TODOs with:
1. Realistic test data
2. Proper mocking where needed
3. Comprehensive assertions
4. Both success and error cases

Output the COMPLETE test file, no TODOs remaining."""

        content, _in_tokens, _out_tokens = await self._call_llm(
            tier=ModelTier.CAPABLE,
            system="You are a test completion assistant. Output ONLY Python code.",
            user_message=prompt,
        )

        return content

    async def process_module_batch(
        self,
        modules: list[tuple[str, float]],
        output_dir: Path,
        batch_size: int = 10,
    ) -> list[TestGenerationTask]:
        """Generate and complete tests for modules in parallel batches.

        For each batch, templates are generated concurrently (cheap
        tier), then completed concurrently (capable tier), then
        written to disk.

        Args:
            modules: List of (module_path, coverage_pct) tuples.
            output_dir: Directory to write generated test files.
            batch_size: Modules to process concurrently per batch.

        Returns:
            List of TestGenerationTask with status ``completed``
            or ``error``.

        """
        tasks = []

        # Create tasks
        for module_path, coverage in modules:
            test_filename = f"test_{Path(module_path).stem}_behavioral.py"
            output_path = output_dir / test_filename

            tasks.append(
                TestGenerationTask(
                    module_path=module_path,
                    coverage=coverage,
                    output_path=str(output_path),
                ),
            )

        # Process in batches
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]

            # Generate templates in parallel
            template_coros = []
            for task in batch:
                structure = self.analyze_module_structure(task.module_path)
                coro = self.generate_test_template_with_ai(task.module_path, structure)
                template_coros.append(coro)

            templates = await asyncio.gather(*template_coros, return_exceptions=True)

            # Complete tests in parallel
            completion_coros = []
            for task, template in zip(batch, templates, strict=False):
                if isinstance(template, Exception):
                    task.status = "error"
                    continue

                coro = self.complete_test_with_ai(template, task.module_path)
                completion_coros.append(coro)

            completed = await asyncio.gather(*completion_coros, return_exceptions=True)

            # Save results
            for task, completed_test in zip(batch, completed, strict=False):
                if isinstance(completed_test, Exception):
                    task.status = "error"
                    continue

                # Extract code from markdown if needed
                code = self._extract_code(completed_test)

                # Save to file
                validated_path = _validate_file_path(task.output_path)
                validated_path.write_text(code)
                task.status = "completed"

                self.logger.info(f"✅ Generated: {task.output_path}")

        return tasks

    def _extract_code(self, content: str) -> str:
        """Extract Python code from markdown fenced code blocks.

        Args:
            content: Raw LLM output that may contain
                triple-backtick python blocks.

        Returns:
            Extracted code, or the original content if no
            markdown fencing is detected.

        """
        if "```python" in content:
            parts = content.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
                return code.strip()

        # If no markdown, assume it's already code
        return content

    async def execute(
        self,
        top: int = 200,
        batch_size: int = 10,
        output_dir: str = "tests/behavioral/generated",
        **kwargs,
    ) -> WorkflowResult:
        """Execute parallel test generation workflow.

        Args:
            top: Number of modules to process
            batch_size: Number of modules to process in parallel (10-50 recommended)
            output_dir: Where to save generated tests

        Returns:
            WorkflowResult with generated file paths and statistics

        """
        started_at = datetime.now()
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

        # Stage 1: Discover modules
        self.logger.info(f"Discovering top {top} modules with lowest coverage...")
        modules = self.discover_low_coverage_modules(top_n=top)

        if not modules:
            completed_at = datetime.now()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            return WorkflowResult(
                success=False,
                stages=[
                    WorkflowStage(
                        name="discover",
                        tier=self.tier_map["discover"],
                        description="Discover low-coverage modules",
                    ),
                ],
                final_output={"error": "No coverage data found. Run pytest with coverage first."},
                cost_report=self._generate_cost_report(),
                started_at=started_at,
                completed_at=completed_at,
                total_duration_ms=duration_ms,
            )

        self.logger.info(f"Found {len(modules)} modules to process")

        # Stage 2 & 3: Generate and complete in parallel batches
        self.logger.info(f"Processing in batches of {batch_size}...")
        tasks = await self.process_module_batch(modules, output_path, batch_size=batch_size)

        # Statistics
        completed = [t for t in tasks if t.status == "completed"]
        errors = [t for t in tasks if t.status == "error"]

        result_data = {
            "total_modules": len(modules),
            "completed": len(completed),
            "errors": len(errors),
            "output_dir": str(output_path),
            "generated_files": [t.output_path for t in completed],
        }

        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"COMPLETED: {len(completed)} test files")
        self.logger.info(f"ERRORS: {len(errors)} modules")
        self.logger.info(f"Location: {output_path}")
        self.logger.info(f"{'='*80}\n")

        completed_at = datetime.now()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        stage_names = ["discover", "generate_templates", "complete_tests"]
        return WorkflowResult(
            success=len(errors) == 0,
            stages=[
                WorkflowStage(
                    name=s,
                    tier=self.tier_map[s],
                    description=s.replace("_", " ").title(),
                )
                for s in stage_names
            ],
            final_output=result_data,
            cost_report=self._generate_cost_report(),
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=duration_ms,
        )


# Export
__all__ = ["ParallelTestGenerationWorkflow"]
