"""Authentication Strategy for Claude Subscriptions vs API

Intelligent routing between Claude.ai/Code subscriptions and Anthropic API based on:
- User subscription tier (Pro, Max, Enterprise)
- Module size (small/medium → subscription, large → API)
- User preferences (first-time setup with pros/cons)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

# Configuration file location
AUTH_STRATEGY_FILE = Path.home() / ".attune" / "auth_strategy.json"


class SubscriptionTier(str, Enum):
    """Claude subscription tiers."""

    FREE = "free"  # Free tier (limited)
    PRO = "pro"  # $20/month - 200K context
    MAX = "max"  # $200/month - 200K context + higher limits
    ENTERPRISE = "enterprise"  # Custom pricing
    API_ONLY = "api_only"  # No subscription, API only


class AuthMode(str, Enum):
    """Authentication mode selection."""

    SUBSCRIPTION = "subscription"  # Use Claude.ai/Code subscription
    API = "api"  # Use Anthropic API (pay-per-token)
    AUTO = "auto"  # Auto-select based on module size


@dataclass
class AuthStrategy:
    """Authentication strategy configuration.

    Controls when to use Claude subscriptions vs Anthropic API based on
    user tier, module size, and preferences.
    """

    # User's subscription tier
    subscription_tier: SubscriptionTier = SubscriptionTier.PRO

    # Default auth mode
    default_mode: AuthMode = AuthMode.AUTO

    # Module size thresholds (lines of code)
    small_module_threshold: int = 500  # < 500 LOC = small
    medium_module_threshold: int = 2000  # 500-2000 LOC = medium

    # Token estimation multiplier (LOC to tokens)
    loc_to_tokens_multiplier: float = 4.0  # ~4 tokens per line

    # First-time setup completed (True by default — zero-config install)
    setup_completed: bool = True

    # User preferences
    prefer_subscription: bool = True  # Use subscription when possible
    cost_optimization: bool = True  # Optimize for cost

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_recommended_mode(self, module_lines: int) -> AuthMode:
        """Get recommended auth mode based on module size.

        Args:
            module_lines: Number of lines in the module

        Returns:
            Recommended AuthMode

        Strategy:
            - Pro users → API (lower usage = economical)
            - Max/Enterprise users → AUTO (subscription for small/medium, API for large)
            - Small modules (< 500 LOC) → Subscription (fits easily)
            - Medium modules (500-2000 LOC) → Subscription (still fits)
            - Large modules (> 2000 LOC) → API (1M context window)

        """
        # If not in AUTO mode, respect user preference
        if self.default_mode != AuthMode.AUTO:
            return self.default_mode

        # Pro users → Recommend API (pay-per-token more economical)
        if self.subscription_tier == SubscriptionTier.PRO:
            return AuthMode.API

        # API-only users → API
        if self.subscription_tier == SubscriptionTier.API_ONLY:
            return AuthMode.API

        # Max/Enterprise users → Dynamic based on size
        if module_lines < self.small_module_threshold:
            # Small modules → Use subscription (saves money)
            return AuthMode.SUBSCRIPTION

        if module_lines < self.medium_module_threshold:
            # Medium modules → Use subscription if preferred
            return AuthMode.SUBSCRIPTION if self.prefer_subscription else AuthMode.API

        # Large modules → Use API (1M context window benefit)
        return AuthMode.API

    def estimate_tokens(self, module_lines: int) -> int:
        """Estimate token count from lines of code.

        Args:
            module_lines: Number of lines in the module

        Returns:
            Estimated token count

        """
        return int(module_lines * self.loc_to_tokens_multiplier)

    def estimate_cost(self, module_lines: int, mode: AuthMode | None = None) -> dict[str, Any]:
        """Estimate cost for documentation generation.

        Args:
            module_lines: Number of lines in the module
            mode: AuthMode to estimate (defaults to recommended mode)

        Returns:
            Cost estimate with breakdown

        """
        if mode is None:
            mode = self.get_recommended_mode(module_lines)

        tokens = self.estimate_tokens(module_lines)

        # Cost estimates (based on document_gen.py pipeline)
        # Outline: cheap tier, ~3K tokens
        # Write: capable tier, ~15K tokens
        # Polish: premium tier, ~10K tokens
        # API Reference: cheap tier, ~5K tokens

        # Each term is (tokens-in-millions) * ($-per-million-input-tokens).
        # The rate factors were previously 1000x too small (e.g. 0.00025
        # instead of 0.25 for $0.25/M), making the estimate read ~$0.0002
        # when the real figure is ~$0.20 — see get_pros_cons prose.
        outline_cost = 0.003 * 0.25  # 3K tokens * $0.25/M input
        write_cost = 0.015 * 3.0  # 15K tokens * $3/M input
        polish_cost = 0.010 * 15.0  # 10K tokens * $15/M input
        api_ref_cost = 0.005 * 0.25  # 5K tokens * $0.25/M input

        total_api_cost = outline_cost + write_cost + polish_cost + api_ref_cost

        if mode == AuthMode.SUBSCRIPTION:
            return {
                "mode": "subscription",
                "monetary_cost": 0.0,
                "quota_cost": f"~{tokens:,} tokens from subscription quota",
                "tokens_used": tokens,
                "fits_in_context": tokens < 200_000,  # 200K context window
            }
        # API
        return {
            "mode": "api",
            "monetary_cost": round(total_api_cost, 4),
            "quota_cost": None,
            "tokens_used": tokens,
            "fits_in_context": tokens < 1_000_000,  # 1M context window
        }

    def get_pros_cons(self, module_lines: int) -> dict[str, Any]:
        """Get pros/cons comparison for first-time setup.

        Args:
            module_lines: Number of lines in the module

        Returns:
            Comparison data for UI display

        """
        sub_estimate = self.estimate_cost(module_lines, AuthMode.SUBSCRIPTION)
        api_estimate = self.estimate_cost(module_lines, AuthMode.API)

        return {
            "subscription": {
                "name": "Use Subscription",
                "cost": "No additional cost (uses quota)",
                "pros": [
                    "No per-token charges",
                    f"Uses existing {self.subscription_tier.value} subscription",
                    "Simple auth (already logged in)",
                    "Good for small/medium modules",
                ],
                "cons": [
                    "Uses monthly quota",
                    "200K context limit (may not fit large modules)",
                    "Rate limits apply",
                ],
                "estimate": sub_estimate,
            },
            "api": {
                "name": "Use API",
                "cost": f"~${api_estimate['monetary_cost']} per module",
                "pros": [
                    "1M context window (fits large modules)",
                    "No quota consumption",
                    "Separate billing (easier tracking)",
                    "Higher rate limits",
                ],
                "cons": [
                    "Requires API key setup",
                    "Pay-per-token (~$0.20 per module)",
                    "Separate authentication",
                ],
                "estimate": api_estimate,
            },
            "auto": {
                "name": "Auto (Recommended)",
                "cost": "Smart routing based on module size",
                "pros": [
                    f"Small modules (< {self.small_module_threshold} LOC) → Subscription",
                    f"Medium modules ({self.small_module_threshold}-{self.medium_module_threshold} LOC) → Subscription",
                    f"Large modules (> {self.medium_module_threshold} LOC) → API",
                    "Best of both worlds",
                ],
                "cons": [
                    "Requires both subscription and API key",
                ],
                "estimate": {
                    "mode": "auto",
                    "current_recommendation": self.get_recommended_mode(module_lines).value,
                },
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "subscription_tier": self.subscription_tier.value,
            "default_mode": self.default_mode.value,
            "small_module_threshold": self.small_module_threshold,
            "medium_module_threshold": self.medium_module_threshold,
            "loc_to_tokens_multiplier": self.loc_to_tokens_multiplier,
            "setup_completed": self.setup_completed,
            "prefer_subscription": self.prefer_subscription,
            "cost_optimization": self.cost_optimization,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthStrategy:
        """Deserialize from dictionary."""
        return cls(
            subscription_tier=SubscriptionTier(data.get("subscription_tier", "pro")),
            default_mode=AuthMode(data.get("default_mode", "auto")),
            small_module_threshold=data.get("small_module_threshold", 500),
            medium_module_threshold=data.get("medium_module_threshold", 2000),
            loc_to_tokens_multiplier=data.get("loc_to_tokens_multiplier", 4.0),
            setup_completed=data.get("setup_completed", True),
            prefer_subscription=data.get("prefer_subscription", True),
            cost_optimization=data.get("cost_optimization", True),
            metadata=data.get("metadata", {}),
        )

    def save(self, path: Path | None = None) -> None:
        """Save authentication strategy to file (owner-only, atomic).

        The config records the resolved auth tier/mode, so it is written
        0600 inside a 0700 directory to keep it unreadable by co-tenants on
        shared/CI hosts. The path is validated BEFORE any directory is
        created, so a rejected path can never create attacker-controlled
        directories first.
        """
        if path is None:
            path = AUTH_STRATEGY_FILE
        validated_path = _validate_file_path(str(path))
        validated_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        payload = json.dumps(self.to_dict(), indent=2)
        # mkstemp creates the temp file 0600; write then atomically replace
        # so a partial write never leaves a half-readable config.
        fd, tmp_name = tempfile.mkstemp(
            dir=str(validated_path.parent), prefix=".auth_strategy.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp_name, validated_path)
        except OSError:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    @classmethod
    def load(cls, path: Path | None = None) -> AuthStrategy:
        """Load authentication strategy from file, or create default."""
        if path is None:
            path = AUTH_STRATEGY_FILE

        validated_path = _validate_file_path(str(path))
        if validated_path.exists():
            try:
                with open(validated_path) as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Graceful fallback to default config
                # when saved state is corrupt or unreadable.
                logger.warning(
                    "auth_strategy_load_failed: %s",
                    str(path),
                    exc_info=True,
                )

        # Return default if no config exists
        return cls()


def configure_auth_interactive(module_lines: int = 1000) -> AuthStrategy:
    """Interactive authentication configuration (first-time setup).

    Shows pros/cons comparison and guides user to choose auth strategy.

    Args:
        module_lines: Sample module size for cost estimates

    Returns:
        Configured AuthStrategy

    """
    print("\n" + "=" * 60)
    print("Attune AI - Authentication Setup")
    print("=" * 60)

    print("\nThis framework can use your Claude subscription OR the Anthropic API.")
    print("Let's help you choose the best approach for your needs.")

    # Detect subscription tier
    print("\n1. What Claude subscription tier do you have?")
    print("   1) Free (limited access)")
    print("   2) Pro ($20/month)")
    print("   3) Max ($200/month)")
    print("   4) Enterprise (custom)")
    print("   5) None (API only)")

    tier_choice = input("\nYour tier [1-5]: ").strip()
    tier_map = {
        "1": SubscriptionTier.FREE,
        "2": SubscriptionTier.PRO,
        "3": SubscriptionTier.MAX,
        "4": SubscriptionTier.ENTERPRISE,
        "5": SubscriptionTier.API_ONLY,
    }
    subscription_tier = tier_map.get(tier_choice, SubscriptionTier.API_ONLY)

    # Create strategy with detected tier
    strategy = AuthStrategy(subscription_tier=subscription_tier)

    # Show pros/cons comparison
    print("\n" + "=" * 60)
    print("Comparison: Subscription vs API vs Auto")
    print("=" * 60)

    comparison = strategy.get_pros_cons(module_lines)

    for _mode_key, mode_data in comparison.items():
        print(f"\n### {mode_data['name']}")
        print(f"Cost: {mode_data['cost']}")
        print("\nPros:")
        for pro in mode_data["pros"]:
            print(f"  ✓ {pro}")
        print("\nCons:")
        for con in mode_data["cons"]:
            print(f"  ✗ {con}")

    # Get user choice
    print("\n" + "=" * 60)
    print("2. Which authentication mode do you prefer?")
    print("   1) Subscription (use my Claude quota)")
    print("   2) API (pay-per-token)")
    print("   3) Auto (smart routing based on module size) [RECOMMENDED]")

    mode_choice = input("\nYour choice [1-3]: ").strip()
    mode_map = {
        "1": AuthMode.SUBSCRIPTION,
        "2": AuthMode.API,
        "3": AuthMode.AUTO,
    }
    default_mode = mode_map.get(mode_choice, AuthMode.AUTO)

    # Create final strategy
    strategy = AuthStrategy(
        subscription_tier=subscription_tier,
        default_mode=default_mode,
        setup_completed=True,
    )

    # Save configuration
    strategy.save()
    print("\n✓ Authentication strategy saved to ~/.attune/auth_strategy.json")

    # Show recommendation
    print(f"\n✓ Using {default_mode.value} mode")
    if default_mode == AuthMode.AUTO:
        print(f"   Small/medium modules (< {strategy.medium_module_threshold} LOC) → Subscription")
        print(f"   Large modules (> {strategy.medium_module_threshold} LOC) → API")

    return strategy


def get_auth_strategy() -> AuthStrategy:
    """Get the global authentication strategy.

    Zero-config by default: uses subscription-first routing with automatic
    API fallback for large modules when ``ANTHROPIC_API_KEY`` is available.

    Users can optionally run ``python -m attune.models.auth_cli setup`` to
    customize tier, thresholds, and routing preferences.

    Returns:
        AuthStrategy instance

    """
    return AuthStrategy.load()


# Utility functions for module size calculation
def count_lines_of_code(file_path: str | Path) -> int:
    """Count lines of code in a Python file.

    Args:
        file_path: Path to Python file

    Returns:
        Number of lines (excluding blank lines and comments)

    """
    # Validate before reading — file_path may be caller-controlled; block
    # traversal / system paths per the "ALWAYS validate file paths" rule.
    path = _validate_file_path(str(file_path))
    if not path.exists():
        return 0

    lines = 0
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                # Skip blank lines and comments
                if stripped and not stripped.startswith("#"):
                    lines += 1
    except Exception:  # noqa: BLE001
        # If we can't read the file, estimate from total lines
        try:
            with open(path, encoding="utf-8") as f:
                return len(f.readlines())
        except Exception:  # noqa: BLE001
            return 0

    return lines


def get_module_size_category(module_lines: int) -> str:
    """Categorize module size.

    Args:
        module_lines: Number of lines in the module

    Returns:
        Size category: "small", "medium", or "large"

    """
    if module_lines < 500:
        return "small"
    if module_lines < 2000:
        return "medium"
    return "large"
