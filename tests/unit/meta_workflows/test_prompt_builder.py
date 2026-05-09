"""Unit tests for attune.meta_workflows.prompt_builder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from attune.meta_workflows.models import AgentSpec, TierStrategy
from attune.meta_workflows.prompt_builder import (
    build_agent_prompt,
    get_generic_instructions,
)


class TestGetGenericInstructions:
    def test_analyst_role(self):
        text = get_generic_instructions("data_analyst")
        assert "expert analyst" in text

    def test_analyze_keyword(self):
        text = get_generic_instructions("code-analyze")
        assert "expert analyst" in text

    def test_reviewer_role(self):
        text = get_generic_instructions("code_reviewer")
        assert "careful reviewer" in text

    def test_review_keyword(self):
        text = get_generic_instructions("review-bot")
        assert "careful reviewer" in text

    def test_generator_role(self):
        text = get_generic_instructions("test_generator")
        # 'test' matches first → testing specialist (because 'test' check is later
        # but order in the source: analyst > reviewer > generator/create/writer > validator > synthesizer > test > doc)
        # Let me re-check: line 48 'generator' check happens before 'test'.
        assert "skilled content generator" in text

    def test_create_keyword(self):
        text = get_generic_instructions("create_docs")
        # 'create' matches generator branch first; 'doc' would also match, but
        # generator/create/writer is checked before 'doc'.
        assert "skilled content generator" in text

    def test_writer_role(self):
        text = get_generic_instructions("content_writer")
        assert "skilled content generator" in text

    def test_validator_role(self):
        text = get_generic_instructions("schema_validator")
        assert "thorough validator" in text

    def test_verify_keyword(self):
        text = get_generic_instructions("verify_outputs")
        assert "thorough validator" in text

    def test_synthesizer_role(self):
        text = get_generic_instructions("data_synthesizer")
        assert "expert synthesizer" in text

    def test_combine_keyword(self):
        text = get_generic_instructions("combine_results")
        assert "expert synthesizer" in text

    def test_test_role(self):
        text = get_generic_instructions("integration_tester")
        assert "testing specialist" in text

    def test_doc_role(self):
        text = get_generic_instructions("api_documentor")
        assert "documentation specialist" in text

    def test_unknown_role_uses_default(self):
        text = get_generic_instructions("custom_xyz")
        assert "custom_xyz agent" in text
        assert "best practices" in text

    def test_uppercase_role_lowered(self):
        """role.lower() applied → uppercase still matches keywords."""
        text = get_generic_instructions("ANALYST")
        assert "expert analyst" in text


class TestBuildAgentPrompt:
    def test_with_known_template(self):
        """Lines 103-105: get_template returns a template → use its instructions."""
        spec = AgentSpec(
            role="reviewer",
            base_template="code_review",
            tier_strategy=TierStrategy.PROGRESSIVE,
        )

        fake_template = MagicMock()
        fake_template.default_instructions = "Review code carefully."

        with patch(
            "attune.meta_workflows.prompt_builder.get_template",
            return_value=fake_template,
        ):
            prompt = build_agent_prompt(spec)

        assert "Role: reviewer" in prompt
        assert "Review code carefully." in prompt

    def test_unknown_template_falls_back_to_generic(self, caplog):
        """Lines 106-109: template not found → log warning + generic prompt."""
        spec = AgentSpec(
            role="custom_role",
            base_template="missing-template",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )

        with (
            patch(
                "attune.meta_workflows.prompt_builder.get_template",
                return_value=None,
            ),
            caplog.at_level("WARNING"),
        ):
            prompt = build_agent_prompt(spec)

        assert any("not found" in r.message for r in caplog.records)
        # Default fallback (no keyword match)
        assert "custom_role agent" in prompt

    def test_includes_config_when_present(self):
        """Lines 118-119: agent.config truthy → include Configuration section."""
        spec = AgentSpec(
            role="r",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            config={"timeout": 30, "retries": 3},
        )
        with patch(
            "attune.meta_workflows.prompt_builder.get_template",
            return_value=None,
        ):
            prompt = build_agent_prompt(spec)
        assert "Configuration:" in prompt
        assert '"timeout": 30' in prompt

    def test_omits_config_when_empty(self):
        spec = AgentSpec(
            role="r",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        with patch(
            "attune.meta_workflows.prompt_builder.get_template",
            return_value=None,
        ):
            prompt = build_agent_prompt(spec)
        assert "Configuration:" not in prompt

    def test_includes_success_criteria(self):
        """Lines 122-123: success_criteria present → include section."""
        spec = AgentSpec(
            role="r",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            success_criteria=["fast", "accurate"],
        )
        with patch(
            "attune.meta_workflows.prompt_builder.get_template",
            return_value=None,
        ):
            prompt = build_agent_prompt(spec)
        assert "Success Criteria:" in prompt
        assert '"fast"' in prompt

    def test_includes_tools(self):
        """Lines 126-127: tools present → include 'Available Tools' line."""
        spec = AgentSpec(
            role="r",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["bash", "grep"],
        )
        with patch(
            "attune.meta_workflows.prompt_builder.get_template",
            return_value=None,
        ):
            prompt = build_agent_prompt(spec)
        assert "Available Tools: bash, grep" in prompt

    def test_omits_tools_when_empty(self):
        spec = AgentSpec(
            role="r",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        with patch(
            "attune.meta_workflows.prompt_builder.get_template",
            return_value=None,
        ):
            prompt = build_agent_prompt(spec)
        assert "Available Tools" not in prompt
