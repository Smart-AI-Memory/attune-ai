"""Framework information commands.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune import load_config
from attune.logging_config import get_logger

logger = get_logger(__name__)


def cmd_info(args):
    """Display information about the framework.

    Shows configuration, persistence, and feature status.

    Args:
        args: Namespace object from argparse with attributes:
            - config (str | None): Optional path to configuration file.

    Returns:
        None: Prints framework information to stdout.
    """
    config_file = args.config
    logger.info("Displaying framework information")

    if config_file:
        logger.debug(f"Loading config from file: {config_file}")
        config = load_config(filepath=config_file)
    else:
        logger.debug("Loading default configuration")
        config = load_config()

    logger.info("=== Attune AI Info ===\n")
    logger.info("Configuration:")
    logger.info(f"  User ID: {config.user_id}")
    logger.info(f"  Target Level: {config.target_level}")
    logger.info(f"  Confidence Threshold: {config.confidence_threshold}")
    logger.info("\nPersistence:")
    logger.info(f"  Backend: {config.persistence_backend}")
    logger.info(f"  Path: {config.persistence_path}")
    logger.info(f"  Enabled: {config.persistence_enabled}")
    logger.info("\nMetrics:")
    logger.info(f"  Enabled: {config.metrics_enabled}")
    logger.info(f"  Path: {config.metrics_path}")
    logger.info("\nPattern Library:")
    logger.info(f"  Enabled: {config.pattern_library_enabled}")
    logger.info(f"  Pattern Sharing: {config.pattern_sharing}")
    logger.info(f"  Confidence Threshold: {config.pattern_confidence_threshold}")


def cmd_frameworks(args):
    """List and manage agent frameworks.

    Displays available agent frameworks with their capabilities and recommendations.

    Args:
        args: Namespace object from argparse with attributes:
            - all (bool): If True, show all frameworks including experimental.
            - recommend (str | None): Use case for framework recommendation.
            - json (bool): If True, output as JSON format.

    Returns:
        int: 0 on success, 1 on failure.
    """
    import json as json_mod

    try:
        from attune.agent_factory import AgentFactory
        from attune.agent_factory.framework import (
            get_framework_info,
            get_recommended_framework,
        )
    except ImportError:
        print("Agent Factory not available. Install empathy-framework with all dependencies.")
        return 1

    show_all = getattr(args, "all", False)
    recommend_use_case = getattr(args, "recommend", None)
    output_json = getattr(args, "json", False)

    if recommend_use_case:
        # Recommend a framework
        recommended = get_recommended_framework(recommend_use_case)
        info = get_framework_info(recommended)

        if output_json:
            print(
                json_mod.dumps(
                    {"use_case": recommend_use_case, "recommended": recommended.value, **info},
                    indent=2,
                )
            )
        else:
            print(f"\nRecommended framework for '{recommend_use_case}': {info['name']}")
            print(f"  Best for: {', '.join(info['best_for'])}")
            if info.get("install_command"):
                print(f"  Install: {info['install_command']}")
            print()
        return 0

    # List frameworks
    frameworks = AgentFactory.list_frameworks(installed_only=not show_all)

    if output_json:
        print(
            json_mod.dumps(
                [
                    {
                        "id": f["framework"].value,
                        "name": f["name"],
                        "installed": f["installed"],
                        "best_for": f["best_for"],
                        "install_command": f.get("install_command"),
                    }
                    for f in frameworks
                ],
                indent=2,
            )
        )
    else:
        print("\n" + "=" * 60)
        print("  AGENT FRAMEWORKS")
        print("=" * 60 + "\n")

        for f in frameworks:
            status = "INSTALLED" if f["installed"] else "not installed"
            print(f"  {f['name']:20} [{status}]")
            print(f"    Best for: {', '.join(f['best_for'][:3])}")
            if not f["installed"] and f.get("install_command"):
                print(f"    Install:  {f['install_command']}")
            print()

        print("-" * 60)
        print("  Use: Attune AIs --recommend <use_case>")
        print("  Use cases: general, rag, multi_agent, code_analysis")
        print("=" * 60 + "\n")

    return 0
