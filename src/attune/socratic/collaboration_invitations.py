"""Collaboration Invitation Management.

Manages invitations to join collaborative sessions.
Extracted from collaboration.py for maintainability.

Contains:
- Invitation: Dataclass for session invitations
- InvitationManager: Manages invitation lifecycle

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .collaboration_models import Participant, ParticipantRole

if TYPE_CHECKING:
    from .collaboration import CollaborationManager


@dataclass
class Invitation:
    """An invitation to join a collaborative session."""

    invite_id: str
    session_id: str
    inviter_id: str
    invitee_email: str
    role: ParticipantRole
    message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None
    accepted: bool = False


class InvitationManager:
    """Manages invitations to collaborative sessions."""

    def __init__(self, collaboration_manager: CollaborationManager):
        """Initialize the manager.

        Args:
            collaboration_manager: The collaboration manager

        """
        self.collab = collaboration_manager
        self._invitations: dict[str, Invitation] = {}

    def create_invitation(
        self,
        session_id: str,
        inviter_id: str,
        invitee_email: str,
        role: ParticipantRole = ParticipantRole.REVIEWER,
        message: str = "",
        expires_hours: int = 72,
    ) -> Invitation | None:
        """Create an invitation.

        Args:
            session_id: Session ID
            inviter_id: ID of user sending invite
            invitee_email: Email of invitee
            role: Role to assign
            message: Optional message
            expires_hours: Hours until expiration

        Returns:
            Created invitation or None

        """
        session = self.collab.get_session(session_id)
        if not session:
            return None

        # Verify inviter has permission
        inviter = next((p for p in session.participants if p.user_id == inviter_id), None)
        if not inviter or inviter.role not in [ParticipantRole.OWNER, ParticipantRole.EDITOR]:
            return None

        invite_id = hashlib.sha256(
            f"{session_id}:{invitee_email}:{time.time()}".encode(),
        ).hexdigest()[:16]

        expires = datetime.now() + timedelta(hours=expires_hours)

        invitation = Invitation(
            invite_id=invite_id,
            session_id=session_id,
            inviter_id=inviter_id,
            invitee_email=invitee_email,
            role=role,
            message=message,
            expires_at=expires,
        )

        self._invitations[invite_id] = invitation
        return invitation

    def accept_invitation(
        self,
        invite_id: str,
        user_id: str,
        user_name: str,
    ) -> Participant | None:
        """Accept an invitation.

        Args:
            invite_id: Invitation ID
            user_id: ID of accepting user
            user_name: Name of accepting user

        Returns:
            Added participant or None

        """
        invitation = self._invitations.get(invite_id)
        if not invitation:
            return None

        # Check expiration
        if invitation.expires_at and datetime.now() > invitation.expires_at:
            return None

        if invitation.accepted:
            return None

        # Add participant
        participant = self.collab.add_participant(
            invitation.session_id,
            user_id,
            user_name,
            email=invitation.invitee_email,
            role=invitation.role,
        )

        if participant:
            invitation.accepted = True

        return participant

    def get_pending_invitations(self, session_id: str) -> list[Invitation]:
        """Get pending invitations for a session.

        Args:
            session_id: Session ID

        Returns:
            List of pending invitations

        """
        now = datetime.now()
        return [
            inv
            for inv in self._invitations.values()
            if inv.session_id == session_id
            and not inv.accepted
            and (inv.expires_at is None or inv.expires_at > now)
        ]
