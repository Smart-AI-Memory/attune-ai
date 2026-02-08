"""Hybrid CLI Demo - Skills + Keywords + Natural Language

Demonstrates three levels of user interaction:
1. Claude Code Skills (/dev, /testing, /workflows)
2. Keywords (commit, test, security)
3. Natural language (automatic routing)

Usage:
    python examples/hybrid_cli_demo.py

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from attune.cli_router import HybridRouter


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


async def demo_level_1_discovery():
    """Level 1: Discovery using Claude Code skills."""
    print_section("LEVEL 1: Claude Code Skills")

    examples = [
        ("/help", "Show all available skills"),
        ("/dev", "Development tools"),
        ("/testing", "Testing commands"),
        ("/workflows", "AI-powered workflows"),
    ]

    router = HybridRouter()

    for command, description in examples:
        print(f"\n💡 {description}")
        print(f"   In Claude Code: {command}")

        result = await router.route(command)
        print(f"   → Type: {result['type']}")
        print(f"   → Skill: {result['skill']}")
        print(f"   → Args: {result['args'] or '(interactive menu)'}")
        print(f"   → Instruction: {result['instruction']}")


async def demo_level_2_structured():
    """Level 2: Keyword shortcuts for Skills."""
    print_section("LEVEL 2: Keywords → Skills")

    examples = [
        ("commit", "Create a git commit", "Skill: /dev commit"),
        ("test", "Run test suite", "Skill: /testing run"),
        ("security", "Run security audit", "Skill: /workflows run security-audit"),
        ("review", "Code review", "Skill: /dev review"),
    ]

    router = HybridRouter()

    for keyword, description, usage in examples:
        print(f"\n🎯 {description}")
        print(f"   Maps to: {usage}")

        result = await router.route(keyword)
        print(f"   → Type: {result['type']}")
        print(f"   → Skill: {result['skill']}")
        print(f"   → Args: {result['args']}")
        print(f"   → Confidence: {result['confidence']:.0%}")


async def demo_level_3_natural_language():
    """Level 3: Natural language routing."""
    print_section("LEVEL 3: Natural Language")

    examples = [
        ("I want to commit my changes", "Commit workflow"),
        ("Run security audit on auth.py", "Security analysis"),
        ("Generate tests for my new feature", "Test generation"),
        ("Something's slow in the API", "Performance audit"),
    ]

    router = HybridRouter()

    for text, description in examples:
        print(f'\n💬 User says: "{text}"')
        print(f"   Expected: {description}")

        result = await router.route(text)
        print(f"   → Type: {result['type']}")
        print(f"   → Skill: {result['skill']}")
        print(f"   → Args: {result['args']}")
        print(f"   → Confidence: {result['confidence']:.0%}")
        if result.get("reasoning"):
            print(f"   → Reasoning: {result['reasoning']}")


async def demo_user_preference_learning():
    """Demo: User preference learning."""
    print_section("DEMO: User Preference Learning")

    router = HybridRouter()

    print("\n📚 Learning from user behavior:")

    # Scenario: User types "deploy" and chooses "/release prep"
    print("\n1. User types: deploy")
    print("   Framework suggests: /release prep")
    print("   User confirms: y")

    # Learn this preference
    router.learn_preference("deploy", "/release prep")
    print("   ✅ Learned: deploy → /release prep")

    # Next time user types "deploy"
    print("\n2. User types: deploy (again)")
    result = await router.route("deploy")

    if result["type"] == "inferred" and result.get("source") == "learned":
        print(f"   ✅ Auto-inferred: {result['slash_equivalent']}")
        print(f"   → Confidence: {result['confidence']:.0%}")
        print(f"   → Usage count: {router.preferences['deploy'].usage_count}")
    else:
        print("   ℹ️  No learned preference yet")


async def demo_real_world_flow():
    """Demo: Real-world user flow."""
    print_section("DEMO: Real-World User Flow")

    print(
        """
📖 Scenario: Developer's typical workflow

1. Morning: Check what to work on (in Claude Code)
   /context status
   → Interactive skill menu shows: memory, current tasks, recent activity

2. Start work: Make code changes
   [... editing files ...]

3. Run tests quickly (in Claude Code):
   /testing run
   → Interactive test runner with options
   → Test suite executes

4. Tests fail - debug (in Claude Code):
   /dev debug "tests failing in auth.py"
   → Interactive Socratic debugging
   → Guides you through root cause analysis

5. Fix bugs, run tests again:
   /testing run
   → Tests pass ✅

6. Commit changes (in Claude Code):
   /dev commit
   → Guided interactive commit creation
   → Reviews changes, suggests message

7. Pre-commit hook triggers (automation):
   $ empathy workflow run security-audit
   → Runs: security-audit workflow
   → Finds 5 issues
   → Chain triggers: bug-predict (auto)
   → Chain suggests: code-review (asks approval)

8. End of day (in Claude Code):
   /learning evaluate
   → Analyzes session, suggests improvements

💡 Two interfaces, one framework:
   - Claude Code skills for interactive work (/dev, /testing, /workflows)
   - Workflow commands for automation (CI/CD, hooks, scripts)
   - Natural language routing maps to skills
   - Simple and focused! ✨
    """
    )


async def demo_suggestions():
    """Demo: Command suggestions."""
    print_section("DEMO: Command Suggestions")

    router = HybridRouter()

    print("\n🔍 Autocomplete suggestions:")

    partial_inputs = ["com", "test", "sec", "rev"]

    for partial in partial_inputs:
        suggestions = router.get_suggestions(partial)
        print(f"\n   User types: '{partial}'")
        print("   Suggestions:")
        for suggestion in suggestions[:3]:
            print(f"     → {suggestion}")


async def main():
    """Run all demos."""
    print("=" * 70)
    print("HYBRID CLI DEMO")
    print("Empathy Framework - Skills + Keywords + Natural Language")
    print("=" * 70)

    try:
        await demo_level_1_discovery()
        await demo_level_2_structured()
        await demo_level_3_natural_language()
        await demo_user_preference_learning()
        await demo_suggestions()
        await demo_real_world_flow()

        print("\n" + "=" * 70)
        print("✅ DEMO COMPLETE")
        print("=" * 70)

        print(
            """
🎯 Key Takeaways:

1. **Three Input Methods**
   - Claude Code skills: Interactive, guided (/dev, /testing, /workflows)
   - Natural language: Router maps to skills ("commit my changes" → /dev commit)
   - Workflow automation: CI/CD integration (empathy workflow run <name>)

2. **Learning System**
   - Framework learns your preferences
   - Repeated usage increases confidence
   - Personalized experience over time

3. **Real Integration**
   - Skills invoke Claude Code functionality
   - Natural language maps to real skill invocations
   - No fake slash commands - everything works!

4. **Choose Your Interface**
   - Interactive work: Use skills in Claude Code
   - Natural language: "commit my changes", "run security audit"
   - Automation/CI: empathy workflow run <name>
   - All methods work together seamlessly

📚 Next Steps:
1. In Claude Code: /help (discover all skills)
2. In Claude Code: /dev commit (interactive commit)
3. Natural language: "debug the login issue"
4. In CI/CD: empathy workflow run security-audit
        """
        )

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
