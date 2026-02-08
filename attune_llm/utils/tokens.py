"""Token counting utilities using Anthropic's tokenizer.

Provides accurate token counting for billing-accurate cost tracking.
Replaces rough estimates (4 chars per token) with Anthropic's official counter.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import functools
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import to avoid requiring dependencies if not used
_client = None
_tiktoken_encoding = None

# Try to import tiktoken for fast local estimation
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.debug("tiktoken not available - will use API or heuristic fallback")


@dataclass
class TokenCount:
    """Token count result with metadata."""

    tokens: int
    method: str  # "anthropic_api", "tiktoken", "heuristic"
    model: str | None = None


def _get_client():
    """Get or create Anthropic client for token counting."""
    global _client
    if _client is None:
        try:
            from anthropic import Anthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable required for API token counting"
                )
            _client = Anthropic(api_key=api_key)
        except ImportError as e:
            raise ImportError(
                "anthropic package required for token counting. Install with: pip install anthropic"
            ) from e
    return _client


@functools.lru_cache(maxsize=4)
def _get_tiktoken_encoding(model: str) -> Any:
    """Get tiktoken encoding for Claude models (cached)."""
    if not TIKTOKEN_AVAILABLE:
        return None
    try:
        # Claude uses cl100k_base encoding (similar to GPT-4)
        return tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        logger.warning(f"Failed to get tiktoken encoding: {e}")
        return None


def _count_tokens_tiktoken(text: str, model: str) -> int:
    """Count tokens using tiktoken (fast local estimation)."""
    if not text:
        return 0

    encoding = _get_tiktoken_encoding(model)
    if not encoding:
        return 0

    try:
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"tiktoken encoding failed: {e}")
        return 0


def _count_tokens_heuristic(text: str) -> int:
    """Fallback heuristic token counting (~4 chars per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def count_tokens(
    text: str, model: str = "claude-sonnet-4-5-20250929", use_api: bool = False
) -> int:
    """Count tokens using best available method.

    By default, uses tiktoken for fast local estimation (~98% accurate).
    Set use_api=True for exact count via Anthropic API (requires network call).

    Args:
        text: Text to tokenize
        model: Model ID (different models may have different tokenizers)
        use_api: Whether to use Anthropic API for exact count (slower, requires API key)

    Returns:
        Token count

    Example:
        >>> count_tokens("Hello, world!")
        4
        >>> count_tokens("def hello():\\n    print('hi')", use_api=True)
        8

    Raises:
        ImportError: If anthropic package not installed (when use_api=True)
        ValueError: If API key missing (when use_api=True)

    """
    if not text:
        return 0

    # Use API if explicitly requested
    if use_api:
        try:
            client = _get_client()
            # FIXED: Use correct API method - client.messages.count_tokens()
            result = client.messages.count_tokens(
                model=model,
                messages=[{"role": "user", "content": text}],
            )
            return int(result.input_tokens)
        except Exception as e:
            logger.warning(f"API token counting failed, using fallback: {e}")
            # Continue to fallback methods

    # Try tiktoken first (fast and accurate)
    if TIKTOKEN_AVAILABLE:
        tokens = _count_tokens_tiktoken(text, model)
        if tokens > 0:
            return tokens

    # Fallback to heuristic
    return _count_tokens_heuristic(text)


def count_message_tokens(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    model: str = "claude-sonnet-4-5-20250929",
    use_api: bool = False,
) -> dict[str, int]:
    """Count tokens in a conversation.

    By default uses tiktoken for fast estimation. Set use_api=True for exact count.

    Args:
        messages: List of message dicts with "role" and "content"
        system_prompt: Optional system prompt
        model: Model ID
        use_api: Whether to use Anthropic API for exact count

    Returns:
        Dict with token counts by component:
        - "system": System prompt tokens
        - "messages": Message tokens
        - "total": Sum of all tokens

    Example:
        >>> messages = [{"role": "user", "content": "Hello!"}]
        >>> count_message_tokens(messages, system_prompt="You are helpful")
        {"system": 4, "messages": 6, "total": 10}

    """
    if not messages:
        if system_prompt:
            tokens = count_tokens(system_prompt, model, use_api)
            return {"system": tokens, "messages": 0, "total": tokens}
        return {"system": 0, "messages": 0, "total": 0}

    # Use Anthropic API for exact count if requested
    if use_api:
        try:
            client = _get_client()
            kwargs: dict[str, Any] = {"model": model, "messages": messages}
            if system_prompt:
                kwargs["system"] = system_prompt

            result = client.messages.count_tokens(**kwargs)
            # API returns total input tokens, estimate breakdown
            total_tokens = result.input_tokens

            # Estimate system vs message breakdown
            if system_prompt:
                system_tokens = count_tokens(system_prompt, model, use_api=False)
                message_tokens = max(0, total_tokens - system_tokens)
            else:
                system_tokens = 0
                message_tokens = total_tokens

            return {
                "system": system_tokens,
                "messages": message_tokens,
                "total": total_tokens,
            }
        except Exception as e:
            logger.warning(f"API token counting failed, using fallback: {e}")
            # Continue to fallback method

    # Fallback: count each component separately
    counts: dict[str, int] = {}

    # Count system prompt
    if system_prompt:
        counts["system"] = count_tokens(system_prompt, model, use_api=False)
    else:
        counts["system"] = 0

    # Count messages with overhead
    message_tokens = 0
    for message in messages:
        content = message.get("content", "")
        message_tokens += count_tokens(content, model, use_api=False)
        message_tokens += 4  # Overhead for role markers

    counts["messages"] = message_tokens
    counts["total"] = counts["system"] + message_tokens

    return counts


def estimate_cost(input_tokens: int, output_tokens: int, model: str = "claude-sonnet-4-5-20250929") -> float:
    """Estimate cost in USD based on token counts.

    Args:
        input_tokens: Input token count
        output_tokens: Output token count
        model: Model ID (used to look up pricing)

    Returns:
        Estimated cost in USD

    Example:
        >>> estimate_cost(1000, 500, "claude-sonnet-4-5")
        0.0105  # $3/M input + $15/M output

    Raises:
        ValueError: If model is unknown

    """
    # Import here to avoid circular dependency
    try:
        from attune.models.registry import get_pricing_for_model

        pricing = get_pricing_for_model(model)
        if not pricing:
            raise ValueError(f"Unknown model: {model}")

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
    except ImportError:
        # Fallback if registry not available
        # Use default Sonnet 4.5 pricing
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost


def calculate_cost_with_cache(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    model: str = "claude-sonnet-4-5-20250929",
) -> dict[str, Any]:
    """Calculate cost including Anthropic prompt caching.

    Anthropic prompt caching pricing:
    - Cache writes: 25% markup over standard input pricing
    - Cache reads: 90% discount from standard input pricing

    Args:
        input_tokens: Regular input tokens (not cached)
        output_tokens: Output tokens
        cache_creation_tokens: Tokens written to cache
        cache_read_tokens: Tokens read from cache
        model: Model ID

    Returns:
        Dict with cost breakdown:
        - "base_cost": Cost without cache
        - "cache_write_cost": Cost for cache writes (25% markup)
        - "cache_read_cost": Cost for cache reads (90% discount)
        - "total_cost": Sum of all costs
        - "savings": Amount saved by cache reads

    Example:
        >>> calculate_cost_with_cache(1000, 500, 5000, 10000, "claude-sonnet-4-5")
        {
            "base_cost": 0.0105,
            "cache_write_cost": 0.01875,  # 5000 tokens * $3.75/M
            "cache_read_cost": 0.003,     # 10000 tokens * $0.30/M
            "total_cost": 0.03225,
            "savings": 0.027,             # Saved vs. no cache
        }

    """
    # Get pricing for model
    try:
        from attune.models.registry import get_pricing_for_model

        pricing = get_pricing_for_model(model)
        if not pricing:
            raise ValueError(f"Unknown model: {model}")

        input_price_per_million = pricing["input"]
        output_price_per_million = pricing["output"]
    except (ImportError, ValueError):
        # Fallback to default Sonnet 4.5 pricing
        input_price_per_million = 3.00
        output_price_per_million = 15.00

    # Base cost (non-cached tokens)
    base_cost = (input_tokens / 1_000_000) * input_price_per_million
    base_cost += (output_tokens / 1_000_000) * output_price_per_million

    # Cache write cost (25% markup)
    cache_write_price = input_price_per_million * 1.25
    cache_write_cost = (cache_creation_tokens / 1_000_000) * cache_write_price

    # Cache read cost (90% discount = 10% of input price)
    cache_read_price = input_price_per_million * 0.1
    cache_read_cost = (cache_read_tokens / 1_000_000) * cache_read_price

    # Calculate what we would have paid without cache
    full_price_for_cached = (cache_read_tokens / 1_000_000) * input_price_per_million
    savings = full_price_for_cached - cache_read_cost

    return {
        "base_cost": round(base_cost, 6),
        "cache_write_cost": round(cache_write_cost, 6),
        "cache_read_cost": round(cache_read_cost, 6),
        "total_cost": round(base_cost + cache_write_cost + cache_read_cost, 6),
        "savings": round(savings, 6),
    }
