"""Verification mixin for BaseWorkflow.

Provides post-execution verification loops that run real tools
(pytest, ruff, mypy, etc.) to verify workflow output. Follows
the same pattern as StatePersistenceMixin: no-ops when disabled,
never crashes the workflow, best-effort semantics.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .data_classes import WorkflowResult

from ..verification import VerificationResult
from ..verification.config import VerificationConfig
from ..verification.defaults import get_default_strategy
from ..verification.runner import run_verification
from ..verification.strategies import get_strategy

logger = logging.getLogger(__name__)


class VerificationMixin:
    """Mixin providing post-execution verification loops.

    Silently no-ops when verification is disabled or unconfigured.
    All methods are wrapped in try/except so verification never
    crashes the host workflow.

    Expected attributes on the host class:
        name (str): Workflow name
        _config (WorkflowConfig | None): Workflow configuration

    """

    _verification_config: VerificationConfig | None = None

    def _init_verification(self) -> None:
        """Load verification config from WorkflowConfig.

        Called from BaseWorkflow.__init__. Loads the verification
        section from the workflow config and resolves per-workflow
        overrides.
        """
        try:
            config = getattr(self, "_config", None)
            if config is None:
                self._verification_config = None
                return

            verification_data = getattr(config, "verification", None)
            if verification_data is None:
                self._verification_config = None
                return

            workflow_name = getattr(self, "name", "unknown")
            self._verification_config = VerificationConfig.load_for_workflow(
                workflow_name, verification_data
            )
        except Exception as e:
            # INTENTIONAL: Verification init is optional, never crash
            logger.debug("Verification init failed: %s", e)
            self._verification_config = None

    def _resolve_strategy_instance(self) -> Any:
        """Resolve the verification strategy for this workflow.

        Returns:
            VerificationStrategy instance, or None if strategy is "none".

        """
        if self._verification_config is None:
            return None

        strategy_name = self._verification_config.strategy
        custom_command = self._verification_config.command

        # "auto" -> look up default for this workflow
        if strategy_name == "auto":
            workflow_name = getattr(self, "name", "unknown")
            strategy_name = get_default_strategy(workflow_name)

        if strategy_name == "none":
            return None

        return get_strategy(strategy_name, custom_command)

    async def _run_verification_loop(
        self,
        workflow_result: WorkflowResult,
        kwargs: dict[str, Any],
    ) -> tuple[WorkflowResult, VerificationResult | None]:
        """Run verification with retry and optional LLM correction loop.

        Executes the configured verification strategy after the
        workflow completes. On failure, optionally feeds errors back
        to the LLM for self-correction (Boris's 2-3x quality
        principle), then re-verifies.

        When correction_enabled is False (default), behaves exactly
        as before: retries re-run verification only.

        Args:
            workflow_result: The completed WorkflowResult.
            kwargs: Original workflow kwargs.

        Returns:
            Tuple of (possibly-updated WorkflowResult,
            VerificationResult or None).

        """
        if self._verification_config is None or not self._verification_config.enabled:
            return workflow_result, None

        try:
            strategy = self._resolve_strategy_instance()
            if strategy is None:
                return workflow_result, None

            last_result: VerificationResult | None = None
            max_attempts = self._verification_config.max_retries + 1
            total_correction_cost = 0.0
            corrections_made = 0

            for attempt in range(1, max_attempts + 1):
                last_result = run_verification(
                    config=self._verification_config,
                    strategy=strategy,
                    workflow_name=getattr(self, "name", "unknown"),
                    workflow_result=workflow_result,
                    attempt=attempt,
                )

                if last_result.passed:
                    logger.info(
                        "Verification passed on attempt %d/%d: %s",
                        attempt,
                        max_attempts,
                        last_result.strategy,
                    )
                    break

                if attempt < max_attempts:
                    # Attempt LLM correction if enabled
                    if (
                        self._verification_config.correction_enabled
                        and corrections_made < self._verification_config.max_corrections
                    ):
                        corrected, cost = await self._request_correction(
                            workflow_result,
                            last_result,
                            corrections_made + 1,
                        )
                        if corrected is not None:
                            workflow_result.final_output = corrected
                            total_correction_cost += cost
                            corrections_made += 1
                            logger.info(
                                "Correction applied (attempt %d/%d), " "re-verifying...",
                                corrections_made,
                                self._verification_config.max_corrections,
                            )
                        else:
                            logger.info(
                                "Verification failed (attempt %d/%d), "
                                "correction unavailable, retrying...",
                                attempt,
                                max_attempts,
                            )
                    else:
                        logger.info(
                            "Verification failed (attempt %d/%d), " "retrying...",
                            attempt,
                            max_attempts,
                        )

            # Attach correction cost to last result
            if last_result is not None:
                last_result.correction_attempt = corrections_made
                last_result.correction_cost = total_correction_cost

            # Attach result to WorkflowResult metadata
            if last_result is not None:
                verification_meta: dict[str, Any] = {
                    "passed": last_result.passed,
                    "strategy": last_result.strategy,
                    "command": last_result.command,
                    "attempts": last_result.attempt,
                    "duration_ms": last_result.duration_ms,
                    "exit_code": last_result.exit_code,
                }
                if corrections_made > 0:
                    verification_meta["corrections"] = corrections_made
                    verification_meta["correction_cost"] = total_correction_cost
                workflow_result.metadata["verification"] = verification_meta

                # Failed verification marks workflow as failed
                # (unless fail_open is True)
                if not last_result.passed and not self._verification_config.fail_open:
                    workflow_result.success = False
                    workflow_result.error = (
                        f"Verification failed after "
                        f"{last_result.attempt} attempt(s): "
                        f"{last_result.strategy} exited with "
                        f"code {last_result.exit_code}"
                    )
                    workflow_result.error_type = "verification"

            return workflow_result, last_result

        except Exception as e:
            # INTENTIONAL: Verification is best-effort, never crash
            logger.exception("Verification loop error: %s", e)
            return workflow_result, None

    async def _request_correction(
        self,
        workflow_result: Any,
        verification_result: VerificationResult,
        attempt: int,
    ) -> tuple[str | None, float]:
        """Request LLM correction based on verification errors.

        Feeds the verification stderr/stdout back to the LLM so it
        can suggest corrections to the workflow output. This is the
        core of Boris's "verify AND self-correct" feedback loop.

        Args:
            workflow_result: The current WorkflowResult.
            verification_result: The failed verification result.
            attempt: Which correction attempt this is (1-based).

        Returns:
            Tuple of (corrected_output or None, cost).

        """
        try:
            from attune.workflows.compat import ModelTier

            # Build error context from verification output
            error_output = ""
            if verification_result.stderr:
                error_output += f"STDERR:\n{verification_result.stderr}\n"
            if verification_result.stdout:
                error_output += f"STDOUT:\n{verification_result.stdout}\n"

            if not error_output.strip():
                logger.debug("No verification output to feed back")
                return None, 0.0

            current_output = getattr(workflow_result, "final_output", None) or ""
            workflow_name = getattr(self, "name", "unknown")

            system_prompt = (
                f"You are correcting output from the '{workflow_name}' workflow. "
                f"The verification step ({verification_result.strategy}) failed "
                f"with exit code {verification_result.exit_code}. "
                f"Analyze the error output and provide a corrected version of "
                f"the workflow output that addresses the issues found. "
                f"Return ONLY the corrected output, no explanations."
            )

            user_message = (
                f"## Verification Errors (attempt {attempt})\n\n"
                f"Command: `{verification_result.command}`\n\n"
                f"```\n{error_output}```\n\n"
                f"## Current Workflow Output\n\n"
                f"```\n{current_output[:8000]}```\n\n"
                f"Please provide the corrected output."
            )

            content, in_tokens, out_tokens = await self._call_llm(
                tier=ModelTier.CAPABLE,
                system=system_prompt,
                user_message=user_message,
                max_tokens=8192,
                stage_name=f"verification_correction_{attempt}",
            )

            # Calculate cost for this correction call
            cost = self._calculate_cost(ModelTier.CAPABLE, in_tokens, out_tokens)

            # Check for error responses from _call_llm
            if content.startswith("Error calling LLM"):
                logger.warning("Correction LLM call failed: %s", content)
                return None, 0.0

            logger.info(
                "Correction generated (attempt %d, %d tokens)",
                attempt,
                out_tokens,
            )
            return content, cost

        except Exception as e:
            # INTENTIONAL: Correction is best-effort, never crash
            logger.warning("Correction request failed: %s", e)
            return None, 0.0


__all__ = ["VerificationMixin"]
