"""Refactoring Crew - Types

Enums and dataclasses for the refactoring crew:
RefactoringCategory, Severity, Impact, RefactoringFinding,
CodeCheckpoint, RefactoringReport, UserProfile, RefactoringConfig.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum

# =============================================================================
# Enums
# =============================================================================


class RefactoringCategory(Enum):
    """Categories of refactoring opportunities."""

    EXTRACT_METHOD = "extract_method"
    EXTRACT_VARIABLE = "extract_variable"
    RENAME = "rename"
    SIMPLIFY = "simplify"
    REMOVE_DUPLICATION = "remove_duplication"
    RESTRUCTURE = "restructure"
    DEAD_CODE = "dead_code"
    TYPE_SAFETY = "type_safety"
    INLINE = "inline"
    CONSOLIDATE_CONDITIONAL = "consolidate_conditional"
    OTHER = "other"


class Severity(Enum):
    """Severity levels for refactoring findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Impact(Enum):
    """Estimated impact of applying a refactoring."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RefactoringFinding:
    """A single refactoring opportunity identified by the analyzer."""

    id: str
    title: str
    description: str
    category: RefactoringCategory
    severity: Severity
    file_path: str
    start_line: int
    end_line: int
    before_code: str = ""
    after_code: str | None = None
    confidence: float = 1.0
    estimated_impact: Impact = Impact.MEDIUM
    rationale: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert finding to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "before_code": self.before_code,
            "after_code": self.after_code,
            "confidence": self.confidence,
            "estimated_impact": self.estimated_impact.value,
            "rationale": self.rationale,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RefactoringFinding":
        """Create finding from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", "Untitled"),
            description=data.get("description", ""),
            category=RefactoringCategory(data.get("category", "other")),
            severity=Severity(data.get("severity", "medium")),
            file_path=data.get("file_path", ""),
            start_line=data.get("start_line", 0),
            end_line=data.get("end_line", 0),
            before_code=data.get("before_code", ""),
            after_code=data.get("after_code"),
            confidence=data.get("confidence", 1.0),
            estimated_impact=Impact(data.get("estimated_impact", "medium")),
            rationale=data.get("rationale", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CodeCheckpoint:
    """Checkpoint for rollback capability."""

    id: str
    file_path: str
    original_content: str
    timestamp: str
    finding_id: str

    def to_dict(self) -> dict:
        """Convert checkpoint to dictionary."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "original_content": self.original_content,
            "timestamp": self.timestamp,
            "finding_id": self.finding_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CodeCheckpoint":
        """Create checkpoint from dictionary."""
        return cls(
            id=data["id"],
            file_path=data["file_path"],
            original_content=data["original_content"],
            timestamp=data["timestamp"],
            finding_id=data["finding_id"],
        )


@dataclass
class RefactoringReport:
    """Complete refactoring analysis report."""

    target: str
    findings: list[RefactoringFinding]
    summary: str = ""
    duration_seconds: float = 0.0
    agents_used: list[str] = field(default_factory=list)
    checkpoints: list[CodeCheckpoint] = field(default_factory=list)
    memory_graph_hits: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def high_impact_findings(self) -> list[RefactoringFinding]:
        """Get high impact findings."""
        return [f for f in self.findings if f.estimated_impact == Impact.HIGH]

    @property
    def findings_by_category(self) -> dict[str, list[RefactoringFinding]]:
        """Group findings by category."""
        result: dict[str, list[RefactoringFinding]] = {}
        for finding in self.findings:
            cat = finding.category.value
            if cat not in result:
                result[cat] = []
            result[cat].append(finding)
        return result

    @property
    def total_lines_affected(self) -> int:
        """Calculate total lines that would be affected."""
        return sum(f.end_line - f.start_line + 1 for f in self.findings)

    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "target": self.target,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "duration_seconds": self.duration_seconds,
            "agents_used": self.agents_used,
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "memory_graph_hits": self.memory_graph_hits,
            "high_impact_count": len(self.high_impact_findings),
            "total_lines_affected": self.total_lines_affected,
            "metadata": self.metadata,
        }


@dataclass
class UserProfile:
    """User preferences learned over time."""

    user_id: str = "default"
    updated_at: str = ""
    accepted_categories: dict[str, int] = field(default_factory=dict)
    rejected_categories: dict[str, int] = field(default_factory=dict)
    preferred_complexity: str = "medium"
    history: list[dict] = field(default_factory=list)

    def get_category_score(self, category: RefactoringCategory) -> float:
        """Get score for a category based on user history (higher = more preferred)."""
        cat = category.value
        accepted = self.accepted_categories.get(cat, 0)
        rejected = self.rejected_categories.get(cat, 0)
        total = accepted + rejected
        if total == 0:
            return 0.5  # Neutral
        return accepted / total

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "updated_at": self.updated_at,
            "preferences": {
                "accepted_categories": self.accepted_categories,
                "rejected_categories": self.rejected_categories,
                "preferred_complexity": self.preferred_complexity,
            },
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Create from dictionary."""
        prefs = data.get("preferences", {})
        return cls(
            user_id=data.get("user_id", "default"),
            updated_at=data.get("updated_at", ""),
            accepted_categories=prefs.get("accepted_categories", {}),
            rejected_categories=prefs.get("rejected_categories", {}),
            preferred_complexity=prefs.get("preferred_complexity", "medium"),
            history=data.get("history", []),
        )


@dataclass
class RefactoringConfig:
    """Configuration for the refactoring crew."""

    # API Configuration
    provider: str = "anthropic"
    api_key: str | None = None

    # Analysis Configuration
    depth: str = "standard"  # "quick", "standard", "thorough"
    focus_areas: list[str] = field(
        default_factory=lambda: [
            "extract_method",
            "simplify",
            "remove_duplication",
            "rename",
            "dead_code",
        ],
    )

    # Memory Graph
    memory_graph_enabled: bool = True
    memory_graph_path: str = "patterns/refactoring_memory.json"

    # User Profile
    user_profile_enabled: bool = True
    user_profile_path: str = ".attune/refactor_profile.json"

    # Agent Tiers (cost optimization)
    analyzer_tier: str = "capable"  # GPT-4o / Claude Sonnet
    writer_tier: str = "capable"

    # Resilience
    resilience_enabled: bool = True
    timeout_seconds: float = 300.0

    # XML Prompts
    xml_prompts_enabled: bool = True
    xml_schema_version: str = "1.0"
