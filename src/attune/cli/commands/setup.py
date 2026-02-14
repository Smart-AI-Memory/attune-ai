"""Setup commands for initialization and validation.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import sys

from attune.config import EmpathyConfig, _validate_file_path, load_config
from attune.logging_config import get_logger

logger = get_logger(__name__)


def cmd_init(args):
    """Initialize a new Attune AI project.

    Creates a configuration file with sensible defaults.

    Args:
        args: Namespace object from argparse with attributes:
            - format (str): Output format ('yaml' or 'json').
            - output (str | None): Output file path.

    Returns:
        None: Creates configuration file at specified path.

    Raises:
        ValueError: If output path is invalid or unsafe.
    """
    config_format = args.format
    output_path = args.output or f"attune.config.{config_format}"

    # Validate output path to prevent path traversal attacks
    validated_path = _validate_file_path(output_path)

    logger.info(f"Initializing new Attune AI project with format: {config_format}")

    # Create default config
    config = EmpathyConfig()

    # Save to file
    if config_format == "yaml":
        config.to_yaml(str(validated_path))
        logger.info(f"Created YAML configuration file: {output_path}")
        logger.info(f"✓ Created YAML configuration: {output_path}")
    elif config_format == "json":
        config.to_json(str(validated_path))
        logger.info(f"Created JSON configuration file: {validated_path}")
        logger.info(f"✓ Created JSON configuration: {validated_path}")

    logger.info("\nNext steps:")
    logger.info(f"  1. Edit {output_path} to customize settings")
    logger.info("  2. Use 'attune run' to start using the framework")


def cmd_validate(args):
    """Validate a configuration file.

    Loads and validates the specified configuration file.

    Args:
        args: Namespace object from argparse with attributes:
            - config (str): Path to configuration file to validate.

    Returns:
        None: Prints validation result. Exits with code 1 on failure.
    """
    filepath = args.config
    logger.info(f"Validating configuration file: {filepath}")

    try:
        config = load_config(filepath=filepath, use_env=False)
        config.validate()
        logger.info(f"Configuration validation successful: {filepath}")
        logger.info(f"✓ Configuration valid: {filepath}")
        logger.info(f"\n  User ID: {config.user_id}")
        logger.info(f"  Target Level: {config.target_level}")
        logger.info(f"  Confidence Threshold: {config.confidence_threshold}")
        logger.info(f"  Persistence Backend: {config.persistence_backend}")
        logger.info(f"  Metrics Enabled: {config.metrics_enabled}")
    except (OSError, FileNotFoundError) as e:
        # Config file not found or cannot be read
        logger.error(f"Configuration file error: {e}")
        logger.error(f"✗ Cannot read configuration file: {e}")
        sys.exit(1)
    except ValueError as e:
        # Invalid configuration values
        logger.error(f"Configuration validation failed: {e}")
        logger.error(f"✗ Configuration invalid: {e}")
        sys.exit(1)
    except Exception as e:
        # Unexpected errors during config validation
        logger.exception(f"Unexpected error validating configuration: {e}")
        logger.error(f"✗ Configuration invalid: {e}")
        sys.exit(1)


def cmd_setup(args):
    """Interactive setup workflow.

    Guides user through initial framework configuration step by step.
    Updated for Claude-native v5.0.0 (Anthropic-only).

    Args:
        args: Namespace object from argparse (no additional attributes used).

    Returns:
        None: Creates attune.config.yml with user's choices.
    """
    print("🧙 Attune AI Setup Workflow")
    print("=" * 50)
    print("\nI'll help you set up your Attune AI configuration.\n")

    # Step 1: Use case
    print("1. What's your primary use case?")
    print("   [1] Software development")
    print("   [2] Healthcare applications")
    print("   [3] Customer support")
    print("   [4] Other")

    use_case_choice = input("\nYour choice (1-4): ").strip()
    use_case_map = {
        "1": "software_development",
        "2": "healthcare",
        "3": "customer_support",
        "4": "general",
    }
    use_case = use_case_map.get(use_case_choice, "general")

    # Step 2: Target level
    print("\n2. What interaction level do you want to target?")
    print("   [1] Level 1 - Reactive (basic Q&A)")
    print("   [2] Level 2 - Guided (asks clarifying questions)")
    print("   [3] Level 3 - Proactive (offers improvements)")
    print("   [4] Level 4 - Anticipatory (predicts problems) ⭐ Recommended")
    print("   [5] Level 5 - Transformative (reshapes workflows)")

    level_choice = input("\nYour choice (1-5) [4]: ").strip() or "4"
    target_level = int(level_choice) if level_choice in ["1", "2", "3", "4", "5"] else 4

    # Step 3: LLM provider (Anthropic-only as of v5.0.0)
    print("\n3. LLM Provider: Anthropic Claude")
    print("   Attune AI is Claude-native and uses Anthropic exclusively.")

    from attune.models.provider_config import ProviderConfig

    config_detected = ProviderConfig.auto_detect()
    if config_detected.available_providers:
        print("   ✓ ANTHROPIC_API_KEY detected")
    else:
        print("   ⚠️  ANTHROPIC_API_KEY not detected")
        print("   Set your API key: export ANTHROPIC_API_KEY='your-key-here'")
        print("   Get key at: https://console.anthropic.com/settings/keys")

    # Step 4: User ID
    print("\n4. What user ID should we use?")
    user_id = input("User ID [default_user]: ").strip() or "default_user"

    # Generate configuration
    config = {
        "user_id": user_id,
        "target_level": target_level,
        "confidence_threshold": 0.75,
        "persistence_enabled": True,
        "persistence_backend": "sqlite",
        "persistence_path": ".attune",
        "metrics_enabled": True,
        "use_case": use_case,
        "llm_provider": "anthropic",
    }

    # Save configuration
    output_file = "attune.config.yml"
    print(f"\n5. Creating configuration file: {output_file}")

    # Write YAML config
    yaml_content = f"""# Attune AI Configuration
# Generated by setup workflow

# Core settings
user_id: "{config["user_id"]}"
target_level: {config["target_level"]}
confidence_threshold: {config["confidence_threshold"]}

# Use case
use_case: "{config["use_case"]}"

# Persistence
persistence_enabled: {str(config["persistence_enabled"]).lower()}
persistence_backend: "{config["persistence_backend"]}"
persistence_path: "{config["persistence_path"]}"

# Metrics
metrics_enabled: {str(config["metrics_enabled"]).lower()}

# LLM Provider (Claude-native v5.0.0)
llm_provider: "anthropic"
"""

    validated_output = _validate_file_path(output_file)
    with open(validated_output, "w") as f:
        f.write(yaml_content)

    print(f"  ✓ Created {validated_output}")

    print("\n" + "=" * 50)
    print("✅ Setup complete!")
    print("\nNext steps:")
    print(f"  1. Edit {output_file} to customize settings")

    if not config_detected.available_providers:
        print("  2. Set ANTHROPIC_API_KEY environment variable")
        print("  3. Run: attune run --config attune.config.yml")
    else:
        print("  2. Run: attune run --config attune.config.yml")

    print("\nHappy coding! 🧠✨\n")
