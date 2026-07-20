"""Interactive Agent Team Creation Example.

Demonstrates using the meta-orchestrator's interactive mode to get
user input when automatic selection has low confidence.

Usage:
    # With Claude Code (IPC mode):
    export CLAUDE_CODE_SESSION=1
    python examples/interactive_team_creation.py

    # With CLI handler:
    python examples/interactive_team_creation.py --mode cli

    # Automatic mode (no prompts):
    python examples/interactive_team_creation.py --mode auto

Requirements:
    pip install attune-ai
"""

import asyncio
import argparse
from attune.orchestration import MetaOrchestrator
from attune.tools import set_ask_user_question_handler


def cli_handler(questions):
    """Simple CLI handler for interactive questions."""
    print("\n" + "=" * 60)
    print("INTERACTIVE TEAM CREATION")
    print("=" * 60)

    answers = {}

    for q in questions:
        print(f"\n{q['question']}\n")

        options = q["options"]
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt['label']}")
            if opt["description"]:
                # Wrap description
                desc = opt["description"]
                print(f"     {desc}")

        print()
        if q["multiSelect"]:
            print("Select multiple (comma-separated numbers) or press Enter for all:")
            choice = input("> ").strip()

            if not choice:
                selected = [opt["label"] for opt in options]
            else:
                indices = [int(i.strip()) - 1 for i in choice.split(",")]
                selected = [options[i]["label"] for i in indices]

            answers[q["header"]] = selected
        else:
            print("Select one (enter number):")
            while True:
                try:
                    choice = input("> ").strip()
                    idx = int(choice) - 1
                    if 0 <= idx < len(options):
                        answers[q["header"]] = options[idx]["label"]
                        break
                    print("Invalid choice, try again:")
                except (ValueError, IndexError):
                    print("Invalid input, try again:")

    print("\n" + "=" * 60)
    return answers


def demo_interactive_simple():
    """Demo 1: Simple task (high confidence, automatic)."""
    print("\n" + "=" * 60)
    print("DEMO 1: Simple Task (High Confidence)")
    print("=" * 60)

    orchestrator = MetaOrchestrator()

    # Simple task → High confidence → Automatic
    plan = orchestrator.analyze_and_compose(
        task="Run tests and report coverage",
        context={},
        interactive=True,  # Won't prompt - confidence is high
    )

    print(f"\nResult: {plan.strategy.value}")
    print(f"Agents: {[a.role for a in plan.agents]}")
    print(f"Estimated duration: {plan.estimated_duration}s")
    print("\n→ No prompt shown (confidence >= 0.8)")


def demo_interactive_complex():
    """Demo 2: Complex task (low confidence, prompts user)."""
    print("\n" + "=" * 60)
    print("DEMO 2: Complex Task (Low Confidence)")
    print("=" * 60)

    orchestrator = MetaOrchestrator()

    # Complex ambiguous task → Low confidence → Prompt user
    try:
        plan = orchestrator.analyze_and_compose(
            task="Prepare comprehensive system architecture redesign",
            context={},
            interactive=True,  # Will prompt user
        )

        print(f"\nResult: {plan.strategy.value}")
        print(f"Agents: {[a.role for a in plan.agents]}")
        print(f"Estimated duration: {plan.estimated_duration}s")

    except NotImplementedError as e:
        print(f"\n⚠️  {e}")
        print("\nFalling back to automatic mode...")

        plan = orchestrator.analyze_and_compose(
            task="Prepare comprehensive system architecture redesign", context={}, interactive=False
        )

        print(f"\nResult: {plan.strategy.value}")
        print(f"Agents: {[a.role for a in plan.agents]}")


def demo_interactive_with_tools():
    """Demo 3: Single agent with tools (tool-enhanced pattern)."""
    print("\n" + "=" * 60)
    print("DEMO 3: Single Agent + Tools (Tool-Enhanced)")
    print("=" * 60)

    orchestrator = MetaOrchestrator()

    # Tools in context → Should select TOOL_ENHANCED if 1 agent
    plan = orchestrator.analyze_and_compose(
        task="Analyze Python code files",
        context={
            "tools": [
                {"name": "read_file", "description": "Read file contents"},
                {"name": "analyze_ast", "description": "Parse Python AST"},
            ]
        },
        interactive=True,
    )

    print(f"\nResult: {plan.strategy.value}")
    print(f"Agents: {[a.role for a in plan.agents]}")
    print(f"Tools provided: {len(plan.quality_gates.get('tools', []))} tools")


def main():
    """Main demo runner."""
    parser = argparse.ArgumentParser(description="Interactive agent team creation demo")
    parser.add_argument(
        "--mode",
        choices=["cli", "ipc", "auto"],
        default="ipc",
        help="Integration mode (cli=CLI prompts, ipc=Claude Code IPC, auto=automatic)",
    )
    parser.add_argument(
        "--demo",
        choices=["1", "2", "3", "all"],
        default="all",
        help="Which demo to run (1=simple, 2=complex, 3=tools, all=all demos)",
    )

    args = parser.parse_args()

    # Setup handler based on mode
    if args.mode == "cli":
        print("Using CLI handler for prompts")
        set_ask_user_question_handler(cli_handler)
    elif args.mode == "auto":
        print("Using automatic mode (no prompts)")
        # Don't set handler, don't enable IPC
    else:
        print("Using Claude Code IPC mode")
        # IPC will be auto-detected if in Claude Code environment

    # Run demos
    if args.demo == "all":
        demo_interactive_simple()
        demo_interactive_complex()
        demo_interactive_with_tools()
    elif args.demo == "1":
        demo_interactive_simple()
    elif args.demo == "2":
        demo_interactive_complex()
    elif args.demo == "3":
        demo_interactive_with_tools()

    print("\n" + "=" * 60)
    print("DEMOS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
