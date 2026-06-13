"""Behavioral tests for CollaborationManager.

The existing test_collaboration.py covers the data models; this file drives
the manager's CRUD surface: sessions, participants, comments, reactions,
votes, voting results, change tracking/listeners, and persistence (save +
load + corrupted-file skip).
"""

from __future__ import annotations

import pytest

from attune.socratic.collaboration import CollaborationManager
from attune.socratic.collaboration_models import (
    ChangeType,
    CollaborativeSession,
    CommentStatus,
    Participant,
    ParticipantRole,
    VoteType,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def mgr(tmp_path):
    """A manager backed by an isolated temp storage directory."""
    return CollaborationManager(storage_path=tmp_path)


def _new_session(mgr, owner_id="owner-1", owner_name="Owner"):
    return mgr.create_session(
        base_session_id="base-1",
        name="Design review",
        owner_id=owner_id,
        owner_name=owner_name,
    )


# ---------------------------------------------------------------------------
# create / get / persistence
# ---------------------------------------------------------------------------


class TestSessionLifecycle:
    def test_create_session_adds_owner_and_persists(self, mgr, tmp_path):
        """A created session has the owner as OWNER and is written to disk."""
        session = _new_session(mgr)

        assert session.participants[0].role == ParticipantRole.OWNER
        assert (tmp_path / f"{session.session_id}.json").exists()
        assert mgr.get_session(session.session_id) is session

    def test_get_session_unknown_returns_none(self, mgr):
        assert mgr.get_session("nope") is None

    def test_default_storage_path_under_home(self, tmp_path, monkeypatch):
        """With no storage_path, the manager nests under ~/.attune/socratic."""
        monkeypatch.setattr("attune.socratic.collaboration.Path.home", lambda: tmp_path)
        manager = CollaborationManager()
        assert manager.storage_path == tmp_path / ".attune" / "socratic" / "collaboration"
        assert manager.storage_path.exists()

    def test_list_sessions_sorted_by_updated(self, mgr):
        s1 = _new_session(mgr, owner_id="a")
        s2 = _new_session(mgr, owner_id="b")
        ids = {s.session_id for s in mgr.list_sessions()}
        assert ids == {s1.session_id, s2.session_id}

    def test_get_user_sessions_filters_by_participant(self, mgr):
        session = _new_session(mgr, owner_id="owner-1")
        mgr.add_participant(session.session_id, "rev-1", "Rev")

        assert any(s.session_id == session.session_id for s in mgr.get_user_sessions("rev-1"))
        assert mgr.get_user_sessions("stranger") == []

    def test_load_sessions_on_init(self, mgr, tmp_path):
        """A second manager on the same path reloads persisted sessions."""
        session = _new_session(mgr)
        reloaded = CollaborationManager(storage_path=tmp_path)
        assert reloaded.get_session(session.session_id) is not None

    def test_load_sessions_skips_corrupted_file(self, tmp_path):
        """A malformed json file is skipped without crashing init."""
        (tmp_path / "broken.json").write_text("{ not json")
        manager = CollaborationManager(storage_path=tmp_path)
        assert manager.list_sessions() == []


# ---------------------------------------------------------------------------
# participants
# ---------------------------------------------------------------------------


class TestParticipants:
    def test_add_participant_unknown_session(self, mgr):
        assert mgr.add_participant("nope", "u", "U") is None

    def test_add_participant_new(self, mgr):
        session = _new_session(mgr)
        p = mgr.add_participant(session.session_id, "rev-1", "Rev", email="r@x.io")
        assert p is not None
        assert p.role == ParticipantRole.REVIEWER

    def test_add_participant_existing_returns_existing(self, mgr):
        session = _new_session(mgr)
        first = mgr.add_participant(session.session_id, "rev-1", "Rev")
        again = mgr.add_participant(session.session_id, "rev-1", "Rev")
        assert again is first

    def test_update_role_unknown_session(self, mgr):
        assert mgr.update_participant_role("nope", "u", ParticipantRole.EDITOR, "owner-1") is False

    def test_update_role_requires_owner(self, mgr):
        session = _new_session(mgr)
        mgr.add_participant(session.session_id, "rev-1", "Rev")
        # rev-1 (REVIEWER) cannot promote anyone
        assert (
            mgr.update_participant_role(
                session.session_id, "rev-1", ParticipantRole.EDITOR, "rev-1"
            )
            is False
        )

    def test_update_role_unknown_target(self, mgr):
        session = _new_session(mgr)
        assert (
            mgr.update_participant_role(
                session.session_id, "ghost", ParticipantRole.EDITOR, "owner-1"
            )
            is False
        )

    def test_update_role_success(self, mgr):
        session = _new_session(mgr)
        mgr.add_participant(session.session_id, "rev-1", "Rev")
        ok = mgr.update_participant_role(
            session.session_id, "rev-1", ParticipantRole.EDITOR, "owner-1"
        )
        assert ok is True
        p = next(p for p in session.participants if p.user_id == "rev-1")
        assert p.role == ParticipantRole.EDITOR


# ---------------------------------------------------------------------------
# comments + reactions
# ---------------------------------------------------------------------------


class TestComments:
    def test_add_comment_unknown_session(self, mgr):
        assert mgr.add_comment("nope", "owner-1", "hi", "req", "r1") is None

    def test_add_comment_non_participant(self, mgr):
        session = _new_session(mgr)
        assert mgr.add_comment(session.session_id, "stranger", "hi", "req", "r1") is None

    def test_add_comment_success_tracks_change(self, mgr):
        session = _new_session(mgr)
        comment = mgr.add_comment(session.session_id, "owner-1", "looks good", "req", "r1")
        assert comment is not None
        assert any(c.change_type == ChangeType.COMMENT_ADDED for c in session.changes)

    def test_resolve_comment_unknown_session(self, mgr):
        assert mgr.resolve_comment("nope", "c1", "owner-1") is False

    def test_resolve_comment_unknown_comment(self, mgr):
        session = _new_session(mgr)
        assert mgr.resolve_comment(session.session_id, "ghost", "owner-1") is False

    def test_resolve_comment_success(self, mgr):
        session = _new_session(mgr)
        comment = mgr.add_comment(session.session_id, "owner-1", "x", "req", "r1")
        ok = mgr.resolve_comment(session.session_id, comment.comment_id, "owner-1")
        assert ok is True
        assert comment.status == CommentStatus.RESOLVED

    def test_get_comments_for_target_filters(self, mgr):
        session = _new_session(mgr)
        c_open = mgr.add_comment(session.session_id, "owner-1", "a", "req", "r1")
        c_res = mgr.add_comment(session.session_id, "owner-1", "b", "req", "r1")
        mgr.resolve_comment(session.session_id, c_res.comment_id, "owner-1")
        mgr.add_comment(session.session_id, "owner-1", "other", "req", "r2")

        all_r1 = mgr.get_comments_for_target(session.session_id, "req", "r1")
        open_only = mgr.get_comments_for_target(
            session.session_id, "req", "r1", include_resolved=False
        )
        assert {c.comment_id for c in all_r1} == {c_open.comment_id, c_res.comment_id}
        assert [c.comment_id for c in open_only] == [c_open.comment_id]

    def test_get_comments_unknown_session(self, mgr):
        assert mgr.get_comments_for_target("nope", "req", "r1") == []

    def test_add_reaction_unknown_session(self, mgr):
        assert mgr.add_reaction("nope", "c1", "owner-1", "👍") is False

    def test_add_reaction_unknown_comment(self, mgr):
        session = _new_session(mgr)
        assert mgr.add_reaction(session.session_id, "ghost", "owner-1", "👍") is False

    def test_add_reaction_new_and_deduped(self, mgr):
        session = _new_session(mgr)
        comment = mgr.add_comment(session.session_id, "owner-1", "x", "req", "r1")
        assert mgr.add_reaction(session.session_id, comment.comment_id, "owner-1", "👍") is True
        # same user + emoji again does not duplicate
        assert mgr.add_reaction(session.session_id, comment.comment_id, "owner-1", "👍") is True
        assert comment.reactions["👍"] == ["owner-1"]


# ---------------------------------------------------------------------------
# votes + voting result
# ---------------------------------------------------------------------------


class TestVotes:
    def test_cast_vote_unknown_session(self, mgr):
        assert mgr.cast_vote("nope", "owner-1", "req", "r1", VoteType.APPROVE) is None

    def test_cast_vote_viewer_rejected(self, mgr):
        session = _new_session(mgr)
        mgr.add_participant(session.session_id, "viewer-1", "Viewer", role=ParticipantRole.VIEWER)
        assert mgr.cast_vote(session.session_id, "viewer-1", "req", "r1", VoteType.APPROVE) is None

    def test_cast_vote_new_tracks_change(self, mgr):
        session = _new_session(mgr)
        vote = mgr.cast_vote(session.session_id, "owner-1", "req", "r1", VoteType.APPROVE)
        assert vote is not None
        assert any(c.change_type == ChangeType.VOTE_CAST for c in session.changes)

    def test_cast_vote_updates_existing(self, mgr):
        session = _new_session(mgr)
        first = mgr.cast_vote(session.session_id, "owner-1", "req", "r1", VoteType.APPROVE)
        second = mgr.cast_vote(
            session.session_id, "owner-1", "req", "r1", VoteType.REJECT, comment="changed"
        )
        assert second.vote_id == first.vote_id
        assert second.vote_type == VoteType.REJECT
        assert len(session.votes) == 1

    def test_get_voting_result_unknown_session(self, mgr):
        assert mgr.get_voting_result("nope", "req", "r1") is None

    def test_get_voting_result_approved(self, mgr):
        session = _new_session(mgr)
        mgr.add_participant(session.session_id, "ed-1", "Ed", role=ParticipantRole.EDITOR)
        mgr.cast_vote(session.session_id, "owner-1", "req", "r1", VoteType.APPROVE)
        mgr.cast_vote(session.session_id, "ed-1", "req", "r1", VoteType.APPROVE)

        result = mgr.get_voting_result(session.session_id, "req", "r1")
        assert result.approvals == 2
        assert result.quorum_reached is True
        assert result.is_approved is True

    def test_get_voting_result_counts_all_types(self, mgr):
        session = _new_session(mgr)
        mgr.add_participant(session.session_id, "ed-1", "Ed", role=ParticipantRole.EDITOR)
        mgr.add_participant(session.session_id, "ed-2", "Ed2", role=ParticipantRole.EDITOR)
        mgr.cast_vote(session.session_id, "owner-1", "req", "r1", VoteType.APPROVE)
        mgr.cast_vote(session.session_id, "ed-1", "req", "r1", VoteType.REJECT)
        mgr.cast_vote(session.session_id, "ed-2", "req", "r1", VoteType.ABSTAIN)

        result = mgr.get_voting_result(session.session_id, "req", "r1")
        assert (result.approvals, result.rejections, result.abstentions) == (1, 1, 1)

    def test_get_voting_result_no_eligible_voters(self, mgr):
        """A session with only viewers yields a zero participation rate."""
        session = CollaborativeSession(
            session_id="viewers-only",
            base_session_id="b",
            name="n",
            participants=[
                Participant(user_id="v1", name="V1", role=ParticipantRole.VIEWER),
            ],
        )
        mgr._sessions[session.session_id] = session

        result = mgr.get_voting_result(session.session_id, "req", "r1")
        assert result.quorum_reached is False
        assert result.is_approved is False


# ---------------------------------------------------------------------------
# change tracking + listeners + history
# ---------------------------------------------------------------------------


class TestChangeTracking:
    def test_get_change_history_unknown_session(self, mgr):
        assert mgr.get_change_history("nope") == []

    def test_get_change_history_recent_first_and_limited(self, mgr):
        session = _new_session(mgr)
        for i in range(3):
            mgr.track_change(session.session_id, ChangeType.GOAL_SET, "owner-1", f"change {i}")
        history = mgr.get_change_history(session.session_id, limit=2)
        assert len(history) == 2  # limit applied
        assert history[0].created_at >= history[1].created_at  # recent first

    def test_track_change_unknown_session_is_noop(self, mgr):
        # No session -> no exception, nothing tracked.
        mgr.track_change("nope", ChangeType.GOAL_SET, "owner-1", "x")

    def test_listener_invoked_on_change(self, mgr):
        session = _new_session(mgr)
        seen = []
        mgr.add_change_listener(seen.append)
        mgr.track_change(session.session_id, ChangeType.GOAL_SET, "owner-1", "fired")
        assert any(c.description == "fired" for c in seen)

    def test_listener_exception_is_swallowed(self, mgr):
        session = _new_session(mgr)

        def boom(_change):
            raise RuntimeError("bad listener")

        good = []
        mgr.add_change_listener(boom)
        mgr.add_change_listener(good.append)
        mgr.track_change(session.session_id, ChangeType.GOAL_SET, "owner-1", "ok")
        assert len(good) == 1  # good listener still ran despite bad one

    def test_remove_change_listener(self, mgr):
        session = _new_session(mgr)
        seen = []
        mgr.add_change_listener(seen.append)
        mgr.remove_change_listener(seen.append)  # removing an equal-but-unregistered no-ops
        mgr.remove_change_listener(seen.append)

        captured = []
        mgr.add_change_listener(captured.append)
        mgr.remove_change_listener(captured.append)
        mgr.track_change(session.session_id, ChangeType.GOAL_SET, "owner-1", "x")
        assert captured == []  # listener was removed, not called
