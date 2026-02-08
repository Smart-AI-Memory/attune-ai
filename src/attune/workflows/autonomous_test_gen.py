"""Autonomous Test Generation with Dashboard Integration - Enhanced Edition.

Generates behavioral tests with real-time monitoring via Agent Coordination Dashboard.

ENHANCEMENTS (Phase 1):
- Extended thinking mode for better test planning
- Prompt caching for 90% cost reduction
- Full source code (no truncation)
- Workflow-specific prompts with mocking templates
- Few-shot learning with examples

ENHANCEMENTS (Phase 2 - Multi-Turn Refinement):
- Iterative test generation with validation loop
- Automatic failure detection and fixing
- Conversation history for context preservation

ENHANCEMENTS (Phase 3 - Coverage-Guided Generation):
- Coverage analysis integration
- Iterative coverage improvement targeting uncovered lines
- Systematic path to 80%+ coverage

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from attune.config import _validate_file_path
from attune.memory.short_term import RedisShortTermMemory
from attune.telemetry.agent_tracking import HeartbeatCoordinator
from attune.telemetry.event_streaming import EventStreamer
from attune.telemetry.feedback_loop import FeedbackLoop

from .test_gen_coverage import TestGenCoverageMixin
from .test_gen_prompts import TestGenPromptMixin
from .test_gen_refinement import TestGenRefinementMixin

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of pytest validation."""

    passed: bool
    failures: str
    error_count: int
    output: str


@dataclass
class CoverageResult:
    """Result of coverage analysis."""

    coverage: float
    missing_lines: list[int]
    total_statements: int
    covered_statements: int


class AutonomousTestGenerator(
    TestGenPromptMixin,
    TestGenRefinementMixin,
    TestGenCoverageMixin,
):
    """Generate tests autonomously with dashboard monitoring and Anthropic best practices."""

    def __init__(
        self,
        agent_id: str,
        batch_num: int,
        modules: list[dict[str, Any]],
        enable_refinement: bool = True,
        max_refinement_iterations: int = 3,
        enable_coverage_guided: bool = False,
        target_coverage: float = 0.80,
    ):
        """Initialize generator.

        Args:
            agent_id: Unique agent identifier
            batch_num: Batch number (1-18)
            modules: List of modules to generate tests for
            enable_refinement: Enable Phase 2 multi-turn refinement (default: True)
            max_refinement_iterations: Max iterations for refinement (default: 3)
            enable_coverage_guided: Enable Phase 3 coverage-guided generation (default: False)
            target_coverage: Target coverage percentage (default: 0.80 = 80%)
        """
        self.agent_id = agent_id
        self.batch_num = batch_num
        self.modules = modules

        # Phase 2 & 3 configuration
        self.enable_refinement = enable_refinement
        self.max_refinement_iterations = max_refinement_iterations
        self.enable_coverage_guided = enable_coverage_guided
        self.target_coverage = target_coverage

        # Initialize memory backend for dashboard integration
        try:
            self.memory = RedisShortTermMemory()
            self.coordinator = HeartbeatCoordinator(memory=self.memory, enable_streaming=True)
            self.event_streamer = EventStreamer(memory=self.memory)
            self.feedback_loop = FeedbackLoop(memory=self.memory)
        except Exception as e:
            logger.warning(f"Failed to initialize memory backend: {e}")
            self.coordinator = HeartbeatCoordinator()
            self.event_streamer = None
            self.feedback_loop = None

        self.output_dir = Path(f"tests/behavioral/generated/batch{batch_num}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Generator initialized: refinement={enable_refinement}, coverage_guided={enable_coverage_guided}"
        )

    def generate_all(self) -> dict[str, Any]:
        """Generate tests for all modules with progress tracking.

        Returns:
            Summary of generation results
        """
        # Start tracking
        self.coordinator.start_heartbeat(
            agent_id=self.agent_id,
            metadata={
                "batch": self.batch_num,
                "total_modules": len(self.modules),
                "workflow": "autonomous_test_generation",
            },
        )

        try:
            results = {
                "batch": self.batch_num,
                "total_modules": len(self.modules),
                "completed": 0,
                "failed": 0,
                "tests_generated": 0,
                "files_created": [],
            }

            for i, module in enumerate(self.modules):
                progress = (i + 1) / len(self.modules)
                module_name = module["file"].replace("src/attune/", "")

                # Update dashboard
                self.coordinator.beat(
                    status="running",
                    progress=progress,
                    current_task=f"Generating tests for {module_name}",
                )

                try:
                    # Generate tests for this module
                    test_file = self._generate_module_tests(module)
                    if test_file:
                        results["completed"] += 1
                        results["files_created"].append(str(test_file))
                        logger.info(f"✅ Generated tests for {module_name}")

                        # Send event to dashboard
                        if self.event_streamer:
                            self.event_streamer.publish_event(
                                event_type="test_file_created",
                                data={
                                    "agent_id": self.agent_id,
                                    "module": module_name,
                                    "test_file": str(test_file),
                                    "batch": self.batch_num,
                                },
                            )

                        # Record quality feedback
                        if self.feedback_loop:
                            self.feedback_loop.record_feedback(
                                workflow_name="test-generation",
                                stage_name="generation",
                                tier="capable",
                                quality_score=1.0,  # Success
                                metadata={
                                    "module": module_name,
                                    "status": "success",
                                    "batch": self.batch_num,
                                },
                            )
                    else:
                        results["failed"] += 1
                        logger.warning(f"⚠️ Skipped {module_name} (validation failed)")

                        # Record failure feedback
                        if self.feedback_loop:
                            self.feedback_loop.record_feedback(
                                workflow_name="test-generation",
                                stage_name="validation",
                                tier="capable",
                                quality_score=0.0,  # Failure
                                metadata={
                                    "module": module_name,
                                    "status": "validation_failed",
                                    "batch": self.batch_num,
                                },
                            )

                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"❌ Error generating tests for {module_name}: {e}")

                    # Send error event
                    if self.event_streamer:
                        self.event_streamer.publish_event(
                            event_type="test_generation_error",
                            data={
                                "agent_id": self.agent_id,
                                "module": module_name,
                                "error": str(e),
                                "batch": self.batch_num,
                            },
                        )

            # Count total tests
            results["tests_generated"] = self._count_tests()

            # Final update
            self.coordinator.beat(
                status="completed",
                progress=1.0,
                current_task=f"Completed: {results['completed']}/{results['total_modules']} modules",
            )

            return results

        except Exception as e:
            # Error tracking
            self.coordinator.beat(status="failed", progress=0.0, current_task=f"Failed: {str(e)}")
            raise

        finally:
            # Stop heartbeat
            self.coordinator.stop_heartbeat(
                final_status="completed" if results["completed"] > 0 else "failed"
            )

    def _generate_module_tests(self, module: dict[str, Any]) -> Path | None:
        """Generate tests for a single module using LLM agent.

        Args:
            module: Module info dict with 'file', 'total', 'missing', etc.

        Returns:
            Path to generated test file, or None if skipped
        """
        source_file = Path(module["file"])
        module_name = source_file.stem

        # Skip if module doesn't exist
        if not source_file.exists():
            logger.warning(f"Source file not found: {source_file}")
            return None

        # Read source to understand what needs testing
        try:
            source_code = source_file.read_text()
        except Exception as e:
            logger.error(f"Cannot read {source_file}: {e}")
            return None

        # Generate test file path
        test_file = self.output_dir / f"test_{module_name}_behavioral.py"

        # Extract module path for imports
        module_path = str(source_file).replace("src/", "").replace(".py", "").replace("/", ".")

        # Generate tests using LLM agent with Anthropic best practices
        # Phase 1: Basic generation
        # Phase 2: Multi-turn refinement (if enabled)
        # Phase 3: Coverage-guided improvement (if enabled)

        if self.enable_refinement:
            logger.info(f"🔄 Using Phase 2: Multi-turn refinement for {module_name}")
            test_content = self._generate_with_refinement(
                module_name, module_path, source_file, source_code, test_file
            )
        else:
            logger.info(f"📝 Using Phase 1: Basic generation for {module_name}")
            test_content = self._generate_with_llm(
                module_name, module_path, source_file, source_code
            )

        if not test_content:
            logger.warning(f"LLM generation failed for {module_name}")
            return None

        logger.info(f"LLM generated {len(test_content)} bytes for {module_name}")

        # Phase 3: Coverage-guided improvement (if enabled)
        if self.enable_coverage_guided:
            logger.info(f"📊 Applying Phase 3: Coverage-guided improvement for {module_name}")
            improved_content = self._generate_with_coverage_target(
                module_name, module_path, source_file, source_code, test_file, test_content
            )
            if improved_content:
                test_content = improved_content
                logger.info(f"✅ Coverage-guided improvement complete for {module_name}")
            else:
                logger.warning(
                    f"⚠️  Coverage-guided improvement failed, using previous version for {module_name}"
                )

        # Write final test file
        validated_path = _validate_file_path(str(test_file))
        validated_path.write_text(test_content)
        logger.info(f"Wrote test file: {validated_path}")

        # Validate it can be imported
        if not self._validate_test_file(test_file):
            test_file.unlink()
            return None

        return test_file

    def _generate_with_llm(
        self, module_name: str, module_path: str, source_file: Path, source_code: str
    ) -> str | None:
        """Generate comprehensive tests using LLM with Anthropic best practices.

        ENHANCEMENTS (Phase 1):
        - Extended thinking (20K token budget) for thorough test planning
        - Prompt caching for 90% cost reduction
        - Full source code (NO TRUNCATION)
        - Workflow-specific prompts when detected

        Args:
            module_name: Name of module being tested
            module_path: Python import path (e.g., attune.config)
            source_file: Path to source file
            source_code: Source code content (FULL, not truncated)

        Returns:
            Test file content with comprehensive tests, or None if generation failed
        """
        import os

        try:
            import anthropic
        except ImportError:
            logger.error("anthropic package not installed")
            return None

        # Get API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not set")
            return None

        # Detect if this is a workflow module
        is_workflow = self._is_workflow_module(source_code, module_path)
        logger.info(
            f"Module {module_name}: workflow={is_workflow}, size={len(source_code)} bytes (FULL)"
        )

        # Build appropriate prompt based on module type
        if is_workflow:
            generation_prompt = self._get_workflow_specific_prompt(
                module_name, module_path, source_code
            )
        else:
            generation_prompt = f"""Generate comprehensive behavioral tests for this Python module.

SOURCE FILE: {source_file}
MODULE PATH: {module_path}

SOURCE CODE (COMPLETE):
```python
{source_code}
```

Generate a complete test file that:
1. Uses Given/When/Then behavioral test structure
2. Tests all public functions and classes
3. Includes edge cases and error handling
4. Uses proper mocking for external dependencies
5. Targets 80%+ code coverage for this module
6. Follows pytest conventions

Requirements:
- Import from {module_path} (not from src/)
- Use pytest fixtures where appropriate
- Mock external dependencies (APIs, databases, file I/O)
- Test both success and failure paths
- Include docstrings for all tests
- Use descriptive test names
- Start with copyright header:
\"\"\"Behavioral tests for {module_name}.

Generated by enhanced autonomous test generation system.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
\"\"\"

Return ONLY the complete Python test file content, no explanations."""

        # Build messages with prompt caching (90% cost reduction on retries)
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "You are an expert Python test engineer. Here are examples of excellent tests:",
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": self._get_example_tests(),
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": generation_prompt},
                ],
            }
        ]

        try:
            # Call Anthropic API with extended thinking and caching
            logger.info(
                f"Calling LLM with extended thinking for {module_name} (workflow={is_workflow})"
            )
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",  # capable tier
                max_tokens=40000,  # Very generous total budget for comprehensive tests
                thinking={
                    "type": "enabled",
                    "budget_tokens": 20000,  # Generous thinking budget for thorough planning
                },
                messages=messages,
                timeout=900.0,  # 15 minutes timeout for extended thinking + generation
            )

            if not response.content:
                logger.warning(f"Empty LLM response for {module_name}")
                return None

            # Extract test content (thinking comes first, then text)
            test_content = None
            for block in response.content:
                if block.type == "text":
                    test_content = block.text.strip()
                    break

            if not test_content:
                logger.warning(f"No text content in LLM response for {module_name}")
                return None

            logger.info(f"LLM returned {len(test_content)} bytes for {module_name}")

            if len(test_content) < 100:
                logger.warning(f"LLM response too short for {module_name}: {test_content[:200]}")
                return None

            # Clean up response (remove markdown fences if present)
            if test_content.startswith("```python"):
                test_content = test_content[len("```python") :].strip()
            if test_content.endswith("```"):
                test_content = test_content[:-3].strip()

            # Check for truncation indicators
            if response.stop_reason == "max_tokens":
                logger.warning(f"⚠️  LLM response truncated for {module_name} (hit max_tokens)")
                # Response might be incomplete but let validation catch it

            # Quick syntax pre-check before returning
            try:
                import ast

                ast.parse(test_content)
                logger.info(f"✓ Quick syntax check passed for {module_name}")
            except SyntaxError as e:
                logger.error(
                    f"❌ LLM generated invalid syntax for {module_name}: {e.msg} at line {e.lineno}"
                )
                return None

            logger.info(f"Test content cleaned, final size: {len(test_content)} bytes")
            return test_content

        except Exception as e:
            logger.error(f"LLM generation error for {module_name}: {e}", exc_info=True)
            return None

    def _validate_test_file(self, test_file: Path) -> bool:
        """Validate test file can be imported and has valid syntax.

        Args:
            test_file: Path to test file

        Returns:
            True if valid, False otherwise
        """
        # Step 1: Check for syntax errors with ast.parse (fast)
        try:
            import ast

            content = test_file.read_text()
            ast.parse(content)
            logger.info(f"✓ Syntax check passed for {test_file.name}")
        except SyntaxError as e:
            logger.error(f"❌ Syntax error in {test_file.name} at line {e.lineno}: {e.msg}")
            return False
        except Exception as e:
            logger.error(f"❌ Cannot parse {test_file.name}: {e}")
            return False

        # Step 2: Check if pytest can collect the tests
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", str(test_file)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.error(f"❌ Pytest collection failed for {test_file.name}")
                logger.error(f"   Error: {result.stderr[:500]}")
                return False

            logger.info(f"✓ Pytest collection passed for {test_file.name}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Validation timeout for {test_file.name}")
            return False
        except Exception as e:
            logger.error(f"❌ Validation exception for {test_file}: {e}")
            return False

    def _count_tests(self) -> int:
        """Count total tests in generated files.

        Returns:
            Number of tests
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q", str(self.output_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Parse output like "123 tests collected"
            for line in result.stdout.split("\n"):
                if "tests collected" in line:
                    return int(line.split()[0])
            return 0
        except Exception:
            return 0


def run_batch_generation(
    batch_num: int,
    modules_json: str,
    enable_refinement: bool = True,
    enable_coverage_guided: bool = False,
) -> None:
    """Run test generation for a batch.

    Args:
        batch_num: Batch number
        modules_json: JSON string of modules to process
        enable_refinement: Enable Phase 2 multi-turn refinement (default: True)
        enable_coverage_guided: Enable Phase 3 coverage-guided generation (default: False)
    """
    # Parse modules
    modules = json.loads(modules_json)

    # Create agent with Phase 2 & 3 configuration
    agent_id = f"test-gen-batch{batch_num}"
    generator = AutonomousTestGenerator(
        agent_id,
        batch_num,
        modules,
        enable_refinement=enable_refinement,
        enable_coverage_guided=enable_coverage_guided,
    )

    # Generate tests
    print(f"Starting autonomous test generation for batch {batch_num}")
    print(f"Modules to process: {len(modules)}")
    print(f"Agent ID: {agent_id}")
    print("\nENHANCEMENTS:")
    print("  Phase 1: Extended thinking + Prompt caching + Workflow detection")
    print(f"  Phase 2: Multi-turn refinement = {'ENABLED' if enable_refinement else 'DISABLED'}")
    print(f"  Phase 3: Coverage-guided = {'ENABLED' if enable_coverage_guided else 'DISABLED'}")
    print("\nMonitor at: http://localhost:8000\n")

    results = generator.generate_all()

    # Report results
    print(f"\n{'='*60}")
    print(f"Batch {batch_num} Complete!")
    print(f"{'='*60}")
    print(f"Modules processed: {results['completed']}/{results['total_modules']}")
    print(f"Tests generated: {results['tests_generated']}")
    print(f"Files created: {len(results['files_created'])}")
    print(f"Failed: {results['failed']}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python -m attune.workflows.autonomous_test_gen <batch_num> <modules_json> [--no-refinement] [--coverage-guided]"
        )
        print("\nOptions:")
        print("  --no-refinement     Disable Phase 2 multi-turn refinement")
        print("  --coverage-guided   Enable Phase 3 coverage-guided generation (slower)")
        sys.exit(1)

    batch_num = int(sys.argv[1])
    modules_json = sys.argv[2]

    # Parse optional flags
    enable_refinement = "--no-refinement" not in sys.argv
    enable_coverage_guided = "--coverage-guided" in sys.argv

    run_batch_generation(batch_num, modules_json, enable_refinement, enable_coverage_guided)
