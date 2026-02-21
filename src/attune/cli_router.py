"""Hybrid CLI Router - Skills + Natural Language

Routes keywords and natural language to Claude Code skill invocations:
- Skills: /dev, /testing, /workflows (Claude Code Skill tool)
- Keywords: commit, test, security (maps to skills)
- Natural language: "commit my changes" (SmartRouter classification)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from attune.routing import SmartRouter
from attune.security.path_validation import _validate_file_path


@dataclass
class RoutingPreference:
    """User's learned routing preferences."""

    keyword: str
    skill: str
    args: str = ""
    usage_count: int = 0
    confidence: float = 1.0


class HybridRouter:
    """Routes user input to Claude Code skill invocations.

    Supports three input modes:
    1. Skills: /dev, /testing (returns skill invocation metadata)
    2. Keywords: commit, test (maps to skill invocations)
    3. Natural language: "I need to commit" (uses SmartRouter)

    Example:
        router = HybridRouter()

        # Skill invocation
        result = await router.route("/dev")
        # → {type: "skill", skill: "dev", args: "", instruction: "Use Skill tool..."}

        # Keyword to skill
        result = await router.route("commit")
        # → {type: "skill", skill: "dev", args: "commit", instruction: "Use Skill tool..."}

        # Natural language
        result = await router.route("I want to commit my changes")
        # → {type: "skill", skill: "dev", args: "commit", reasoning: "..."}
    """

    def __init__(self, preferences_path: str | None = None):
        """Initialize hybrid router.

        Args:
            preferences_path: Path to user preferences YAML
                Default: .attune/routing_preferences.yaml
        """
        self.preferences_path = Path(
            preferences_path or Path.home() / ".attune" / "routing_preferences.yaml"
        )
        self.smart_router = SmartRouter()
        self.preferences: dict[str, RoutingPreference] = {}

        # Keyword to skill mapping: keyword → (skill_name, args)
        self._keyword_to_skill = {
            # Dev commands → /dev skill
            "commit": ("dev", "commit"),
            "review": ("dev", "review"),
            "review-pr": ("dev", "review"),
            "refactor": ("dev", "refactor"),
            "perf": ("dev", "perf-audit"),
            "perf-audit": ("dev", "perf-audit"),
            "debug": ("dev", "debug"),
            # Testing commands → /testing skill
            "test": ("testing", "run"),
            "tests": ("testing", "run"),
            "coverage": ("testing", "coverage"),
            "generate-tests": ("testing", "gen"),
            "test-gen": ("testing", "gen"),
            "benchmark": ("testing", "benchmark"),
            # Workflow commands → /workflows skill
            "security": ("workflows", "run security-audit"),
            "security-audit": ("workflows", "run security-audit"),
            "bug-predict": ("workflows", "run bug-predict"),
            "bugs": ("workflows", "run bug-predict"),
            "perf-workflow": ("dev", "perf-audit"),
            # Doc commands → /docs skill
            "explain": ("docs", "explain"),
            "document": ("docs", "generate"),
            "overview": ("docs", "overview"),
            # SEO commands → /workflows skill
            "seo": ("workflows", "run seo-optimization --mode audit"),
            "seo-audit": ("workflows", "run seo-optimization --mode audit"),
            "seo-optimize": ("workflows", "run seo-optimization --mode fix"),
            # Plan commands → /plan skill
            "plan": ("plan", ""),
            # Release commands → /release skill
            "release": ("release", "prep"),
            "ship": ("release", "prep"),
            # Authentication strategy commands (CLI)
            "auth-setup": ("utilities", "uv run attune provider setup"),
            "auth-status": ("utilities", "uv run attune provider status"),
            "auth-recommend": ("utilities", "uv run attune provider recommend"),
            "auth-reset": ("utilities", "uv run attune provider reset"),
            "auth": ("utilities", "uv run attune provider status"),
            # Agent dashboard commands
            "dashboard": ("agent", "uv run attune dashboard start"),
            "agent-dashboard": ("agent", "uv run attune dashboard start"),
            # Dependency and research workflows
            "deps": ("workflows", "run dependency-check"),
            "dependency-check": ("workflows", "run dependency-check"),
            "research": ("workflows", "run research"),
            # Batch test generation (enhanced)
            "batch-tests": ("testing", "generate --batch"),
            "bulk-tests": ("testing", "generate --batch"),
            # Wizard commands → /wizard skill
            "wizard": ("wizard", ""),
            "wizard-debug": ("wizard", "run debug"),
            "wizard-test": ("wizard", "run test-gen"),
            "wizard-refactor": ("wizard", "run refactor"),
            "wizard-security": ("wizard", "run security"),
            "wizard-release": ("wizard", "run release-prep"),
            "wizard-create": ("wizard", "create"),
            "wizard-list": ("wizard", "list"),
            "wizard-edit": ("wizard", "edit"),
            "wizard-run": ("wizard", "run"),
            "create-wizard": ("wizard", "create"),
            "new-wizard": ("wizard", "create"),
            # Batch API commands → /batch skill
            "batch": ("batch", ""),
            "batch-submit": ("batch", "submit"),
            "submit-batch": ("batch", "submit"),
            "batch-status": ("batch", "status"),
            "batch-results": ("batch", "results"),
            "batch-wait": ("batch", "wait"),
            "bulk-process": ("batch", "submit"),
            "batch-api": ("batch", ""),
            # Brainstorm commands → /brainstorm skill
            "brainstorm": ("brainstorm", ""),
            "think": ("brainstorm", ""),
            "ideate": ("brainstorm", ""),
            "think-through": ("brainstorm", ""),
            "figure-out": ("brainstorm", ""),
            # Agent commands → /agent skill
            "agent": ("agent", ""),
            "agent-create": ("agent", "create"),
            "create-agent": ("agent", "create"),
            "new-agent": ("agent", "create"),
            "agent-list": ("agent", "list"),
            "agent-run": ("agent", "run"),
            "create-team": ("agent", "create-team"),
            "new-team": ("agent", "create-team"),
            "agent-team": ("agent", "create-team"),
        }

        # Hub descriptions for disambiguation
        self._hub_descriptions = {
            "dev": "Development tools (commits, reviews, refactoring)",
            "testing": "Test generation and coverage analysis",
            "workflows": "AI-powered workflows (security, bugs, performance)",
            "docs": "Documentation generation",
            "plan": "Development planning and architecture",
            "release": "Release preparation and publishing",
            "wizard": "Guided multi-step wizards with XML task decomposition",
            "agent": "Create and manage custom AI agents and teams",
            "batch": "Batch API processing (50% cost savings)",
            "utilities": "Utility tools (profiling, dependencies)",
            "brainstorm": "Guided brainstorming with structured discovery and plan output",
        }

        self._load_preferences()

    def _load_preferences(self) -> None:
        """Load user routing preferences from disk."""
        if not self.preferences_path.exists():
            return

        try:
            with open(self.preferences_path) as f:
                data = yaml.safe_load(f) or {}

            for keyword, pref_data in data.get("preferences", {}).items():
                # Handle backward compatibility: old format had "slash_command"
                if "slash_command" in pref_data:
                    # Migrate old format: "/dev commit" → skill="dev", args="commit"
                    slash_cmd = pref_data["slash_command"].lstrip("/")
                    parts = slash_cmd.split(maxsplit=1)
                    skill = parts[0] if parts else "help"
                    args = parts[1] if len(parts) > 1 else ""
                else:
                    # New format
                    skill = pref_data["skill"]
                    args = pref_data.get("args", "")

                self.preferences[keyword] = RoutingPreference(
                    keyword=keyword,
                    skill=skill,
                    args=args,
                    usage_count=pref_data.get("usage_count", 0),
                    confidence=pref_data.get("confidence", 1.0),
                )
        except Exception as e:
            print(f"Warning: Could not load routing preferences: {e}")

    def _save_preferences(self) -> None:
        """Save user routing preferences to disk."""
        self.preferences_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "preferences": {
                pref.keyword: {
                    "skill": pref.skill,
                    "args": pref.args,
                    "usage_count": pref.usage_count,
                    "confidence": pref.confidence,
                }
                for pref in self.preferences.values()
            }
        }

        validated_path = _validate_file_path(str(self.preferences_path))
        with open(validated_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    async def route(self, user_input: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Route user input to appropriate command or workflow.

        Args:
            user_input: User's input (slash command, keyword, or natural language)
            context: Optional context (current file, project info, etc.)

        Returns:
            Routing result with type, command/workflow, and metadata
        """
        user_input = user_input.strip()

        # Level 1: Slash command (direct execution)
        if user_input.startswith("/"):
            return self._route_slash_command(user_input)

        # Level 2: Single word or known command (inference)
        words = user_input.split()
        if len(words) <= 2:
            inferred = self._infer_command(user_input)
            if inferred:
                return inferred

        # Level 3: Natural language (SmartRouter)
        return await self._route_natural_language(user_input, context)

    def _route_slash_command(self, command: str) -> dict[str, Any]:
        """Route slash command to skill invocation.

        Args:
            command: Slash command like "/dev" or "/dev commit"

        Returns:
            Skill invocation instructions
        """
        parts = command[1:].split(maxsplit=1)  # Remove leading /
        skill = parts[0] if parts else "help"
        args = parts[1] if len(parts) > 1 else ""

        return {
            "type": "skill",
            "skill": skill,
            "args": args,
            "original": command,
            "confidence": 1.0,
            "instruction": f"Use Skill tool with skill='{skill}'"
            + (f", args='{args}'" if args else ""),
        }

    def _infer_command(self, keyword: str) -> dict[str, Any] | None:
        """Infer skill invocation from keyword or short phrase.

        Args:
            keyword: Single word or short phrase

        Returns:
            Skill invocation instructions if inference successful, None otherwise
        """
        keyword_lower = keyword.lower().strip()

        # Check learned preferences first
        if keyword_lower in self.preferences:
            pref = self.preferences[keyword_lower]

            # Update usage count
            pref.usage_count += 1
            self._save_preferences()

            return {
                "type": "skill",
                "skill": pref.skill,
                "args": pref.args,
                "original": keyword,
                "confidence": pref.confidence,
                "source": "learned",
                "instruction": f"Use Skill tool with skill='{pref.skill}'"
                + (f", args='{pref.args}'" if pref.args else ""),
            }

        # Check built-in keyword map
        if keyword_lower in self._keyword_to_skill:
            skill, args = self._keyword_to_skill[keyword_lower]
            return {
                "type": "skill",
                "skill": skill,
                "args": args,
                "original": keyword,
                "confidence": 0.9,
                "source": "builtin",
                "instruction": f"Use Skill tool with skill='{skill}'"
                + (f", args='{args}'" if args else ""),
            }

        # Check for hub names (show hub menu)
        if keyword_lower in self._hub_descriptions:
            return {
                "type": "skill",
                "skill": keyword_lower,
                "args": "",
                "original": keyword,
                "confidence": 1.0,
                "source": "hub",
                "instruction": f"Use Skill tool with skill='{keyword_lower}'",
            }

        return None

    async def _route_natural_language(
        self, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Route natural language input using SmartRouter.

        Args:
            text: Natural language input
            context: Optional context

        Returns:
            Skill invocation instructions based on SmartRouter decision
        """
        # Use SmartRouter for classification
        decision = await self.smart_router.route(text, context)

        # Map workflow to skill invocation
        skill, args = self._workflow_to_skill(decision.primary_workflow)

        return {
            "type": "skill",
            "skill": skill,
            "args": args,
            "workflow": decision.primary_workflow,
            "secondary_workflows": decision.secondary_workflows,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "original": text,
            "source": "natural_language",
            "instruction": f"Use Skill tool with skill='{skill}'"
            + (f", args='{args}'" if args else ""),
        }

    def _workflow_to_skill(self, workflow: str) -> tuple[str, str]:
        """Map workflow name to skill invocation.

        Args:
            workflow: Workflow name (e.g., "security-audit")

        Returns:
            Tuple of (skill_name, args)
        """
        # Workflow to skill mapping
        workflow_map = {
            "security-audit": ("workflows", "run security-audit"),
            "bug-predict": ("workflows", "run bug-predict"),
            "code-review": ("dev", "review"),
            "test-gen": ("testing", "gen"),
            "perf-audit": ("workflows", "run perf-audit"),
            "seo-optimization": ("workflows", "run seo-optimization"),
            "commit": ("dev", "commit"),
            "refactor": ("dev", "refactor"),
            "debug": ("dev", "debug"),
            "explain": ("docs", "explain"),
            "plan": ("plan", ""),
        }

        return workflow_map.get(workflow, ("workflows", f"run {workflow}"))

    def learn_preference(self, keyword: str, skill: str, args: str = "") -> None:
        """Learn user's routing preference.

        Args:
            keyword: Keyword user typed
            skill: Skill name that was invoked
            args: Arguments passed to skill
        """
        if keyword in self.preferences:
            pref = self.preferences[keyword]
            pref.usage_count += 1
            # Increase confidence with repeated usage
            pref.confidence = min(1.0, pref.confidence + 0.05)
        else:
            self.preferences[keyword] = RoutingPreference(
                keyword=keyword,
                skill=skill,
                args=args,
                usage_count=1,
                confidence=0.8,
            )

        self._save_preferences()

    def get_suggestions(self, partial: str) -> list[str]:
        """Get command suggestions based on partial input.

        Args:
            partial: Partial command input

        Returns:
            List of suggested keywords and skills
        """
        suggestions = []
        partial_lower = partial.lower()

        # Suggest keywords
        for keyword in self._keyword_to_skill.keys():
            if partial_lower in keyword:
                skill, args = self._keyword_to_skill[keyword]
                suggestions.append(f"{keyword} → /{skill} {args}".strip())

        # Suggest learned preferences
        for pref in self.preferences.values():
            if partial_lower in pref.keyword.lower():
                suggestions.append(f"{pref.keyword} → /{pref.skill} {pref.args}".strip())

        return suggestions[:5]  # Top 5 suggestions


# Convenience functions
async def route_user_input(
    user_input: str, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Quick routing helper.

    Args:
        user_input: User's input
        context: Optional context

    Returns:
        Routing result
    """
    router = HybridRouter()
    return await router.route(user_input, context)


def is_slash_command(text: str) -> bool:
    """Check if text is a slash command.

    Args:
        text: Input text

    Returns:
        True if slash command, False otherwise
    """
    return text.strip().startswith("/")
