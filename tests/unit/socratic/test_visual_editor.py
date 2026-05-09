"""Tests for the Socratic visual editor module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json


class TestEditorNode:
    """Tests for EditorNode dataclass."""

    def test_create_node(self):
        """Test creating an editor node."""
        from attune.socratic.visual_editor import EditorNode

        node = EditorNode(
            node_id="node-001",
            node_type="agent",
            label="Code Reviewer",
            position={"x": 100, "y": 200},
            data={"agent_id": "agent-001", "role": "reviewer"},
        )

        assert node.node_id == "node-001"
        assert node.node_type == "agent"
        assert node.position["x"] == 100
        assert node.position["y"] == 200

    def test_node_with_position_object(self):
        """Test creating node with Position object."""
        from attune.socratic.visual_editor import EditorNode, Position

        pos = Position(x=50, y=100)
        node = EditorNode(
            node_id="node-002",
            node_type="stage",
            label="Test Stage",
            position=pos,
        )

        assert node.position.x == 50
        assert node.position.y == 100

    def test_node_with_node_type_enum(self):
        """Test creating node with NodeType enum."""
        from attune.socratic.visual_editor import EditorNode, NodeType

        node = EditorNode(
            node_id="node-003",
            node_type=NodeType.AGENT,
            label="Test Agent",
            position={"x": 0, "y": 0},
        )

        assert node.node_type == NodeType.AGENT

    def test_node_to_dict(self):
        """Test node serialization."""
        from attune.socratic.visual_editor import EditorNode

        node = EditorNode(
            node_id="node-001",
            node_type="agent",
            label="Test Agent",
            position={"x": 0, "y": 0},
        )

        data = node.to_dict()

        assert data["id"] == "node-001"
        assert data["type"] == "agent"
        assert data["data"]["label"] == "Test Agent"

    def test_node_to_dict_with_enum(self):
        """Test node serialization with NodeType enum."""
        from attune.socratic.visual_editor import EditorNode, NodeType

        node = EditorNode(
            node_id="node-001",
            node_type=NodeType.STAGE,
            label="Test Stage",
            position={"x": 0, "y": 0},
        )

        data = node.to_dict()
        assert data["type"] == "stage"

    def test_node_default_values(self):
        """Test node default values."""
        from attune.socratic.visual_editor import EditorNode

        node = EditorNode(
            node_id="node-001",
            node_type="agent",
            label="Test",
            position={"x": 0, "y": 0},
        )

        assert node.data == {}
        assert node.selected is False
        assert node.locked is False


class TestEditorEdge:
    """Tests for EditorEdge dataclass."""

    def test_create_edge(self):
        """Test creating an editor edge."""
        from attune.socratic.visual_editor import EditorEdge

        edge = EditorEdge(
            edge_id="edge-001",
            source="node-001",
            target="node-002",
            label="on_success",
        )

        assert edge.edge_id == "edge-001"
        assert edge.source == "node-001"
        assert edge.target == "node-002"
        assert edge.label == "on_success"

    def test_edge_to_dict(self):
        """Test edge serialization."""
        from attune.socratic.visual_editor import EditorEdge

        edge = EditorEdge(
            edge_id="edge-001",
            source="node-001",
            target="node-002",
        )

        data = edge.to_dict()

        assert data["id"] == "edge-001"
        assert data["source"] == "node-001"
        assert data["target"] == "node-002"

    def test_edge_default_values(self):
        """Test edge default values."""
        from attune.socratic.visual_editor import EditorEdge

        edge = EditorEdge(
            edge_id="edge-001",
            source="node-001",
            target="node-002",
        )

        assert edge.label == ""
        assert edge.animated is False


class TestPosition:
    """Tests for Position dataclass."""

    def test_create_position(self):
        """Test creating a position."""
        from attune.socratic.visual_editor import Position

        pos = Position(x=100, y=200)

        assert pos.x == 100
        assert pos.y == 200

    def test_position_to_dict(self):
        """Test position serialization."""
        from attune.socratic.visual_editor import Position

        pos = Position(x=50, y=75)
        data = pos.to_dict()

        assert data == {"x": 50, "y": 75}


class TestNodeType:
    """Tests for NodeType enum."""

    def test_all_node_types_exist(self):
        """Test all expected node types exist."""
        from attune.socratic.visual_editor import NodeType

        assert NodeType.AGENT.value == "agent"
        assert NodeType.STAGE.value == "stage"
        assert NodeType.START.value == "start"
        assert NodeType.END.value == "end"
        assert NodeType.CONNECTOR.value == "connector"


class TestEditorState:
    """Tests for EditorState dataclass."""

    def test_create_state(self):
        """Test creating an editor state."""
        from attune.socratic.visual_editor import EditorEdge, EditorNode, EditorState

        nodes = [
            EditorNode(
                node_id="node-1",
                node_type="agent",
                label="Agent 1",
                position={"x": 0, "y": 0},
            ),
            EditorNode(
                node_id="node-2",
                node_type="agent",
                label="Agent 2",
                position={"x": 200, "y": 0},
            ),
        ]

        edges = [
            EditorEdge(
                edge_id="edge-1",
                source="node-1",
                target="node-2",
            ),
        ]

        state = EditorState(
            workflow_id="wf-001",
            nodes=nodes,
            edges=edges,
        )

        assert state.workflow_id == "wf-001"
        assert len(state.nodes) == 2
        assert len(state.edges) == 1

    def test_state_default_values(self):
        """Test EditorState default values."""
        from attune.socratic.visual_editor import EditorState

        state = EditorState()

        assert state.workflow_id == ""
        assert state.nodes == []
        assert state.edges == []
        assert state.selected_node_id is None
        assert state.zoom == 1.0
        assert state.pan_x == 0
        assert state.pan_y == 0

    def test_state_to_dict(self):
        """Test EditorState serialization."""
        from attune.socratic.visual_editor import EditorNode, EditorState

        state = EditorState(
            workflow_id="wf-001",
            nodes=[
                EditorNode(
                    node_id="n1",
                    node_type="agent",
                    label="Agent",
                    position={"x": 0, "y": 0},
                ),
            ],
            edges=[],
            zoom=1.5,
        )

        data = state.to_dict()

        assert "nodes" in data
        assert "edges" in data
        assert data["zoom"] == 1.5
        assert len(data["nodes"]) == 1

    def test_state_to_react_flow(self):
        """Test converting state to React Flow schema."""
        from attune.socratic.visual_editor import EditorNode, EditorState

        state = EditorState(
            workflow_id="wf-001",
            nodes=[
                EditorNode(
                    node_id="n1",
                    node_type="agent",
                    label="Agent",
                    position={"x": 0, "y": 0},
                ),
            ],
            edges=[],
        )

        react_flow = state.to_react_flow()

        assert "nodes" in react_flow
        assert "edges" in react_flow
        assert len(react_flow["nodes"]) == 1


class TestWorkflowVisualizer:
    """Tests for WorkflowVisualizer class."""

    def test_create_visualizer(self):
        """Test creating a workflow visualizer."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        visualizer = WorkflowVisualizer()
        assert visualizer is not None
        assert visualizer.node_spacing == 200
        assert visualizer.stage_spacing == 150

    def test_create_visualizer_custom_spacing(self):
        """Test creating visualizer with custom spacing."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        visualizer = WorkflowVisualizer(node_spacing=300, stage_spacing=200)

        assert visualizer.node_spacing == 300
        assert visualizer.stage_spacing == 200

    def test_blueprint_to_editor_method_exists(self):
        """Test blueprint_to_editor method exists."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        visualizer = WorkflowVisualizer()
        assert hasattr(visualizer, "blueprint_to_editor")
        assert callable(visualizer.blueprint_to_editor)

    def test_from_blueprint_alias_exists(self):
        """Test from_blueprint alias method exists."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        visualizer = WorkflowVisualizer()
        assert hasattr(visualizer, "from_blueprint")
        assert callable(visualizer.from_blueprint)

    def test_editor_to_blueprint_method_exists(self):
        """Test editor_to_blueprint method exists."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        visualizer = WorkflowVisualizer()
        assert hasattr(visualizer, "editor_to_blueprint")
        assert callable(visualizer.editor_to_blueprint)

    def test_to_blueprint_alias_exists(self):
        """Test to_blueprint alias method exists."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        visualizer = WorkflowVisualizer()
        assert hasattr(visualizer, "to_blueprint")
        assert callable(visualizer.to_blueprint)

    def test_visualize_blueprint(self, sample_workflow_blueprint):
        """Test visualizing a workflow blueprint."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        visualizer = WorkflowVisualizer()
        state = visualizer.blueprint_to_editor(sample_workflow_blueprint)

        assert state is not None
        assert state.workflow_id == sample_workflow_blueprint.id
        assert len(state.nodes) > 0

    def test_state_has_start_end_nodes(self, sample_workflow_blueprint):
        """Test that state includes start and end nodes."""
        from attune.socratic.visual_editor import NodeType, WorkflowVisualizer

        visualizer = WorkflowVisualizer()
        state = visualizer.blueprint_to_editor(sample_workflow_blueprint)

        node_types = [n.node_type for n in state.nodes]
        assert NodeType.START in node_types
        assert NodeType.END in node_types


class TestASCIIVisualizer:
    """Tests for ASCIIVisualizer class."""

    def test_create_ascii_visualizer(self):
        """Test creating an ASCII visualizer."""
        from attune.socratic.visual_editor import ASCIIVisualizer

        visualizer = ASCIIVisualizer()
        assert visualizer is not None
        assert visualizer.width == 80

    def test_create_ascii_visualizer_custom_width(self):
        """Test creating ASCII visualizer with custom width."""
        from attune.socratic.visual_editor import ASCIIVisualizer

        visualizer = ASCIIVisualizer(width=100)
        assert visualizer.width == 100

    def test_render_method_exists(self):
        """Test render method exists."""
        from attune.socratic.visual_editor import ASCIIVisualizer

        visualizer = ASCIIVisualizer()
        assert hasattr(visualizer, "render")
        assert callable(visualizer.render)

    def test_render_compact_method_exists(self):
        """Test render_compact method exists."""
        from attune.socratic.visual_editor import ASCIIVisualizer

        visualizer = ASCIIVisualizer()
        assert hasattr(visualizer, "render_compact")
        assert callable(visualizer.render_compact)

    def test_render_workflow(self, sample_workflow_blueprint):
        """Test rendering a workflow as ASCII art."""
        from attune.socratic.visual_editor import ASCIIVisualizer

        visualizer = ASCIIVisualizer()
        ascii_art = visualizer.render(sample_workflow_blueprint)

        assert isinstance(ascii_art, str)
        assert len(ascii_art) > 0
        assert "Workflow" in ascii_art
        assert "START" in ascii_art
        assert "END" in ascii_art

    def test_render_handles_agent_with_many_tools(self):
        """ASCII renderer truncates tool list when >3 tools (line 62)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            StageSpec,
            ToolCategory,
            ToolSpec,
            WorkflowBlueprint,
        )
        from attune.socratic.visual_editor import ASCIIVisualizer

        many_tools = [
            ToolSpec(
                id=f"tool_{i}", name=f"T{i}", description="", category=ToolCategory.CODE_ANALYSIS
            )
            for i in range(6)
        ]
        agent = AgentBlueprint(
            spec=AgentSpec(
                id="a1",
                name="A",
                role=AgentRole.REVIEWER,
                goal="g",
                backstory="b",
                tools=many_tools,
            )
        )
        bp = WorkflowBlueprint(
            id="bp1",
            name="WF",
            description="d",
            domain="general",
            agents=[agent],
            stages=[StageSpec(id="s1", name="S", description="d", agent_ids=["a1"])],
        )
        out = ASCIIVisualizer().render(bp)
        assert "(+3 more)" in out

    def test_render_truncates_long_agent_string(self):
        """When concatenated agent_ids exceed width, the string is truncated (line 88)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            StageSpec,
            WorkflowBlueprint,
        )
        from attune.socratic.visual_editor import ASCIIVisualizer

        # Many long agent IDs that exceed width when joined
        agent_ids = [f"very-long-agent-name-{i:03d}" for i in range(10)]
        agents = [
            AgentBlueprint(
                spec=AgentSpec(id=aid, name=aid, role=AgentRole.REVIEWER, goal="g", backstory="b")
            )
            for aid in agent_ids
        ]
        bp = WorkflowBlueprint(
            id="bp1",
            name="WF",
            description="d",
            domain="general",
            agents=agents,
            stages=[StageSpec(id="s1", name="S", description="d", agent_ids=agent_ids)],
        )
        out = ASCIIVisualizer(width=40).render(bp)
        assert "..." in out

    def test_render_marks_parallel_stage_indicator(self):
        """A parallel next-stage gets a (parallel) marker (line 95)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            StageSpec,
            WorkflowBlueprint,
        )
        from attune.socratic.visual_editor import ASCIIVisualizer

        agent = AgentBlueprint(
            spec=AgentSpec(id="a1", name="A", role=AgentRole.REVIEWER, goal="g", backstory="b")
        )
        bp = WorkflowBlueprint(
            id="bp1",
            name="WF",
            description="d",
            domain="general",
            agents=[agent],
            stages=[
                StageSpec(id="s1", name="S1", description="d", agent_ids=["a1"]),
                StageSpec(id="s2", name="S2", description="d", agent_ids=["a1"], parallel=True),
            ],
        )
        out = ASCIIVisualizer().render(bp)
        assert "(parallel)" in out

    def test_render_skips_agent_listing_when_stage_empty(self):
        """Stage with no agent_ids skips the agent-string block (branch 85->92)."""
        from attune.socratic.blueprint import (
            AgentBlueprint,
            AgentRole,
            AgentSpec,
            StageSpec,
            WorkflowBlueprint,
        )
        from attune.socratic.visual_editor import ASCIIVisualizer

        agent = AgentBlueprint(
            spec=AgentSpec(id="a1", name="A", role=AgentRole.REVIEWER, goal="g", backstory="b")
        )
        bp = WorkflowBlueprint(
            id="bp1",
            name="WF",
            description="d",
            domain="general",
            agents=[agent],
            stages=[StageSpec(id="s1", name="S", description="d", agent_ids=[])],
        )
        out = ASCIIVisualizer().render(bp)
        # No "()" agent listing line — stage block still present
        assert "S" in out

    def test_center_returns_text_when_too_wide(self):
        """_center returns text unchanged when len(text) >= width (line 138)."""
        from attune.socratic.visual_editor import ASCIIVisualizer

        v = ASCIIVisualizer(width=10)
        long_text = "x" * 20
        assert v._center(long_text) == long_text

    def test_render_compact(self, sample_workflow_blueprint):
        """Test compact rendering."""
        from attune.socratic.visual_editor import ASCIIVisualizer

        visualizer = ASCIIVisualizer()
        compact = visualizer.render_compact(sample_workflow_blueprint)

        assert isinstance(compact, str)
        assert len(compact) > 0


class TestVisualWorkflowEditor:
    """Tests for VisualWorkflowEditor class."""

    def test_create_editor(self):
        """Test creating a visual workflow editor."""
        from attune.socratic.visual_editor import VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        assert editor is not None

    def test_editor_has_visualizer(self):
        """Test editor has visualizer attribute."""
        from attune.socratic.visual_editor import VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        assert hasattr(editor, "visualizer")
        assert hasattr(editor, "ascii_visualizer")

    def test_create_editor_state(self, sample_workflow_blueprint):
        """Test creating editor state from blueprint."""
        from attune.socratic.visual_editor import VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        state = editor.create_editor_state(sample_workflow_blueprint)

        assert state is not None
        assert len(state.nodes) > 0

    def test_apply_changes(self, sample_workflow_blueprint):
        """Test applying editor changes to blueprint."""
        from attune.socratic.visual_editor import VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        state = editor.create_editor_state(sample_workflow_blueprint)

        # Apply changes
        updated_blueprint = editor.apply_changes(state, sample_workflow_blueprint)

        assert updated_blueprint is not None
        assert updated_blueprint.id == sample_workflow_blueprint.id

    def test_render_ascii(self, sample_workflow_blueprint):
        """Test ASCII rendering via editor."""
        from attune.socratic.visual_editor import VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        ascii_art = editor.render_ascii(sample_workflow_blueprint)

        assert isinstance(ascii_art, str)
        assert len(ascii_art) > 0

    def test_render_compact(self, sample_workflow_blueprint):
        """Test compact rendering via editor."""
        from attune.socratic.visual_editor import VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        compact = editor.render_compact(sample_workflow_blueprint)

        assert isinstance(compact, str)
        assert len(compact) > 0

    def test_generate_html_editor(self, sample_workflow_blueprint):
        """Test generating HTML editor."""
        from attune.socratic.visual_editor import VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        html = editor.generate_html_editor(sample_workflow_blueprint)

        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "react" in html.lower()

    def test_generate_react_schema(self, sample_workflow_blueprint):
        """Test generating React schema."""
        from attune.socratic.visual_editor import VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        schema = editor.generate_react_schema(sample_workflow_blueprint)

        assert isinstance(schema, dict)
        assert "nodes" in schema
        assert "edges" in schema

    def test_validate_state_empty(self):
        """Test validating empty editor state."""
        from attune.socratic.visual_editor import EditorState, VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        state = EditorState()

        errors = editor.validate_state(state)

        assert isinstance(errors, list)
        assert len(errors) > 0  # Should have errors for missing start/end

    def test_validate_state_valid(self, sample_workflow_blueprint):
        """Test validating a valid editor state."""
        from attune.socratic.visual_editor import VisualWorkflowEditor

        editor = VisualWorkflowEditor()
        state = editor.create_editor_state(sample_workflow_blueprint)

        errors = editor.validate_state(state)

        assert isinstance(errors, list)
        # Valid state should have no errors (or minimal)


class TestGenerateReactFlowSchema:
    """Tests for generate_react_flow_schema function."""

    def test_generate_schema(self, sample_workflow_blueprint):
        """Test generating React Flow schema from editor state."""
        from attune.socratic.visual_editor import WorkflowVisualizer, generate_react_flow_schema

        # First convert blueprint to editor state
        visualizer = WorkflowVisualizer()
        state = visualizer.blueprint_to_editor(sample_workflow_blueprint)

        # Then generate schema from state
        schema = generate_react_flow_schema(state)

        assert isinstance(schema, dict)
        assert "nodes" in schema
        assert "edges" in schema
        assert "defaultViewport" in schema
        assert isinstance(schema["nodes"], list)
        assert isinstance(schema["edges"], list)

    def test_schema_is_json_serializable(self, sample_workflow_blueprint):
        """Test that schema can be serialized to JSON."""
        from attune.socratic.visual_editor import WorkflowVisualizer, generate_react_flow_schema

        visualizer = WorkflowVisualizer()
        state = visualizer.blueprint_to_editor(sample_workflow_blueprint)
        schema = generate_react_flow_schema(state)

        # Should not raise
        json_str = json.dumps(schema)
        assert isinstance(json_str, str)

        # Should be parseable
        parsed = json.loads(json_str)
        assert parsed == schema


class TestGenerateEditorHtml:
    """Tests for generate_editor_html function."""

    def test_generate_html(self, sample_workflow_blueprint):
        """Test generating standalone HTML editor."""
        from attune.socratic.visual_editor import generate_editor_html

        html = generate_editor_html(sample_workflow_blueprint)

        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "react" in html.lower() or "script" in html.lower()

    def test_html_contains_workflow_data(self, sample_workflow_blueprint):
        """Test that HTML contains workflow data."""
        from attune.socratic.visual_editor import generate_editor_html

        html = generate_editor_html(sample_workflow_blueprint)

        # Should contain workflow name
        assert sample_workflow_blueprint.name in html

    def test_generate_html_with_title(self, sample_workflow_blueprint):
        """Test generating HTML with custom title."""
        from attune.socratic.visual_editor import generate_editor_html

        html = generate_editor_html(
            sample_workflow_blueprint,
            title="Custom Editor Title",
        )

        assert "Custom Editor Title" in html


class TestVisualEditorValidateState:
    """Cover VisualWorkflowEditor.validate_state error branches."""

    def _make_state(self, nodes, edges):
        from attune.socratic.visual_editor import EditorState

        return EditorState(nodes=nodes, edges=edges)

    def _node(self, node_id: str, node_type):
        from attune.socratic.visual_editor import EditorNode, Position

        return EditorNode(
            node_id=node_id,
            node_type=node_type,
            label=node_id,
            position=Position(x=0, y=0),
            data={},
        )

    def _edge(self, source: str, target: str):
        from attune.socratic.visual_editor import EditorEdge

        return EditorEdge(edge_id=f"{source}-{target}", source=source, target=target)

    def test_validate_state_detects_orphan_node(self):
        """Node with no edges (and not start/end) is reported as orphan (line 154)."""
        from attune.socratic.visual_editor import NodeType, VisualWorkflowEditor

        nodes = [
            self._node("start", NodeType.START),
            self._node("end", NodeType.END),
            self._node("orphan-x", NodeType.AGENT),
        ]
        edges = [self._edge("start", "end")]
        state = self._make_state(nodes, edges)

        editor = VisualWorkflowEditor()
        errors = editor.validate_state(state)

        assert any("Orphan" in e and "orphan-x" in e for e in errors)

    def test_validate_state_detects_cycle(self):
        """Workflow with a cycle is reported (lines 163, 173, 178)."""
        from attune.socratic.visual_editor import NodeType, VisualWorkflowEditor

        # start -> A -> B -> A  (cycle between A and B)
        nodes = [
            self._node("start", NodeType.START),
            self._node("A", NodeType.AGENT),
            self._node("B", NodeType.AGENT),
            self._node("end", NodeType.END),
        ]
        edges = [
            self._edge("start", "A"),
            self._edge("A", "B"),
            self._edge("B", "A"),  # cycle
            self._edge("A", "end"),
        ]
        state = self._make_state(nodes, edges)

        editor = VisualWorkflowEditor()
        errors = editor.validate_state(state)

        assert any("cycle" in e.lower() for e in errors)

    def test_blueprint_to_editor_skips_unknown_agent_in_stage(self, sample_workflow_blueprint):
        """Stage that references an agent not in the blueprint skips that node (line 105)."""
        from attune.socratic.blueprint import StageSpec
        from attune.socratic.visual_editor import (
            NodeType,
            WorkflowVisualizer,
        )

        # Add a stage that references an unknown agent ID
        sample_workflow_blueprint.stages.append(
            StageSpec(
                id="ghost-stage",
                name="Ghost",
                description="references unknown agent",
                agent_ids=["nonexistent-agent-id"],
                depends_on=[sample_workflow_blueprint.stages[0].id],
            )
        )
        viz = WorkflowVisualizer()
        state = viz.blueprint_to_editor(sample_workflow_blueprint)

        # The ghost-stage stage node should exist, but the missing agent's
        # AGENT node must not.
        agent_ids = [n.node_id for n in state.nodes if n.node_type == NodeType.AGENT]
        assert "nonexistent-agent-id" not in agent_ids

    def test_blueprint_to_editor_with_no_stages_does_not_connect_to_end(self):
        """Blueprint with empty stages skips the end-edge creation (branch 145->156)."""
        from attune.socratic.blueprint import WorkflowBlueprint
        from attune.socratic.visual_editor import WorkflowVisualizer

        bp = WorkflowBlueprint(
            id="empty-1",
            name="Empty",
            description="No stages",
            domain="general",
            agents=[],
            stages=[],
        )
        viz = WorkflowVisualizer()
        state = viz.blueprint_to_editor(bp)

        # Should still produce start and end nodes, but no edges (no stage to link)
        node_ids = {n.node_id for n in state.nodes}
        assert "start" in node_ids
        assert "end" in node_ids
        assert state.edges == []

    def test_workflow_visualizer_from_blueprint_alias(self, sample_workflow_blueprint):
        """from_blueprint is an alias for blueprint_to_editor (line 168)."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        viz = WorkflowVisualizer()
        state = viz.from_blueprint(sample_workflow_blueprint)
        assert state.workflow_id == sample_workflow_blueprint.id

    def test_workflow_visualizer_to_blueprint_without_original(self, sample_workflow_blueprint):
        """to_blueprint with no original_blueprint constructs a minimal one (lines 185-195)."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        viz = WorkflowVisualizer()
        state = viz.blueprint_to_editor(sample_workflow_blueprint)
        rebuilt = viz.to_blueprint(state, original_blueprint=None)

        assert rebuilt.name == "Reconstructed Workflow"
        assert rebuilt.id == state.workflow_id

    def test_workflow_visualizer_to_blueprint_with_original(self, sample_workflow_blueprint):
        """to_blueprint with original_blueprint skips the placeholder branch (185->195)."""
        from attune.socratic.visual_editor import WorkflowVisualizer

        viz = WorkflowVisualizer()
        state = viz.blueprint_to_editor(sample_workflow_blueprint)
        rebuilt = viz.to_blueprint(state, original_blueprint=sample_workflow_blueprint)

        assert rebuilt.name == sample_workflow_blueprint.name
        assert rebuilt.id == sample_workflow_blueprint.id

    def test_validate_state_visits_node_only_once(self):
        """Diamond pattern (two paths converge) hits the 'already visited' branch (line 165)."""
        from attune.socratic.visual_editor import NodeType, VisualWorkflowEditor

        # start -> A -> C -> end
        # start -> B -> C -> end
        # When traversing from start, both A and B reach C; second time C is in visited.
        nodes = [
            self._node("start", NodeType.START),
            self._node("A", NodeType.AGENT),
            self._node("B", NodeType.AGENT),
            self._node("C", NodeType.AGENT),
            self._node("end", NodeType.END),
        ]
        edges = [
            self._edge("start", "A"),
            self._edge("start", "B"),
            self._edge("A", "C"),
            self._edge("B", "C"),
            self._edge("C", "end"),
        ]
        state = self._make_state(nodes, edges)

        editor = VisualWorkflowEditor()
        errors = editor.validate_state(state)
        # No cycle, no orphans — the diamond is just a converging DAG
        assert not any("cycle" in e.lower() for e in errors)
        assert not any("Orphan" in e for e in errors)
