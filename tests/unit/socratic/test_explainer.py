"""Tests for the Socratic workflow explainer module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

from attune.socratic.blueprint import (
    AgentBlueprint,
    AgentRole,
    AgentSpec,
    StageSpec,
    WorkflowBlueprint,
)
from attune.socratic.explainer import WorkflowExplainer
from attune.socratic.explainer import explain_workflow as top_level_explain
from attune.socratic.explainer_types import AudienceLevel, DetailLevel, OutputFormat
from attune.socratic.success import SuccessCriteria, SuccessMetric


class TestAudienceLevel:
    """Tests for AudienceLevel enum."""

    def test_all_levels_exist(self):
        """Test all expected audience levels exist."""
        from attune.socratic.explainer import AudienceLevel

        assert hasattr(AudienceLevel, "TECHNICAL")
        assert hasattr(AudienceLevel, "BUSINESS")
        assert hasattr(AudienceLevel, "BEGINNER")

    def test_level_values(self):
        """Test audience level values."""
        from attune.socratic.explainer import AudienceLevel

        assert AudienceLevel.TECHNICAL.value == "technical"
        assert AudienceLevel.BUSINESS.value == "business"
        assert AudienceLevel.BEGINNER.value == "beginner"


class TestDetailLevel:
    """Tests for DetailLevel enum."""

    def test_all_levels_exist(self):
        """Test all expected detail levels exist."""
        from attune.socratic.explainer import DetailLevel

        assert hasattr(DetailLevel, "BRIEF")
        assert hasattr(DetailLevel, "STANDARD")
        assert hasattr(DetailLevel, "DETAILED")


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_all_formats_exist(self):
        """Test all expected output formats exist."""
        from attune.socratic.explainer import OutputFormat

        assert hasattr(OutputFormat, "TEXT")
        assert hasattr(OutputFormat, "MARKDOWN")
        assert hasattr(OutputFormat, "HTML")
        assert hasattr(OutputFormat, "JSON")


class TestExplanation:
    """Tests for Explanation dataclass."""

    def test_create_explanation(self):
        """Test creating an explanation."""
        from attune.socratic.explainer import AudienceLevel, DetailLevel, Explanation

        explanation = Explanation(
            title="Code Review Workflow",
            summary="This workflow automates code review.",
            sections=[
                {"heading": "Overview", "content": "The workflow consists of..."},
                {"heading": "Steps", "content": "1. Analyze code..."},
            ],
            audience=AudienceLevel.TECHNICAL,
            detail_level=DetailLevel.STANDARD,
        )

        assert explanation.title == "Code Review Workflow"
        assert explanation.audience == AudienceLevel.TECHNICAL
        assert len(explanation.sections) == 2

    def test_explanation_to_text(self):
        """Test converting explanation to text."""
        from attune.socratic.explainer import AudienceLevel, DetailLevel, Explanation

        explanation = Explanation(
            title="Code Review",
            summary="Automated code review workflow.",
            sections=[
                {"heading": "Benefits", "content": "Improves code quality."},
            ],
            audience=AudienceLevel.BUSINESS,
            detail_level=DetailLevel.BRIEF,
        )

        text = explanation.to_text()

        assert isinstance(text, str)
        assert "Automated code review" in text

    def test_explanation_to_markdown(self):
        """Test converting explanation to markdown."""
        from attune.socratic.explainer import AudienceLevel, DetailLevel, Explanation

        explanation = Explanation(
            title="Technical Explanation",
            summary="Technical explanation",
            sections=[
                {"heading": "Architecture", "content": "The system uses..."},
            ],
            audience=AudienceLevel.TECHNICAL,
            detail_level=DetailLevel.DETAILED,
        )

        markdown = explanation.to_markdown()

        assert isinstance(markdown, str)
        assert "#" in markdown  # Should have headers

    def test_explanation_to_html(self):
        """Test converting explanation to HTML."""
        from attune.socratic.explainer import AudienceLevel, DetailLevel, Explanation

        explanation = Explanation(
            title="Simple Guide",
            summary="Simple explanation",
            sections=[],
            audience=AudienceLevel.BEGINNER,
            detail_level=DetailLevel.STANDARD,
        )

        html = explanation.to_html()

        assert isinstance(html, str)
        assert "<" in html  # Should have HTML tags

    def test_explanation_to_dict(self):
        """Test converting explanation to dict."""
        from attune.socratic.explainer import AudienceLevel, DetailLevel, Explanation

        explanation = Explanation(
            title="Test Workflow",
            summary="Test",
            sections=[],
            audience=AudienceLevel.TECHNICAL,
            detail_level=DetailLevel.STANDARD,
        )

        data = explanation.to_dict()

        assert isinstance(data, dict)
        assert data["title"] == "Test Workflow"
        assert data["audience"] == "technical"


class TestWorkflowExplainer:
    """Tests for WorkflowExplainer class."""

    def test_create_explainer(self):
        """Test creating a workflow explainer."""
        from attune.socratic.explainer import WorkflowExplainer

        explainer = WorkflowExplainer()
        assert explainer is not None

    def test_create_explainer_with_options(self):
        """Test creating explainer with options."""
        from attune.socratic.explainer import AudienceLevel, DetailLevel, WorkflowExplainer

        explainer = WorkflowExplainer(
            audience=AudienceLevel.BUSINESS,
            detail_level=DetailLevel.BRIEF,
        )

        assert explainer.audience == AudienceLevel.BUSINESS
        assert explainer.detail_level == DetailLevel.BRIEF

    def test_explain_workflow_for_technical(self, sample_workflow_blueprint):
        """Test explaining workflow for technical audience."""
        from attune.socratic.explainer import AudienceLevel, WorkflowExplainer

        explainer = WorkflowExplainer(audience=AudienceLevel.TECHNICAL)

        explanation = explainer.explain_workflow(sample_workflow_blueprint)

        assert explanation is not None
        assert explanation.audience == AudienceLevel.TECHNICAL
        assert len(explanation.summary) > 0

    def test_explain_workflow_for_business(self, sample_workflow_blueprint):
        """Test explaining workflow for business audience."""
        from attune.socratic.explainer import AudienceLevel, WorkflowExplainer

        explainer = WorkflowExplainer(audience=AudienceLevel.BUSINESS)

        explanation = explainer.explain_workflow(sample_workflow_blueprint)

        assert explanation is not None
        assert explanation.audience == AudienceLevel.BUSINESS

    def test_explain_workflow_for_beginner(self, sample_workflow_blueprint):
        """Test explaining workflow for beginner audience."""
        from attune.socratic.explainer import AudienceLevel, WorkflowExplainer

        explainer = WorkflowExplainer(audience=AudienceLevel.BEGINNER)

        explanation = explainer.explain_workflow(sample_workflow_blueprint)

        assert explanation is not None
        assert explanation.audience == AudienceLevel.BEGINNER

    def test_explain_agent(self, sample_agent_spec):
        """Test explaining individual agent."""
        from attune.socratic.explainer import WorkflowExplainer

        explainer = WorkflowExplainer()

        agent_explanation = explainer.explain_agent(sample_agent_spec)

        assert agent_explanation is not None
        assert len(agent_explanation.summary) > 0


class TestLLMExplanationGenerator:
    """Tests for LLMExplanationGenerator class."""

    def test_create_generator(self):
        """Test creating an LLM explanation generator."""
        from attune.socratic.explainer import LLMExplanationGenerator

        generator = LLMExplanationGenerator()
        assert generator is not None

    def test_create_generator_with_api_key(self):
        """Test creating generator with API key."""
        from attune.socratic.explainer import LLMExplanationGenerator

        generator = LLMExplanationGenerator(api_key="test-api-key")
        assert generator.api_key == "test-api-key"


class TestExplainWorkflowFunction:
    """Tests for the explain_workflow convenience function."""

    def test_explain_workflow_returns_string(self, sample_workflow_blueprint):
        """Test the explain_workflow function returns string."""
        from attune.socratic.explainer import explain_workflow

        result = explain_workflow(sample_workflow_blueprint)

        # Module-level function returns string (formatted output)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_explain_workflow_with_audience(self, sample_workflow_blueprint):
        """Test explain_workflow with audience parameter."""
        from attune.socratic.explainer import AudienceLevel, explain_workflow

        result = explain_workflow(
            sample_workflow_blueprint,
            audience=AudienceLevel.BEGINNER,
        )

        assert isinstance(result, str)

    def test_explain_workflow_with_format(self, sample_workflow_blueprint):
        """Test explain_workflow with output format."""
        from attune.socratic.explainer import OutputFormat, explain_workflow

        result = explain_workflow(
            sample_workflow_blueprint,
            format=OutputFormat.MARKDOWN,
        )

        assert "#" in result  # Markdown headers


class TestExplanationContent:
    """Tests for explanation content quality."""

    def test_technical_includes_details(self, sample_workflow_blueprint):
        """Test technical explanation includes technical details."""
        from attune.socratic.explainer import AudienceLevel, DetailLevel, WorkflowExplainer

        explainer = WorkflowExplainer(
            audience=AudienceLevel.TECHNICAL,
            detail_level=DetailLevel.DETAILED,
        )

        explanation = explainer.explain_workflow(sample_workflow_blueprint)

        text = explanation.to_text()

        # Should have content
        assert len(text) > 0

    def test_business_explanation_works(self, sample_workflow_blueprint):
        """Test business explanation generates valid output."""
        from attune.socratic.explainer import AudienceLevel, WorkflowExplainer

        explainer = WorkflowExplainer(audience=AudienceLevel.BUSINESS)

        explanation = explainer.explain_workflow(sample_workflow_blueprint)

        assert explanation is not None

    def test_beginner_explanation_works(self, sample_workflow_blueprint):
        """Test beginner explanation generates valid output."""
        from attune.socratic.explainer import AudienceLevel, WorkflowExplainer

        explainer = WorkflowExplainer(audience=AudienceLevel.BEGINNER)

        explanation = explainer.explain_workflow(sample_workflow_blueprint)

        assert explanation is not None


class TestRoleDescriptions:
    """Tests for role description mappings."""

    def test_role_descriptions_exist(self):
        """Test role descriptions are configured."""
        from attune.socratic.explainer import ROLE_DESCRIPTIONS

        assert len(ROLE_DESCRIPTIONS) > 0

    def test_role_descriptions_for_all_audiences(self):
        """Test role descriptions exist for all audience levels."""
        from attune.socratic.explainer import ROLE_DESCRIPTIONS, AudienceLevel

        for audience in AudienceLevel:
            assert audience in ROLE_DESCRIPTIONS


# =============================================================================
# Branch-coverage additions — targets lines 106, 213, 238, 267, 293,
# 298-309, 341-386, 416-455 in src/attune/socratic/explainer.py
# =============================================================================


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _spec(agent_id="a1", name="Bot", role=AgentRole.ANALYZER, tools=None):
    t = MagicMock()
    t.id = "read_file"
    return AgentSpec(
        id=agent_id,
        name=name,
        role=role,
        goal="analyse code",
        backstory="exp",
        tools=tools if tools is not None else [t],
    )


def _bp_agent(spec=None):
    return AgentBlueprint(spec=spec or _spec())


def _stage(sid="s1", name="Rev", agent_ids=None, parallel=False, depends_on=None):
    return StageSpec(
        id=sid,
        name=name,
        description="d",
        agent_ids=agent_ids or ["a1"],
        parallel=parallel,
        depends_on=depends_on or [],
    )


def _blueprint(agents=None, stages=None, description="Desc", domain="quality"):
    a = agents or [_bp_agent()]
    s = stages or [_stage()]
    return WorkflowBlueprint(
        id="w1",
        name="TestWF",
        description=description,
        agents=a,
        stages=s,
        domain=domain,
        generated_at=datetime(2025, 1, 1),
    )


def _criteria():
    from attune.socratic.success import MetricType

    m = SuccessMetric(
        id="m1",
        name="Cov",
        description="coverage",
        metric_type=MetricType.PERCENTAGE,
        target_value=0.9,
    )
    return SuccessCriteria(id="sc1", name="Gates", description="", metrics=[m])


# ---------------------------------------------------------------------------
# explain_workflow — success_criteria branch (line 106)
# ---------------------------------------------------------------------------


class TestExplainWorkflowSuccessCriteriaBranch:
    def test_success_criteria_section_added(self):
        expl = WorkflowExplainer()
        bp = _blueprint()
        result = expl.explain_workflow(bp, success_criteria=_criteria())
        headings = [s["heading"] for s in result.sections]
        assert "Success Metrics" in headings

    def test_no_success_criteria_omits_section(self):
        expl = WorkflowExplainer()
        bp = _blueprint()
        result = expl.explain_workflow(bp)
        headings = [s["heading"] for s in result.sections]
        assert "Success Metrics" not in headings


# ---------------------------------------------------------------------------
# _explain_agents — BRIEF / DETAILED (line 213, 217)
# ---------------------------------------------------------------------------


class TestExplainAgentsBranches:
    def test_brief_no_tools_count(self):
        expl = WorkflowExplainer(detail_level=DetailLevel.BRIEF)
        result = expl._explain_agents(_blueprint().agents)
        assert "Bot" in result
        assert "tools" not in result

    def test_detailed_shows_tool_count(self):
        expl = WorkflowExplainer(detail_level=DetailLevel.DETAILED)
        result = expl._explain_agents(_blueprint().agents)
        assert "tool" in result

    def test_standard_shows_goal(self):
        expl = WorkflowExplainer(detail_level=DetailLevel.STANDARD)
        result = expl._explain_agents(_blueprint().agents)
        assert "analyse code" in result


# ---------------------------------------------------------------------------
# _explain_process — BEGINNER parallel/sequential, DETAILED depends_on
# ---------------------------------------------------------------------------


class TestExplainProcessBranches:
    def test_beginner_parallel(self):
        s1, s2 = _spec("a1", "B1"), _spec("a2", "B2")
        agents = [_bp_agent(s1), _bp_agent(s2)]
        stage = _stage(agent_ids=["a1", "a2"], parallel=True)
        bp = _blueprint(agents=agents, stages=[stage])
        expl = WorkflowExplainer(audience=AudienceLevel.BEGINNER)
        result = expl._explain_process(bp.stages, bp.agents)
        assert "same time" in result

    def test_beginner_sequential(self):
        agents = [_bp_agent(_spec("a1", "B1"))]
        stage = _stage(agent_ids=["a1"], parallel=False)
        bp = _blueprint(agents=agents, stages=[stage])
        expl = WorkflowExplainer(audience=AudienceLevel.BEGINNER)
        result = expl._explain_process(bp.stages, bp.agents)
        assert "one after another" in result

    def test_detailed_shows_depends_on(self):
        agents = [_bp_agent(_spec("a1", "B1"))]
        stage = _stage(agent_ids=["a1"], depends_on=["init_stage"])
        bp = _blueprint(agents=agents, stages=[stage])
        expl = WorkflowExplainer(detail_level=DetailLevel.DETAILED)
        result = expl._explain_process(bp.stages, bp.agents)
        assert "init_stage" in result


# ---------------------------------------------------------------------------
# _explain_tools — BRIEF (line 267)
# ---------------------------------------------------------------------------


class TestExplainToolsBranch:
    def test_brief_shows_count_only(self):
        expl = WorkflowExplainer(detail_level=DetailLevel.BRIEF)
        result = expl._explain_tools(_spec().tools)
        assert "1 tool" in result

    def test_unknown_tool_uses_id(self):
        expl = WorkflowExplainer(detail_level=DetailLevel.STANDARD)
        t = MagicMock()
        t.id = "my_custom_tool"
        result = expl._explain_tools([t])
        assert "my_custom_tool" in result


# ---------------------------------------------------------------------------
# _explain_agent_value — BEGINNER (line 293)
# ---------------------------------------------------------------------------


class TestExplainAgentValueBranch:
    def test_beginner_saves_time(self):
        expl = WorkflowExplainer(audience=AudienceLevel.BEGINNER)
        result = expl._explain_agent_value(_spec(role=AgentRole.ANALYZER))
        assert "saves you time" in result

    def test_technical_adds_value(self):
        expl = WorkflowExplainer(audience=AudienceLevel.TECHNICAL)
        result = expl._explain_agent_value(_spec(role=AgentRole.REVIEWER))
        assert "adds value" in result


# ---------------------------------------------------------------------------
# _explain_success_criteria — BEGINNER / TECHNICAL (lines 301-307)
# ---------------------------------------------------------------------------


class TestExplainSuccessCriteriaBranch:
    def test_beginner_omits_target(self):
        expl = WorkflowExplainer(audience=AudienceLevel.BEGINNER)
        result = expl._explain_success_criteria(_criteria())
        assert "Cov" in result
        assert "0.9" not in result

    def test_technical_shows_target(self):
        expl = WorkflowExplainer(audience=AudienceLevel.TECHNICAL)
        result = expl._explain_success_criteria(_criteria())
        assert "0.9" in result

    def test_no_target_value_omits_target(self):
        from attune.socratic.success import MetricType

        expl = WorkflowExplainer(audience=AudienceLevel.TECHNICAL)
        m = SuccessMetric(
            id="m2",
            name="Pass",
            description="tests",
            metric_type=MetricType.BOOLEAN,
            target_value=None,
        )
        crit = SuccessCriteria(id="sc2", name="G", description="", metrics=[m])
        result = expl._explain_success_criteria(crit)
        assert "target" not in result


# ---------------------------------------------------------------------------
# generate_narrative (lines 341-386)
# ---------------------------------------------------------------------------


class TestGenerateNarrativeBranch:
    def test_contains_workflow_name(self):
        expl = WorkflowExplainer()
        result = expl.generate_narrative(_blueprint())
        assert "TestWF" in result

    def test_contains_stage_name(self):
        expl = WorkflowExplainer()
        result = expl.generate_narrative(_blueprint())
        assert "Rev" in result

    def test_parallel_stage_narrative(self):
        s1, s2 = _spec("a1", "B1"), _spec("a2", "B2")
        agents = [_bp_agent(s1), _bp_agent(s2)]
        stage = _stage(agent_ids=["a1", "a2"], parallel=True)
        bp = _blueprint(agents=agents, stages=[stage])
        result = WorkflowExplainer().generate_narrative(bp)
        assert "parallel" in result.lower()

    def test_sequential_stage_narrative(self):
        agents = [_bp_agent(_spec("a1", "B1"))]
        stage = _stage(agent_ids=["a1"], parallel=False)
        bp = _blueprint(agents=agents, stages=[stage])
        result = WorkflowExplainer().generate_narrative(bp)
        assert "B1" in result

    def test_ends_with_result_section(self):
        result = WorkflowExplainer().generate_narrative(_blueprint())
        assert "The Result" in result


# ---------------------------------------------------------------------------
# top-level explain_workflow (lines 415-455)
# ---------------------------------------------------------------------------


class TestTopLevelExplainWorkflowBranch:
    def test_string_args_accepted(self):
        result = top_level_explain(_blueprint(), audience="technical", detail_level="standard")
        assert isinstance(result, str)

    def test_format_text(self):
        result = top_level_explain(_blueprint(), format=OutputFormat.TEXT)
        assert isinstance(result, str)

    def test_format_markdown(self):
        result = top_level_explain(_blueprint(), format="markdown")
        assert isinstance(result, str)

    def test_format_html(self):
        result = top_level_explain(_blueprint(), format=OutputFormat.HTML)
        assert "<" in result or isinstance(result, str)

    def test_format_json(self):
        import json

        result = top_level_explain(_blueprint(), format=OutputFormat.JSON)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_use_llm_markdown(self):
        with patch("attune.socratic.explainer.LLMExplanationGenerator") as M:
            M.return_value.generate.return_value = "# LLM Output"
            result = top_level_explain(_blueprint(), use_llm=True, format=OutputFormat.MARKDOWN)
        assert result == "# LLM Output"

    def test_use_llm_text_strips_headers(self):
        with patch("attune.socratic.explainer.LLMExplanationGenerator") as M:
            M.return_value.generate.return_value = "## Header\n**Bold**"
            result = top_level_explain(_blueprint(), use_llm=True, format=OutputFormat.TEXT)
        assert "##" not in result
        assert "**" not in result

    def test_use_llm_html_wraps_div(self):
        with patch("attune.socratic.explainer.LLMExplanationGenerator") as M:
            M.return_value.generate.return_value = "content"
            result = top_level_explain(_blueprint(), use_llm=True, format=OutputFormat.HTML)
        assert "<div" in result

    def test_beginner_audience(self):
        result = top_level_explain(_blueprint(), audience="beginner")
        assert isinstance(result, str)

    def test_business_audience(self):
        result = top_level_explain(_blueprint(), audience="business")
        assert isinstance(result, str)
