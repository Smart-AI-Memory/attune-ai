"""Autonomous Test Generation Refinement (Phase 2).

Iterative test generation with validation loop and multi-turn conversation.
Extracted from autonomous_test_gen.py for maintainability.

Contains:
- TestGenRefinementMixin: Pytest validation, LLM conversation, and refinement loop

Expected attributes on the host class:
    max_refinement_iterations: int
    _is_workflow_module: method (from TestGenPromptMixin)
    _get_workflow_specific_prompt: method (from TestGenPromptMixin)
    _get_example_tests: method (from TestGenPromptMixin)
    _generate_with_llm: method (from AutonomousTestGenerator)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from attune.config import _validate_file_path

logger = logging.getLogger(__name__)


class ValidationResult:
    """Re-export reference - actual class is in autonomous_test_gen.py."""

    pass


class TestGenRefinementMixin:
    """Mixin providing Phase 2 multi-turn refinement for test generation."""

    # Class-level defaults for expected attributes
    max_refinement_iterations: int = 3

    def _run_pytest_validation(self, test_file: Path) -> Any:
        """Run pytest on generated tests and collect failures.

        Args:
            test_file: Path to test file to validate

        Returns:
            ValidationResult with test outcomes and failure details
        """
        from .autonomous_test_gen import ValidationResult

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            passed = result.returncode == 0
            output = result.stdout + "\n" + result.stderr

            # Count errors
            error_count = output.count("FAILED") + output.count("ERROR")

            # Extract failure details
            failures = ""
            if not passed:
                # Extract relevant failure information
                lines = output.split("\n")
                failure_lines = []
                in_failure = False
                for line in lines:
                    if "FAILED" in line or "ERROR" in line:
                        in_failure = True
                    if in_failure:
                        failure_lines.append(line)
                        if line.startswith("="):  # End of failure section
                            in_failure = False
                failures = "\n".join(failure_lines[:100])  # Limit to 100 lines

            logger.info(f"Pytest validation: passed={passed}, errors={error_count}")

            return ValidationResult(
                passed=passed, failures=failures, error_count=error_count, output=output
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Pytest validation timeout for {test_file}")
            return ValidationResult(
                passed=False,
                failures="Validation timeout after 60 seconds",
                error_count=1,
                output="Timeout",
            )
        except Exception as e:
            logger.error(f"Pytest validation exception: {e}")
            return ValidationResult(
                passed=False, failures=f"Validation exception: {e}", error_count=1, output=str(e)
            )

    def _call_llm_with_history(
        self, conversation_history: list[dict[str, Any]], api_key: str
    ) -> str | None:
        """Call LLM with conversation history for refinement.

        Args:
            conversation_history: List of messages (role + content)
            api_key: Anthropic API key

        Returns:
            Refined test content or None if failed
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=40000,  # Very generous total budget for iterative refinement
                thinking={
                    "type": "enabled",
                    "budget_tokens": 20000,  # Generous thinking budget for thorough analysis
                },
                messages=conversation_history,
                timeout=900.0,  # 15 minutes timeout for refinement iterations
            )

            if not response.content:
                logger.warning("Empty LLM response during refinement")
                return None

            # Extract text content
            test_content = None
            for block in response.content:
                if block.type == "text":
                    test_content = block.text.strip()
                    break

            if not test_content:
                logger.warning("No text content in refinement response")
                return None

            # Clean up response
            if test_content.startswith("```python"):
                test_content = test_content[len("```python") :].strip()
            if test_content.endswith("```"):
                test_content = test_content[:-3].strip()

            return test_content

        except Exception as e:
            logger.error(f"LLM refinement error: {e}", exc_info=True)
            return None

    def _generate_with_refinement(
        self,
        module_name: str,
        module_path: str,
        source_file: Path,
        source_code: str,
        test_file: Path,
    ) -> str | None:
        """Generate tests with iterative refinement (Phase 2).

        Process:
        1. Generate initial tests
        2. Run pytest validation
        3. If failures, ask Claude to fix
        4. Repeat until tests pass or max iterations

        Args:
            module_name: Name of module being tested
            module_path: Python import path
            source_file: Path to source file
            source_code: Source code content
            test_file: Path where tests will be written

        Returns:
            Final test content or None if all attempts failed
        """
        import os

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not set")
            return None

        logger.info(
            f"🔄 Phase 2: Multi-turn refinement enabled for {module_name} (max {self.max_refinement_iterations} iterations)"
        )

        # Step 1: Generate initial tests
        test_content = self._generate_with_llm(module_name, module_path, source_file, source_code)
        if not test_content:
            logger.warning("Initial generation failed")
            return None

        # Build conversation history for subsequent refinements
        is_workflow = self._is_workflow_module(source_code, module_path)

        # Initial prompt (for history tracking)
        if is_workflow:
            initial_prompt = self._get_workflow_specific_prompt(
                module_name, module_path, source_code
            )
        else:
            initial_prompt = f"""Generate comprehensive behavioral tests for {module_name}.

SOURCE CODE:
```python
{source_code}
```"""

        conversation_history = [
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
                    {"type": "text", "text": initial_prompt},
                ],
            },
            {"role": "assistant", "content": test_content},
        ]

        # Step 2: Iterative refinement loop
        for iteration in range(self.max_refinement_iterations):
            logger.info(
                f"📝 Refinement iteration {iteration + 1}/{self.max_refinement_iterations} for {module_name}"
            )

            # Write current version to temp file
            temp_test_file = test_file.parent / f"_temp_{test_file.name}"
            validated_temp = _validate_file_path(str(temp_test_file))
            validated_temp.write_text(test_content)

            # Validate with pytest
            validation_result = self._run_pytest_validation(temp_test_file)

            if validation_result.passed:
                logger.info(f"✅ Tests passed on iteration {iteration + 1} for {module_name}")
                temp_test_file.unlink()  # Clean up
                return test_content

            # Tests failed - ask Claude to fix
            logger.warning(
                f"⚠️  Tests failed on iteration {iteration + 1}: {validation_result.error_count} errors"
            )

            refinement_prompt = f"""The tests you generated have failures. Please fix these specific issues:

FAILURES:
{validation_result.failures[:2000]}

Requirements:
1. Fix ONLY the failing tests - don't rewrite everything
2. Ensure imports are correct
3. Ensure mocking is properly configured
4. Return the COMPLETE corrected test file (not just the fixes)
5. Keep the same structure and copyright header

Return ONLY the complete Python test file, no explanations."""

            # Add to conversation history
            conversation_history.append({"role": "user", "content": refinement_prompt})

            # Call LLM for refinement
            refined_content = self._call_llm_with_history(conversation_history, api_key)

            if not refined_content:
                logger.error(f"❌ Refinement failed on iteration {iteration + 1}")
                temp_test_file.unlink()
                break

            # Update content and history
            test_content = refined_content
            conversation_history.append({"role": "assistant", "content": test_content})

            logger.info(f"🔄 Refinement iteration {iteration + 1} complete, retrying validation...")

        # Max iterations reached
        logger.warning(
            f"⚠️  Max refinement iterations reached for {module_name} - returning best attempt"
        )
        return test_content
