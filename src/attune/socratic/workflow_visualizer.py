"""Workflow-to-Editor Conversion

Converts workflow blueprints to visual editor state and back.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .blueprint import StageSpec, WorkflowBlueprint
from .editor_models import (
    EditorEdge,
    EditorNode,
    EditorState,
    NodeType,
    Position,
)


class WorkflowVisualizer:
    """Converts workflow blueprints to visual editor state."""

    def __init__(self, node_spacing: int = 200, stage_spacing: int = 150):
        """Initialize visualizer.

        Args:
            node_spacing: Horizontal spacing between nodes
            stage_spacing: Vertical spacing between stages
        """
        self.node_spacing = node_spacing
        self.stage_spacing = stage_spacing

    def blueprint_to_editor(self, blueprint: WorkflowBlueprint) -> EditorState:
        """Convert a workflow blueprint to editor state.

        Args:
            blueprint: The workflow blueprint

        Returns:
            EditorState ready for visualization
        """
        nodes: list[EditorNode] = []
        edges: list[EditorEdge] = []

        # Create agent lookup (agents are AgentBlueprint objects with .spec attribute)
        agents_by_id = {a.spec.id: a for a in blueprint.agents}

        # Create start node
        start_node = EditorNode(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            position=Position(x=400, y=50),
            locked=True,
        )
        nodes.append(start_node)

        # Process stages
        y_offset = 150
        first_stage = True

        for stage in blueprint.stages:
            # Create stage node
            stage_node = EditorNode(
                node_id=stage.id,
                node_type=NodeType.STAGE,
                label=stage.name,
                position=Position(x=400, y=y_offset),
                data={
                    "parallel": stage.parallel,
                    "timeout": stage.timeout,
                },
            )
            nodes.append(stage_node)

            # Connect from start or dependencies
            if first_stage:
                edges.append(
                    EditorEdge(
                        edge_id=f"start->{stage.id}",
                        source="start",
                        target=stage.id,
                        animated=True,
                    )
                )
                first_stage = False
            else:
                for dep in stage.depends_on:
                    edges.append(
                        EditorEdge(
                            edge_id=f"{dep}->{stage.id}",
                            source=dep,
                            target=stage.id,
                        )
                    )

            # Create agent nodes for this stage
            agent_x_start = 200
            for i, agent_id in enumerate(stage.agent_ids):
                agent_bp = agents_by_id.get(agent_id)
                if not agent_bp:
                    continue

                agent_node = EditorNode(
                    node_id=agent_id,
                    node_type=NodeType.AGENT,
                    label=agent_bp.spec.name,
                    position=Position(
                        x=agent_x_start + (i * self.node_spacing),
                        y=y_offset + 60,
                    ),
                    data={
                        "role": agent_bp.spec.role.value,
                        "tools": [t.id for t in agent_bp.spec.tools],
                        "goal": agent_bp.spec.goal,
                    },
                )
                nodes.append(agent_node)

                # Connect stage to agent
                edges.append(
                    EditorEdge(
                        edge_id=f"{stage.id}->{agent_id}",
                        source=stage.id,
                        target=agent_id,
                    )
                )

            y_offset += self.stage_spacing

        # Create end node
        end_node = EditorNode(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            position=Position(x=400, y=y_offset),
            locked=True,
        )
        nodes.append(end_node)

        # Connect last stage to end
        if blueprint.stages:
            last_stage = blueprint.stages[-1]
            edges.append(
                EditorEdge(
                    edge_id=f"{last_stage.id}->end",
                    source=last_stage.id,
                    target="end",
                    animated=True,
                )
            )

        return EditorState(workflow_id=blueprint.id, nodes=nodes, edges=edges)

    def from_blueprint(self, blueprint: WorkflowBlueprint) -> EditorState:
        """Alias for blueprint_to_editor - converts blueprint to editor state.

        Args:
            blueprint: The workflow blueprint

        Returns:
            EditorState ready for visualization
        """
        return self.blueprint_to_editor(blueprint)

    def to_blueprint(
        self, state: EditorState, original_blueprint: WorkflowBlueprint | None = None
    ) -> WorkflowBlueprint:
        """Alias for editor_to_blueprint - converts editor state back to blueprint.

        Args:
            state: The editor state
            original_blueprint: Original blueprint for reference

        Returns:
            Updated WorkflowBlueprint
        """
        if original_blueprint is None:
            # Create minimal blueprint for reconstruction
            from .blueprint import WorkflowBlueprint

            original_blueprint = WorkflowBlueprint(
                id=state.workflow_id,
                name="Reconstructed Workflow",
                description="Reconstructed from editor state",
                domain="general",
            )
        return self.editor_to_blueprint(state, original_blueprint)

    def editor_to_blueprint(
        self,
        state: EditorState,
        original_blueprint: WorkflowBlueprint,
    ) -> WorkflowBlueprint:
        """Convert editor state back to workflow blueprint.

        Args:
            state: The editor state
            original_blueprint: Original blueprint for reference

        Returns:
            Updated WorkflowBlueprint
        """
        # Extract stage nodes and their agents
        stage_nodes = [n for n in state.nodes if n.node_type == NodeType.STAGE]
        agent_nodes = [n for n in state.nodes if n.node_type == NodeType.AGENT]

        # Build edge lookup
        edges_by_source: dict[str, list[str]] = {}
        edges_by_target: dict[str, list[str]] = {}
        for edge in state.edges:
            edges_by_source.setdefault(edge.source, []).append(edge.target)
            edges_by_target.setdefault(edge.target, []).append(edge.source)

        # Rebuild stages
        new_stages: list[StageSpec] = []
        for stage_node in stage_nodes:
            # Find agents connected to this stage
            agent_ids = [
                target
                for target in edges_by_source.get(stage_node.node_id, [])
                if any(a.node_id == target and a.node_type == NodeType.AGENT for a in agent_nodes)
            ]

            # Find dependencies (stages that connect TO this stage)
            dependencies = [
                source
                for source in edges_by_target.get(stage_node.node_id, [])
                if source != "start"
                and any(s.node_id == source and s.node_type == NodeType.STAGE for s in stage_nodes)
            ]

            new_stages.append(
                StageSpec(
                    id=stage_node.node_id,
                    name=stage_node.label,
                    description=stage_node.data.get("description", f"Stage: {stage_node.label}"),
                    agent_ids=agent_ids,
                    depends_on=dependencies,
                    parallel=stage_node.data.get("parallel", False),
                    timeout=stage_node.data.get("timeout"),
                )
            )

        # Update blueprint
        return WorkflowBlueprint(
            id=original_blueprint.id,
            name=original_blueprint.name,
            description=original_blueprint.description,
            domain=original_blueprint.domain,
            agents=original_blueprint.agents,
            stages=new_stages,
            generated_at=original_blueprint.generated_at,
        )
