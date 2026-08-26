"""LLM Executor Mixin for BaseWorkflow.

Extracted from BaseWorkflow to improve maintainability.
Provides LLMExecutor integration for workflow step execution.

Expected attributes on the host class:
    name (str): Workflow name
    _run_id (str): Current run ID
    _provider_str (str): Provider string
    _api_key (str | None): API key
    _telemetry_backend (TelemetryBackend | None): Telemetry backend
    _enable_tier_fallback (bool): Whether tier fallback is enabled
    _executor (LLMExecutor | None): Optional pre-configured executor
    _emit_call_telemetry(...): Telemetry emission method (from TelemetryMixin)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from attune.models import (
    ExecutionContext,
    LLMExecutor,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StepResult:
    """Result of a single workflow step execution.

    Replaces the old 4-tuple return so cache-token telemetry can flow
    through to ``UsageTracker.track_llm_call`` without further signature
    growth. Anthropic prompt-cache fields are zero when the underlying
    provider didn't report them (non-Anthropic providers, older SDKs).
    """

    content: str
    input_tokens: int
    output_tokens: int
    cost: float
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def prompt_cache_hit(self) -> bool:
        return self.cache_read_tokens > 0


if TYPE_CHECKING:
    from .step_config import WorkflowStepConfig


def _load_hybrid_tier_models() -> dict[str, str] | None:
    """Read the hybrid tier -> model_id mapping from ``workflows.yaml``.

    Owns the config read on behalf of the models layer, which must not
    import ``attune.workflows.config`` (#2239 Edge 1). Returns ``None``
    when the mapping is absent or unreadable — hybrid routing then falls
    back to the single configured provider, preserving the behavior the
    executor had while it read the config itself.
    """
    try:
        from attune.workflows.config import WorkflowConfig

        config = WorkflowConfig.load()
        if config.custom_models and "hybrid" in config.custom_models:
            return config.custom_models["hybrid"]
    except Exception as e:  # noqa: BLE001 - config read is best-effort
        logger.warning(f"Failed to load hybrid config: {e}")
    return None


class ExecutorMixin:
    """Mixin providing LLMExecutor integration methods."""

    # Expected attributes (set by BaseWorkflow.__init__)
    name: str
    _run_id: str
    _provider_str: str
    _api_key: str | None
    _telemetry_backend: Any  # TelemetryBackend | None
    _enable_tier_fallback: bool
    _executor: LLMExecutor | None

    def _create_execution_context(
        self,
        step_name: str,
        task_type: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionContext:
        """Create an ExecutionContext for a step execution.

        Args:
            step_name: Name of the workflow step
            task_type: Task type for routing
            user_id: Optional user ID
            session_id: Optional session ID

        Returns:
            ExecutionContext populated with workflow info

        """
        return ExecutionContext(
            workflow_name=self.name,
            step_name=step_name,
            user_id=user_id,
            session_id=session_id,
            metadata={
                "task_type": task_type,
                "run_id": self._run_id,
                "provider": self._provider_str,
            },
        )

    def _create_default_executor(self) -> LLMExecutor:
        """Create a default EmpathyLLMExecutor with optional resilience wrapper.

        This method is called lazily when run_step_with_executor is used
        without a pre-configured executor.

        When tier fallback is enabled (enable_tier_fallback=True), the base
        executor is returned without the ResilientExecutor wrapper to avoid
        double fallback (tier-level + LLM-level).

        When tier fallback is disabled (default), the executor is wrapped with
        resilience features (retry, fallback, circuit breaker).

        Returns:
            LLMExecutor instance (optionally wrapped with ResilientExecutor)

        """
        from attune.models.empathy_executor import EmpathyLLMExecutor
        from attune.models.fallback import ResilientExecutor

        # Create the base executor
        executor_kwargs: dict[str, Any] = {
            "provider": self._provider_str,
            "api_key": self._api_key,
            "telemetry_store": self._telemetry_backend,
        }

        # Enable extended thinking if the workflow opts in
        if getattr(self, "_use_thinking", False):
            executor_kwargs["use_thinking"] = True
            executor_kwargs["thinking_budget"] = getattr(self, "_thinking_budget", 10000)

        # Hybrid mode routes each tier to a different model. The workflows
        # layer owns the workflows.yaml read and injects the resolved
        # mapping; the models layer never imports the config type (#2239
        # Edge 1 / models-workflows-layering R1).
        if self._provider_str == "hybrid":
            executor_kwargs["hybrid_config"] = _load_hybrid_tier_models()

        base_executor = EmpathyLLMExecutor(**executor_kwargs)

        # When tier fallback is enabled, skip LLM-level fallback
        # to avoid double fallback (tier-level + LLM-level)
        if self._enable_tier_fallback:
            return base_executor

        # Standard mode: wrap with resilience layer (retry, fallback, circuit breaker)
        return ResilientExecutor(executor=base_executor)

    def _get_executor(self) -> LLMExecutor:
        """Get or create the LLM executor.

        Returns the configured executor or creates a default one.

        Returns:
            LLMExecutor instance

        """
        if self._executor is None:
            self._executor = self._create_default_executor()
        return self._executor

    # Note: _emit_call_telemetry and _emit_workflow_telemetry are inherited from TelemetryMixin

    async def run_step_with_executor(
        self,
        step: WorkflowStepConfig,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> StepResult:
        """Run a workflow step using the LLMExecutor.

        This method provides a unified interface for executing steps with
        automatic routing, telemetry, and cost tracking. If no executor
        was provided at construction, a default EmpathyLLMExecutor is created.

        Args:
            step: WorkflowStepConfig defining the step
            prompt: The prompt to send
            system: Optional system prompt
            **kwargs: Additional arguments passed to executor

        Returns:
            StepResult with content, token counts, cost, and Anthropic
            prompt-cache stats. Cache fields are zero when the underlying
            provider didn't report them.
        """
        executor = self._get_executor()

        context = self._create_execution_context(
            step_name=step.name,
            task_type=step.task_type,
        )

        start_time = datetime.now()
        response = await executor.run(
            task_type=step.task_type,
            prompt=prompt,
            system=system,
            context=context,
            **kwargs,
        )
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        # Pull Anthropic prompt-cache stats out of the response metadata.
        # AnthropicProvider stamps these onto LLMResponse.metadata when the
        # SDK response carries cache_creation_input_tokens / cache_read_input_tokens.
        # Other providers (or older SDKs) leave the keys absent, in which
        # case we record zeros — JSONL stays clean either way.
        meta = response.metadata or {}
        cache_creation = int(meta.get("cache_creation_tokens", 0) or 0)
        cache_read = int(meta.get("cache_read_tokens", 0) or 0)

        # Emit telemetry
        self._emit_call_telemetry(
            step_name=step.name,
            task_type=step.task_type,
            tier=response.tier,
            model_id=response.model_id,
            input_tokens=response.tokens_input,
            output_tokens=response.tokens_output,
            cost=response.cost_estimate,
            latency_ms=latency_ms,
            success=True,
        )

        return StepResult(
            content=response.content,
            input_tokens=response.tokens_input,
            output_tokens=response.tokens_output,
            cost=response.cost_estimate,
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
        )
