"""Unit tests for CLI router module.

Tests HybridRouter class for routing user input to skill invocations.
Covers slash commands, keyword mapping, natural language routing, and preference learning.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.cli_router import (
    HybridRouter,
    RoutingPreference,
    is_slash_command,
    route_user_input,
)


@pytest.mark.unit
class TestRoutingPreference:
    """Test RoutingPreference dataclass."""

    def test_routing_preference_defaults(self):
        """Test RoutingPreference has correct default values."""
        pref = RoutingPreference(keyword="test", skill="dev")
        assert pref.keyword == "test"
        assert pref.skill == "dev"
        assert pref.args == ""
        assert pref.usage_count == 0
        assert pref.confidence == 1.0

    def test_routing_preference_with_all_fields(self):
        """Test RoutingPreference with all fields specified."""
        pref = RoutingPreference(
            keyword="commit",
            skill="dev",
            args="commit",
            usage_count=5,
            confidence=0.95,
        )
        assert pref.keyword == "commit"
        assert pref.skill == "dev"
        assert pref.args == "commit"
        assert pref.usage_count == 5
        assert pref.confidence == 0.95


@pytest.mark.unit
class TestHybridRouterInit:
    """Test HybridRouter initialization."""

    def test_init_default_preferences_path(self, tmp_path):
        """Test HybridRouter uses default preferences path."""
        router = HybridRouter()
        assert router.preferences_path is not None
        assert "routing_preferences.yaml" in str(router.preferences_path)

    def test_init_custom_preferences_path(self, tmp_path):
        """Test HybridRouter accepts custom preferences path."""
        custom_path = tmp_path / "custom_prefs.yaml"
        router = HybridRouter(preferences_path=str(custom_path))
        assert router.preferences_path == custom_path

    def test_init_empty_preferences(self, tmp_path):
        """Test HybridRouter starts with empty preferences when file doesn't exist."""
        custom_path = tmp_path / "nonexistent.yaml"
        router = HybridRouter(preferences_path=str(custom_path))
        assert router.preferences == {}

    def test_init_loads_existing_preferences(self, tmp_path):
        """Test HybridRouter loads existing preferences from YAML."""
        prefs_path = tmp_path / "prefs.yaml"
        prefs_path.write_text(
            """
preferences:
  mycommand:
    skill: testing
    args: run
    usage_count: 3
    confidence: 0.9
"""
        )
        router = HybridRouter(preferences_path=str(prefs_path))
        assert "mycommand" in router.preferences
        assert router.preferences["mycommand"].skill == "testing"
        assert router.preferences["mycommand"].args == "run"
        assert router.preferences["mycommand"].usage_count == 3

    def test_init_keyword_to_skill_mapping(self):
        """Test HybridRouter has built-in keyword mappings."""
        router = HybridRouter()
        assert "commit" in router._keyword_to_skill
        assert "test" in router._keyword_to_skill
        assert "security" in router._keyword_to_skill
        assert "debug" in router._keyword_to_skill

    def test_init_hub_descriptions(self):
        """Test HybridRouter has hub descriptions."""
        router = HybridRouter()
        assert "dev" in router._hub_descriptions
        assert "testing" in router._hub_descriptions
        assert "workflows" in router._hub_descriptions


@pytest.mark.unit
class TestRouteSlashCommand:
    """Test slash command routing."""

    def test_route_slash_command_simple(self):
        """Test routing simple slash command."""
        router = HybridRouter()
        result = router._route_slash_command("/dev")
        assert result["type"] == "skill"
        assert result["skill"] == "dev"
        assert result["args"] == ""
        assert result["confidence"] == 1.0

    def test_route_slash_command_with_args(self):
        """Test routing slash command with arguments."""
        router = HybridRouter()
        result = router._route_slash_command("/dev commit")
        assert result["type"] == "skill"
        assert result["skill"] == "dev"
        assert result["args"] == "commit"

    def test_route_slash_command_with_multiple_args(self):
        """Test routing slash command with multiple arguments."""
        router = HybridRouter()
        result = router._route_slash_command("/workflows run security-audit")
        assert result["skill"] == "workflows"
        assert result["args"] == "run security-audit"

    def test_route_slash_command_instruction(self):
        """Test slash command includes skill tool instruction."""
        router = HybridRouter()
        result = router._route_slash_command("/testing gen")
        assert "instruction" in result
        assert "Skill tool" in result["instruction"]
        assert "testing" in result["instruction"]


@pytest.mark.unit
class TestInferCommand:
    """Test keyword inference."""

    def test_infer_command_builtin_keyword(self):
        """Test inferring command from built-in keyword."""
        router = HybridRouter()
        result = router._infer_command("commit")
        assert result is not None
        assert result["type"] == "skill"
        assert result["skill"] == "dev"
        assert result["args"] == "commit"
        assert result["source"] == "builtin"

    def test_infer_command_test_keyword(self):
        """Test inferring test command."""
        router = HybridRouter()
        result = router._infer_command("test")
        assert result is not None
        assert result["skill"] == "testing"
        assert result["args"] == "run"

    def test_infer_command_security_keyword(self):
        """Test inferring security workflow."""
        router = HybridRouter()
        result = router._infer_command("security")
        assert result is not None
        assert result["skill"] == "workflows"
        assert "security-audit" in result["args"]

    def test_infer_command_hub_name(self):
        """Test inferring command from hub name."""
        router = HybridRouter()
        result = router._infer_command("dev")
        assert result is not None
        assert result["skill"] == "dev"
        assert result["source"] == "hub"

    def test_infer_command_unknown_keyword(self):
        """Test unknown keyword returns None."""
        router = HybridRouter()
        result = router._infer_command("unknown_xyz_123")
        assert result is None

    def test_infer_command_case_insensitive(self):
        """Test keyword inference is case insensitive."""
        router = HybridRouter()
        result = router._infer_command("COMMIT")
        assert result is not None
        assert result["skill"] == "dev"

    def test_infer_command_learned_preference(self, tmp_path):
        """Test learned preference takes priority."""
        prefs_path = tmp_path / "prefs.yaml"
        prefs_path.write_text(
            """
preferences:
  mykey:
    skill: custom
    args: custom-args
    usage_count: 5
    confidence: 0.9
"""
        )
        router = HybridRouter(preferences_path=str(prefs_path))
        result = router._infer_command("mykey")
        assert result is not None
        assert result["skill"] == "custom"
        assert result["args"] == "custom-args"
        assert result["source"] == "learned"


@pytest.mark.unit
class TestRouteAsync:
    """Test async route method."""

    @pytest.mark.asyncio
    async def test_route_slash_command(self):
        """Test routing slash command through main route method."""
        router = HybridRouter()
        result = await router.route("/dev commit")
        assert result["type"] == "skill"
        assert result["skill"] == "dev"
        assert result["args"] == "commit"

    @pytest.mark.asyncio
    async def test_route_single_keyword(self):
        """Test routing single keyword."""
        router = HybridRouter()
        result = await router.route("commit")
        assert result["type"] == "skill"
        assert result["skill"] == "dev"

    @pytest.mark.asyncio
    async def test_route_two_word_keyword(self):
        """Test routing two-word keyword."""
        router = HybridRouter()
        result = await router.route("review-pr")
        assert result["type"] == "skill"
        assert result["skill"] == "dev"

    @pytest.mark.asyncio
    async def test_route_strips_whitespace(self):
        """Test route method strips whitespace."""
        router = HybridRouter()
        result = await router.route("  /dev  ")
        assert result["skill"] == "dev"

    @pytest.mark.asyncio
    async def test_route_natural_language(self):
        """Test routing natural language falls through to SmartRouter."""
        router = HybridRouter()
        with patch.object(router.smart_router, "route", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = MagicMock(
                primary_workflow="code-review",
                secondary_workflows=[],
                confidence=0.85,
                reasoning="Test reasoning",
            )
            result = await router.route("please review my code changes")
            assert result["type"] == "skill"
            assert "source" in result
            assert result["source"] == "natural_language"


@pytest.mark.unit
class TestLearnPreference:
    """Test preference learning."""

    def test_learn_preference_new(self, tmp_path):
        """Test learning new preference."""
        prefs_path = tmp_path / "prefs.yaml"
        router = HybridRouter(preferences_path=str(prefs_path))

        router.learn_preference("mykey", "myskill", "myargs")

        assert "mykey" in router.preferences
        assert router.preferences["mykey"].skill == "myskill"
        assert router.preferences["mykey"].args == "myargs"
        assert router.preferences["mykey"].usage_count == 1
        assert router.preferences["mykey"].confidence == 0.8

    def test_learn_preference_updates_existing(self, tmp_path):
        """Test learning updates existing preference."""
        prefs_path = tmp_path / "prefs.yaml"
        router = HybridRouter(preferences_path=str(prefs_path))

        router.learn_preference("mykey", "skill1", "args1")
        initial_count = router.preferences["mykey"].usage_count
        initial_confidence = router.preferences["mykey"].confidence

        router.learn_preference("mykey", "skill1", "args1")

        assert router.preferences["mykey"].usage_count == initial_count + 1
        assert router.preferences["mykey"].confidence > initial_confidence

    def test_learn_preference_saves_to_disk(self, tmp_path):
        """Test learning preference persists to disk."""
        prefs_path = tmp_path / "prefs.yaml"
        router = HybridRouter(preferences_path=str(prefs_path))

        router.learn_preference("persist", "testskill", "testargs")

        assert prefs_path.exists()
        content = prefs_path.read_text()
        assert "persist" in content
        assert "testskill" in content

    def test_learn_preference_confidence_cap(self, tmp_path):
        """Test confidence doesn't exceed 1.0."""
        prefs_path = tmp_path / "prefs.yaml"
        router = HybridRouter(preferences_path=str(prefs_path))

        # Learn same preference many times
        for _ in range(50):
            router.learn_preference("cap", "skill", "args")

        assert router.preferences["cap"].confidence <= 1.0


@pytest.mark.unit
class TestGetSuggestions:
    """Test autocomplete suggestions."""

    def test_get_suggestions_partial_match(self):
        """Test suggestions for partial keyword match."""
        router = HybridRouter()
        suggestions = router.get_suggestions("com")
        assert len(suggestions) > 0
        assert any("commit" in s for s in suggestions)

    def test_get_suggestions_empty_for_no_match(self):
        """Test no suggestions for non-matching input."""
        router = HybridRouter()
        suggestions = router.get_suggestions("xyz123abc")
        assert len(suggestions) == 0

    def test_get_suggestions_limit(self):
        """Test suggestions are limited to 5."""
        router = HybridRouter()
        suggestions = router.get_suggestions("t")  # Many matches expected
        assert len(suggestions) <= 5

    def test_get_suggestions_includes_learned(self, tmp_path):
        """Test suggestions include learned preferences."""
        prefs_path = tmp_path / "prefs.yaml"
        prefs_path.write_text(
            """
preferences:
  custom:
    skill: myskill
    args: myargs
    usage_count: 1
    confidence: 0.8
"""
        )
        router = HybridRouter(preferences_path=str(prefs_path))
        suggestions = router.get_suggestions("cust")
        assert any("custom" in s for s in suggestions)


@pytest.mark.unit
class TestWorkflowToSkill:
    """Test workflow to skill mapping."""

    def test_workflow_to_skill_known_workflow(self):
        """Test mapping known workflow to skill."""
        router = HybridRouter()
        skill, args = router._workflow_to_skill("security-audit")
        assert skill == "workflows"
        assert "security-audit" in args

    def test_workflow_to_skill_code_review(self):
        """Test code-review maps to dev skill."""
        router = HybridRouter()
        skill, args = router._workflow_to_skill("code-review")
        assert skill == "dev"
        assert args == "review"

    def test_workflow_to_skill_unknown(self):
        """Test unknown workflow uses default mapping."""
        router = HybridRouter()
        skill, args = router._workflow_to_skill("unknown-workflow")
        assert skill == "workflows"
        assert "unknown-workflow" in args


@pytest.mark.unit
class TestIsSlashCommand:
    """Test is_slash_command helper function."""

    def test_is_slash_command_true(self):
        """Test detecting slash commands."""
        assert is_slash_command("/dev") is True
        assert is_slash_command("/testing run") is True
        assert is_slash_command("  /dev  ") is True

    def test_is_slash_command_false(self):
        """Test non-slash commands."""
        assert is_slash_command("commit") is False
        assert is_slash_command("run tests") is False
        assert is_slash_command("") is False


@pytest.mark.unit
class TestRouteUserInput:
    """Test route_user_input convenience function."""

    @pytest.mark.asyncio
    async def test_route_user_input_slash_command(self):
        """Test convenience function with slash command."""
        result = await route_user_input("/dev commit")
        assert result["type"] == "skill"
        assert result["skill"] == "dev"

    @pytest.mark.asyncio
    async def test_route_user_input_keyword(self):
        """Test convenience function with keyword."""
        result = await route_user_input("commit")
        assert result["type"] == "skill"


@pytest.mark.unit
class TestKeywordMappings:
    """Test specific keyword mappings."""

    def test_dev_commands(self):
        """Test dev-related keyword mappings."""
        router = HybridRouter()
        dev_keywords = ["commit", "review", "refactor", "debug", "perf"]
        for kw in dev_keywords:
            result = router._infer_command(kw)
            assert result is not None, f"Keyword '{kw}' should be mapped"

    def test_testing_commands(self):
        """Test testing-related keyword mappings."""
        router = HybridRouter()
        test_keywords = ["test", "tests", "coverage", "benchmark"]
        for kw in test_keywords:
            result = router._infer_command(kw)
            assert result is not None, f"Keyword '{kw}' should be mapped"
            assert result["skill"] == "testing"

    def test_workflow_commands(self):
        """Test workflow-related keyword mappings."""
        router = HybridRouter()
        workflow_keywords = ["security", "bugs", "seo"]
        for kw in workflow_keywords:
            result = router._infer_command(kw)
            assert result is not None, f"Keyword '{kw}' should be mapped"
            assert result["skill"] == "workflows"

    def test_plan_commands(self):
        """Test plan-related keyword mappings."""
        router = HybridRouter()
        result = router._infer_command("plan")
        assert result is not None
        assert result["skill"] == "plan"

        result = router._infer_command("tdd")
        assert result is not None
        assert result["skill"] == "plan"


@pytest.mark.unit
class TestBackwardCompatibility:
    """Test backward compatibility with old preference format."""

    def test_loads_old_slash_command_format(self, tmp_path):
        """Test loading old format with slash_command field."""
        prefs_path = tmp_path / "prefs.yaml"
        prefs_path.write_text(
            """
preferences:
  oldkey:
    slash_command: /dev commit
    usage_count: 5
    confidence: 0.9
"""
        )
        router = HybridRouter(preferences_path=str(prefs_path))
        assert "oldkey" in router.preferences
        assert router.preferences["oldkey"].skill == "dev"
        assert router.preferences["oldkey"].args == "commit"
