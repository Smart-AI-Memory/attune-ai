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
from pathlib import Path
from typing import Any

from ..config import _validate_file_path
from ..workflows.base import BaseWorkflow, ModelTier, WorkflowResult, WorkflowStage


@dataclass
class TestGenerationTask:
    """A test generation task."""

    module_path: str
    coverage: float
    output_path: str
    status: str = "pending"  # pending, generated, completed, validated


class ParallelTestGenerationWorkflow(BaseWorkflow):
    """Generate and complete behavioral tests in parallel using multi-tier LLMs."""

    def __init__(self):
        super().__init__(
            name="parallel-test-generation",
            description="Generate behavioral tests in parallel with AI completion",
            stages={
                "discover": WorkflowStage(
                    name="discover",
                    description="Find modules needing tests",
                    tier_hint=ModelTier.CHEAP,
                    system_prompt="Analyze coverage and prioritize modules for testing",
                    task_type="analysis",
                ),
                "generate_templates": WorkflowStage(
                    name="generate_templates",
                    description="Generate test templates in parallel",
                    tier_hint=ModelTier.CHEAP,
                    system_prompt="Generate behavioral test template structure",
                    task_type="code_generation",
                ),
                "complete_tests": WorkflowStage(
                    name="complete_tests",
                    description="Complete test implementation with AI",
                    tier_hint=ModelTier.CAPABLE,
                    system_prompt="""Complete the behavioral test implementation.

You are given a test template with TODO markers. Your task:

1. Analyze the module being tested
2. Create realistic test data
3. Add proper assertions
4. Test both success AND error paths
5. Use mocks/patches where needed
6. Follow pytest best practices

Generate complete, runnable tests that will increase coverage.""",
                    task_type="code_generation",
                ),
                "validate": WorkflowStage(
                    name="validate",
                    description="Validate generated tests run correctly",
                    tier_hint=ModelTier.CHEAP,
                    system_prompt="Check if tests are valid Python and follow pytest conventions",
                    task_type="validation",
                ),
            },
        )

    def discover_low_coverage_modules(self, top_n: int = 200) -> list[tuple[str, float]]:
        """Find modules with lowest coverage."""
        try:
            # Get coverage data
            import subprocess

            subprocess.run(
                ["coverage", "json", "-o", "/tmp/coverage_batch.json"],  # nosec B108
                capture_output=True,
                check=True,
            )

            with open("/tmp/coverage_batch.json") as f:  # nosec B108
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

        except Exception as e:
            self.logger.warning(f"Could not get coverage data: {e}")
            return []

    def analyze_module_structure(self, file_path: str) -> dict[str, Any]:
        """Analyze module to extract structure (fast, synchronous)."""
        try:
            source = Path(file_path).read_text()
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

        except Exception as e:
            return {"file": file_path, "error": str(e)}

    async def generate_test_template_with_ai(
        self, module_path: str, structure: dict[str, Any]
    ) -> str:
        """Generate test template using cheap tier AI."""
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

        result = await self._call_llm(
            tier=ModelTier.CHEAP,
            user_prompt=prompt,
            context={"module": module_path, "structure": structure},
        )

        return result.get("content", "")

    async def complete_test_with_ai(self, template: str, module_path: str) -> str:
        """Complete test implementation using capable tier AI."""
        source_code = Path(module_path).read_text()

        prompt = f"""Complete this behavioral test implementation.

MODULE SOURCE CODE:
```python
{source_code[:5000]}  # First 5000 chars
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

        result = await self._call_llm(
            tier=ModelTier.CAPABLE,
            user_prompt=prompt,
            context={"template": template, "module": module_path},
        )

        return result.get("content", "")

    async def process_module_batch(
        self, modules: list[tuple[str, float]], output_dir: Path, batch_size: int = 10
    ) -> list[TestGenerationTask]:
        """Process modules in parallel batches."""
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
                )
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
        """Extract Python code from markdown code blocks if present."""
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
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

        # Stage 1: Discover modules
        self.logger.info(f"🔍 Discovering top {top} modules with lowest coverage...")
        modules = self.discover_low_coverage_modules(top_n=top)

        if not modules:
            return WorkflowResult(
                workflow_name=self.name,
                stages_executed=["discover"],
                final_output={"error": "No coverage data found. Run pytest with coverage first."},
                cost_report=self._generate_cost_report(),
            )

        self.logger.info(f"📋 Found {len(modules)} modules to process")

        # Stage 2 & 3: Generate and complete in parallel batches
        self.logger.info(f"⚡ Processing in batches of {batch_size}...")
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
        self.logger.info(f"✅ COMPLETED: {len(completed)} test files")
        self.logger.info(f"❌ ERRORS: {len(errors)} modules")
        self.logger.info(f"📁 Location: {output_path}")
        self.logger.info(f"{'='*80}\n")

        return WorkflowResult(
            workflow_name=self.name,
            stages_executed=["discover", "generate_templates", "complete_tests"],
            final_output=result_data,
            cost_report=self._generate_cost_report(),
        )


# Export
__all__ = ["ParallelTestGenerationWorkflow"]
