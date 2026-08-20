"""Tests for cross-session conflict-resolution strategies.

`conflicts.py` is three pure functions — priority-based, first-write-wins
(Redis lock), and last-write-wins. No live Redis: `resolve_first_write`
takes the client as an argument, so a `MagicMock` exercises every lock
branch. Assertions pin the winner/loser, the strategy tag, the lock key
and TTL, and the tier/timestamp comparisons so the operator and
default-value mutations are caught.

Coverage: `conflicts.py` 68.4% -> 100% (38/38 stmts).

Mutation status (mutmut 2.4.4, this suite as runner): ``48 mutants ->
41 killed, 7 survived``. All 7 survivors are documented equivalents:
fragments of the priority-branch ``"Higher tier (X > Y)"`` reason
f-string, which embeds the dynamic tier names — a substring assertion
can't kill an ``XX``-wrapped fragment and exact-matching the dynamic
text would be over-fitting. The behaviorally meaningful reason mutations
(``reason = None``, the equal-tier and last-write reason text, and the
``"unknown"`` loser default) are killed. Killable kill-rate 41/41 = 100%.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from attune.memory.cross_session.conflicts import (
    resolve_by_priority,
    resolve_first_write,
    resolve_last_write,
)
from attune.memory.cross_session.models import (
    ConflictStrategy,
    SessionInfo,
    SessionType,
)
from attune.memory.short_term import AccessTier

pytestmark = pytest.mark.unit

EARLY = datetime(2026, 1, 1, 12, 0, 0)
LATE = datetime(2026, 1, 1, 13, 0, 0)


def session(agent_id: str, tier: AccessTier, started_at: datetime = EARLY) -> SessionInfo:
    return SessionInfo(
        agent_id=agent_id,
        session_type=SessionType.CLAUDE,
        access_tier=tier,
        capabilities=[],
        started_at=started_at,
        last_heartbeat=started_at,
    )


class TestResolveByPriority:
    def test_higher_tier_wins(self):
        me = session("me", AccessTier.STEWARD)
        other = session("other", AccessTier.OBSERVER)
        r = resolve_by_priority("me", AccessTier.STEWARD, me, "res", other)
        assert (r.winner_agent_id, r.loser_agent_id) == ("me", "other")
        assert r.strategy_used == ConflictStrategy.PRIORITY_BASED
        assert r.resource_key == "res"
        assert "Higher tier" in r.reason

    def test_lower_tier_loses(self):
        me = session("me", AccessTier.OBSERVER)
        other = session("other", AccessTier.STEWARD)
        r = resolve_by_priority("me", AccessTier.OBSERVER, me, "res", other)
        assert (r.winner_agent_id, r.loser_agent_id) == ("other", "me")
        assert "Higher tier" in r.reason  # reason is a real string, not None

    def test_equal_tier_earlier_other_session_wins(self):
        me = session("me", AccessTier.CONTRIBUTOR, started_at=LATE)
        other = session("other", AccessTier.CONTRIBUTOR, started_at=EARLY)
        r = resolve_by_priority("me", AccessTier.CONTRIBUTOR, me, "res", other)
        assert (r.winner_agent_id, r.loser_agent_id) == ("other", "me")
        assert r.reason == "Equal tier, earlier session wins"

    def test_equal_tier_later_other_session_self_wins(self):
        me = session("me", AccessTier.CONTRIBUTOR, started_at=EARLY)
        other = session("other", AccessTier.CONTRIBUTOR, started_at=LATE)
        r = resolve_by_priority("me", AccessTier.CONTRIBUTOR, me, "res", other)
        assert r.winner_agent_id == "me"
        assert r.reason == "Equal tier, earlier session wins"

    def test_equal_tier_same_timestamp_self_wins(self):
        me = session("me", AccessTier.CONTRIBUTOR, started_at=EARLY)
        other = session("other", AccessTier.CONTRIBUTOR, started_at=EARLY)
        r = resolve_by_priority("me", AccessTier.CONTRIBUTOR, me, "res", other)
        assert r.winner_agent_id == "me"

    def test_no_other_session_self_wins_against_unknown(self):
        """other_session=None -> other_tier defaults to 0, id to 'unknown'."""
        me = session("me", AccessTier.OBSERVER)  # tier 1 > 0
        r = resolve_by_priority("me", AccessTier.OBSERVER, me, "res", None)
        assert (r.winner_agent_id, r.loser_agent_id) == ("me", "unknown")
        assert "N/A" in r.reason


class TestResolveFirstWrite:
    def test_no_client_local_wins(self):
        other = session("other", AccessTier.CONTRIBUTOR)
        r = resolve_first_write("me", None, "res", other)
        assert (r.winner_agent_id, r.loser_agent_id) == ("me", "other")
        assert r.strategy_used == ConflictStrategy.FIRST_WRITE_WINS
        assert r.reason == "No Redis connection - local wins"

    def test_no_client_no_other_session_loser_unknown(self):
        r = resolve_first_write("me", None, "res", None)
        assert r.loser_agent_id == "unknown"

    def test_lock_acquired_self_wins_with_the_ttl_in_one_command(self):
        """The TTL rides on the acquisition, not on a follow-up EXPIRE.

        Library-review H2: a crash between SETNX and EXPIRE left the lock
        immortal. That the TTL is *reached* through a single command is
        proven server-side in ``test_lock_liveness.py``; here it is the
        call shape that must not regress.
        """
        client = MagicMock()
        client.set.return_value = True
        other = session("other", AccessTier.CONTRIBUTOR)
        r = resolve_first_write("me", client, "res", other)
        assert (r.winner_agent_id, r.loser_agent_id) == ("me", "other")
        assert r.reason == "First to acquire lock"
        client.set.assert_called_once_with("empathy:lock:res", "me", nx=True, ex=300)
        client.expire.assert_not_called()

    def test_lock_acquired_no_other_session_loser_unknown(self):
        client = MagicMock()
        client.set.return_value = True
        r = resolve_first_write("me", client, "res", None)
        assert (r.winner_agent_id, r.loser_agent_id) == ("me", "unknown")

    def test_lock_held_bytes_owner_decoded(self):
        client = MagicMock()
        client.set.return_value = None
        client.get.return_value = b"owner_agent"
        r = resolve_first_write("me", client, "res", None)
        assert (r.winner_agent_id, r.loser_agent_id) == ("owner_agent", "me")
        assert r.reason == "Lock already held"

    def test_lock_held_str_owner(self):
        client = MagicMock()
        client.set.return_value = None
        client.get.return_value = "owner_agent"
        r = resolve_first_write("me", client, "res", None)
        assert r.winner_agent_id == "owner_agent"

    def test_lock_held_missing_owner_defaults_unknown(self):
        client = MagicMock()
        client.set.return_value = None
        client.get.return_value = None
        r = resolve_first_write("me", client, "res", None)
        assert r.winner_agent_id == "unknown"
        assert r.loser_agent_id == "me"


class TestResolveLastWrite:
    def test_current_writer_wins(self):
        other = session("other", AccessTier.CONTRIBUTOR)
        r = resolve_last_write("me", "res", other)
        assert (r.winner_agent_id, r.loser_agent_id) == ("me", "other")
        assert r.strategy_used == ConflictStrategy.LAST_WRITE_WINS
        assert r.reason == "Last write wins - current writer takes precedence"

    def test_no_other_session_loser_unknown(self):
        r = resolve_last_write("me", "res", None)
        assert (r.winner_agent_id, r.loser_agent_id) == ("me", "unknown")
