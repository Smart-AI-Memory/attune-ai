"""Workflow commands for multi-model execution.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
import inspect
import json as json_mod
from pathlib import Path

from attune.config import _validate_file_path
from attune.logging_config import get_logger
from attune.workflows import get_workflow
from attune.workflows import list_workflows as get_workflow_list
from attune.workflows.config import WorkflowConfig, create_example_config
from attune.workflows.migration import (
    WORKFLOW_ALIASES,
    resolve_workflow_migration,
    show_migration_tip,
)

logger = get_logger(__name__)


def _extract_workflow_content(final_output):
    """Extract readable content from workflow final_output.

    Workflows return their results in various formats - this extracts
    the actual content users want to see.
    """
    if final_output is None:
        return None

    # If it's already a string, return it
    if isinstance(final_output, str):
        return final_output

    # If it's a dict, try to extract meaningful content
    if isinstance(final_output, dict):
        # Common keys that contain the main output
        # formatted_report is first - preferred for security-audit and other formatted outputs
        content_keys = [
            "formatted_report",  # Human-readable formatted output (security-audit, etc.)
            "answer",
            "synthesis",
            "result",
            "output",
            "content",
            "report",
            "summary",
            "analysis",
            "review",
            "documentation",
            "response",
            "recommendations",
            "findings",
            "tests",
            "plan",
        ]
        for key in content_keys:
            if final_output.get(key):
                val = final_output[key]
                if isinstance(val, str):
                    return val
                if isinstance(val, dict):
                    # Recursively extract
                    return _extract_workflow_content(val)

        # If no common key found, try to format the dict nicely
        # Look for any string value that's substantial
        for _key, val in final_output.items():
            if isinstance(val, str) and len(val) > 100:
                return val

        # Last resort: return a formatted version
        return json_mod.dumps(final_output, indent=2)

    # For lists or other types, convert to string
    return str(final_output)


def cmd_workflow(args):
    """Multi-model workflow management and execution.

    Supports listing, describing, and running workflows with tier-based models.

    Args:
        args: Namespace object from argparse with attributes:
            - action (str): Action to perform ('list', 'describe', 'run').
            - name (str | None): Workflow name (for describe/run).
            - input (str | None): JSON input for workflow execution.
            - provider (str | None): LLM provider override.
            - json (bool): If True, output as JSON format.
            - use_recommended_tier (bool): Enable tier fallback.
            - write_tests (bool): For test-gen, write tests to files.
            - output_dir (str | None): For test-gen, output directory.

    Returns:
        int | None: 0 on success, 1 on failure, None for list action.
    """
    action = args.action

    if action == "list":
        # List available workflows
        workflows = get_workflow_list()

        if args.json:
            print(json_mod.dumps(workflows, indent=2))
        else:
            print("\n" + "=" * 60)
            print("  MULTI-MODEL WORKFLOWS")
            print("=" * 60 + "\n")

            for wf in workflows:
                print(f"  {wf['name']:15} {wf['description']}")
                tier_map = wf.get("tier_map", {})
                if tier_map:
                    stages = " → ".join(
                        f"{s}({tier_map[s]})" for s in wf["stages"] if s in tier_map
                    )
                else:
                    stages = " → ".join(wf["stages"])
                print(f"    Stages: {stages}")
                print()

            print("-" * 60)
            print("  Use: attune workflow describe <name>")
            print("  Use: attune workflow run <name> [--input JSON]")
            print("=" * 60 + "\n")

    elif action == "describe":
        # Describe a specific workflow
        name = args.name
        if not name:
            print("Error: workflow name required")
            print("Usage: attune workflow describe <name>")
            return 1

        try:
            # Check for workflow migration (describe still works with old names)
            if name in WORKFLOW_ALIASES:
                resolved_name, migration_kwargs, _ = resolve_workflow_migration(name)
                if resolved_name and resolved_name != name:
                    print(f"ℹ️  '{name}' is now '{resolved_name}'")
                    name = resolved_name

            workflow_cls = get_workflow(name)
            provider = getattr(args, "provider", None)
            workflow = workflow_cls(provider=provider)

            # Get actual provider from workflow (may come from config)
            actual_provider = getattr(workflow, "_provider_str", provider or "anthropic")

            if args.json:
                info = {
                    "name": workflow.name,
                    "description": workflow.description,
                    "provider": actual_provider,
                    "stages": workflow.stages,
                    "tier_map": {k: v.value for k, v in workflow.tier_map.items()},
                    "models": {
                        stage: workflow.get_model_for_tier(workflow.tier_map[stage])
                        for stage in workflow.stages
                    },
                }
                print(json_mod.dumps(info, indent=2))
            else:
                print(f"Provider: {actual_provider}")
                print(workflow.describe())

        except KeyError:
            print(f"Error: Workflow '{name}' not found")
            print("\nRun 'attune workflow list' to see available workflows")
            return 1

    elif action == "run":
        # Run a workflow
        name = args.name
        if not name:
            print("Error: workflow name required")
            print('Usage: attune workflow run <name> --input \'{"key": "value"}\'')
            return 1

        try:
            # Check for workflow migration (environment-aware)
            original_name = name
            migration_kwargs = {}
            was_migrated = False

            if name in WORKFLOW_ALIASES:
                name, migration_kwargs, was_migrated = resolve_workflow_migration(name)
                if was_migrated:
                    logger.info(f"Migrated '{original_name}' -> '{name}' with {migration_kwargs}")

            workflow_cls = get_workflow(name)

            # Get provider from CLI arg, or fall back to config's default_provider
            if args.provider:
                provider = args.provider
            else:
                wf_config = WorkflowConfig.load()
                provider = wf_config.default_provider

            # Initialize workflow with provider and optional tier fallback
            # Note: Not all workflows support enable_tier_fallback, so we check first
            use_tier_fallback = getattr(args, "use_recommended_tier", False)

            # Get the workflow's __init__ signature to know what params it accepts
            init_sig = inspect.signature(workflow_cls.__init__)
            init_params = set(init_sig.parameters.keys())

            workflow_kwargs = {}

            # Add provider if supported
            if "provider" in init_params:
                workflow_kwargs["provider"] = provider

            # Add enable_tier_fallback only if the workflow supports it
            if "enable_tier_fallback" in init_params and use_tier_fallback:
                workflow_kwargs["enable_tier_fallback"] = use_tier_fallback

            # Add health-check specific parameters
            if name == "health-check" and "health_score_threshold" in init_params:
                health_score_threshold = getattr(args, "health_score_threshold", 100)
                workflow_kwargs["health_score_threshold"] = health_score_threshold

            # Merge migration kwargs (from workflow consolidation)
            for key, value in migration_kwargs.items():
                if not key.startswith("_") and key in init_params:
                    workflow_kwargs[key] = value

            workflow = workflow_cls(**workflow_kwargs)

            # Parse input
            input_data = {}
            if args.input:
                input_data = json_mod.loads(args.input)

            # Add test-gen specific flags to input_data (only for test-gen workflow)
            if name == "test-gen":
                if getattr(args, "write_tests", False):
                    input_data["write_tests"] = True
                if getattr(args, "output_dir", None):
                    input_data["output_dir"] = args.output_dir

            # Only print header when not in JSON mode
            if not args.json:
                print(f"\n Running workflow: {name} (provider: {provider})")
                print("=" * 50)

            # Execute workflow
            result = asyncio.run(workflow.execute(**input_data))

            # Extract the actual content - handle different result types
            if hasattr(result, "final_output"):
                output_content = _extract_workflow_content(result.final_output)
            elif hasattr(result, "metadata") and isinstance(result.metadata, dict):
                # Check for formatted_report in metadata (e.g., HealthCheckResult)
                output_content = result.metadata.get("formatted_report")
                if not output_content and hasattr(result, "summary"):
                    output_content = result.summary
            elif hasattr(result, "summary"):
                output_content = result.summary
            else:
                output_content = str(result)

            # Get timing - handle different attribute names
            duration_ms = getattr(result, "total_duration_ms", None)
            if duration_ms is None and hasattr(result, "duration_seconds"):
                duration_ms = int(result.duration_seconds * 1000)

            # Get cost info if available (check cost_report first, then direct cost attribute)
            cost_report = getattr(result, "cost_report", None)
            if cost_report and hasattr(cost_report, "total_cost"):
                total_cost = cost_report.total_cost
                savings = getattr(cost_report, "savings", 0.0)
            else:
                # Fall back to direct cost attribute (e.g., CodeReviewPipelineResult)
                total_cost = getattr(result, "cost", 0.0)
                savings = 0.0

            if args.json:
                # Extract error from various result types
                error = getattr(result, "error", None)
                is_successful = getattr(result, "success", getattr(result, "approved", True))
                if not error and not is_successful:
                    blockers = getattr(result, "blockers", [])
                    if blockers:
                        error = "; ".join(blockers)
                    else:
                        metadata = getattr(result, "metadata", {})
                        error = metadata.get("error") if isinstance(metadata, dict) else None

                # JSON output includes both content and metadata
                # Include final_output for programmatic access (VSCode panels, etc.)
                raw_final_output = getattr(result, "final_output", None)
                if raw_final_output and isinstance(raw_final_output, dict):
                    # Make a copy to avoid modifying the original
                    final_output_serializable = {}
                    for k, v in raw_final_output.items():
                        # Skip non-serializable items
                        if isinstance(v, set):
                            final_output_serializable[k] = list(v)
                        elif v is None or isinstance(v, str | int | float | bool | list | dict):
                            final_output_serializable[k] = v
                        else:
                            try:
                                final_output_serializable[k] = str(v)
                            except Exception as e:  # noqa: BLE001
                                # INTENTIONAL: Silently skip any non-serializable objects
                                # This is a best-effort serialization for JSON output
                                # We cannot predict all possible object types users might return
                                logger.debug(f"Cannot serialize field {k}: {e}")
                                pass
                else:
                    final_output_serializable = None

                output = {
                    "success": is_successful,
                    "output": output_content,
                    "final_output": final_output_serializable,
                    "cost": total_cost,
                    "savings": savings,
                    "duration_ms": duration_ms or 0,
                    "error": error,
                }
                print(json_mod.dumps(output, indent=2))
            # Display the actual results - this is what users want to see
            else:
                # Show tier progression if tier fallback was used
                if use_tier_fallback and hasattr(workflow, "_tier_progression"):
                    tier_progression = workflow._tier_progression
                    if tier_progression:
                        print("\n" + "=" * 60)
                        print("  TIER PROGRESSION (Intelligent Fallback)")
                        print("=" * 60)

                        # Group by stage
                        stage_tiers: dict[str, list[tuple[str, bool]]] = {}
                        for stage, tier, success in tier_progression:
                            if stage not in stage_tiers:
                                stage_tiers[stage] = []
                            stage_tiers[stage].append((tier, success))

                        # Display progression for each stage
                        for stage, attempts in stage_tiers.items():
                            status = "✓" if any(success for _, success in attempts) else "✗"
                            print(f"\n{status} Stage: {stage}")

                            for idx, (tier, success) in enumerate(attempts, 1):
                                attempt_status = "✓ SUCCESS" if success else "✗ FAILED"
                                if idx == 1:
                                    print(f"  Attempt {idx}: {tier.upper():8} → {attempt_status}")
                                else:
                                    prev_tier = attempts[idx - 2][0]
                                    print(
                                        f"  Attempt {idx}: {tier.upper():8} → {attempt_status} "
                                        f"(upgraded from {prev_tier.upper()})"
                                    )

                        # Calculate cost savings (only if result has stages attribute)
                        if hasattr(result, "stages") and result.stages:
                            actual_cost = sum(stage.cost for stage in result.stages if stage.cost)
                            # Estimate what cost would be if all stages used PREMIUM
                            premium_cost = actual_cost * 3  # Conservative estimate

                            savings = premium_cost - actual_cost
                            savings_pct = (savings / premium_cost * 100) if premium_cost > 0 else 0

                            print("\n" + "-" * 60)
                            print("💰 Cost Savings:")
                            print(f"  Actual cost:   ${actual_cost:.4f}")
                            print(f"  Premium cost:  ${premium_cost:.4f} (if all PREMIUM)")
                            print(f"  Savings:       ${savings:.4f} ({savings_pct:.1f}%)")
                        print("=" * 60 + "\n")

                # Display workflow result
                # Handle different result types (success, approved, etc.)
                is_successful = getattr(result, "success", getattr(result, "approved", True))
                if is_successful:
                    if output_content:
                        print(f"\n{output_content}\n")
                    else:
                        print("\n✓ Workflow completed successfully.\n")
                else:
                    # Extract error from various result types
                    error_msg = getattr(result, "error", None)
                    if not error_msg:
                        # Check for blockers (CodeReviewPipelineResult)
                        blockers = getattr(result, "blockers", [])
                        if blockers:
                            error_msg = "; ".join(blockers)
                        else:
                            # Check metadata for error
                            metadata = getattr(result, "metadata", {})
                            error_msg = (
                                metadata.get("error") if isinstance(metadata, dict) else None
                            )
                    error_msg = error_msg or "Unknown error"
                    print(f"\n✗ Workflow failed: {error_msg}\n")

            # Show migration tip if workflow was migrated (helps users learn new syntax)
            if was_migrated and original_name != name:
                show_migration_tip(original_name, name, migration_kwargs)

        except KeyError:
            print(f"Error: Workflow '{name}' not found")
            print("\nRun 'attune workflow list' to see available workflows")
            return 1
        except json_mod.JSONDecodeError as e:
            print(f"Error parsing input JSON: {e}")
            print('\nExpected valid JSON, e.g.: --input \'{"key": "value"}\'')
            print("Make sure to use single quotes around JSON and double quotes inside")
            return 1

    elif action == "config":
        # Generate or show workflow configuration
        config_path = Path(".attune/workflows.yaml")

        if config_path.exists() and not getattr(args, "force", False):
            print(f"Config already exists: {config_path}")
            print("Use --force to overwrite")
            print("\nCurrent configuration:")
            print("-" * 40)
            config = WorkflowConfig.load()
            print(f"  Default provider: {config.default_provider}")
            if config.workflow_providers:
                print("  Workflow providers:")
                for wf, prov in config.workflow_providers.items():
                    print(f"    {wf}: {prov}")
            if config.custom_models:
                print("  Custom models configured")
            return 0

        # Create config directory and file
        config_path.parent.mkdir(parents=True, exist_ok=True)
        validated_config_path = _validate_file_path(str(config_path))
        validated_config_path.write_text(create_example_config())
        print(f"✓ Created workflow config: {validated_config_path}")
        print("\nEdit this file to customize:")
        print("  - Default provider (anthropic, openai, ollama)")
        print("  - Per-workflow provider overrides")
        print("  - Custom model mappings")
        print("  - Model pricing")
        print("\nOr use environment variables:")
        print("  ATTUNE_WORKFLOW_PROVIDER=openai")
        print("  ATTUNE_MODEL_PREMIUM=gpt-5.2")

    else:
        print(f"Unknown action: {action}")
        print("Available: list, describe, run, config")
        return 1

    return 0


def cmd_workflow_legacy(args):
    """Interactive setup workflow (DEPRECATED).

    DEPRECATED: This command is deprecated in favor of 'attune init'.
    It will be removed in version 5.0.

    Guides user through initial framework configuration step by step.

    Args:
        args: Namespace object from argparse (no additional attributes used).

    Returns:
        None: Creates attune.config.yml with user's choices.
    """
    import warnings

    warnings.warn(
        "The 'workflow-setup' command is deprecated. "
        "Use 'attune init' instead. "
        "This command will be removed in version 5.0.",
        DeprecationWarning,
        stacklevel=2,
    )

    print("⚠️  DEPRECATED: This command is being replaced by 'attune init'")
    print("    Please use 'attune init' for interactive setup.")
    print("    This command will be removed in version 5.0.\n")
    print("=" * 60)

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

    # Step 3: LLM provider
    print("\n3. Which LLM provider will you use?")
    print("   [1] Anthropic Claude ⭐ Recommended")
    print("   [2] OpenAI GPT-4")
    print("   [3] Google Gemini (2M context)")
    print("   [4] Local (Ollama)")
    print("   [5] Hybrid (mix best models from each provider)")
    print("   [6] Skip (configure later)")

    llm_choice = input("\nYour choice (1-6) [1]: ").strip() or "1"
    llm_map = {
        "1": "anthropic",
        "2": "openai",
        "3": "google",
        "4": "ollama",
        "5": "hybrid",
        "6": None,
    }
    llm_provider = llm_map.get(llm_choice, "anthropic")

    # If hybrid selected, launch interactive tier selection
    if llm_provider == "hybrid":
        from attune.models.provider_config import configure_hybrid_interactive

        configure_hybrid_interactive()
        llm_provider = None  # Already saved by hybrid config

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
    }

    if llm_provider:
        config["llm_provider"] = llm_provider

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
"""

    if llm_provider:
        yaml_content += f"""
# LLM Provider
llm_provider: "{llm_provider}"
"""

    validated_output = _validate_file_path(output_file)
    with open(validated_output, "w") as f:
        f.write(yaml_content)

    print(f"  ✓ Created {validated_output}")

    print("\n" + "=" * 50)
    print("✅ Setup complete!")
    print("\nNext steps:")
    print(f"  1. Edit {output_file} to customize settings")

    if llm_provider in ["anthropic", "openai", "google"]:
        env_var_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        env_var = env_var_map.get(llm_provider, "API_KEY")
        print(f"  2. Set {env_var} environment variable")

    print("  3. Run: attune run --config attune.config.yml")
    print("\nHappy coding! 🧠✨\n")
