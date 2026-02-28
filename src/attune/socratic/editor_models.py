"""Visual Editor Data Models

Data structures for the visual workflow editor, including nodes,
edges, positions, and editor state.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(Enum):
    """Types of nodes in the visual editor."""

    AGENT = "agent"
    STAGE = "stage"
    START = "start"
    END = "end"
    CONNECTOR = "connector"


@dataclass
class Position:
    """Position in the visual editor."""

    x: int
    y: int

    def to_dict(self) -> dict[str, int]:
        """Convert position to dictionary.

        Returns:
            Dict with x and y coordinates.

        """
        return {"x": self.x, "y": self.y}


@dataclass
class EditorNode:
    """A node in the visual editor."""

    node_id: str
    node_type: str | NodeType  # Accept both string and enum
    label: str
    position: dict[str, int] | Position  # Accept both dict and Position
    data: dict[str, Any] = field(default_factory=dict)
    selected: bool = False
    locked: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize node to dictionary.

        Returns:
            Dict representation of the node.

        """
        # Handle both string and enum for node_type
        node_type_str = (
            self.node_type.value if isinstance(self.node_type, NodeType) else self.node_type
        )
        # Handle both dict and Position for position
        pos_dict = self.position.to_dict() if isinstance(self.position, Position) else self.position
        return {
            "id": self.node_id,
            "type": node_type_str,
            "data": {"label": self.label, **self.data},
            "position": pos_dict,
            "selected": self.selected,
            "locked": self.locked,
        }


@dataclass
class EditorEdge:
    """An edge (connection) in the visual editor."""

    edge_id: str
    source: str  # Source node ID
    target: str  # Target node ID
    label: str = ""
    animated: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize edge to dictionary.

        Returns:
            Dict representation of the edge.

        """
        return {
            "id": self.edge_id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "animated": self.animated,
        }


@dataclass
class EditorState:
    """State of the visual editor."""

    workflow_id: str = ""  # ID of the workflow being edited
    nodes: list[EditorNode] = field(default_factory=list)
    edges: list[EditorEdge] = field(default_factory=list)
    selected_node_id: str | None = None
    zoom: float = 1.0
    pan_x: int = 0
    pan_y: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary.

        Returns:
            Dict representation of the editor state.

        """
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "selectedNodeId": self.selected_node_id,
            "zoom": self.zoom,
            "panX": self.pan_x,
            "panY": self.pan_y,
        }

    def to_react_flow(self) -> dict[str, Any]:
        """Convert state to React Flow schema format.

        Returns:
            Dict with 'nodes' and 'edges' arrays for React Flow

        """
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
