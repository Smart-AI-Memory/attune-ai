"""Authentication configuration section.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class AuthConfig:
    """Authentication and API key configuration.

    Controls how Attune authenticates with LLM providers and routes
    requests between subscription-based and API-based access.

    Attributes:
        strategy: Authentication strategy - 'subscription' uses Claude subscription,
            'api' uses API key, 'hybrid' intelligently routes between both.
        api_key_env: Environment variable name containing the API key.
        claude_subscription: Whether user has an active Claude subscription.
        small_module_threshold: Token count below which subscription is preferred.
        medium_module_threshold: Token count for medium-sized modules.
        subscription_daily_limit: Max requests per day via subscription.
        api_daily_limit: Max requests per day via API.
        fallback_enabled: Whether to fallback to API when subscription limit reached.

    """

    strategy: Literal["subscription", "api", "hybrid"] = "hybrid"
    api_key_env: str = "ANTHROPIC_API_KEY"
    claude_subscription: bool = True
    small_module_threshold: int = 500
    medium_module_threshold: int = 2000
    subscription_daily_limit: int = 100
    api_daily_limit: int = 1000
    fallback_enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "strategy": self.strategy,
            "api_key_env": self.api_key_env,
            "claude_subscription": self.claude_subscription,
            "small_module_threshold": self.small_module_threshold,
            "medium_module_threshold": self.medium_module_threshold,
            "subscription_daily_limit": self.subscription_daily_limit,
            "api_daily_limit": self.api_daily_limit,
            "fallback_enabled": self.fallback_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthConfig":
        """Create from dictionary."""
        return cls(
            strategy=data.get("strategy", "hybrid"),
            api_key_env=data.get("api_key_env", "ANTHROPIC_API_KEY"),
            claude_subscription=data.get("claude_subscription", True),
            small_module_threshold=data.get("small_module_threshold", 500),
            medium_module_threshold=data.get("medium_module_threshold", 2000),
            subscription_daily_limit=data.get("subscription_daily_limit", 100),
            api_daily_limit=data.get("api_daily_limit", 1000),
            fallback_enabled=data.get("fallback_enabled", True),
        )
