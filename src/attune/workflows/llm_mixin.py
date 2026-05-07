"""LLM Calling Mixin for BaseWorkflow.

Extracted from BaseWorkflow to improve maintainability.
Provides LLM invocation, output validation, and complexity assessment.

Expected attributes on the host class:
    name (str): Workflow name
    stages (list[str]): Stage names
    provider (ModelProvider): Model provider enum
    _config (WorkflowConfig | None): Workflow configuration
    _provider_str (str): Provider string identifier
    cost_tracker (CostTracker): Cost tracker instance
    get_tier_for_stage(stage_name): Returns tier for a stage
    run_step_with_executor(step, prompt, system): Executes LLM step (from ExecutorMixin)
    _try_cache_lookup(...): Cache lookup (from CachingMixin)
    _store_in_cache(...): Cache store (from CachingMixin)
    _get_cache_type(): Get cache type string (from CachingMixin)
    _calculate_cost(tier, in_tokens, out_tokens): Cost calc (from CostTrackingMixin)
    _track_telemetry(...): Telemetry tracking (from TelemetryMixin)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from .validation import (
    InputSchema,
    StageContract,
    WorkflowValidationError,
    validate_against_contract,
    validate_against_input_schema,
)

if TYPE_CHECKING:
    from .compat import ModelTier

logger = logging.getLogger(__name__)


class LLMMixin:
    """Mixin providing LLM calling, output validation, and complexity assessment."""

    # Expected attributes (set by BaseWorkflow.__init__)
    name: str
    stages: list[str]

    # Validation schemas (override in subclasses to enable)
    input_schema: InputSchema | None = None
    stage_contracts: dict[str, StageContract] = {}  # noqa: RUF012

    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Get the model for a tier based on configured provider and config."""
        from .config import get_model

        provider_str = getattr(self, "_provider_str", self.provider.value)

        # Use config-aware model lookup
        model = get_model(provider_str, tier.value, self._config)
        return model

    async def _call_llm(
        self,
        tier: ModelTier,
        system: str,
        user_message: str,
        max_tokens: int = 4096,
        stage_name: str | None = None,
    ) -> tuple[str, int, int]:
        """Provider-agnostic LLM call using the configured provider.

        This method uses run_step_with_executor internally to make LLM calls
        that respect the configured provider (anthropic, openai, google, etc.).

        Supports automatic caching to reduce API costs and latency.
        Tracks telemetry for usage analysis and cost savings measurement.

        Args:
            tier: Model tier to use (CHEAP, CAPABLE, PREMIUM)
            system: System prompt
            user_message: User message/prompt
            max_tokens: Maximum tokens in response
            stage_name: Optional stage name for cache key (defaults to tier)

        Returns:
            Tuple of (response_content, input_tokens, output_tokens)

        """
        from .caching import CachedResponse
        from .step_config import WorkflowStepConfig

        # Start timing for telemetry
        start_time = time.time()

        # Determine stage name for cache key
        stage = stage_name or f"llm_call_{tier.value}"
        model = self.get_model_for_tier(tier)
        cache_type = None

        # Try cache lookup using CachingMixin
        cached = self._try_cache_lookup(stage, system, user_message, model)
        if cached is not None:
            # Track telemetry for cache hit
            duration_ms = int((time.time() - start_time) * 1000)
            cost = self._calculate_cost(tier, cached.input_tokens, cached.output_tokens)
            cache_type = self._get_cache_type()

            self._track_telemetry(
                stage=stage,
                tier=tier,
                model=model,
                cost=cost,
                tokens={"input": cached.input_tokens, "output": cached.output_tokens},
                cache_hit=True,
                cache_type=cache_type,
                duration_ms=duration_ms,
            )

            return (cached.content, cached.input_tokens, cached.output_tokens)

        # Create a step config for this call
        step = WorkflowStepConfig(
            name=stage,
            task_type="general",
            tier_hint=tier.value,
            description="LLM call",
            max_tokens=max_tokens,
        )

        try:
            result = await self.run_step_with_executor(
                step=step,
                prompt=user_message,
                system=system,
            )
            content = result.content
            in_tokens = result.input_tokens
            out_tokens = result.output_tokens
            cost = result.cost

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Track telemetry for actual LLM call
            self._track_telemetry(
                stage=stage,
                tier=tier,
                model=model,
                cost=cost,
                tokens={"input": in_tokens, "output": out_tokens},
                cache_hit=False,
                cache_type=None,
                duration_ms=duration_ms,
                prompt_cache_creation_tokens=result.cache_creation_tokens,
                prompt_cache_read_tokens=result.cache_read_tokens,
            )

            # Store in cache using CachingMixin
            self._store_in_cache(
                stage,
                system,
                user_message,
                model,
                CachedResponse(content=content, input_tokens=in_tokens, output_tokens=out_tokens),
            )

            return content, in_tokens, out_tokens
        except (ValueError, TypeError, KeyError) as e:
            # Invalid input or configuration errors
            logger.warning("LLM call failed (invalid input): %s", e)
            return f"Error calling LLM (invalid input): {e}", 0, 0
        except (TimeoutError, RuntimeError, ConnectionError) as e:
            # Timeout, API errors, or connection failures
            logger.warning("LLM call failed (timeout/API/connection error): %s", e)
            return f"Error calling LLM (timeout/API error): {e}", 0, 0
        except (OSError, PermissionError) as e:
            # File system or permission errors
            logger.warning("LLM call failed (file system error): %s", e)
            return f"Error calling LLM (file system error): {e}", 0, 0
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation - return error message rather than crashing workflow
            logger.exception("Unexpected error calling LLM: %s", e)
            return f"Error calling LLM: {type(e).__name__}", 0, 0

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Determine if a stage should be skipped.

        Override in subclasses for conditional stage execution.

        Args:
            stage_name: Name of the stage
            input_data: Current workflow data

        Returns:
            Tuple of (should_skip, reason)

        """
        return False, None

    def validate_output(self, stage_output: dict) -> tuple[bool, str | None]:
        """Validate stage output quality for tier fallback decisions.

        This is called after each stage execution when tier fallback is enabled.
        Override in subclasses to add workflow-specific validation logic.

        Default implementation checks:
        - No exceptions during execution (execution_succeeded)
        - Output is not empty (output_valid)
        - Required keys present if defined in stage config

        Args:
            stage_output: Output dict from run_stage()

        Returns:
            Tuple of (is_valid, failure_reason)
            - is_valid: True if output passes quality gates
            - failure_reason: Error code if validation failed (e.g., "output_empty",
              "health_score_low", "tests_failed")

        Example:
            >>> def validate_output(self, stage_output):
            ...     # Check health score for health-check workflow
            ...     health_score = stage_output.get("health_score", 0)
            ...     if health_score < 80:
            ...         return False, "health_score_low"
            ...     return True, None

        """
        # Default validation: check output is not empty
        if not stage_output:
            return False, "output_empty"

        # Check for error indicators in output
        if stage_output.get("error") is not None:
            return False, "execution_error"

        # Output is valid by default
        return True, None

    def validate_input(self, kwargs: dict[str, Any]) -> None:
        """Validate workflow input against input_schema.

        Called at the top of execute() before any stage runs.
        Raises WorkflowValidationError if required fields are
        missing or have wrong types.

        Args:
            kwargs: The input keyword arguments to validate.

        Raises:
            WorkflowValidationError: If validation fails.
        """
        if self.input_schema is None:
            return
        errors = validate_against_input_schema(kwargs, self.input_schema)
        if errors:
            raise WorkflowValidationError(
                workflow_name=self.name,
                stage="input",
                errors=errors,
            )

    def validate_contract(self, stage_name: str, stage_output: dict[str, Any]) -> None:
        """Validate stage output against its declared contract.

        Called after validate_output() succeeds. Checks that the
        stage output contains all required keys with correct types.

        Args:
            stage_name: Name of the stage that produced the output.
            stage_output: The output dict from run_stage().

        Raises:
            WorkflowValidationError: If contract validation fails.
        """
        contract = self.stage_contracts.get(stage_name)
        if contract is None:
            return
        errors = validate_against_contract(stage_output, contract)
        if errors:
            raise WorkflowValidationError(
                workflow_name=self.name,
                stage=stage_name,
                errors=errors,
            )

    def _assess_complexity(self, input_data: dict[str, Any]) -> str:
        """Assess task complexity based on workflow stages and input.

        Args:
            input_data: Workflow input data

        Returns:
            Complexity level: "simple", "moderate", or "complex"

        """
        from .compat import ModelTier

        # Simple heuristic: based on number of stages and tier requirements
        num_stages = len(self.stages)
        premium_stages = sum(
            1 for s in self.stages if self.get_tier_for_stage(s) == ModelTier.PREMIUM
        )

        if num_stages <= 2 and premium_stages == 0:
            return "simple"
        if num_stages <= 4 and premium_stages <= 1:
            return "moderate"
        return "complex"
