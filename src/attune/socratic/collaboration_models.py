"""Collaboration Data Models.

Enums and dataclasses for collaborative workflow sessions.
Extracted from collaboration.py for maintainability.

Contains:
- ParticipantRole, CommentStatus, VoteType, ChangeType (enums)
- Participant, Comment, Vote, Change, VotingResult (dataclasses)
- CollaborativeSession (dataclass)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# =============================================================================
# ENUMS
# =============================================================================


class ParticipantRole(Enum):
    """Roles for session participants."""

    OWNER = "owner"  # Full control
    EDITOR = "editor"  # Can edit and vote
    REVIEWER = "reviewer"  # Can comment and vote
    VIEWER = "viewer"  # Read-only access


class CommentStatus(Enum):
    """Status of a comment."""

    OPEN = "open"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class VoteType(Enum):
    """Types of votes."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class ChangeType(Enum):
    """Types of changes tracked."""

    GOAL_SET = "goal_set"
    ANSWER_SUBMITTED = "answer_submitted"
    REQUIREMENT_ADDED = "requirement_added"
    REQUIREMENT_REMOVED = "requirement_removed"
    AGENT_ADDED = "agent_added"
    AGENT_REMOVED = "agent_removed"
    WORKFLOW_MODIFIED = "workflow_modified"
    COMMENT_ADDED = "comment_added"
    VOTE_CAST = "vote_cast"


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class Participant:
    """A participant in a collaborative session."""

    user_id: str
    name: str
    email: str | None = None
    role: ParticipantRole = ParticipantRole.VIEWER
    joined_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    is_online: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize participant to a JSON-compatible dictionary.

        Returns:
            Dictionary with all participant fields; datetime values as
            ISO-8601 strings and role as its string value.

        """
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "joined_at": self.joined_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "is_online": self.is_online,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Participant:
        """Deserialize a participant from a dictionary.

        Args:
            data: Dictionary as produced by ``to_dict()``.

        Returns:
            A new ``Participant`` instance.

        """
        return cls(
            user_id=data["user_id"],
            name=data["name"],
            email=data.get("email"),
            role=ParticipantRole(data.get("role", "viewer")),
            joined_at=datetime.fromisoformat(data["joined_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
            is_online=data.get("is_online", False),
        )


@dataclass
class Comment:
    """A comment on a session or specific element."""

    comment_id: str
    author_id: str
    content: str
    target_type: str  # "session", "answer", "agent", "stage", etc.
    target_id: str  # ID of the target element
    status: CommentStatus = CommentStatus.OPEN
    parent_id: str | None = None  # For threaded comments
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    reactions: dict[str, list[str]] = field(default_factory=dict)  # emoji -> user_ids

    def to_dict(self) -> dict[str, Any]:
        """Serialize comment to a JSON-compatible dictionary.

        Returns:
            Dictionary with all comment fields; datetime values as
            ISO-8601 strings and status as its string value.

        """
        return {
            "comment_id": self.comment_id,
            "author_id": self.author_id,
            "content": self.content,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "reactions": self.reactions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Comment:
        """Deserialize a comment from a dictionary.

        Args:
            data: Dictionary as produced by ``to_dict()``.

        Returns:
            A new ``Comment`` instance.

        """
        return cls(
            comment_id=data["comment_id"],
            author_id=data["author_id"],
            content=data["content"],
            target_type=data["target_type"],
            target_id=data["target_id"],
            status=CommentStatus(data.get("status", "open")),
            parent_id=data.get("parent_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            reactions=data.get("reactions", {}),
        )


@dataclass
class Vote:
    """A vote on a decision or requirement."""

    vote_id: str
    voter_id: str
    target_type: str  # "requirement", "agent", "workflow", etc.
    target_id: str
    vote_type: VoteType
    comment: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize vote to a JSON-compatible dictionary.

        Returns:
            Dictionary with all vote fields; datetime as ISO-8601 string
            and vote_type as its string value.

        """
        return {
            "vote_id": self.vote_id,
            "voter_id": self.voter_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "vote_type": self.vote_type.value,
            "comment": self.comment,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Vote:
        """Deserialize a vote from a dictionary.

        Args:
            data: Dictionary as produced by ``to_dict()``.

        Returns:
            A new ``Vote`` instance.

        """
        return cls(
            vote_id=data["vote_id"],
            voter_id=data["voter_id"],
            target_type=data["target_type"],
            target_id=data["target_id"],
            vote_type=VoteType(data["vote_type"]),
            comment=data.get("comment", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class Change:
    """A tracked change in the session."""

    change_id: str
    change_type: ChangeType
    author_id: str
    description: str
    before_value: Any = None
    after_value: Any = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize change record to a JSON-compatible dictionary.

        Returns:
            Dictionary with all change fields; datetime as ISO-8601 string
            and change_type as its string value.

        """
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "author_id": self.author_id,
            "description": self.description,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Change:
        """Deserialize a change record from a dictionary.

        Args:
            data: Dictionary as produced by ``to_dict()``.

        Returns:
            A new ``Change`` instance.

        """
        return cls(
            change_id=data["change_id"],
            change_type=ChangeType(data["change_type"]),
            author_id=data["author_id"],
            description=data["description"],
            before_value=data.get("before_value"),
            after_value=data.get("after_value"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class VotingResult:
    """Result of a voting round."""

    target_id: str
    total_votes: int
    approvals: int
    rejections: int
    abstentions: int
    is_approved: bool
    quorum_reached: bool

    @property
    def approval_rate(self) -> float:
        """Calculate approval rate (excluding abstentions)."""
        active_votes = self.approvals + self.rejections
        if active_votes == 0:
            return 0.0
        return self.approvals / active_votes


# =============================================================================
# COLLABORATIVE SESSION
# =============================================================================


@dataclass
class CollaborativeSession:
    """A session with collaboration features enabled."""

    session_id: str
    base_session_id: str  # ID of the underlying SocraticSession
    name: str
    description: str = ""
    participants: list[Participant] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    votes: list[Vote] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    require_approval: bool = True
    approval_threshold: float = 0.5  # 50% approval required
    quorum: float = 0.5  # 50% participation required

    def to_dict(self) -> dict[str, Any]:
        """Serialize session to a JSON-compatible dictionary.

        Returns:
            Dictionary with all session fields; nested participants,
            comments, votes, and changes are each serialized via their
            own ``to_dict()`` methods; datetime values as ISO-8601 strings.

        """
        return {
            "session_id": self.session_id,
            "base_session_id": self.base_session_id,
            "name": self.name,
            "description": self.description,
            "participants": [p.to_dict() for p in self.participants],
            "comments": [c.to_dict() for c in self.comments],
            "votes": [v.to_dict() for v in self.votes],
            "changes": [c.to_dict() for c in self.changes],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "require_approval": self.require_approval,
            "approval_threshold": self.approval_threshold,
            "quorum": self.quorum,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CollaborativeSession:
        """Deserialize a collaborative session from a dictionary.

        Args:
            data: Dictionary as produced by ``to_dict()``.

        Returns:
            A new ``CollaborativeSession`` instance with all nested
            objects reconstructed.

        """
        return cls(
            session_id=data["session_id"],
            base_session_id=data["base_session_id"],
            name=data["name"],
            description=data.get("description", ""),
            participants=[Participant.from_dict(p) for p in data.get("participants", [])],
            comments=[Comment.from_dict(c) for c in data.get("comments", [])],
            votes=[Vote.from_dict(v) for v in data.get("votes", [])],
            changes=[Change.from_dict(c) for c in data.get("changes", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            require_approval=data.get("require_approval", True),
            approval_threshold=data.get("approval_threshold", 0.5),
            quorum=data.get("quorum", 0.5),
        )
