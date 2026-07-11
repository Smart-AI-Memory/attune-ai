"""Provider CLI commands.

Commands for viewing and setting LLM provider configuration.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

logger = logging.getLogger(__name__)


def cmd_provider_show(args: Namespace) -> int:
    """Show current provider configuration."""
    try:
        from attune.models.provider_config import get_provider_config

        config = get_provider_config()

        print("\n🔧 Provider Configuration\n")
        print("-" * 60)
        print(f"  Mode:            {config.mode.value}")
        print(f"  Primary provider: {config.primary_provider}")
        print(f"  Cost optimization: {'✅ Enabled' if config.cost_optimization else '❌ Disabled'}")

        if config.available_providers:
            print("\n  Available providers:")
            for provider in config.available_providers:
                status = "✓" if provider == config.primary_provider else " "
                print(f"    [{status}] {provider}")
        else:
            print("\n  ⚠️  No API keys detected")
            print("  Set ANTHROPIC_API_KEY")
            print("  Run: attune auth setup")

        print("-" * 60)
        return 0

    except ImportError:
        print("❌ Provider module not available")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception(f"Provider error: {e}")
        print(f"❌ Error: {e}")
        return 1


def cmd_provider_set(args: Namespace) -> int:
    """Set the LLM provider."""
    try:
        from attune.models.provider_config import (
            ProviderMode,
            get_provider_config,
            set_provider_config,
        )

        # Get current config and update
        config = get_provider_config()

        if args.name == "hybrid":
            config.mode = ProviderMode.HYBRID
            print("✅ Provider mode set to: hybrid (multi-provider)")
        else:
            config.mode = ProviderMode.SINGLE
            config.primary_provider = args.name
            print(f"✅ Provider set to: {args.name}")

        set_provider_config(config)
        return 0

    except ImportError:
        print("❌ Provider module not available")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception(f"Provider error: {e}")
        print(f"❌ Error: {e}")
        return 1
