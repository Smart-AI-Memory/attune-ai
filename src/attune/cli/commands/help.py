"""Help and information commands for the CLI.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from importlib.metadata import version as get_version

from attune.logging_config import get_logger

from ..utils.data import CHEATSHEET, EXPLAIN_CONTENT
from ..utils.helpers import _file_exists, _show_achievements

logger = get_logger(__name__)


def cmd_version(args):
    """Display version information for Attune AI.

    Args:
        args: Namespace object from argparse (no additional attributes used).

    Returns:
        None: Prints version, copyright, and license information to stdout.
    """
    logger.info("Displaying version information")
    try:
        version = get_version("attune-ai")
    except Exception as e:
        # Package metadata not available or invalid (development install)
        logger.debug(f"Version not available: {e}")
        version = "unknown"
    logger.info(f"Attune v{version}")
    logger.info("Copyright 2025 Smart-AI-Memory")
    logger.info("Licensed under the Apache License, Version 2.0")
    logger.info("\n✨ Built with Claude Code + MemDocs + VS Code transformative stack")


def cmd_cheatsheet(args):
    """Display quick reference cheatsheet for all commands.

    Args:
        args: Namespace object from argparse with attributes:
            - category (str | None): Specific category to show (e.g., 'daily-workflow').
            - compact (bool): If True, show commands only without descriptions.

    Returns:
        None: Prints formatted cheatsheet to stdout.
    """
    category = getattr(args, "category", None)
    compact = getattr(args, "compact", False)

    print()
    print("=" * 60)
    print("  ATTUNE AI - QUICK REFERENCE")
    print("=" * 60)

    if category:
        # Show specific category
        category_title = category.replace("-", " ").title()
        if category_title in CHEATSHEET:
            print(f"\n  {category_title}")
            print("  " + "-" * 40)
            for cmd, desc in CHEATSHEET[category_title]:
                if compact:
                    print(f"  {cmd}")
                else:
                    print(f"  {cmd:35} {desc}")
        else:
            print(f"\n  Unknown category: {category}")
            print("  Available: " + ", ".join(k.lower().replace(" ", "-") for k in CHEATSHEET))
    else:
        # Show all categories
        for cat_name, commands in CHEATSHEET.items():
            print(f"\n  {cat_name}")
            print("  " + "-" * 40)
            for cmd, desc in commands:
                if compact:
                    print(f"  {cmd}")
                else:
                    print(f"  {cmd:35} {desc}")

    print()
    print("-" * 60)
    print("  Use: attune <command> --explain  for detailed explanation")
    print("  Use: attune onboard              for interactive tutorial")
    print("=" * 60)
    print()


def cmd_onboard(args):
    """Interactive onboarding tutorial for new users.

    Guides users through setup steps: init, learn, sync-claude, health check.

    Args:
        args: Namespace object from argparse with attributes:
            - step (int | None): Jump to specific tutorial step (1-5).
            - reset (bool): If True, reset onboarding progress.

    Returns:
        None: Prints tutorial content and tracks progress.
    """
    from attune.discovery import get_engine

    step = getattr(args, "step", None)
    reset = getattr(args, "reset", False)

    engine = get_engine()
    stats = engine.get_stats()

    if reset:
        # Reset onboarding progress
        engine.state["onboarding_step"] = 0
        engine.state["onboarding_completed"] = []
        engine._save()
        print("Onboarding progress reset.")
        return

    # Define onboarding steps
    steps = [
        {
            "title": "Welcome to Attune AI",
            "content": """
Welcome! Attune AI helps you build AI systems with 5 levels
of sophistication, from reactive responses to anticipatory assistance.

This tutorial will walk you through the key features.

Let's check your current setup first...
""",
            "check": lambda: True,
            "action": None,
        },
        {
            "title": "Step 1: Initialize Your Project",
            "content": """
First, let's create a configuration file for your project.

Run: attune init

This creates attune.config.yaml with sensible defaults.
Alternatively, use 'attune workflow' for an interactive setup.
""",
            "check": lambda: _file_exists("attune.config.yaml")
            or _file_exists("attune.config.yml"),
            "action": "attune init",
        },
        {
            "title": "Step 2: Learn From Your History",
            "content": """
Attune can learn patterns from your git commit history.
This teaches Claude about your codebase's patterns and past bugs.

Run: attune learn --analyze 10

This analyzes the last 10 commits and extracts:
- Bug fix patterns
- Security decisions
- Technical debt markers
""",
            "check": lambda: _file_exists("patterns/debugging.json"),
            "action": "attune learn --analyze 10",
        },
        {
            "title": "Step 3: Sync Patterns to Claude",
            "content": """
Now let's share what we learned with Claude Code.

Run: attune sync-claude

This creates .claude/rules/attune/ with markdown rules
that Claude Code automatically loads when you work in this directory.
""",
            "check": lambda: _file_exists(".claude/rules/attune/debugging.md"),
            "action": "attune sync-claude",
        },
        {
            "title": "Step 4: Check Code Health",
            "content": """
Let's run a quick health check on your codebase.

Run: attune health

This checks:
- Linting issues
- Type errors
- Formatting problems

Try 'attune health --fix' to auto-fix what's possible.
""",
            "check": lambda: stats.get("command_counts", {}).get("health", 0) > 0,
            "action": "attune health",
        },
        {
            "title": "Step 5: Daily Workflow",
            "content": """
You're almost there! Here's your recommended daily workflow:

MORNING:
  attune morning     - Get your priority briefing

BEFORE COMMITS:
  attune ship        - Validate before committing

WEEKLY:
  attune learn       - Update patterns from new commits
  attune sync-claude - Keep Claude current

You've completed the basics! Run 'attune cheatsheet' anytime
for a quick reference of all commands.
""",
            "check": lambda: True,
            "action": None,
        },
    ]

    # Determine current step
    current_step = engine.state.get("onboarding_step", 0)
    if step is not None:
        current_step = max(0, min(step - 1, len(steps) - 1))

    step_data = steps[current_step]

    # Display header
    print()
    print("=" * 60)
    print(f"  ONBOARDING ({current_step + 1}/{len(steps)})")
    print("=" * 60)
    print()
    print(f"  {step_data['title']}")
    print("  " + "-" * 50)
    print(step_data["content"])

    # Check if step is completed
    if step_data["check"]():
        if current_step < len(steps) - 1:
            print("  [DONE] This step is complete!")
            print()
            print(f"  Continue with: attune onboard --step {current_step + 2}")
            # Auto-advance
            engine.state["onboarding_step"] = current_step + 1
            engine._save()
        else:
            print("  Congratulations! You've completed the onboarding!")
            print()
            _show_achievements(engine)
    elif step_data["action"]:
        print(f"  NEXT: Run '{step_data['action']}'")
        print("        Then run 'attune onboard' to continue")

    print()
    print("-" * 60)
    print(f"  Progress: {'*' * (current_step + 1)}{'.' * (len(steps) - current_step - 1)}")
    print("=" * 60)
    print()


def cmd_explain(args):
    """Show detailed explanation for a command.

    Provides in-depth documentation about how specific commands work.

    Args:
        args: Namespace object from argparse with attributes:
            - command (str): Command name to explain (e.g., 'morning', 'ship').

    Returns:
        None: Prints detailed explanation to stdout.
    """
    command = args.command

    if command in EXPLAIN_CONTENT:
        print(EXPLAIN_CONTENT[command])
    else:
        available = ", ".join(EXPLAIN_CONTENT.keys())
        print(f"\nNo detailed explanation available for '{command}'")
        print(f"Available: {available}")
        print("\nTry: attune cheatsheet  for a quick reference")
        print()


def cmd_achievements(args):
    """Show user achievements and progress.

    Displays gamification stats including unlocked achievements and usage streaks.

    Args:
        args: Namespace object from argparse (no additional attributes used).

    Returns:
        None: Prints achievements and progress to stdout.
    """
    from attune.discovery import get_engine

    engine = get_engine()
    stats = engine.get_stats()

    print()
    print("=" * 60)
    print("  YOUR ATTUNE AI JOURNEY")
    print("=" * 60)
    print()

    # Stats summary
    print("  STATISTICS")
    print("  " + "-" * 40)
    print(f"  Total commands run:    {stats.get('total_commands', 0)}")
    print(f"  Days active:           {stats.get('days_active', 0)}")
    print(f"  Patterns learned:      {stats.get('patterns_learned', 0)}")
    shown = stats.get("tips_shown", 0)
    total = shown + stats.get("tips_remaining", 0)
    print(f"  Tips discovered:       {shown}/{total}")
    print()

    # Command breakdown
    cmd_counts = stats.get("command_counts", {})
    if cmd_counts:
        print("  COMMAND USAGE")
        print("  " + "-" * 40)
        sorted_cmds = sorted(cmd_counts.items(), key=lambda x: x[1], reverse=True)
        for cmd, count in sorted_cmds[:10]:
            bar = "*" * min(count, 20)
            print(f"  {cmd:15} {count:4} {bar}")
        print()

    # Achievements
    _show_achievements(engine)

    print("=" * 60)
    print()
