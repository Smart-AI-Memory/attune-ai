"""Memory Graph Node Types

Defines node types for the cross-workflow knowledge graph. Most nodes
represent an entity discovered by a workflow (a bug, a fix, a test).
The "Curated memory" category (below) is the exception: those nodes
represent hand-curated cross-session memory - decisions, standing
feedback, project context - that has no workflow origin and no
resolution lifecycle. ``source_workflow`` stays empty and ``severity``
stays unset for curated-memory nodes; ``status`` is reinterpreted as
active/superseded/stale rather than open/investigating/resolved/wontfix
(same field, no schema change). Store curated nodes in the durable
home-directory graph (``MemoryGraph.curated()``), not the cwd-relative
per-project default.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NodeType(Enum):
    """Types of nodes in the memory graph."""

    # Code entities
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"

    # Issues and findings
    BUG = "bug"
    VULNERABILITY = "vulnerability"
    PERFORMANCE_ISSUE = "performance_issue"
    CODE_SMELL = "code_smell"
    TECH_DEBT = "tech_debt"

    # Solutions and patterns
    PATTERN = "pattern"
    FIX = "fix"
    REFACTOR = "refactor"

    # Testing
    TEST = "test"
    TEST_CASE = "test_case"
    COVERAGE_GAP = "coverage_gap"

    # Documentation
    DOC = "doc"
    API_ENDPOINT = "api_endpoint"

    # Dependencies
    DEPENDENCY = "dependency"
    LICENSE = "license"

    # Curated memory (not workflow findings - see module docstring)
    USER_CONTEXT = "user_context"
    FEEDBACK = "feedback"
    PROJECT_CONTEXT = "project_context"
    REFERENCE = "reference"


@dataclass
class Node:
    """A node in the memory graph.

    Represents any entity that workflows discover or create.
    """

    id: str
    type: NodeType
    name: str
    description: str = ""

    # Where this node came from
    source_workflow: str = ""
    source_file: str = ""
    source_line: int | None = None

    # Classification
    severity: str = ""  # critical, high, medium, low, info
    confidence: float = 1.0  # 0.0 - 1.0

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Status tracking
    status: str = "open"  # open, investigating, resolved, wontfix

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "description": self.description,
            "source_workflow": self.source_workflow,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "severity": self.severity,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        """Create node from dictionary."""
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            name=data["name"],
            description=data.get("description", ""),
            source_workflow=data.get("source_workflow", data.get("source_wizard", "")),
            source_file=data.get("source_file", ""),
            source_line=data.get("source_line"),
            severity=data.get("severity", ""),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.now()
            ),
            status=data.get("status", "open"),
        )


@dataclass
class BugNode(Node):
    """Specialized node for bugs."""

    root_cause: str = ""
    fix_suggestion: str = ""
    reproduction_steps: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.type = NodeType.BUG


@dataclass
class VulnerabilityNode(Node):
    """Specialized node for security vulnerabilities."""

    cwe_id: str = ""
    cvss_score: float = 0.0
    attack_vector: str = ""
    remediation: str = ""

    def __post_init__(self):
        self.type = NodeType.VULNERABILITY


@dataclass
class PerformanceNode(Node):
    """Specialized node for performance issues."""

    metric: str = ""  # latency, memory, cpu, etc.
    current_value: float = 0.0
    target_value: float = 0.0
    optimization_suggestion: str = ""

    def __post_init__(self):
        self.type = NodeType.PERFORMANCE_ISSUE


@dataclass
class PatternNode(Node):
    """Specialized node for code patterns."""

    pattern_type: str = ""  # anti-pattern, best-practice, idiom
    language: str = ""
    example_code: str = ""
    applies_to: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.type = NodeType.PATTERN
