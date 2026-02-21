"""Model routing configuration section.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import os
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class RoutingConfig:
    """Model routing and tier selection configuration.

    Controls how requests are routed to different model tiers
    (cheap/capable/premium/ultra) and cost optimization settings.

    Attributes:
        default_tier: Default model tier for requests.
        cheap_model: Model ID for cheap/fast tier (Haiku).
        capable_model: Model ID for capable/balanced tier (Sonnet).
        premium_model: Model ID for premium/powerful tier (Opus).
        ultra_model: Model ID for ultra/1M-context tier (Opus 4.6 1M).
        auto_tier_selection: Automatically select tier based on task complexity.
        cost_optimization: Enable cost-saving optimizations.
        max_tokens_cheap: Max output tokens for cheap tier.
        max_tokens_capable: Max output tokens for capable tier.
        max_tokens_premium: Max output tokens for premium tier.
        max_tokens_ultra: Max output tokens for ultra tier.
        ultra_enabled: Enable ultra tier (EXPERIMENTAL, requires beta access
            and ATTUNE_ULTRA_EXPERIMENTAL=1 environment variable).
        ultra_beta_header: Anthropic beta header value for 1M context.
        temperature_default: Default temperature for completions.
        retry_on_rate_limit: Retry requests on rate limit errors.
        max_retries: Maximum retry attempts.
    """

    default_tier: Literal["cheap", "capable", "premium", "ultra"] = "capable"
    cheap_model: str = "claude-haiku-4-5-20251001"
    capable_model: str = "claude-sonnet-4-6"
    premium_model: str = "claude-opus-4-6"
    ultra_model: str = "claude-opus-4-6"
    auto_tier_selection: bool = True
    cost_optimization: bool = True
    max_tokens_cheap: int = 4096
    max_tokens_capable: int = 8192
    max_tokens_premium: int = 16384
    max_tokens_ultra: int = 128_000
    ultra_enabled: bool = False
    ultra_beta_header: str = "context-1m-2025-08-07"
    temperature_default: float = 0.7
    retry_on_rate_limit: bool = True
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Enforce experimental gate for ultra tier."""
        if self.ultra_enabled:
            env_flag = os.environ.get("ATTUNE_ULTRA_EXPERIMENTAL", "")
            if env_flag != "1":
                logger.warning(
                    "ultra_enabled=True in config but "
                    "ATTUNE_ULTRA_EXPERIMENTAL=1 not set. "
                    "Ultra tier disabled. The 1M context API "
                    "is experimental and requires opt-in via "
                    "environment variable."
                )
                self.ultra_enabled = False
            else:
                logger.warning(
                    "Ultra tier ENABLED (experimental). "
                    "Using Anthropic 1M context beta API. "
                    "This feature may change without notice."
                )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "default_tier": self.default_tier,
            "cheap_model": self.cheap_model,
            "capable_model": self.capable_model,
            "premium_model": self.premium_model,
            "ultra_model": self.ultra_model,
            "auto_tier_selection": self.auto_tier_selection,
            "cost_optimization": self.cost_optimization,
            "max_tokens_cheap": self.max_tokens_cheap,
            "max_tokens_capable": self.max_tokens_capable,
            "max_tokens_premium": self.max_tokens_premium,
            "max_tokens_ultra": self.max_tokens_ultra,
            "ultra_enabled": self.ultra_enabled,
            "ultra_beta_header": self.ultra_beta_header,
            "temperature_default": self.temperature_default,
            "retry_on_rate_limit": self.retry_on_rate_limit,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoutingConfig":
        """Create from dictionary."""
        return cls(
            default_tier=data.get("default_tier", "capable"),
            cheap_model=data.get("cheap_model", "claude-haiku-4-5-20251001"),
            capable_model=data.get("capable_model", "claude-sonnet-4-6"),
            premium_model=data.get("premium_model", "claude-opus-4-6"),
            ultra_model=data.get("ultra_model", "claude-opus-4-6"),
            auto_tier_selection=data.get("auto_tier_selection", True),
            cost_optimization=data.get("cost_optimization", True),
            max_tokens_cheap=data.get("max_tokens_cheap", 4096),
            max_tokens_capable=data.get("max_tokens_capable", 8192),
            max_tokens_premium=data.get("max_tokens_premium", 16384),
            max_tokens_ultra=data.get("max_tokens_ultra", 128_000),
            ultra_enabled=data.get("ultra_enabled", False),
            ultra_beta_header=data.get("ultra_beta_header", "context-1m-2025-08-07"),
            temperature_default=data.get("temperature_default", 0.7),
            retry_on_rate_limit=data.get("retry_on_rate_limit", True),
            max_retries=data.get("max_retries", 3),
        )
