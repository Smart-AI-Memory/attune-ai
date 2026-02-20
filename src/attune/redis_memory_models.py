"""Redis Memory Data Models for Attune AI

Data models used by Redis short-term memory:
- TTLStrategy: TTL strategies for different memory types
- AgentCredentials: Agent identity and access permissions
- StagedPattern: Pattern awaiting validation
- ConflictContext: Context for principled negotiation

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# Import AccessTier from the canonical location to avoid duplicate enums
from .memory.short_term import AccessTier  # noqa: F401 - re-exported


class TTLStrategy(Enum):
    """TTL strategies for different memory types

    Per EMPATHY_PHILOSOPHY.md Section 9.3:
    - Working results: 1 hour
    - Staged patterns: 24 hours
    - Coordination signals: 5 minutes
    - Conflict context: Until resolution
    """

    WORKING_RESULTS = 3600  # 1 hour
    STAGED_PATTERNS = 86400  # 24 hours
    COORDINATION = 300  # 5 minutes
    CONFLICT_CONTEXT = 604800  # 7 days (fallback for unresolved)
    SESSION = 1800  # 30 minutes


@dataclass
class AgentCredentials:
    """Agent identity and access permissions"""

    agent_id: str
    tier: AccessTier
    roles: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def can_read(self) -> bool:
        """All tiers can read"""
        return True

    def can_stage(self) -> bool:
        """Contributor+ can stage patterns"""
        return self.tier.value >= AccessTier.CONTRIBUTOR.value

    def can_validate(self) -> bool:
        """Validator+ can promote patterns"""
        return self.tier.value >= AccessTier.VALIDATOR.value

    def can_administer(self) -> bool:
        """Only Stewards have full admin access"""
        return self.tier.value >= AccessTier.STEWARD.value


@dataclass
class StagedPattern:
    """Pattern awaiting validation"""

    pattern_id: str
    agent_id: str
    pattern_type: str
    name: str
    description: str
    code: str | None = None
    context: dict = field(default_factory=dict)
    confidence: float = 0.5
    staged_at: datetime = field(default_factory=datetime.now)
    interests: list[str] = field(default_factory=list)  # For negotiation

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "agent_id": self.agent_id,
            "pattern_type": self.pattern_type,
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "context": self.context,
            "confidence": self.confidence,
            "staged_at": self.staged_at.isoformat(),
            "interests": self.interests,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StagedPattern":
        """Deserialize from dictionary."""
        return cls(
            pattern_id=data["pattern_id"],
            agent_id=data["agent_id"],
            pattern_type=data["pattern_type"],
            name=data["name"],
            description=data["description"],
            code=data.get("code"),
            context=data.get("context", {}),
            confidence=data.get("confidence", 0.5),
            staged_at=datetime.fromisoformat(data["staged_at"]),
            interests=data.get("interests", []),
        )


@dataclass
class ConflictContext:
    """Context for principled negotiation

    Per Getting to Yes framework:
    - Positions: What each party says they want
    - Interests: Why they want it (underlying needs)
    - BATNA: Best Alternative to Negotiated Agreement
    """

    conflict_id: str
    positions: dict[str, Any]  # agent_id -> stated position
    interests: dict[str, list[str]]  # agent_id -> underlying interests
    batna: str | None = None  # Fallback strategy
    created_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution: str | None = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "positions": self.positions,
            "interests": self.interests,
            "batna": self.batna,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConflictContext":
        """Deserialize from dictionary."""
        return cls(
            conflict_id=data["conflict_id"],
            positions=data["positions"],
            interests=data["interests"],
            batna=data.get("batna"),
            created_at=datetime.fromisoformat(data["created_at"]),
            resolved=data.get("resolved", False),
            resolution=data.get("resolution"),
        )
