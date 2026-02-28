"""Visual Workflow Editor

Provides a visual editor for modifying generated workflow blueprints.
Supports both terminal-based visualization and web-based React components.

Features:
- ASCII art workflow visualization for terminal
- Drag-and-drop capable React schemas
- Agent configuration panels
- Stage dependency editing
- Real-time validation

This module re-exports all public symbols from the focused submodules
so that existing ``from attune.socratic.visual_editor import X`` imports
continue to work unchanged.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any

from .ascii_visualizer import ASCIIVisualizer
from .blueprint import WorkflowBlueprint
from .editor_models import (
    EditorEdge,
    EditorNode,
    EditorState,
    NodeType,
    Position,
)
from .react_editor import generate_editor_html, generate_react_flow_schema
from .workflow_visualizer import WorkflowVisualizer


class VisualWorkflowEditor:
    """High-level API for visual workflow editing."""

    def __init__(self) -> None:
        """Initialize the editor."""
        self.visualizer = WorkflowVisualizer()
        self.ascii_visualizer = ASCIIVisualizer()

    def create_editor_state(self, blueprint: WorkflowBlueprint) -> EditorState:
        """Create editor state from blueprint.

        Args:
            blueprint: The workflow blueprint

        Returns:
            EditorState for the editor

        """
        return self.visualizer.blueprint_to_editor(blueprint)

    def apply_changes(
        self,
        state: EditorState,
        original_blueprint: WorkflowBlueprint,
    ) -> WorkflowBlueprint:
        """Apply editor changes to create updated blueprint.

        Args:
            state: Modified editor state
            original_blueprint: Original blueprint

        Returns:
            Updated WorkflowBlueprint

        """
        return self.visualizer.editor_to_blueprint(state, original_blueprint)

    def render_ascii(self, blueprint: WorkflowBlueprint) -> str:
        """Render workflow as ASCII art.

        Args:
            blueprint: The workflow blueprint

        Returns:
            ASCII art visualization

        """
        return self.ascii_visualizer.render(blueprint)

    def render_compact(self, blueprint: WorkflowBlueprint) -> str:
        """Render compact representation.

        Args:
            blueprint: The workflow blueprint

        Returns:
            Compact string

        """
        return self.ascii_visualizer.render_compact(blueprint)

    def generate_html_editor(self, blueprint: WorkflowBlueprint) -> str:
        """Generate HTML page with interactive editor.

        Args:
            blueprint: The workflow blueprint

        Returns:
            Complete HTML page

        """
        return generate_editor_html(blueprint)

    def generate_react_schema(self, blueprint: WorkflowBlueprint) -> dict[str, Any]:
        """Generate React Flow compatible schema.

        Args:
            blueprint: The workflow blueprint

        Returns:
            React Flow schema

        """
        state = self.visualizer.blueprint_to_editor(blueprint)
        return generate_react_flow_schema(state)

    def validate_state(self, state: EditorState) -> list[str]:
        """Validate editor state for errors.

        Args:
            state: The editor state

        Returns:
            List of validation errors (empty if valid)

        """
        errors: list[str] = []

        # Check for required nodes
        has_start = any(n.node_type == NodeType.START for n in state.nodes)
        has_end = any(n.node_type == NodeType.END for n in state.nodes)

        if not has_start:
            errors.append("Workflow must have a start node")
        if not has_end:
            errors.append("Workflow must have an end node")

        # Check for orphan nodes (no connections)
        node_ids = {n.node_id for n in state.nodes}
        connected_nodes: set[str] = set()
        for edge in state.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)

        orphans = node_ids - connected_nodes - {"start", "end"}
        if orphans:
            errors.append(f"Orphan nodes (not connected): {', '.join(orphans)}")

        # Check for cycles (simple detection)
        # Note: A more robust implementation would use DFS
        visited: set[str] = set()

        def check_cycle(node_id: str, path: set[str]) -> bool:
            if node_id in path:
                return True
            if node_id in visited:
                return False

            visited.add(node_id)
            path.add(node_id)

            for edge in state.edges:
                if edge.source == node_id:
                    if check_cycle(edge.target, path.copy()):
                        return True

            return False

        if check_cycle("start", set()):
            errors.append("Workflow contains a cycle")

        return errors


# Re-export all public symbols for backward compatibility
__all__ = [
    "ASCIIVisualizer",
    "EditorEdge",
    "EditorNode",
    "EditorState",
    "NodeType",
    "Position",
    "VisualWorkflowEditor",
    "WorkflowVisualizer",
    "generate_editor_html",
    "generate_react_flow_schema",
]
