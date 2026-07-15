"""EmpathyLLM Executor Implementation

Default LLMExecutor implementation that wraps EmpathyLLM for use
in workflows with automatic model routing and cost tracking.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any

from .executor import ExecutionContext, LLMResponse
from .registry import get_model
from .tasks import get_tier_for_task
from .telemetry import LLMCallRecord, TelemetryBackend, TelemetryStore

logger = logging.getLogger(__name__)


class EmpathyLLMExecutor:
    """Default executor wrapping EmpathyLLM with routing.

    This executor provides a unified interface for workflows to call LLMs
    with automatic tier-based model routing and cost tracking.

    Supports hybrid mode where different tiers use different providers.

    Example:
        >>> executor = EmpathyLLMExecutor(provider="anthropic")
        >>> response = await executor.run(
        ...     task_type="summarize",
        ...     prompt="Summarize this document...",
        ... )
        >>> print(f"Model used: {response.model_used}")
        >>> print(f"Cost: ${response.cost:.4f}")

    """

    def __init__(
        self,
        empathy_llm: Any | None = None,
        provider: str = "anthropic",
        api_key: str | None = None,
        telemetry_store: TelemetryBackend | TelemetryStore | None = None,
        use_thinking: bool = False,
        thinking_budget: int = 10000,
        **llm_kwargs: Any,
    ):
        """Initialize the EmpathyLLM executor.

        Args:
            empathy_llm: Optional pre-configured EmpathyLLM instance.
            provider: LLM provider (anthropic).
            api_key: Optional API key for the provider.
            telemetry_store: Optional telemetry store for recording calls.
            use_thinking: Enable extended thinking for complex analysis.
                Adds a thinking step before generating output.
            thinking_budget: Max tokens for thinking (default: 10000).
            **llm_kwargs: Additional arguments for EmpathyLLM.

        """
        self._provider = provider
        self._api_key = api_key
        # Thread thinking config through to the provider
        if use_thinking:
            llm_kwargs["use_thinking"] = True
            llm_kwargs["thinking_budget"] = thinking_budget
        self._llm_kwargs = llm_kwargs
        self._llm = empathy_llm
        self._telemetry = telemetry_store
        self._hybrid_llms: dict[str, Any] = {}  # Cache per-provider LLMs for hybrid mode
        self._hybrid_config: dict[str, str] | None = None  # tier -> model_id mapping

        # Load hybrid config if provider is hybrid
        if provider == "hybrid":
            self._load_hybrid_config()

    def _load_hybrid_config(self) -> None:
        """Load hybrid tier->model mapping from workflows.yaml."""
        try:
            from attune.workflows.config import WorkflowConfig

            config = WorkflowConfig.load()
            if config.custom_models and "hybrid" in config.custom_models:
                self._hybrid_config = config.custom_models["hybrid"]
                logger.info(f"Loaded hybrid config: {self._hybrid_config}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to load hybrid config: {e}")

    def _get_provider_for_model(self, model_id: str) -> str:
        """Determine which provider a model belongs to based on its ID."""
        model_lower = model_id.lower()
        if (
            "claude" in model_lower
            or "haiku" in model_lower
            or "sonnet" in model_lower
            or "opus" in model_lower
        ):
            return "anthropic"
        # Claude-native architecture (v5.0.0+): all models are Anthropic
        return "anthropic"

    def _get_llm_for_tier(self, tier: str) -> tuple[Any, str, str]:
        """Get the appropriate LLM for a tier (supports hybrid mode).

        Returns:
            Tuple of (llm_instance, actual_provider, model_id)

        """
        if self._provider != "hybrid" or not self._hybrid_config:
            # Non-hybrid mode: use single provider
            return self._get_llm(), self._provider, ""

        # Hybrid mode: determine provider based on tier's model
        model_id = self._hybrid_config.get(tier, "")
        if not model_id:
            # Fall back to non-hybrid
            return self._get_llm(), self._provider, ""

        actual_provider = self._get_provider_for_model(model_id)

        # Get or create LLM for this provider
        if actual_provider not in self._hybrid_llms:
            try:
                import os

                from attune.llm.core import EmpathyLLM

                # Get API key for this provider from environment
                api_key_map = {
                    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
                }
                api_key = api_key_map.get(actual_provider)

                kwargs = {
                    "provider": actual_provider,
                    "model": model_id,
                    "enable_model_routing": False,  # Use explicit model
                    **self._llm_kwargs,
                }
                if api_key:
                    kwargs["api_key"] = api_key

                self._hybrid_llms[actual_provider] = EmpathyLLM(**kwargs)
                logger.info(f"Created hybrid LLM for {actual_provider} with model {model_id}")
            except ImportError as e:
                raise ImportError("empathy_llm_toolkit is required for EmpathyLLMExecutor.") from e

        return self._hybrid_llms[actual_provider], actual_provider, model_id

    def _get_llm(self) -> Any:
        """Lazy initialization of EmpathyLLM."""
        if self._llm is None:
            try:
                from attune.llm.core import EmpathyLLM

                kwargs = {
                    "provider": self._provider,
                    "enable_model_routing": True,
                    **self._llm_kwargs,
                }
                if self._api_key:
                    kwargs["api_key"] = self._api_key

                self._llm = EmpathyLLM(**kwargs)
            except ImportError as e:
                raise ImportError(
                    "empathy_llm_toolkit is required for EmpathyLLMExecutor. "
                    "Install it or use MockLLMExecutor for testing.",
                ) from e
        return self._llm

    @staticmethod
    def _build_full_context(
        system: str | None, context: ExecutionContext | None, existing_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge system prompt, context fields, and metadata into one dict."""
        full_context: dict[str, Any] = existing_context
        if system:
            full_context["system_prompt"] = system
        if context:
            if context.workflow_name:
                full_context["workflow_name"] = context.workflow_name
            if context.step_name:
                full_context["step_name"] = context.step_name
            if context.session_id:
                full_context["session_id"] = context.session_id
            if context.metadata:
                full_context.update(context.metadata)
        return full_context

    @staticmethod
    def _compute_cost(model_info: Any, tokens_input: int, tokens_output: int) -> float:
        """Estimate USD cost from token counts; 0.0 when model_info is unknown."""
        if not model_info:
            return 0.0
        return (tokens_input / 1_000_000) * model_info.input_cost_per_million + (
            tokens_output / 1_000_000
        ) * model_info.output_cost_per_million

    def _record_call_telemetry(
        self,
        call_id: str,
        context: ExecutionContext | None,
        user_id: str,
        effective_task_type: str,
        provider: str,
        tier_str: str,
        model_id: str,
        tokens_input: int,
        tokens_output: int,
        cost_estimate: float,
        latency_ms: int,
    ) -> None:
        """Record telemetry for a completed call; failures are silent."""
        if not self._telemetry:
            return
        try:
            record = LLMCallRecord(
                call_id=call_id,
                timestamp=datetime.now().isoformat(),
                workflow_name=context.workflow_name if context else None,
                step_name=context.step_name if context else None,
                user_id=user_id,
                session_id=context.session_id if context else None,
                task_type=effective_task_type,
                provider=provider,
                tier=tier_str,
                model_id=model_id,
                input_tokens=tokens_input,
                output_tokens=tokens_output,
                estimated_cost=cost_estimate,
                latency_ms=latency_ms,
                success=True,
            )
            self._telemetry.log_call(record)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to record telemetry: %s", e)

    async def run(
        self,
        task_type: str,
        prompt: str,
        system: str | None = None,
        context: ExecutionContext | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute an LLM call with routing and cost tracking.

        Args:
            task_type: Type of task for routing (e.g., "summarize", "fix_bug").
            prompt: The user prompt to send.
            system: Optional system prompt (passed as context).
            context: Optional execution context for tracking.
            **kwargs: Additional arguments for EmpathyLLM.interact().

        Returns:
            LLMResponse with content, tokens, cost, and metadata.

        """
        start_time = time.time()
        call_id = str(uuid.uuid4())

        # Use task_type from context if provided
        effective_task_type = task_type
        if context and context.task_type:
            effective_task_type = context.task_type

        # Determine tier for this task
        tier = get_tier_for_task(effective_task_type)
        tier_str = tier.value if hasattr(tier, "value") else str(tier)

        # Get appropriate LLM (supports hybrid mode)
        llm, actual_provider, hybrid_model_id = self._get_llm_for_tier(tier_str)

        full_context = self._build_full_context(system, context, kwargs.pop("existing_context", {}))

        # Determine user_id
        user_id = context.user_id if context and context.user_id else "workflow"

        # Use actual provider (resolved for hybrid mode)
        provider = actual_provider

        # Call EmpathyLLM with task_type routing
        result = await llm.interact(
            user_id=user_id,
            user_input=prompt,
            context=full_context or None,
            task_type=effective_task_type,
            **kwargs,
        )

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Extract routing metadata
        metadata = result.get("metadata", {})

        # Get token counts
        tokens_input = metadata.get("tokens_used", 0)
        tokens_output = metadata.get("output_tokens", 0)

        # Get model info - use hybrid_model_id if set, otherwise look up
        model_info = get_model(provider, tier_str)
        model_id = hybrid_model_id or metadata.get("routed_model", metadata.get("model", ""))
        if not model_id and model_info:
            model_id = model_info.id

        cost_estimate = self._compute_cost(model_info, tokens_input, tokens_output)

        # Build response
        response = LLMResponse(
            content=result.get("content", ""),
            model_id=model_id,
            provider=provider,
            tier=tier_str,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_estimate=cost_estimate,
            latency_ms=latency_ms,
            metadata={
                "call_id": call_id,
                "level_used": result.get("level_used"),
                "level_description": result.get("level_description"),
                "proactive": result.get("proactive"),
                "task_type": effective_task_type,
                "model_routing_enabled": metadata.get("model_routing_enabled", False),
                "routed_tier": metadata.get("routed_tier"),
                **metadata,
            },
        )

        self._record_call_telemetry(
            call_id=call_id,
            context=context,
            user_id=user_id,
            effective_task_type=effective_task_type,
            provider=provider,
            tier_str=tier_str,
            model_id=model_id,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_estimate=cost_estimate,
            latency_ms=latency_ms,
        )

        return response

    def get_model_for_task(self, task_type: str) -> str:
        """Get the model that would be used for a task type.

        Args:
            task_type: Type of task to route

        Returns:
            Model identifier string

        """
        tier = get_tier_for_task(task_type)
        model_info = get_model(self._provider, tier.value)
        return model_info.id if model_info else ""

    def estimate_cost(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a task before execution.

        Args:
            task_type: Type of task
            input_tokens: Estimated input tokens
            output_tokens: Estimated output tokens

        Returns:
            Estimated cost in dollars

        """
        tier = get_tier_for_task(task_type)
        model_info = get_model(self._provider, tier.value)

        if not model_info:
            return 0.0

        return (input_tokens / 1_000_000) * model_info.input_cost_per_million + (
            output_tokens / 1_000_000
        ) * model_info.output_cost_per_million
