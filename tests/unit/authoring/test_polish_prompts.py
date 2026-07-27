"""Tests for attune.authoring.polish_prompts."""

from __future__ import annotations

import pytest

from attune.authoring.polish_prompts import (
    ANTI_PATTERNS,
    SYSTEM_PROMPTS,
    get_system_prompt,
)


class TestGetSystemPrompt:
    """Tests for get_system_prompt()."""

    @pytest.mark.parametrize(
        "kind",
        [
            "concept",
            "task",
            "reference",
            "error",
            "warning",
            "troubleshooting",
            "faq",
            "quickstart",
            "tip",
            "note",
            "comparison",
        ],
    )
    def test_known_kinds_include_base_rules(self, kind: str) -> None:
        prompt = get_system_prompt(kind)
        assert "Do not modify the YAML frontmatter" in prompt
        assert "Use second person" in prompt

    def test_concept_includes_concept_guidance(self) -> None:
        prompt = get_system_prompt("concept")
        assert "CONCEPT" in prompt

    def test_task_includes_task_guidance(self) -> None:
        prompt = get_system_prompt("task")
        assert "TASK" in prompt
        assert "Use ... when" in prompt or "Run ... when" in prompt

    def test_unknown_kind_falls_back_to_base_only(self) -> None:
        prompt = get_system_prompt("does-not-exist")
        # Base rules present...
        assert "Do not modify the YAML frontmatter" in prompt
        # ...but no kind-specific marker since the kind is unknown.
        assert "CONCEPT" not in prompt
        assert "TASK" not in prompt

    def test_anti_patterns_are_injected(self) -> None:
        prompt = get_system_prompt("concept")
        # Pull a sentinel anti-pattern phrase from the registered list
        # rather than hard-coding one, so the test follows updates to
        # the anti-pattern set automatically.
        first_anti = ANTI_PATTERNS["concept"][0]
        assert first_anti in prompt
        assert "phrases to avoid" in prompt

    def test_unknown_kind_omits_anti_patterns_section(self) -> None:
        prompt = get_system_prompt("does-not-exist")
        assert "phrases to avoid" not in prompt


class TestSystemPromptsRegistry:
    """The eagerly populated SYSTEM_PROMPTS dict."""

    def test_contains_all_known_kinds(self) -> None:
        # Every kind that has guidance should have a registered prompt.
        for kind in (
            "concept",
            "task",
            "reference",
            "error",
            "warning",
            "troubleshooting",
            "faq",
            "quickstart",
            "tip",
            "note",
            "comparison",
        ):
            assert kind in SYSTEM_PROMPTS, f"{kind} missing from SYSTEM_PROMPTS"

    def test_registry_matches_get_system_prompt(self) -> None:
        for kind, prompt in SYSTEM_PROMPTS.items():
            assert prompt == get_system_prompt(kind)
