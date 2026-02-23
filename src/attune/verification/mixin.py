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

    def _run_verification_loop(
        self,
        workflow_result: WorkflowResult,
        kwargs: dict[str, Any],
    ) -> tuple[WorkflowResult, VerificationResult | None]:
        """Run verification with retry loop.

        Executes the configured verification strategy after the
        workflow completes. On failure, retries up to max_retries
        times (P0: retries re-run verification only, not stages).

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
                    logger.info(
                        "Verification failed (attempt %d/%d), retrying...",
                        attempt,
                        max_attempts,
                    )

            # Attach result to WorkflowResult metadata
            if last_result is not None:
                workflow_result.metadata["verification"] = {
                    "passed": last_result.passed,
                    "strategy": last_result.strategy,
                    "command": last_result.command,
                    "attempts": last_result.attempt,
                    "duration_ms": last_result.duration_ms,
                    "exit_code": last_result.exit_code,
                }

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


__all__ = ["VerificationMixin"]
