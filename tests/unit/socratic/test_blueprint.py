"""Tests for the Socratic blueprint module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""


class TestAgentSpec:
    """Tests for AgentSpec class."""

    def test_create_agent_spec(self, sample_agent_spec):
        """Test creating an AgentSpec."""
        assert sample_agent_spec.id == "test-agent-001"
        assert sample_agent_spec.name == "Test Code Reviewer"
        assert len(sample_agent_spec.tools) == 2

    def test_agent_role(self, sample_agent_spec):
        """Test agent role."""
        from attune.socratic.blueprint import AgentRole

        assert sample_agent_spec.role == AgentRole.REVIEWER

    def test_agent_serialization(self, sample_agent_spec):
        """Test agent serialization."""
        data = sample_agent_spec.to_dict()

        assert data["id"] == sample_agent_spec.id
        assert data["name"] == sample_agent_spec.name
        assert data["role"] == sample_agent_spec.role.value

    def test_agent_has_expected_fields(self, sample_agent_spec):
        """Test agent has all expected fields."""
        data = sample_agent_spec.to_dict()

        # Core fields
        assert "id" in data
        assert "name" in data
        assert "role" in data
        assert "goal" in data
        assert "backstory" in data
        assert "tools" in data

        # Optional fields with defaults
        assert "quality_focus" in data
        assert "model_tier" in data
        assert "custom_instructions" in data


class TestToolSpec:
    """Tests for ToolSpec class."""

    def test_create_tool_spec(self):
        """Test creating a ToolSpec."""
        from attune.socratic.blueprint import ToolCategory, ToolSpec

        tool = ToolSpec(
            id="security_scan",
            name="Security Scanner",
            description="Scans for vulnerabilities",
            category=ToolCategory.SECURITY,
        )

        assert tool.id == "security_scan"
        assert tool.category == ToolCategory.SECURITY

    def test_tool_serialization(self):
        """Test tool serialization."""
        from attune.socratic.blueprint import ToolCategory, ToolSpec

        tool = ToolSpec(
            id="read_file",
            name="Read File",
            description="Read file contents",
            category=ToolCategory.CODE_ANALYSIS,
        )

        data = tool.to_dict()

        assert data["id"] == "read_file"
        assert data["name"] == "Read File"
        assert data["category"] == "code_analysis"


class TestStageSpec:
    """Tests for StageSpec class."""

    def test_create_stage_spec(self):
        """Test creating a StageSpec."""
        from attune.socratic.blueprint import StageSpec

        stage = StageSpec(
            id="analysis",
            name="Code Analysis",
            description="Analyze code for issues",
            agent_ids=["agent1", "agent2"],
            parallel=True,
        )

        assert stage.id == "analysis"
        assert stage.parallel is True
        assert len(stage.agent_ids) == 2

    def test_stage_with_dependencies(self):
        """Test stage with dependencies."""
        from attune.socratic.blueprint import StageSpec

        stage = StageSpec(
            id="synthesis",
            name="Result Synthesis",
            description="Synthesize results",
            agent_ids=["synthesizer"],
            depends_on=["analysis", "review"],
        )

        assert len(stage.depends_on) == 2
        assert "analysis" in stage.depends_on

    def test_stage_serialization(self):
        """Test stage serialization."""
        from attune.socratic.blueprint import StageSpec

        stage = StageSpec(
            id="analysis",
            name="Code Analysis",
            description="Analyze code",
            agent_ids=["agent1"],
            parallel=False,
            depends_on=["setup"],
        )

        data = stage.to_dict()

        assert data["id"] == "analysis"
        assert data["agent_ids"] == ["agent1"]
        assert data["depends_on"] == ["setup"]


class TestWorkflowBlueprint:
    """Tests for WorkflowBlueprint class."""

    def test_create_workflow_blueprint(self, sample_workflow_blueprint):
        """Test creating a WorkflowBlueprint."""
        assert sample_workflow_blueprint.id == "test-blueprint-001"
        assert sample_workflow_blueprint.name == "Test Code Review Workflow"
        assert len(sample_workflow_blueprint.agents) == 2
        assert len(sample_workflow_blueprint.stages) == 2

    def test_workflow_domain(self, sample_workflow_blueprint):
        """Test workflow domain."""
        assert sample_workflow_blueprint.domain == "code_review"

    def test_workflow_serialization(self, sample_workflow_blueprint):
        """Test workflow serialization."""
        data = sample_workflow_blueprint.to_dict()

        assert data["id"] == sample_workflow_blueprint.id
        assert len(data["agents"]) == 2
        assert len(data["stages"]) == 2

    def test_workflow_deserialization(self, sample_workflow_blueprint):
        """Test workflow deserialization."""
        from attune.socratic.blueprint import WorkflowBlueprint

        data = sample_workflow_blueprint.to_dict()
        restored = WorkflowBlueprint.from_dict(data)

        assert restored.id == sample_workflow_blueprint.id
        assert len(restored.agents) == len(sample_workflow_blueprint.agents)

    def test_workflow_get_agent_by_id(self, sample_workflow_blueprint):
        """Test getting agent by ID."""
        agent = sample_workflow_blueprint.get_agent_by_id("test-agent-001")
        assert agent is not None
        assert agent.spec.id == "test-agent-001"

    def test_workflow_get_stage_by_id(self, sample_workflow_blueprint):
        """Test getting stage by ID."""
        stage = sample_workflow_blueprint.get_stage_by_id("analysis")
        assert stage is not None
        assert stage.id == "analysis"


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_all_roles_exist(self):
        """Test all agent roles exist."""
        from attune.socratic.blueprint import AgentRole

        roles = [
            AgentRole.ANALYZER,
            AgentRole.REVIEWER,
            AgentRole.AUDITOR,
            AgentRole.GENERATOR,
            AgentRole.FIXER,
            AgentRole.ORCHESTRATOR,
            AgentRole.RESEARCHER,
            AgentRole.VALIDATOR,
        ]

        assert len(roles) == 8


class TestAgentBlueprintValidate:
    """Tests for AgentBlueprint.validate() error branches."""

    def _make_blueprint(self, **overrides):
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
        )

        spec_kwargs = {
            "id": "agent-1",
            "name": "Reviewer",
            "role": AgentRole.REVIEWER,
            "goal": "Review",
            "backstory": "Years of experience",
        }
        spec_kwargs.update(overrides)
        spec = AgentSpec(**spec_kwargs)
        return AgentBlueprint(spec=spec)

    def test_validate_missing_id_appends_error(self):
        bp = self._make_blueprint(id="")
        assert bp.validate() is False
        assert any("ID" in e for e in bp.validation_errors)

    def test_validate_missing_name_appends_error(self):
        bp = self._make_blueprint(name="")
        assert bp.validate() is False
        assert any("name" in e for e in bp.validation_errors)

    def test_validate_missing_goal_appends_error(self):
        bp = self._make_blueprint(goal="")
        assert bp.validate() is False
        assert any("goal" in e for e in bp.validation_errors)

    def test_validate_missing_backstory_appends_error(self):
        bp = self._make_blueprint(backstory="")
        assert bp.validate() is False
        assert any("backstory" in e for e in bp.validation_errors)

    def test_validate_passes_with_all_fields(self):
        bp = self._make_blueprint()
        assert bp.validate() is True
        assert bp.validation_errors == []


class TestWorkflowBlueprintLookups:
    """Cover get_agent_by_id / get_stage_by_id None paths."""

    def test_get_agent_by_id_returns_none_for_unknown(self, sample_workflow_blueprint):
        result = sample_workflow_blueprint.get_agent_by_id("does-not-exist")
        assert result is None

    def test_get_stage_by_id_returns_none_for_unknown(self, sample_workflow_blueprint):
        result = sample_workflow_blueprint.get_stage_by_id("nope")
        assert result is None


class TestWorkflowBlueprintValidate:
    """Cover WorkflowBlueprint.validate() error paths."""

    def test_validate_missing_name_appends_error(self):
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            StageSpec,
            WorkflowBlueprint,
        )

        agent = AgentBlueprint(
            spec=AgentSpec(
                id="a1",
                name="Agent",
                role=AgentRole.REVIEWER,
                goal="g",
                backstory="b",
            )
        )
        bp = WorkflowBlueprint(
            name="",
            agents=[agent],
            stages=[StageSpec(id="s1", name="S", description="d", agent_ids=["a1"])],
        )
        is_valid, errors = bp.validate()
        assert is_valid is False
        assert any("name" in e for e in errors)

    def test_validate_invalid_agent_extends_errors(self):
        """An agent failing its own validate() contributes prefixed errors (line 412)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            StageSpec,
            WorkflowBlueprint,
        )

        # Agent with no goal will fail validate()
        bad_agent = AgentBlueprint(
            spec=AgentSpec(
                id="bad-1",
                name="Bad",
                role=AgentRole.REVIEWER,
                goal="",
                backstory="b",
            )
        )
        bp = WorkflowBlueprint(
            name="WF",
            agents=[bad_agent],
            stages=[
                StageSpec(id="s1", name="S", description="d", agent_ids=["bad-1"]),
            ],
        )
        is_valid, errors = bp.validate()
        assert is_valid is False
        # Agent-prefixed error should appear
        assert any("Agent 'bad-1':" in e for e in errors)

    def test_validate_stage_references_unknown_agent(self):
        """Stage referencing an agent not in the workflow appends an error (line 419)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            StageSpec,
            WorkflowBlueprint,
        )

        agent = AgentBlueprint(
            spec=AgentSpec(
                id="known",
                name="Known",
                role=AgentRole.REVIEWER,
                goal="g",
                backstory="b",
            )
        )
        bp = WorkflowBlueprint(
            name="WF",
            agents=[agent],
            stages=[
                StageSpec(
                    id="s1",
                    name="S",
                    description="d",
                    agent_ids=["known", "ghost-agent"],
                ),
            ],
        )
        is_valid, errors = bp.validate()
        assert is_valid is False
        assert any("ghost-agent" in e for e in errors)

    def test_validate_no_agents_appends_error(self):
        """Workflow with no agents appends 'at least one agent' error (line 404)."""
        from attune.socratic.blueprint import StageSpec, WorkflowBlueprint

        bp = WorkflowBlueprint(
            name="WF",
            agents=[],
            stages=[StageSpec(id="s1", name="S", description="d", agent_ids=[])],
        )
        is_valid, errors = bp.validate()
        assert is_valid is False
        assert any("at least one agent" in e for e in errors)

    def test_validate_no_stages_appends_error(self):
        """Workflow with no stages appends 'at least one stage' error (line 407)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            WorkflowBlueprint,
        )

        agent = AgentBlueprint(
            spec=AgentSpec(
                id="a1",
                name="A",
                role=AgentRole.REVIEWER,
                goal="g",
                backstory="b",
            )
        )
        bp = WorkflowBlueprint(name="WF", agents=[agent], stages=[])
        is_valid, errors = bp.validate()
        assert is_valid is False
        assert any("at least one stage" in e for e in errors)

    def test_validate_stage_depends_on_known_stage_no_error(self):
        """Stage depends_on a valid stage takes the if-False branch (425->424)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            StageSpec,
            WorkflowBlueprint,
        )

        agent = AgentBlueprint(
            spec=AgentSpec(
                id="a1",
                name="A",
                role=AgentRole.REVIEWER,
                goal="g",
                backstory="b",
            )
        )
        bp = WorkflowBlueprint(
            name="WF",
            agents=[agent],
            stages=[
                StageSpec(id="s1", name="S1", description="d", agent_ids=["a1"]),
                StageSpec(
                    id="s2",
                    name="S2",
                    description="d",
                    agent_ids=["a1"],
                    depends_on=["s1"],  # valid reference — exercises if-False branch
                ),
            ],
        )
        is_valid, errors = bp.validate()
        assert is_valid is True
        assert errors == []

    def test_validate_stage_depends_on_unknown_stage(self):
        """Stage depending on a non-existent stage appends an error (line 426)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            StageSpec,
            WorkflowBlueprint,
        )

        agent = AgentBlueprint(
            spec=AgentSpec(
                id="a1",
                name="A",
                role=AgentRole.REVIEWER,
                goal="g",
                backstory="b",
            )
        )
        bp = WorkflowBlueprint(
            name="WF",
            agents=[agent],
            stages=[
                StageSpec(
                    id="s1",
                    name="S",
                    description="d",
                    agent_ids=["a1"],
                    depends_on=["non-existent-stage"],
                ),
            ],
        )
        is_valid, errors = bp.validate()
        assert is_valid is False
        assert any("non-existent-stage" in e for e in errors)


class TestToolCategory:
    """Tests for ToolCategory enum."""

    def test_all_categories_exist(self):
        """Test all tool categories exist."""
        from attune.socratic.blueprint import ToolCategory

        # Verify core categories exist (subset check for stability)
        categories = [
            ToolCategory.CODE_ANALYSIS,
            ToolCategory.CODE_SEARCH,
            ToolCategory.CODE_MODIFICATION,
            ToolCategory.SECURITY,
            ToolCategory.TESTING,
            ToolCategory.LINTING,
            ToolCategory.DOCUMENTATION,
            ToolCategory.KNOWLEDGE,
            ToolCategory.API,
            ToolCategory.DATABASE,
            ToolCategory.FILESYSTEM,
        ]

        assert len(categories) == 11
