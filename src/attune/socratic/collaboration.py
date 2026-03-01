"""Collaboration Features for Socratic Workflow Builder

Enables multiple users to collaboratively refine workflow requirements
and review generated workflows.

Features:
- Collaborative sessions with multiple participants
- Comment and discussion threads
- Voting on requirements and decisions
- Change tracking and history
- Conflict resolution
- Real-time synchronization support

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .collaboration_invitations import (  # noqa: F401
    Invitation,
    InvitationManager,
)
from .collaboration_models import (
    Change,
    ChangeType,
    CollaborativeSession,
    Comment,
    CommentStatus,
    Participant,
    ParticipantRole,
    Vote,
    VoteType,
    VotingResult,
)
from .collaboration_sync import (  # noqa: F401
    SyncAdapter,
    SyncEvent,
)

# =============================================================================
# COLLABORATION MANAGER
# =============================================================================


class CollaborationManager:
    """Manages collaborative workflow sessions."""

    def __init__(self, storage_path: Path | str | None = None):
        """Initialize the manager.

        Args:
            storage_path: Path to persist collaboration data

        """
        if storage_path is None:
            storage_path = Path.home() / ".attune" / "socratic" / "collaboration"
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._sessions: dict[str, CollaborativeSession] = {}
        self._change_listeners: list[Callable[[Change], None]] = []

        self._load_sessions()

    def create_session(
        self,
        base_session_id: str,
        name: str,
        owner_id: str,
        owner_name: str,
        description: str = "",
    ) -> CollaborativeSession:
        """Create a new collaborative session.

        Args:
            base_session_id: ID of the underlying SocraticSession
            name: Session name
            owner_id: ID of the session owner
            owner_name: Name of the session owner
            description: Optional description

        Returns:
            The created session

        """
        session_id = hashlib.sha256(f"{base_session_id}:{time.time()}".encode()).hexdigest()[:12]

        owner = Participant(
            user_id=owner_id,
            name=owner_name,
            role=ParticipantRole.OWNER,
            is_online=True,
        )

        session = CollaborativeSession(
            session_id=session_id,
            base_session_id=base_session_id,
            name=name,
            description=description,
            participants=[owner],
        )

        self._sessions[session_id] = session
        self._save_session(session)

        return session

    def get_session(self, session_id: str) -> CollaborativeSession | None:
        """Get a collaborative session by ID."""
        return self._sessions.get(session_id)

    def add_participant(
        self,
        session_id: str,
        user_id: str,
        name: str,
        email: str | None = None,
        role: ParticipantRole = ParticipantRole.REVIEWER,
    ) -> Participant | None:
        """Add a participant to a session.

        Args:
            session_id: Session ID
            user_id: User ID
            name: User name
            email: Optional email
            role: Participant role

        Returns:
            The added participant or None

        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check if already a participant
        existing = next((p for p in session.participants if p.user_id == user_id), None)
        if existing:
            return existing

        participant = Participant(
            user_id=user_id,
            name=name,
            email=email,
            role=role,
        )
        session.participants.append(participant)
        session.updated_at = datetime.now()

        self._save_session(session)
        return participant

    def update_participant_role(
        self,
        session_id: str,
        user_id: str,
        new_role: ParticipantRole,
        by_user_id: str,
    ) -> bool:
        """Update a participant's role.

        Args:
            session_id: Session ID
            user_id: User ID to update
            new_role: New role
            by_user_id: ID of user making the change

        Returns:
            True if successful

        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Check permissions
        requester = next((p for p in session.participants if p.user_id == by_user_id), None)
        if not requester or requester.role != ParticipantRole.OWNER:
            return False

        participant = next((p for p in session.participants if p.user_id == user_id), None)
        if not participant:
            return False

        participant.role = new_role
        session.updated_at = datetime.now()

        self._save_session(session)
        return True

    def add_comment(
        self,
        session_id: str,
        author_id: str,
        content: str,
        target_type: str,
        target_id: str,
        parent_id: str | None = None,
    ) -> Comment | None:
        """Add a comment to a session.

        Args:
            session_id: Session ID
            author_id: Comment author ID
            content: Comment content
            target_type: Type of target element
            target_id: ID of target element
            parent_id: Optional parent comment ID for threading

        Returns:
            The created comment or None

        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Verify author is a participant
        author = next((p for p in session.participants if p.user_id == author_id), None)
        if not author:
            return None

        comment_id = hashlib.sha256(f"{session_id}:{author_id}:{time.time()}".encode()).hexdigest()[
            :12
        ]

        comment = Comment(
            comment_id=comment_id,
            author_id=author_id,
            content=content,
            target_type=target_type,
            target_id=target_id,
            parent_id=parent_id,
        )
        session.comments.append(comment)
        session.updated_at = datetime.now()

        # Track change
        self._track_change(
            session,
            ChangeType.COMMENT_ADDED,
            author_id,
            f"Comment added on {target_type}",
            after_value={"comment_id": comment_id, "target": target_id},
        )

        self._save_session(session)
        return comment

    def resolve_comment(
        self,
        session_id: str,
        comment_id: str,
        by_user_id: str,
        status: CommentStatus = CommentStatus.RESOLVED,
    ) -> bool:
        """Resolve a comment.

        Args:
            session_id: Session ID
            comment_id: Comment ID
            by_user_id: User resolving the comment
            status: New status

        Returns:
            True if successful

        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        comment = next((c for c in session.comments if c.comment_id == comment_id), None)
        if not comment:
            return False

        comment.status = status
        comment.updated_at = datetime.now()
        session.updated_at = datetime.now()

        self._save_session(session)
        return True

    def add_reaction(
        self,
        session_id: str,
        comment_id: str,
        user_id: str,
        emoji: str,
    ) -> bool:
        """Add a reaction to a comment.

        Args:
            session_id: Session ID
            comment_id: Comment ID
            user_id: User adding reaction
            emoji: Emoji reaction

        Returns:
            True if successful

        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        comment = next((c for c in session.comments if c.comment_id == comment_id), None)
        if not comment:
            return False

        if emoji not in comment.reactions:
            comment.reactions[emoji] = []

        if user_id not in comment.reactions[emoji]:
            comment.reactions[emoji].append(user_id)
            session.updated_at = datetime.now()
            self._save_session(session)

        return True

    def cast_vote(
        self,
        session_id: str,
        voter_id: str,
        target_type: str,
        target_id: str,
        vote_type: VoteType,
        comment: str = "",
    ) -> Vote | None:
        """Cast a vote on a target.

        Args:
            session_id: Session ID
            voter_id: Voter ID
            target_type: Type of target
            target_id: ID of target
            vote_type: Type of vote
            comment: Optional comment

        Returns:
            The cast vote or None

        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Verify voter is a participant with voting rights
        voter = next((p for p in session.participants if p.user_id == voter_id), None)
        if not voter or voter.role == ParticipantRole.VIEWER:
            return None

        # Check if already voted
        existing = next(
            (
                v
                for v in session.votes
                if v.voter_id == voter_id
                and v.target_type == target_type
                and v.target_id == target_id
            ),
            None,
        )
        if existing:
            # Update existing vote
            existing.vote_type = vote_type
            existing.comment = comment
            existing.created_at = datetime.now()
            session.updated_at = datetime.now()
            self._save_session(session)
            return existing

        vote_id = hashlib.sha256(
            f"{session_id}:{voter_id}:{target_id}:{time.time()}".encode(),
        ).hexdigest()[:12]

        vote = Vote(
            vote_id=vote_id,
            voter_id=voter_id,
            target_type=target_type,
            target_id=target_id,
            vote_type=vote_type,
            comment=comment,
        )
        session.votes.append(vote)
        session.updated_at = datetime.now()

        # Track change
        self._track_change(
            session,
            ChangeType.VOTE_CAST,
            voter_id,
            f"{vote_type.value} vote on {target_type}",
            after_value={"target": target_id, "vote": vote_type.value},
        )

        self._save_session(session)
        return vote

    def get_voting_result(
        self,
        session_id: str,
        target_type: str,
        target_id: str,
    ) -> VotingResult | None:
        """Get voting results for a target.

        Args:
            session_id: Session ID
            target_type: Type of target
            target_id: ID of target

        Returns:
            VotingResult or None

        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Get votes for this target
        votes = [
            v for v in session.votes if v.target_type == target_type and v.target_id == target_id
        ]

        # Count by type
        approvals = sum(1 for v in votes if v.vote_type == VoteType.APPROVE)
        rejections = sum(1 for v in votes if v.vote_type == VoteType.REJECT)
        abstentions = sum(1 for v in votes if v.vote_type == VoteType.ABSTAIN)

        # Calculate quorum
        eligible_voters = [p for p in session.participants if p.role != ParticipantRole.VIEWER]
        participation_rate = len(votes) / len(eligible_voters) if eligible_voters else 0
        quorum_reached = participation_rate >= session.quorum

        # Calculate approval
        active_votes = approvals + rejections
        approval_rate = approvals / active_votes if active_votes > 0 else 0
        is_approved = quorum_reached and approval_rate >= session.approval_threshold

        return VotingResult(
            target_id=target_id,
            total_votes=len(votes),
            approvals=approvals,
            rejections=rejections,
            abstentions=abstentions,
            is_approved=is_approved,
            quorum_reached=quorum_reached,
        )

    def get_comments_for_target(
        self,
        session_id: str,
        target_type: str,
        target_id: str,
        include_resolved: bool = True,
    ) -> list[Comment]:
        """Get comments for a target.

        Args:
            session_id: Session ID
            target_type: Type of target
            target_id: ID of target
            include_resolved: Include resolved comments

        Returns:
            List of comments

        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        comments = [
            c for c in session.comments if c.target_type == target_type and c.target_id == target_id
        ]

        if not include_resolved:
            comments = [c for c in comments if c.status == CommentStatus.OPEN]

        return sorted(comments, key=lambda c: c.created_at)

    def get_change_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[Change]:
        """Get change history for a session.

        Args:
            session_id: Session ID
            limit: Maximum changes to return

        Returns:
            List of changes (most recent first)

        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        return sorted(
            session.changes,
            key=lambda c: c.created_at,
            reverse=True,
        )[:limit]

    def track_change(
        self,
        session_id: str,
        change_type: ChangeType,
        author_id: str,
        description: str,
        before_value: Any = None,
        after_value: Any = None,
    ):
        """Track a change in the session.

        Args:
            session_id: Session ID
            change_type: Type of change
            author_id: Author of the change
            description: Description of the change
            before_value: Value before change
            after_value: Value after change

        """
        session = self._sessions.get(session_id)
        if session:
            self._track_change(
                session,
                change_type,
                author_id,
                description,
                before_value,
                after_value,
            )
            self._save_session(session)

    def add_change_listener(self, listener: Callable[[Change], None]):
        """Add a listener for changes.

        Args:
            listener: Callback function

        """
        self._change_listeners.append(listener)

    def remove_change_listener(self, listener: Callable[[Change], None]):
        """Remove a change listener.

        Args:
            listener: Callback function to remove

        """
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)

    def _track_change(
        self,
        session: CollaborativeSession,
        change_type: ChangeType,
        author_id: str,
        description: str,
        before_value: Any = None,
        after_value: Any = None,
    ):
        """Internal method to track a change."""
        change_id = hashlib.sha256(f"{session.session_id}:{time.time()}".encode()).hexdigest()[:12]

        change = Change(
            change_id=change_id,
            change_type=change_type,
            author_id=author_id,
            description=description,
            before_value=before_value,
            after_value=after_value,
        )
        session.changes.append(change)

        # Notify listeners
        for listener in self._change_listeners:
            try:
                listener(change)
            except Exception:
                # INTENTIONAL: Listener failure should not break change tracking.
                # One bad listener shouldn't prevent others from executing.
                pass

    def _save_session(self, session: CollaborativeSession):
        """Save a session to storage."""
        path = self.storage_path / f"{session.session_id}.json"
        with path.open("w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def _load_sessions(self):
        """Load all sessions from storage."""
        for path in self.storage_path.glob("*.json"):
            try:
                with path.open("r") as f:
                    data = json.load(f)
                session = CollaborativeSession.from_dict(data)
                self._sessions[session.session_id] = session
            except Exception:
                # INTENTIONAL: Skip corrupted session files gracefully.
                # Loading should not fail due to one malformed file.
                pass

    def list_sessions(self) -> list[CollaborativeSession]:
        """List all collaborative sessions."""
        return sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True,
        )

    def get_user_sessions(self, user_id: str) -> list[CollaborativeSession]:
        """Get sessions for a specific user.

        Args:
            user_id: User ID

        Returns:
            List of sessions the user participates in

        """
        return [
            s for s in self._sessions.values() if any(p.user_id == user_id for p in s.participants)
        ]
