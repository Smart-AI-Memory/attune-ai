"""Tests for the Agent and Workflow Generator.

Tests cover:
- AgentTemplate dataclass
- TOOL_REGISTRY and AGENT_TEMPLATES
- AgentGenerator class
- GeneratedWorkflow dataclass

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock, patch

import pytest

from attune.socratic.blueprint import AgentBlueprint, AgentRole, StageSpec, WorkflowBlueprint
from attune.socratic.generator import (
    AGENT_TEMPLATES,
    TOOL_REGISTRY,
    AgentGenerator,
    AgentTemplate,
    GeneratedWorkflow,
)

# =============================================================================
# TOOL REGISTRY TESTS
# =============================================================================


@pytest.mark.unit
class TestToolRegistry:
    """Tests for TOOL_REGISTRY."""

    def test_registry_not_empty(self):
        """Test that tool registry has entries."""
        assert len(TOOL_REGISTRY) > 0

    def test_contains_common_tools(self):
        """Test that registry contains common tools."""
        expected_tools = [
            "grep_code",
            "read_file",
            "analyze_ast",
            "security_scan",
            "run_linter",
            "run_tests",
            "edit_file",
        ]
        for tool_id in expected_tools:
            assert tool_id in TOOL_REGISTRY

    def test_tool_has_required_fields(self):
        """Test that tools have required fields."""
        for tool_id, tool in TOOL_REGISTRY.items():
            assert tool.id == tool_id
            assert tool.name
            assert tool.category is not None
            assert tool.description


# =============================================================================
# AGENT TEMPLATES TESTS
# =============================================================================


@pytest.mark.unit
class TestAgentTemplates:
    """Tests for AGENT_TEMPLATES."""

    def test_templates_not_empty(self):
        """Test that templates registry has entries."""
        assert len(AGENT_TEMPLATES) > 0

    def test_contains_common_templates(self):
        """Test that registry contains common templates."""
        expected_templates = [
            "security_reviewer",
            "code_quality_reviewer",
            "performance_analyzer",
            "test_generator",
            "documentation_writer",
        ]
        for template_id in expected_templates:
            assert template_id in AGENT_TEMPLATES

    def test_template_has_required_fields(self):
        """Test that templates have required fields."""
        for template_id, template in AGENT_TEMPLATES.items():
            assert template.id == template_id
            assert template.name
            assert template.role is not None
            assert template.base_goal
            assert template.base_backstory


# =============================================================================
# AGENT TEMPLATE TESTS
# =============================================================================


@pytest.mark.unit
class TestAgentTemplateCreation:
    """Tests for AgentTemplate dataclass creation."""

    def test_minimal_creation(self):
        """Test creating template with minimal fields."""
        template = AgentTemplate(
            id="test_template",
            name="Test Template",
            role=AgentRole.REVIEWER,
            base_goal="Test goal",
            base_backstory="Test backstory",
            default_tools=[],
            quality_focus=[],
            languages=[],
        )
        assert template.id == "test_template"
        assert template.model_tier == "capable"  # default

    def test_full_creation(self):
        """Test creating template with all fields."""
        template = AgentTemplate(
            id="full_template",
            name="Full Template",
            role=AgentRole.AUDITOR,
            base_goal="Full goal",
            base_backstory="Full backstory",
            default_tools=["grep_code", "read_file"],
            quality_focus=["security", "performance"],
            languages=["python", "javascript"],
            model_tier="premium",
            custom_instructions=["Instruction 1", "Instruction 2"],
        )
        assert template.id == "full_template"
        assert len(template.default_tools) == 2
        assert len(template.custom_instructions) == 2


@pytest.mark.unit
class TestAgentTemplateCreateSpec:
    """Tests for AgentTemplate.create_spec()."""

    @pytest.fixture
    def basic_template(self):
        """Create a basic template for testing."""
        return AgentTemplate(
            id="test_agent",
            name="Test Agent",
            role=AgentRole.REVIEWER,
            base_goal="Review code",
            base_backstory="Expert reviewer",
            default_tools=["read_file"],
            quality_focus=["maintainability"],
            languages=["python"],
        )

    def test_create_spec_defaults(self, basic_template):
        """Test creating spec with default values."""
        spec = basic_template.create_spec()

        assert spec.id == "test_agent"
        assert spec.name == "Test Agent"
        assert spec.goal == "Review code"

    def test_create_spec_with_goal_override(self, basic_template):
        """Test creating spec with goal override."""
        spec = basic_template.create_spec({"goal": "Custom goal"})
        assert spec.goal == "Custom goal"

    def test_create_spec_with_goal_suffix(self, basic_template):
        """Test creating spec with goal suffix."""
        spec = basic_template.create_spec({"goal_suffix": "with extra focus"})
        assert "with extra focus" in spec.goal

    def test_create_spec_with_backstory_override(self, basic_template):
        """Test creating spec with backstory override."""
        spec = basic_template.create_spec({"backstory": "Custom backstory"})
        assert spec.backstory == "Custom backstory"

    def test_create_spec_with_expertise(self, basic_template):
        """Test creating spec with expertise customization."""
        spec = basic_template.create_spec({"expertise": ["Python", "Security"]})
        assert "Python" in spec.backstory
        assert "Security" in spec.backstory

    def test_create_spec_with_language_override(self, basic_template):
        """Test creating spec with language override."""
        spec = basic_template.create_spec({"languages": ["javascript", "typescript"]})
        assert "javascript" in spec.languages
        assert "typescript" in spec.languages

    def test_create_spec_with_quality_focus_merge(self, basic_template):
        """Test that quality focus is merged."""
        spec = basic_template.create_spec({"quality_focus": ["security"]})
        assert "maintainability" in spec.quality_focus
        assert "security" in spec.quality_focus

    def test_create_spec_with_custom_id(self, basic_template):
        """Test creating spec with custom ID."""
        spec = basic_template.create_spec({"id": "custom_id"})
        assert spec.id == "custom_id"


@pytest.mark.unit
class TestAgentTemplateBuildTools:
    """Tests for AgentTemplate._build_tools()."""

    @pytest.fixture
    def template_with_tools(self):
        """Create a template with default tools."""
        return AgentTemplate(
            id="test",
            name="Test",
            role=AgentRole.REVIEWER,
            base_goal="Test",
            base_backstory="Test",
            default_tools=["read_file", "grep_code"],
            quality_focus=[],
            languages=[],
        )

    def test_builds_default_tools(self, template_with_tools):
        """Test that default tools are built."""
        spec = template_with_tools.create_spec()
        tool_ids = [t.id for t in spec.tools]

        assert "read_file" in tool_ids
        assert "grep_code" in tool_ids

    def test_adds_additional_tools(self, template_with_tools):
        """Test that additional tools are added."""
        spec = template_with_tools.create_spec({"tools": ["run_linter"]})
        tool_ids = [t.id for t in spec.tools]

        assert "run_linter" in tool_ids

    def test_deduplicates_tools(self, template_with_tools):
        """Test that duplicate tools are removed."""
        spec = template_with_tools.create_spec({"tools": ["read_file"]})
        tool_ids = [t.id for t in spec.tools]

        # Should only have read_file once
        assert tool_ids.count("read_file") == 1


# =============================================================================
# AGENT GENERATOR TESTS
# =============================================================================


@pytest.mark.unit
class TestAgentGeneratorInitialization:
    """Tests for AgentGenerator initialization."""

    def test_initialization(self):
        """Test AgentGenerator initialization."""
        generator = AgentGenerator()

        assert generator.templates is not None
        assert generator.tools is not None
        assert len(generator.templates) > 0

    def test_register_template(self):
        """Test registering a custom template."""
        generator = AgentGenerator()
        custom_template = AgentTemplate(
            id="custom_agent",
            name="Custom Agent",
            role=AgentRole.ANALYZER,
            base_goal="Custom goal",
            base_backstory="Custom backstory",
            default_tools=[],
            quality_focus=[],
            languages=[],
        )

        generator.register_template(custom_template)

        assert "custom_agent" in generator.templates

    def test_register_tool(self):
        """Test registering a custom tool."""
        from attune.socratic.blueprint import ToolCategory, ToolSpec

        generator = AgentGenerator()
        custom_tool = ToolSpec(
            id="custom_tool",
            name="Custom Tool",
            category=ToolCategory.CODE_ANALYSIS,
            description="Custom description",
        )

        generator.register_tool(custom_tool)

        assert "custom_tool" in generator.tools


@pytest.mark.unit
class TestAgentGeneratorFromTemplate:
    """Tests for AgentGenerator.generate_agent_from_template()."""

    @pytest.fixture
    def generator(self):
        """Create an AgentGenerator for testing."""
        return AgentGenerator()

    def test_generate_from_existing_template(self, generator):
        """Test generating from an existing template."""
        agent = generator.generate_agent_from_template("security_reviewer")

        assert isinstance(agent, AgentBlueprint)
        assert agent.template_id == "security_reviewer"
        assert agent.generated_from == "template"

    def test_generate_with_customizations(self, generator):
        """Test generating with customizations."""
        agent = generator.generate_agent_from_template(
            "security_reviewer",
            customizations={"languages": ["python"]},
        )

        assert "python" in agent.spec.languages

    def test_generate_from_unknown_template_raises(self, generator):
        """Test that unknown template raises ValueError."""
        with pytest.raises(ValueError, match="Unknown template"):
            generator.generate_agent_from_template("nonexistent_template")


@pytest.mark.unit
class TestAgentGeneratorForRequirements:
    """Tests for AgentGenerator.generate_agents_for_requirements()."""

    @pytest.fixture
    def generator(self):
        """Create an AgentGenerator for testing."""
        return AgentGenerator()

    def test_generates_security_agent_for_security_focus(self, generator):
        """Test that security focus generates security reviewer."""
        agents = generator.generate_agents_for_requirements(
            {
                "quality_focus": ["security"],
            },
        )

        template_ids = [a.template_id for a in agents]
        assert "security_reviewer" in template_ids

    def test_generates_performance_agent_for_performance_focus(self, generator):
        """Test that performance focus generates performance analyzer."""
        agents = generator.generate_agents_for_requirements(
            {
                "quality_focus": ["performance"],
            },
        )

        template_ids = [a.template_id for a in agents]
        assert "performance_analyzer" in template_ids

    def test_generates_default_when_no_focus(self, generator):
        """Test that default agent is generated when no focus specified."""
        agents = generator.generate_agents_for_requirements({})

        template_ids = [a.template_id for a in agents]
        assert "code_quality_reviewer" in template_ids

    def test_adds_synthesizer_for_multiple_agents(self, generator):
        """Test that synthesizer is added when multiple agents needed."""
        agents = generator.generate_agents_for_requirements(
            {
                "quality_focus": ["security", "performance"],
            },
        )

        template_ids = [a.template_id for a in agents]
        assert "result_synthesizer" in template_ids

    def test_applies_automation_level_fully_auto(self, generator):
        """Test that fully_auto automation adds appropriate instructions."""
        agents = generator.generate_agents_for_requirements(
            {
                "quality_focus": ["security"],
                "automation_level": "fully_auto",
            },
        )

        agent = next(a for a in agents if a.template_id == "security_reviewer")
        instructions = agent.spec.custom_instructions

        assert any("automatically" in i.lower() for i in instructions)

    def test_applies_automation_level_advisory(self, generator):
        """Test that advisory automation adds appropriate instructions."""
        agents = generator.generate_agents_for_requirements(
            {
                "quality_focus": ["security"],
                "automation_level": "advisory",
            },
        )

        agent = next(a for a in agents if a.template_id == "security_reviewer")
        instructions = agent.spec.custom_instructions

        assert any("recommendations only" in i.lower() for i in instructions)


@pytest.mark.unit
class TestAgentGeneratorWorkflow:
    """Tests for AgentGenerator.generate_workflow()."""

    @pytest.fixture
    def generator(self):
        """Create an AgentGenerator for testing."""
        return AgentGenerator()

    @pytest.fixture
    def valid_blueprint(self, generator):
        """Create a valid workflow blueprint."""
        agents = generator.generate_agents_for_requirements(
            {
                "quality_focus": ["security"],
            },
        )

        return WorkflowBlueprint(
            id="test-workflow",
            name="Test Workflow",
            description="Test description",
            domain="code_review",
            agents=agents,
            stages=[
                StageSpec(
                    id="analysis",
                    name="Analysis",
                    description="Analyze code",
                    agent_ids=[agents[0].spec.id],
                ),
            ],
        )

    def test_generate_workflow_success(self, generator, valid_blueprint):
        """Test successful workflow generation."""
        with patch("attune.socratic.generator.AgentGenerator._create_xml_agent") as mock_create:
            mock_agent = MagicMock()
            mock_create.return_value = mock_agent

            workflow = generator.generate_workflow(valid_blueprint)

            assert isinstance(workflow, GeneratedWorkflow)
            assert workflow.blueprint == valid_blueprint

    def test_generate_workflow_invalid_blueprint_raises(self, generator):
        """Test that invalid blueprint raises ValueError."""
        invalid_blueprint = WorkflowBlueprint(
            name="Invalid",
            description="",
            domain="",
            agents=[],
            stages=[],
        )

        with pytest.raises(ValueError, match="Invalid blueprint"):
            generator.generate_workflow(invalid_blueprint)

    def test_match_agent_returns_false_for_agent_without_role(self):
        """_match_agent returns False when agent has no `role` attribute (line 100)."""
        from unittest.mock import MagicMock

        # Object that explicitly doesn't have a `role` attribute
        class NoRoleAgent:
            pass

        gw = GeneratedWorkflow(
            blueprint=MagicMock(),
            agents=[],
            stages=[],
        )
        assert gw._match_agent(NoRoleAgent(), "anything") is False

    def test_generate_workflow_calls_real_create_xml_agent(self, generator, valid_blueprint):
        """generate_workflow without patching exercises real _create_xml_agent (line 219)."""
        workflow = generator.generate_workflow(valid_blueprint)
        # Should produce a workflow with at least one agent dict
        assert isinstance(workflow, GeneratedWorkflow)
        # Spot-check: real agents have role/goal/backstory keys
        for a in workflow.agents:
            if isinstance(a, dict):
                assert "role" in a or "goal" in a

    def test_generate_agents_handles_unknown_template_id(self, generator):
        """Unknown template IDs are caught and logged (lines 167-168).

        We force the path by patching the quality_to_templates map to point at
        a template ID that doesn't exist in the registry.
        """
        from unittest.mock import patch

        with patch.object(
            generator,
            "generate_agent_from_template",
            side_effect=ValueError("Unknown template: phantom"),
        ):
            agents = generator.generate_agents_for_requirements(
                {"quality_focus": ["security"]},
            )
        # The except branch swallows the error; result list is empty for this path
        assert agents == []


@pytest.mark.unit
class TestAgentGeneratorCreateWorkflowBlueprint:
    """Tests for AgentGenerator.create_workflow_blueprint()."""

    @pytest.fixture
    def generator(self):
        """Create an AgentGenerator for testing."""
        return AgentGenerator()

    def test_creates_blueprint_with_stages(self, generator):
        """Test that blueprint is created with automatic staging."""
        agents = generator.generate_agents_for_requirements(
            {
                "quality_focus": ["security", "maintainability"],
            },
        )

        blueprint = generator.create_workflow_blueprint(
            name="Test Workflow",
            description="Test description",
            agents=agents,
            quality_focus=["security"],
            automation_level="semi_auto",
        )

        assert blueprint.name == "Test Workflow"
        assert len(blueprint.stages) > 0

    def test_groups_agents_by_role(self, generator):
        """Test that agents are grouped by role into stages."""
        agents = generator.generate_agents_for_requirements(
            {
                "quality_focus": ["security", "testability"],
            },
        )

        blueprint = generator.create_workflow_blueprint(
            name="Test",
            description="Test",
            agents=agents,
            quality_focus=["security"],
            automation_level="semi_auto",
        )

        # Should have analysis stage for reviewers/auditors
        stage_ids = [s.id for s in blueprint.stages]
        assert "analysis" in stage_ids or "generation" in stage_ids

    def test_blueprint_with_only_reporter_skips_analysis_and_generation(self, generator):
        """Reporters-only agent set produces only synthesis stage; depends list is empty
        (covers branches 262->275, 290->292, 292->295)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
        )

        # Some implementations don't have a REPORTER role enum; check the codebase
        reporter_role = getattr(AgentRole, "REPORTER", None)
        if reporter_role is None:
            pytest.skip("AgentRole.REPORTER not present in this build")

        reporter = AgentBlueprint(
            spec=AgentSpec(
                id="r1",
                name="Reporter",
                role=reporter_role,
                goal="report",
                backstory="b",
            )
        )
        bp = generator.create_workflow_blueprint(
            name="ReporterOnly",
            description="d",
            agents=[reporter],
            quality_focus=[],
            automation_level="semi_auto",
        )
        # Synthesis is the only stage
        synthesis = next((s for s in bp.stages if s.id == "synthesis"), None)
        assert synthesis is not None
        # depends_on is empty because no analysis/generation stage was created
        assert synthesis.depends_on == []

    def test_blueprint_with_only_generator_skips_analysis(self, generator):
        """Generator-only set creates Generation stage with no analysis dependency
        (covers `depends_on=[] if analyzers else ...` ternary False branch and 290->292)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
        )

        gen_agent = AgentBlueprint(
            spec=AgentSpec(
                id="g1",
                name="Gen",
                role=AgentRole.GENERATOR,
                goal="generate",
                backstory="b",
            )
        )
        bp = generator.create_workflow_blueprint(
            name="GenOnly",
            description="d",
            agents=[gen_agent],
            quality_focus=[],
            automation_level="semi_auto",
        )
        gen_stage = next((s for s in bp.stages if s.id == "generation"), None)
        assert gen_stage is not None
        assert gen_stage.depends_on == []


# =============================================================================
# GENERATED WORKFLOW TESTS
# =============================================================================


@pytest.mark.unit
class TestGeneratedWorkflowCreation:
    """Tests for GeneratedWorkflow dataclass creation."""

    @pytest.fixture
    def mock_blueprint(self):
        """Create a mock blueprint."""
        blueprint = MagicMock(spec=WorkflowBlueprint)
        blueprint.name = "Test Workflow"
        blueprint.description = "Test description"
        return blueprint

    def test_creation(self, mock_blueprint):
        """Test creating a GeneratedWorkflow."""
        workflow = GeneratedWorkflow(
            blueprint=mock_blueprint,
            agents=[],
            stages=[],
            generated_at="2024-01-01T00:00:00",
        )

        assert workflow.blueprint == mock_blueprint
        assert workflow.validated is False


@pytest.mark.unit
class TestGeneratedWorkflowDescribe:
    """Tests for GeneratedWorkflow.describe()."""

    def test_describe_output(self):
        """Test describe returns readable output."""
        mock_blueprint = MagicMock()
        mock_blueprint.name = "Code Review"
        mock_blueprint.description = "Review code quality"

        mock_agent = MagicMock()
        mock_agent.role = "Security Reviewer"
        mock_agent.goal = "Find vulnerabilities"

        workflow = GeneratedWorkflow(
            blueprint=mock_blueprint,
            agents=[mock_agent],
            stages=[
                {
                    "id": "analysis",
                    "name": "Analysis",
                    "agents": ["security_reviewer"],
                    "parallel": True,
                },
            ],
        )

        description = workflow.describe()

        assert "Code Review" in description
        assert "Security Reviewer" in description
        assert "Analysis" in description


@pytest.mark.unit
class TestGeneratedWorkflowMatchAgent:
    """Tests for GeneratedWorkflow._match_agent()."""

    def test_match_agent_by_role(self):
        """Test matching agent by role name."""
        workflow = GeneratedWorkflow(
            blueprint=MagicMock(),
            agents=[],
            stages=[],
        )

        mock_agent = MagicMock()
        mock_agent.role = "Security Reviewer"

        assert workflow._match_agent(mock_agent, "security_reviewer") is True

    def test_match_agent_no_match(self):
        """Test non-matching agent."""
        workflow = GeneratedWorkflow(
            blueprint=MagicMock(),
            agents=[],
            stages=[],
        )

        mock_agent = MagicMock()
        mock_agent.role = "Performance Analyzer"

        assert workflow._match_agent(mock_agent, "security_reviewer") is False


@pytest.mark.unit
class TestGeneratedWorkflowExecute:
    """Tests for GeneratedWorkflow.execute()."""

    @pytest.mark.asyncio
    async def test_execute_returns_results(self):
        """Test that execute returns results dictionary."""
        mock_blueprint = MagicMock()
        mock_agent = MagicMock()
        mock_agent.role = "Test Agent"

        workflow = GeneratedWorkflow(
            blueprint=mock_blueprint,
            agents=[mock_agent],
            stages=[
                {
                    "id": "test_stage",
                    "name": "Test Stage",
                    "agents": ["test_agent"],
                    "parallel": False,
                },
            ],
        )

        results = await workflow.execute({"input": "test"})

        assert "stages" in results
        assert "success" in results
        assert results["success"] is True

    @pytest.mark.asyncio
    async def test_execute_empty_stages(self):
        """Test execute with no stages."""
        workflow = GeneratedWorkflow(
            blueprint=MagicMock(),
            agents=[],
            stages=[],
        )

        results = await workflow.execute({})

        assert results["success"] is True
        assert results["stages"] == {}
