"""Tests for the Socratic collaboration module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""


class TestParticipantRole:
    """Tests for ParticipantRole enum."""

    def test_all_roles_exist(self):
        """Test all expected roles exist."""
        from attune.socratic.collaboration import ParticipantRole

        assert hasattr(ParticipantRole, "OWNER")
        assert hasattr(ParticipantRole, "EDITOR")
        assert hasattr(ParticipantRole, "REVIEWER")
        assert hasattr(ParticipantRole, "VIEWER")

    def test_role_values(self):
        """Test role values."""
        from attune.socratic.collaboration import ParticipantRole

        assert ParticipantRole.OWNER.value == "owner"
        assert ParticipantRole.EDITOR.value == "editor"


class TestVoteType:
    """Tests for VoteType enum."""

    def test_all_vote_types_exist(self):
        """Test all expected vote types exist."""
        from attune.socratic.collaboration import VoteType

        assert hasattr(VoteType, "APPROVE")
        assert hasattr(VoteType, "REJECT")
        assert hasattr(VoteType, "ABSTAIN")


class TestChangeType:
    """Tests for ChangeType enum."""

    def test_all_change_types_exist(self):
        """Test all expected change types exist."""
        from attune.socratic.collaboration import ChangeType

        # Test actual enum values
        assert hasattr(ChangeType, "GOAL_SET")
        assert hasattr(ChangeType, "ANSWER_SUBMITTED")
        assert hasattr(ChangeType, "REQUIREMENT_ADDED")
        assert hasattr(ChangeType, "REQUIREMENT_REMOVED")
        assert hasattr(ChangeType, "AGENT_ADDED")
        assert hasattr(ChangeType, "AGENT_REMOVED")
        assert hasattr(ChangeType, "WORKFLOW_MODIFIED")
        assert hasattr(ChangeType, "COMMENT_ADDED")
        assert hasattr(ChangeType, "VOTE_CAST")

    def test_change_type_values(self):
        """Test change type values."""
        from attune.socratic.collaboration import ChangeType

        assert ChangeType.AGENT_ADDED.value == "agent_added"
        assert ChangeType.AGENT_REMOVED.value == "agent_removed"


class TestParticipant:
    """Tests for Participant dataclass."""

    def test_create_participant(self):
        """Test creating a participant."""
        from attune.socratic.collaboration import Participant, ParticipantRole

        participant = Participant(
            user_id="user-001",
            name="Alice",
            email="alice@example.com",
            role=ParticipantRole.EDITOR,
        )

        assert participant.user_id == "user-001"
        assert participant.name == "Alice"
        assert participant.role == ParticipantRole.EDITOR

    def test_participant_default_role(self):
        """Test participant default role is viewer."""
        from attune.socratic.collaboration import Participant, ParticipantRole

        participant = Participant(
            user_id="user-002",
            name="Bob",
        )

        assert participant.role == ParticipantRole.VIEWER

    def test_participant_serialization(self):
        """Test participant serialization."""
        from attune.socratic.collaboration import Participant, ParticipantRole

        participant = Participant(
            user_id="user-001",
            name="Alice",
            role=ParticipantRole.EDITOR,
        )

        data = participant.to_dict()

        assert data["user_id"] == "user-001"
        assert data["name"] == "Alice"
        assert data["role"] == "editor"

    def test_participant_deserialization(self):
        """Test participant deserialization."""
        from attune.socratic.collaboration import Participant

        data = {
            "user_id": "user-001",
            "name": "Alice",
            "email": "alice@example.com",
            "role": "editor",
            "joined_at": "2026-01-20T12:00:00",
            "last_active": "2026-01-20T12:00:00",
            "is_online": True,
        }

        participant = Participant.from_dict(data)

        assert participant.user_id == "user-001"
        assert participant.name == "Alice"


class TestChange:
    """Tests for Change dataclass."""

    def test_create_change(self):
        """Test creating a change."""
        from attune.socratic.collaboration import Change, ChangeType

        change = Change(
            change_id="change-001",
            change_type=ChangeType.AGENT_ADDED,
            author_id="user-001",
            description="Added security scanner agent",
            after_value={"agent_id": "agent-new", "name": "Security Scanner"},
        )

        assert change.change_type == ChangeType.AGENT_ADDED
        assert change.after_value["name"] == "Security Scanner"

    def test_change_with_before_after(self):
        """Test change with before and after values."""
        from attune.socratic.collaboration import Change, ChangeType

        change = Change(
            change_id="change-002",
            change_type=ChangeType.WORKFLOW_MODIFIED,
            author_id="user-001",
            description="Updated workflow",
            before_value={"name": "old"},
            after_value={"name": "new"},
        )

        assert change.before_value == {"name": "old"}
        assert change.after_value == {"name": "new"}

    def test_change_serialization(self):
        """Test change serialization."""
        from attune.socratic.collaboration import Change, ChangeType

        change = Change(
            change_id="change-001",
            change_type=ChangeType.AGENT_ADDED,
            author_id="user-001",
            description="Added agent",
        )

        data = change.to_dict()

        assert data["change_id"] == "change-001"
        assert data["change_type"] == "agent_added"
        assert data["author_id"] == "user-001"


class TestVotingResult:
    """Tests for VotingResult dataclass."""

    def test_create_voting_result(self):
        """Test creating a voting result."""
        from attune.socratic.collaboration import VotingResult

        result = VotingResult(
            target_id="change-001",
            total_votes=8,
            approvals=5,
            rejections=1,
            abstentions=2,
            is_approved=True,
            quorum_reached=True,
        )

        assert result.is_approved is True
        assert result.quorum_reached is True
        assert result.approvals == 5

    def test_voting_result_approval_rate(self):
        """Test voting result approval rate calculation."""
        from attune.socratic.collaboration import VotingResult

        result = VotingResult(
            target_id="change-001",
            total_votes=10,
            approvals=8,
            rejections=2,
            abstentions=0,
            is_approved=True,
            quorum_reached=True,
        )

        assert result.approval_rate == 0.8


class TestCollaborativeSession:
    """Tests for CollaborativeSession dataclass."""

    def test_create_session(self):
        """Test creating a collaborative session."""
        from attune.socratic.collaboration import CollaborativeSession

        session = CollaborativeSession(
            session_id="collab-001",
            base_session_id="base-session-001",
            name="Test Collaboration",
        )

        assert session.session_id == "collab-001"
        assert session.base_session_id == "base-session-001"
        assert len(session.participants) == 0

    def test_session_serialization(self):
        """Test session serialization."""
        from attune.socratic.collaboration import CollaborativeSession

        session = CollaborativeSession(
            session_id="collab-001",
            base_session_id="base-session-001",
            name="Test",
            description="A test session",
        )

        data = session.to_dict()

        assert data["session_id"] == "collab-001"
        assert data["base_session_id"] == "base-session-001"
        assert data["name"] == "Test"

    def test_session_with_participants(self):
        """Test session with participants."""
        from attune.socratic.collaboration import (
            CollaborativeSession,
            Participant,
            ParticipantRole,
        )

        session = CollaborativeSession(
            session_id="collab-001",
            base_session_id="base-001",
            name="Test",
            participants=[
                Participant(
                    user_id="user-001",
                    name="Alice",
                    role=ParticipantRole.OWNER,
                ),
            ],
        )

        assert len(session.participants) == 1
        assert session.participants[0].name == "Alice"


class TestCollaborationManager:
    """Tests for CollaborationManager class."""

    def test_create_manager(self, temp_dir):
        """Test creating a collaboration manager."""
        from attune.socratic.collaboration import CollaborationManager

        manager = CollaborationManager(storage_path=temp_dir / "collaboration")

        assert manager is not None
        assert manager.storage_path.exists()

    def test_create_session(self, temp_dir):
        """Test creating a collaborative session via manager."""
        from attune.socratic.collaboration import CollaborationManager

        manager = CollaborationManager(storage_path=temp_dir / "collaboration")

        session = manager.create_session(
            base_session_id="base-001",
            name="Test Session",
            owner_id="user-001",
            owner_name="Alice",
        )

        assert session is not None
        assert session.name == "Test Session"
        assert len(session.participants) == 1  # Owner auto-added

    def test_get_session(self, temp_dir):
        """Test getting a session."""
        from attune.socratic.collaboration import CollaborationManager

        manager = CollaborationManager(storage_path=temp_dir / "collaboration")

        created = manager.create_session(
            base_session_id="base-001",
            name="Test Session",
            owner_id="user-001",
            owner_name="Alice",
        )

        retrieved = manager.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id


class TestSyncAdapter:
    """Tests for SyncAdapter class."""

    def test_create_sync_adapter(self):
        """Test creating a sync adapter."""
        from attune.socratic.collaboration import SyncAdapter

        adapter = SyncAdapter(session_id="session-001")

        assert adapter is not None
        assert adapter.session_id == "session-001"

    def test_register_event_handler(self):
        """Test registering an event handler."""
        from attune.socratic.collaboration import SyncAdapter

        adapter = SyncAdapter(session_id="session-001")

        events_received = []
        adapter.on_event(lambda e: events_received.append(e))

        assert len(adapter._event_handlers) == 1


class TestInvitationManager:
    """Tests for InvitationManager class."""

    def test_create_manager(self, temp_dir):
        """Test creating an invitation manager."""
        from attune.socratic.collaboration import CollaborationManager, InvitationManager

        collab_manager = CollaborationManager(storage_path=temp_dir / "collaboration")
        invitation_manager = InvitationManager(collab_manager)

        assert invitation_manager is not None
        assert invitation_manager.collab is collab_manager


class TestCollaborationModelsSerialization:
    """Roundtrip serialization for collaboration_models data classes."""

    def test_comment_roundtrip(self):
        from attune.socratic.collaboration_models import Comment, CommentStatus

        c = Comment(
            comment_id="c1",
            author_id="u1",
            content="hello",
            target_type="answer",
            target_id="t1",
            status=CommentStatus.OPEN,
            parent_id=None,
            reactions={"thumbs": ["u2"]},
        )
        d = c.to_dict()
        c2 = Comment.from_dict(d)
        assert c2.comment_id == "c1"
        assert c2.status == CommentStatus.OPEN
        assert c2.reactions == {"thumbs": ["u2"]}

    def test_vote_roundtrip(self):
        from attune.socratic.collaboration_models import Vote, VoteType

        v = Vote(
            vote_id="v1",
            voter_id="u1",
            target_type="requirement",
            target_id="t1",
            vote_type=VoteType.APPROVE,
            comment="lgtm",
        )
        d = v.to_dict()
        v2 = Vote.from_dict(d)
        assert v2.vote_id == "v1"
        assert v2.vote_type == VoteType.APPROVE
        assert v2.comment == "lgtm"

    def test_change_roundtrip(self):
        from attune.socratic.collaboration_models import Change, ChangeType

        ch = Change(
            change_id="ch1",
            change_type=ChangeType.GOAL_SET,
            author_id="u1",
            description="added field",
            before_value=None,
            after_value={"x": 1},
        )
        d = ch.to_dict()
        ch2 = Change.from_dict(d)
        assert ch2.change_id == "ch1"
        assert ch2.change_type == ChangeType.GOAL_SET
        assert ch2.after_value == {"x": 1}

    def test_collaborative_session_roundtrip(self):
        from attune.socratic.collaboration_models import (
            CollaborativeSession,
            Comment,
            CommentStatus,
        )

        cs = CollaborativeSession(
            session_id="cs1",
            base_session_id="bs1",
            name="Review",
            description="rev",
            comments=[
                Comment(
                    comment_id="c1",
                    author_id="u1",
                    content="hi",
                    target_type="answer",
                    target_id="t1",
                    status=CommentStatus.OPEN,
                ),
            ],
        )
        d = cs.to_dict()
        cs2 = CollaborativeSession.from_dict(d)
        assert cs2.session_id == "cs1"
        assert cs2.name == "Review"
        assert len(cs2.comments) == 1


class TestVotingResultApprovalRate:
    def test_approval_rate_excludes_abstentions(self):
        from attune.socratic.collaboration_models import VotingResult

        vr = VotingResult(
            target_id="t",
            total_votes=10,
            approvals=6,
            rejections=2,
            abstentions=2,
            is_approved=True,
            quorum_reached=True,
        )
        assert vr.approval_rate == 0.75

    def test_approval_rate_zero_active_returns_zero(self):
        """All abstentions → approval_rate is 0.0 (line 305)."""
        from attune.socratic.collaboration_models import VotingResult

        vr = VotingResult(
            target_id="t",
            total_votes=3,
            approvals=0,
            rejections=0,
            abstentions=3,
            is_approved=False,
            quorum_reached=False,
        )
        assert vr.approval_rate == 0.0
