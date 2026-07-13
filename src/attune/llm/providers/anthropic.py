"""Anthropic (Claude) provider with enhanced features.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
import os
import re
from collections.abc import AsyncGenerator
from typing import Any

from ..fable_call import acreate_with_fable
from .base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)

# Opus 4.7 and later reject temperature/top_p/top_k and the
# enabled-thinking shape (HTTP 400). Matches opus-4-7, opus-4-8, and any
# future opus-4-9 / opus-4-1x. Older models (Opus 4.6-, Sonnet, Haiku)
# still accept these params, so they're left untouched.
_OPUS_NO_SAMPLING_RE = re.compile(r"opus-4-(?:[7-9]|\d{2,})")

# Fable models reject explicit sampling params AND any explicit thinking
# config (adaptive-by-default; even {"type": "disabled"} is a 400).
# Matches attune.model_tiers.fable_extras' model detection.
_FABLE_PREFIX = "claude-fable"


def _cache_control() -> dict[str, str]:
    """Resolve the ephemeral ``cache_control`` marker from the environment.

    ``ATTUNE_CACHE_TTL=1h`` extends the prompt-cache window from the
    5-minute default to 1 hour at the same per-token rate — useful for
    dashboards and benchmark sweeps that issue clusters of related queries
    within an hour. Any other value (including unset or ``5m``) yields the
    default 5-minute ephemeral marker, byte-identical to the prior behavior.

    Read per-call (not cached in a module global) so tests can flip it via
    ``monkeypatch.setenv``; the cost is one ``os.getenv`` on an
    already-networked path.

    Mirrors ``attune_rag.providers.claude._cache_control`` (env var
    ``ATTUNE_RAG_CACHE_TTL``); see specs/extended-cache-ttl-siblings/.
    """
    if os.getenv("ATTUNE_CACHE_TTL", "5m").strip().lower() == "1h":
        return {"type": "ephemeral", "ttl": "1h"}
    return {"type": "ephemeral"}


def _normalize_api_kwargs_for_model(api_kwargs: dict[str, Any]) -> None:
    """Drop request params that newer Claude models reject (in place).

    This provider defaults ``temperature=0.7`` and can set extended
    thinking, both of which Opus 4.7+ reject with a 400 — so without this,
    any premium-tier call through this path would fail. Strip the sampling
    params and convert ``enabled`` thinking to ``adaptive`` for those
    models; leave older models that still accept them untouched.

    Fable models (``claude-fable-*``) go further: they reject ANY explicit
    ``thinking`` config (adaptive-by-default — even ``{"type": "disabled"}``
    is a 400), so both the sampling params and the whole thinking key are
    stripped, each with a logged warning (design §4a: strip + warn, don't
    raise).
    """
    model = api_kwargs.get("model", "")
    if model.startswith(_FABLE_PREFIX):
        for param in ("temperature", "top_p", "top_k"):
            if api_kwargs.pop(param, None) is not None:
                logger.warning(
                    "Dropped %s for %s — fable models reject explicit sampling params",
                    param,
                    model,
                )
        if api_kwargs.pop("thinking", None) is not None:
            logger.warning(
                "Dropped explicit thinking config for %s — fable is "
                "adaptive-by-default and rejects thinking overrides",
                model,
            )
        return
    if not _OPUS_NO_SAMPLING_RE.search(model):
        return
    for param in ("temperature", "top_p", "top_k"):
        api_kwargs.pop(param, None)
    thinking = api_kwargs.get("thinking")
    if isinstance(thinking, dict) and thinking.get("type") == "enabled":
        api_kwargs["thinking"] = {"type": "adaptive"}


class AnthropicProvider(BaseLLMProvider):
    """Anthropic (Claude) provider with enhanced features.

    Supports Claude 4.5/4.6 family models with advanced capabilities:
    - Extended context windows (200K tokens)
    - Prompt caching for faster repeated queries
    - Extended thinking for complex reasoning
    - Streaming for real-time output
    - Batch processing for cost optimization
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-5",
        use_prompt_caching: bool = False,  # Deprecated
        use_thinking: bool = False,  # Deprecated
        thinking_budget: int = 10000,
        use_batch: bool = False,
        **kwargs,
    ):
        """Initialize the Anthropic LLM provider.

        Args:
            api_key: Anthropic API key (falls back to env var).
            model: Model identifier to use.
            use_prompt_caching: (DEPRECATED) This feature is deprecated and will be removed.
            use_thinking: (DEPRECATED) This feature is deprecated and will be removed.
            thinking_budget: Max tokens for thinking budget.
            use_batch: Enable batch processing mode.
            **kwargs: Additional provider configuration.
        """
        super().__init__(api_key, **kwargs)
        self.model = model
        self.use_prompt_caching = use_prompt_caching
        self.use_thinking = use_thinking
        self.thinking_budget = thinking_budget
        self.use_batch = use_batch

        if use_prompt_caching:
            logger.warning(
                "The 'use_prompt_caching' feature is deprecated and may cause "
                "API errors. It will be removed in a future version."
            )

        if use_thinking:
            logger.warning(
                "The 'use_thinking' feature is deprecated and may cause "
                "API errors. It will be removed in a future version."
            )

        # Validate API key is provided
        if not api_key or not api_key.strip():
            raise ValueError(
                "API key is required for Anthropic provider. "
                "Provide via api_key parameter or ANTHROPIC_API_KEY environment variable",
            )

        # Warn if API key doesn't match expected format
        if api_key and not api_key.startswith("sk-ant-"):
            logger.warning(
                "API key does not start with 'sk-ant-'. "
                "Anthropic API keys typically start with 'sk-ant-api03-'. "
                "Verify you are using a valid Anthropic API key.",
            )

        # Lazy import to avoid requiring anthropic if not used
        # v4.6.3: Use AsyncAnthropic for true async I/O (prevents event loop blocking)
        try:
            import anthropic

            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError as e:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic",
            ) from e

        # Initialize batch provider if needed
        if use_batch:
            from .anthropic_batch import AnthropicBatchProvider

            self.batch_provider = AnthropicBatchProvider(api_key=api_key)
        else:
            self.batch_provider = None

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> LLMResponse:
        """Generate response using Anthropic API with enhanced features.

        Claude-specific enhancements:
        - Prompt caching for repeated system prompts (90% cost reduction)
        - Extended context (200K tokens) for large codebase analysis
        - Thinking mode for complex reasoning tasks

        Prompt caching is enabled by default (use_prompt_caching=True).
        This marks system prompts with cache_control for Anthropic's cache.
        Break-even: ~3 requests with same context, 5-minute TTL.
        """
        # Build kwargs for Anthropic
        api_kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        # Enable prompt caching for system prompts (Claude-specific)
        if system_prompt and self.use_prompt_caching:
            api_kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": _cache_control(),
                },
            ]
        elif system_prompt:
            api_kwargs["system"] = system_prompt

        # Enable extended thinking for complex tasks (Claude-specific)
        if self.use_thinking:
            # The API requires max_tokens > thinking.budget_tokens (thinking
            # output counts toward max_tokens) and temperature=1 — otherwise
            # the request fails with HTTP 400. Grow max_tokens so the answer
            # keeps its requested room; never shrink the caller's budget.
            if api_kwargs["max_tokens"] <= self.thinking_budget:
                api_kwargs["max_tokens"] = self.thinking_budget + max_tokens
            api_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            }
            api_kwargs["temperature"] = 1.0

        # Add any additional kwargs
        api_kwargs.update(kwargs)

        # Drop params newer models (Opus 4.7+) reject — must run AFTER the
        # kwargs merge so a caller-supplied temperature is also stripped.
        _normalize_api_kwargs_for_model(api_kwargs)

        # Call Anthropic API (async with AsyncAnthropic) with typed error
        # handling. Fable models route through the beta namespace with the
        # server-side fallback opt-in, surface refusals as
        # ModelRefusalError, and re-raise a 400 with the retention hint —
        # all inside acreate_with_fable; non-fable models take the exact
        # pre-tier code path (plain messages.create, byte-identical).
        try:
            import anthropic

            response = await acreate_with_fable(self.client, **api_kwargs)  # type: ignore[call-overload]
        except anthropic.RateLimitError as e:
            logger.warning(f"Rate limited by Anthropic API: {e}")
            raise
        except anthropic.APIConnectionError as e:
            logger.error(f"Connection error to Anthropic API: {e}")
            raise
        except anthropic.APITimeoutError as e:
            logger.error(f"Anthropic API request timed out: {e}")
            raise
        except anthropic.AuthenticationError as e:
            logger.error(f"Anthropic API authentication failed: {e}")
            raise
        except anthropic.APIStatusError as e:
            logger.error(
                f"Anthropic API error (status {e.status_code}): {e.response.text}",
            )
            raise

        # Extract thinking content and text from response blocks
        thinking_content = None
        response_content = ""
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "thinking":
                thinking_content = block.thinking
            elif block_type == "text" or block_type is None:
                response_content += block.text

        metadata = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "provider": "anthropic",
            "model": self.model,
        }

        self._add_cache_metrics(metadata, response.usage)

        if thinking_content:
            metadata["thinking"] = thinking_content

        return LLMResponse(
            content=response_content,
            model=response.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            finish_reason=response.stop_reason,
            metadata=metadata,
        )

    def _add_cache_metrics(self, metadata: dict, usage) -> None:
        """Add cache performance metrics to metadata if available."""
        if not hasattr(usage, "cache_creation_input_tokens"):
            return

        cache_creation = getattr(usage, "cache_creation_input_tokens", 0)
        cache_read = getattr(usage, "cache_read_input_tokens", 0)

        # Ensure values are numeric (handle mock objects in tests)
        if not (isinstance(cache_creation, int) and isinstance(cache_read, int)):
            return

        metadata["cache_creation_tokens"] = cache_creation
        metadata["cache_read_tokens"] = cache_read

        from attune.models.registry import get_pricing_for_model

        pricing = get_pricing_for_model(self.model)
        input_cost_per_million = pricing["input"] if pricing else 3.00
        input_cost_per_token = input_cost_per_million / 1_000_000

        if cache_read > 0:
            savings_per_token = input_cost_per_token * 0.9
            total_savings = cache_read * savings_per_token
            logger.info(
                f"Cache HIT: {cache_read:,} tokens read from cache "
                f"(saved ${total_savings:.4f} vs full price)",
            )
        if cache_creation > 0:
            write_cost_per_token = input_cost_per_token * 1.25
            write_cost = cache_creation * write_cost_per_token
            logger.debug(
                f"Cache WRITE: {cache_creation:,} tokens written to cache "
                f"(cost ${write_cost:.4f})",
            )

    async def analyze_large_codebase(
        self,
        codebase_files: list[dict[str, str]],
        analysis_prompt: str,
        **kwargs,
    ) -> LLMResponse:
        """Analyze large codebases using Claude's 200K context window.

        Claude-specific feature: Can process entire repositories in one call.

        Args:
            codebase_files: List of {"path": "...", "content": "..."} dicts
            analysis_prompt: What to analyze for
            **kwargs: Additional generation parameters

        Returns:
            LLMResponse with analysis results

        """
        # Build context from all files
        file_context = "\n\n".join(
            [f"# File: {file['path']}\n{file['content']}" for file in codebase_files],
        )

        # Create system prompt with caching for file context
        system_parts = [
            {
                "type": "text",
                "text": "You are a code analysis expert using the Attune AI.",
            },
            {
                "type": "text",
                "text": f"Codebase files:\n\n{file_context}",
                "cache_control": _cache_control(),  # Cache the codebase
            },
        ]

        messages = [{"role": "user", "content": analysis_prompt}]

        # Use extended max_tokens for comprehensive analysis
        return await self.generate(
            messages=messages,
            system_prompt=None,  # We'll pass it directly in api_kwargs
            max_tokens=kwargs.pop("max_tokens", 4096),
            **{**kwargs, "system": system_parts},
        )

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream response from Anthropic API for real-time output.

        Yields text chunks as they arrive from the API.

        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific options

        Yields:
            str: Text chunks as they are generated

        """
        import anthropic

        api_kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt and self.use_prompt_caching:
            api_kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": _cache_control(),
                },
            ]
        elif system_prompt:
            api_kwargs["system"] = system_prompt

        api_kwargs.update(kwargs)

        # Drop params newer models (Opus 4.7+) reject (see generate()).
        _normalize_api_kwargs_for_model(api_kwargs)

        try:
            async with self.client.messages.stream(**api_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.RateLimitError as e:
            logger.warning(f"Rate limited during streaming: {e}")
            raise
        except anthropic.APIConnectionError as e:
            logger.error(f"Connection error during streaming: {e}")
            raise

    def get_model_info(self) -> dict[str, Any]:
        """Get Claude model information with extended context capabilities."""
        model_info = {
            "claude-opus-4-8": {
                "max_tokens": 200000,
                "cost_per_1m_input": 5.00,
                "cost_per_1m_output": 25.00,
                "supports_prompt_caching": True,
                "supports_thinking": True,
                "ideal_for": "Complex reasoning, large codebases",
            },
            "claude-sonnet-5": {
                "max_tokens": 200000,
                "cost_per_1m_input": 3.00,
                "cost_per_1m_output": 15.00,
                "supports_prompt_caching": True,
                "supports_thinking": True,
                "ideal_for": "General development, balanced cost/performance",
            },
            "claude-haiku-4-5": {
                "max_tokens": 200000,
                "cost_per_1m_input": 1.00,
                "cost_per_1m_output": 5.00,
                "supports_prompt_caching": True,
                "supports_thinking": True,
                "ideal_for": "Fast responses, simple tasks",
            },
        }

        return model_info.get(
            self.model,
            {
                "max_tokens": 200000,
                "cost_per_1m_input": 3.00,
                "cost_per_1m_output": 15.00,
                "supports_prompt_caching": True,
                "supports_thinking": True,
                "ideal_for": "General development",
            },
        )

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using accurate token counter (overrides base class).

        Uses tiktoken for fast local estimation (~98% accurate).
        Falls back to heuristic if tiktoken unavailable.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count

        """
        try:
            from attune.utils.tokens import count_tokens

            return count_tokens(text, model=self.model, use_api=False)
        except ImportError:
            # Fallback to base class heuristic if utils not available
            return super().estimate_tokens(text)

    def calculate_actual_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> dict[str, Any]:
        """Calculate actual cost based on precise token counts.

        Includes Anthropic prompt caching cost adjustments:
        - Cache writes: 25% markup over standard input pricing
        - Cache reads: 90% discount from standard input pricing

        Args:
            input_tokens: Regular input tokens (not cached)
            output_tokens: Output tokens
            cache_creation_tokens: Tokens written to cache
            cache_read_tokens: Tokens read from cache

        Returns:
            Dictionary with cost breakdown:
            - base_cost: Cost for regular input/output tokens
            - cache_write_cost: Cost for cache creation (if any)
            - cache_read_cost: Cost for cache reads (if any)
            - total_cost: Total cost including all components
            - savings: Amount saved by cache reads vs. full price

        Example:
            >>> provider = AnthropicProvider(api_key="...")
            >>> cost = provider.calculate_actual_cost(
            ...     input_tokens=1000,
            ...     output_tokens=500,
            ...     cache_read_tokens=10000
            ... )
            >>> cost["total_cost"]
            0.0105  # Significantly less than without cache

        """
        # Get pricing for this model
        model_info = self.get_model_info()
        input_price_per_million = model_info["cost_per_1m_input"]
        output_price_per_million = model_info["cost_per_1m_output"]

        # Base cost (non-cached tokens)
        base_cost = (input_tokens / 1_000_000) * input_price_per_million
        base_cost += (output_tokens / 1_000_000) * output_price_per_million

        # Cache write cost (25% markup)
        cache_write_price = input_price_per_million * 1.25
        cache_write_cost = (cache_creation_tokens / 1_000_000) * cache_write_price

        # Cache read cost (90% discount = 10% of input price)
        cache_read_price = input_price_per_million * 0.1
        cache_read_cost = (cache_read_tokens / 1_000_000) * cache_read_price

        # Calculate savings from cache reads
        full_price_for_cached = (cache_read_tokens / 1_000_000) * input_price_per_million
        savings = full_price_for_cached - cache_read_cost

        return {
            "base_cost": round(base_cost, 6),
            "cache_write_cost": round(cache_write_cost, 6),
            "cache_read_cost": round(cache_read_cost, 6),
            "total_cost": round(base_cost + cache_write_cost + cache_read_cost, 6),
            "savings": round(savings, 6),
            "currency": "USD",
        }
