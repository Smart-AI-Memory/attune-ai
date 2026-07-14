"""CLI commands for authentication strategy management.

Provides commands to configure and manage intelligent authentication routing
between Claude subscriptions and Anthropic API based on module size.

Usage:
    python -m attune.models.auth_cli setup
    python -m attune.models.auth_cli status
    python -m attune.models.auth_cli reset
    python -m attune.models.auth_cli recommend <file_path>

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore

from .auth_strategy import (
    AUTH_STRATEGY_FILE,
    AuthStrategy,
    SubscriptionTier,
    configure_auth_interactive,
    count_lines_of_code,
    get_module_size_category,
)


def cmd_auth_setup(args: Any) -> int:
    """Run interactive authentication strategy setup.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)

    """
    try:
        print("\n🔐 Authentication Strategy Setup\n")
        print("=" * 60)
        print()
        print("Configure intelligent routing between Claude subscriptions")
        print("and Anthropic API based on module size.\n")

        # Run interactive setup
        strategy = configure_auth_interactive()

        print("\n✅ Configuration saved successfully!")
        print(f"Location: {AUTH_STRATEGY_FILE}")
        print()
        print("Your authentication strategy:")
        print(f"  Tier: {strategy.subscription_tier.value}")
        print(f"  Mode: {strategy.default_mode.value}")
        print()
        print("Run 'attune auth status' to view your configuration.")
        return 0

    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Error during setup: {e}")
        return 1


def cmd_auth_status(args: Any) -> int:
    """Show current authentication strategy configuration.

    Args:
        args: Parsed command-line arguments
            - json: Output as JSON instead of formatted table

    Returns:
        Exit code (0 for success)

    """
    try:
        # Load strategy. Track whether it came from a real config file:
        # a fresh install runs on zero-config defaults, and rendering
        # those as "Setup Completed: Yes / Tier: PRO" reads as state the
        # user never created (setup-friction F3). Same values, honest
        # labels.
        strategy = AuthStrategy.load()
        configured = AUTH_STRATEGY_FILE.exists()
        output_json = getattr(args, "json", False)

        if output_json:
            # JSON output
            config = {
                "subscription_tier": strategy.subscription_tier.value,
                "default_mode": strategy.default_mode.value,
                "small_module_threshold": strategy.small_module_threshold,
                "medium_module_threshold": strategy.medium_module_threshold,
                "loc_to_tokens_multiplier": strategy.loc_to_tokens_multiplier,
                "prefer_subscription": strategy.prefer_subscription,
                "cost_optimization": strategy.cost_optimization,
                "setup_completed": strategy.setup_completed,
                "configured": configured,
                "config_file": str(AUTH_STRATEGY_FILE),
            }
            print(json.dumps(config, indent=2))
            return 0

        # Formatted output
        if RICH_AVAILABLE and Console is not None:
            console = Console()

            # Configuration panel
            default_note = "" if configured else " (default)"
            config_text = Text()
            config_text.append("Subscription Tier: ", style="cyan")
            config_text.append(
                f"{strategy.subscription_tier.value.upper()}{default_note}\n", style="bold"
            )
            config_text.append("Default Mode: ", style="cyan")
            config_text.append(
                f"{strategy.default_mode.value.upper()}{default_note}\n", style="bold"
            )
            config_text.append("Setup: ", style="cyan")
            if configured:
                config_text.append(
                    (
                        "✅ Configured\n"
                        if strategy.setup_completed
                        else "❌ Incomplete (run 'attune auth setup')\n"
                    ),
                )
            else:
                config_text.append(
                    "Not configured — using zero-config defaults "
                    "(run 'attune auth setup' to customize)\n",
                )

            console.print(Panel(config_text, title="Authentication Strategy", border_style="blue"))

            # Module size thresholds
            threshold_table = Table(title="Module Size Thresholds", show_header=True)
            threshold_table.add_column("Category", style="cyan")
            threshold_table.add_column("Size (LOC)", justify="right")
            threshold_table.add_column("Recommended Auth", style="green")

            if strategy.subscription_tier == SubscriptionTier.PRO:
                threshold_table.add_row("Small", f"< {strategy.small_module_threshold}", "API")
                threshold_table.add_row(
                    "Medium",
                    f"{strategy.small_module_threshold} - {strategy.medium_module_threshold}",
                    "API",
                )
                threshold_table.add_row("Large", f"> {strategy.medium_module_threshold}", "API")
            else:
                threshold_table.add_row(
                    "Small",
                    f"< {strategy.small_module_threshold}",
                    "Subscription",
                )
                threshold_table.add_row(
                    "Medium",
                    f"{strategy.small_module_threshold} - {strategy.medium_module_threshold}",
                    "Subscription",
                )
                threshold_table.add_row(
                    "Large",
                    f"> {strategy.medium_module_threshold}",
                    "API (1M context)",
                )

            console.print(threshold_table)

            # File location
            file_note = "" if configured else " (not created yet)"
            console.print(f"\n[dim]Configuration file: {AUTH_STRATEGY_FILE}{file_note}[/dim]")

        else:
            # Plain text fallback
            print("\n" + "=" * 60)
            print("AUTHENTICATION STRATEGY")
            print("=" * 60)
            plain_note = "" if configured else " (default)"
            print(f"\nSubscription Tier: {strategy.subscription_tier.value.upper()}{plain_note}")
            print(f"Default Mode: {strategy.default_mode.value.upper()}{plain_note}")
            if configured:
                print(f"Setup Completed: {'Yes' if strategy.setup_completed else 'No'}")
            else:
                print(
                    "Setup: not configured — using zero-config defaults "
                    "(run 'attune auth setup' to customize)"
                )

            print("\nModule Size Thresholds:")
            print(f"  Small: < {strategy.small_module_threshold} LOC")
            print(
                f"  Medium: {strategy.small_module_threshold}-{strategy.medium_module_threshold} LOC",
            )
            print(f"  Large: > {strategy.medium_module_threshold} LOC")

            print("\nRecommended Auth:")
            if strategy.subscription_tier == SubscriptionTier.PRO:
                print("  All modules → API (pay-per-token)")
            else:
                print("  Small/Medium → Subscription")
                print("  Large → API (1M context window)")

            print(
                f"\nConfiguration file: {AUTH_STRATEGY_FILE}{'' if configured else ' (not created yet)'}"
            )
            print("=" * 60)

        return 0

    except FileNotFoundError:
        print("❌ No authentication strategy configured.")
        print("Run 'attune auth setup' to configure your strategy.")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"❌ Error reading configuration: {e}")
        return 1


def cmd_auth_reset(args: Any) -> int:
    """Reset/clear authentication strategy configuration.

    Args:
        args: Parsed command-line arguments
            - confirm: Require confirmation flag

    Returns:
        Exit code (0 for success)

    """
    confirm = getattr(args, "confirm", False)

    if not confirm:
        print("⚠️  WARNING: This will delete your authentication strategy configuration.")
        print(f"Location: {AUTH_STRATEGY_FILE}")
        print("\nUse --confirm to proceed:")
        print("  attune auth reset --confirm")
        return 1

    try:
        if AUTH_STRATEGY_FILE.exists():
            AUTH_STRATEGY_FILE.unlink()
            print("✅ Authentication strategy reset successfully.")
            print("Run 'attune auth setup' to configure a new strategy.")
            return 0
        print("ℹ️  No configuration file found - nothing to reset.")
        return 0

    except Exception as e:  # noqa: BLE001
        print(f"❌ Error resetting configuration: {e}")
        return 1


def cmd_auth_recommend(args: Any) -> int:
    """Get authentication recommendation for a specific file.

    Args:
        args: Parsed command-line arguments
            - file_path: Path to the file to analyze

    Returns:
        Exit code (0 for success)

    """
    file_path_str = getattr(args, "file_path", None)

    if not file_path_str:
        print("❌ Error: file_path is required")
        print("Usage: attune auth recommend <file_path>")
        return 1

    file_path = Path(file_path_str)

    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        return 1

    if not file_path.is_file():
        print(f"❌ Error: Path is not a file: {file_path}")
        return 1

    try:
        # Load strategy
        strategy = AuthStrategy.load()

        # Calculate module size
        module_lines = count_lines_of_code(file_path)
        size_category = get_module_size_category(module_lines)

        # Get recommendation
        recommended_mode = strategy.get_recommended_mode(module_lines)

        # Get cost estimate
        cost_estimate = strategy.estimate_cost(module_lines, recommended_mode)

        # Display results
        if RICH_AVAILABLE and Console is not None:
            console = Console()

            # Module info
            info_text = Text()
            info_text.append("File: ", style="cyan")
            info_text.append(f"{file_path}\n", style="bold")
            info_text.append("Lines of Code: ", style="cyan")
            info_text.append(f"{module_lines:,}\n", style="bold")
            info_text.append("Size Category: ", style="cyan")
            info_text.append(f"{size_category.upper()}\n", style="bold")

            console.print(Panel(info_text, title="Module Analysis", border_style="blue"))

            # Recommendation
            rec_text = Text()
            rec_text.append("Recommended: ", style="cyan")
            rec_text.append(f"{recommended_mode.value.upper()} mode\n", style="green bold")

            if recommended_mode.value == "subscription":
                rec_text.append("\nReason: ", style="cyan")
                rec_text.append("Module fits in 200K context window\n")
                rec_text.append("Benefit: ", style="cyan")
                rec_text.append("No additional cost, uses subscription quota\n")
            else:
                rec_text.append("\nReason: ", style="cyan")
                rec_text.append("Module needs 1M context window\n")
                rec_text.append("Benefit: ", style="cyan")
                rec_text.append("No quota consumption, higher context limit\n")

            console.print(Panel(rec_text, title="Recommendation", border_style="green"))

            # Cost estimate
            cost_table = Table(title="Cost Estimate", show_header=True)
            cost_table.add_column("Metric", style="cyan")
            cost_table.add_column("Value", justify="right", style="green")

            cost_table.add_row("Mode", cost_estimate["mode"].upper())
            if cost_estimate["mode"] == "subscription":
                cost_table.add_row("Monetary Cost", "$0.00")
                cost_table.add_row("Quota Cost", cost_estimate["quota_cost"])
                cost_table.add_row(
                    "Fits in 200K",
                    "✅ Yes" if cost_estimate["fits_in_context"] else "❌ No",
                )
            else:
                cost_table.add_row("Monetary Cost", f"${cost_estimate['monetary_cost']:.4f}")
                cost_table.add_row("Quota Cost", "None")
                cost_table.add_row(
                    "Fits in 1M",
                    "✅ Yes" if cost_estimate["fits_in_context"] else "❌ No",
                )

            cost_table.add_row("Estimated Tokens", f"{cost_estimate['tokens_used']:,}")

            console.print(cost_table)

        else:
            # Plain text fallback
            print("\n" + "=" * 60)
            print("MODULE ANALYSIS")
            print("=" * 60)
            print(f"\nFile: {file_path}")
            print(f"Lines of Code: {module_lines:,}")
            print(f"Size Category: {size_category.upper()}")

            print("\nRECOMMENDATION")
            print("=" * 60)
            print(f"Recommended: {recommended_mode.value.upper()} mode")

            if recommended_mode.value == "subscription":
                print("Reason: Module fits in 200K context window")
                print("Benefit: No additional cost, uses subscription quota")
            else:
                print("Reason: Module needs 1M context window")
                print("Benefit: No quota consumption, higher context limit")

            print("\nCOST ESTIMATE")
            print("=" * 60)
            print(f"Mode: {cost_estimate['mode'].upper()}")
            if cost_estimate["mode"] == "subscription":
                print("Monetary Cost: $0.00")
                print(f"Quota Cost: {cost_estimate['quota_cost']}")
                print(f"Fits in 200K: {'Yes' if cost_estimate['fits_in_context'] else 'No'}")
            else:
                print(f"Monetary Cost: ${cost_estimate['monetary_cost']:.4f}")
                print("Quota Cost: None")
                print(f"Fits in 1M: {'Yes' if cost_estimate['fits_in_context'] else 'No'}")

            print(f"Estimated Tokens: {cost_estimate['tokens_used']:,}")
            print("=" * 60)

        return 0

    except FileNotFoundError:
        print("\n❌ No authentication strategy configured.")
        print("Run 'attune auth setup' to configure your strategy first.")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Error analyzing file: {e}")
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Authentication Strategy Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s setup                        Run interactive setup
  %(prog)s status                       Show current configuration
  %(prog)s status --json                Show configuration as JSON
  %(prog)s reset --confirm              Clear configuration
  %(prog)s recommend path/to/file.py    Get recommendation for file
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Setup command
    subparsers.add_parser("setup", help="Run interactive authentication strategy setup")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show current authentication strategy")
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted table",
    )

    # Reset command
    reset_parser = subparsers.add_parser(
        "reset",
        help="Reset authentication strategy configuration",
    )
    reset_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm deletion of configuration",
    )

    # Recommend command
    rec_parser = subparsers.add_parser(
        "recommend",
        help="Get authentication recommendation for a file",
    )
    rec_parser.add_argument("file_path", help="Path to the file to analyze")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "setup":
        return cmd_auth_setup(args)

    if args.command == "status":
        return cmd_auth_status(args)

    if args.command == "reset":
        return cmd_auth_reset(args)

    if args.command == "recommend":
        return cmd_auth_recommend(args)

    # Should not reach here
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
