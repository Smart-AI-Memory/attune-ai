"""Round-table board tests (agent-round-table Phase 0).

Two layers, mirroring ``test_recall_digest.py``: message/key logic
against a boundary double (runs in keyless CI, no Redis), and the
non-mocked receipts against a REAL Redis with the library loaded by
this suite itself — AC-1 (atomic rejection of malformed messages),
AC-6 (TTL set), and the post→read→promote round trip. Real-Redis
tests skip when localhost:6379 is unreachable.
"""

from __future__ import annotations

import json
import uuid

import pytest

from attune.roundtable import (
    KINDS,
    THREAD_KEY_PREFIX,
    Board,
    BoardMessage,
)


class FakeRedisClient:
    """Boundary double — records fcall/function_load invocations."""

    def __init__(self, reply=None) -> None:
        self.reply = reply
        self.calls: list[tuple] = []
        self.loaded: list[tuple] = []

    def fcall(self, name, numkeys, *args):
        self.calls.append((name, numkeys, *args))
        return self.reply

    def function_load(self, code, replace=False):
        self.loaded.append((code, replace))
        return "attune_roundtable"


def _real_board_or_skip() -> Board:
    """Return a Board on a real Redis with the library loaded, or skip."""
    redis = pytest.importorskip("redis")
    client = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    try:
        client.ping()
    except redis.RedisError:
        pytest.skip("no reachable Redis on localhost:6379")
    board = Board(client=client)
    board.ensure_functions()
    return board


def _fresh_thread() -> str:
    return "test-" + uuid.uuid4().hex[:12]


class TestSchemaAndKeys:
    def test_kinds_cover_spec_enum(self) -> None:
        assert set(KINDS) == {
            "question",
            "position",
            "synthesis",
            "ruling",
            "suggestion",
            "halt",
        }

    def test_thread_key_uses_board_keyspace(self) -> None:
        assert Board.thread_key("t1") == THREAD_KEY_PREFIX + "t1"
        assert THREAD_KEY_PREFIX.startswith("attune:roundtable:")

    @pytest.mark.parametrize("bad", ["", "has space", "tab\tid"])
    def test_thread_key_rejects_invalid_ids(self, bad: str) -> None:
        with pytest.raises(ValueError, match="invalid thread id"):
            Board.thread_key(bad)

    def test_message_from_json_keeps_unknown_fields_in_extra(self) -> None:
        raw = json.dumps(
            {
                "author": "codex@s1",
                "kind": "position",
                "body": "b",
                "id": 3,
                "ts": "1.2",
                "cost_usd": 0.01,
            }
        )
        msg = BoardMessage.from_json(raw)
        assert (msg.author, msg.kind, msg.id) == ("codex@s1", "position", 3)
        assert msg.extra == {"cost_usd": 0.01}


class TestBoardWithFakeClient:
    """Client argument construction — runs everywhere, incl. keyless CI."""

    def test_post_message_sends_schema_fields_and_ttl(self) -> None:
        fake = FakeRedisClient(reply=1)
        board = Board(client=fake, ttl_seconds=60)
        msg_id = board.post_message("t1", author="claude@s1", kind="question", body="Q?")
        assert msg_id == 1
        name, numkeys, key, payload, ttl = fake.calls[0]
        assert (name, numkeys, key, ttl) == ("rt_post_message", 1, THREAD_KEY_PREFIX + "t1", "60")
        assert json.loads(payload) == {"author": "claude@s1", "kind": "question", "body": "Q?"}

    def test_post_message_carries_reply_to_and_extra(self) -> None:
        fake = FakeRedisClient(reply=2)
        Board(client=fake).post_message(
            "t1", author="agy@s2", kind="position", body="B", reply_to=1, round=2
        )
        payload = json.loads(fake.calls[0][3])
        assert payload["reply_to"] == 1
        assert payload["round"] == 2

    def test_read_thread_parses_messages(self) -> None:
        entries = [json.dumps({"author": "a", "kind": "position", "body": "b", "id": 1})]
        board = Board(client=FakeRedisClient(reply=entries))
        msgs = board.read_thread("t1")
        assert len(msgs) == 1 and msgs[0].id == 1

    def test_ensure_functions_loads_with_replace(self) -> None:
        fake = FakeRedisClient()
        Board(client=fake).ensure_functions()
        code, replace = fake.loaded[0]
        assert replace is True
        assert code.startswith("#!lua name=attune_roundtable")


class TestAgainstRealRedis:
    """Non-mocked receipts — the library is loaded by this suite."""

    def test_post_read_round_trip(self) -> None:
        board = _real_board_or_skip()
        thread = _fresh_thread()
        id1 = board.post_message(thread, author="claude@s1", kind="question", body="Q?")
        id2 = board.post_message(
            thread, author="codex@s1", kind="position", body="A.", reply_to=id1
        )
        msgs = board.read_thread(thread)
        assert [m.id for m in msgs] == [id1, id2]
        assert msgs[0].ts is not None
        assert msgs[1].reply_to == id1

    def test_ac1_malformed_message_rejected_atomically(self) -> None:
        """AC-1: server-side rejection, no partial write."""
        redis = pytest.importorskip("redis")
        board = _real_board_or_skip()
        thread = _fresh_thread()
        key = Board.thread_key(thread)

        for bad_args in (
            ("{not json", "60"),
            (json.dumps({"kind": "position", "body": "no author"}), "60"),
            (json.dumps({"author": "a", "body": "no kind"}), "60"),
            (json.dumps({"author": "a", "kind": "not-a-kind", "body": "b"}), "60"),
            (json.dumps({"author": "a", "kind": "position"}), "60"),
        ):
            with pytest.raises(redis.ResponseError, match="rt_post_message"):
                board.client.fcall("rt_post_message", 1, key, *bad_args)

        assert board.client.exists(key) == 0, "malformed post left a partial write"
        assert board.client.exists(key + ":meta") == 0

    def test_ac6_thread_ttl_is_set_and_refreshed(self) -> None:
        board = _real_board_or_skip()
        board.ttl_seconds = 120
        thread = _fresh_thread()
        board.post_message(thread, author="a@s", kind="question", body="q")
        ttl = board.client.ttl(Board.thread_key(thread))
        assert 0 < ttl <= 120

    def test_promote_marks_meta_and_returns_messages(self) -> None:
        board = _real_board_or_skip()
        thread = _fresh_thread()
        board.post_message(thread, author="a@s", kind="suggestion", body="do X")
        msgs = board.promote(thread, "docs/reports/roundtable/test.md")
        assert len(msgs) == 1 and msgs[0].body == "do X"
        meta = board.client.hgetall(Board.thread_key(thread) + ":meta")
        assert meta["status"] == "promoted"
        assert meta["destination"] == "docs/reports/roundtable/test.md"

    def test_promote_missing_thread_errors(self) -> None:
        redis = pytest.importorskip("redis")
        board = _real_board_or_skip()
        with pytest.raises(redis.ResponseError, match="does not exist"):
            board.promote(_fresh_thread(), "anywhere.md")

    def test_promote_requires_destination(self) -> None:
        redis = pytest.importorskip("redis")
        board = _real_board_or_skip()
        thread = _fresh_thread()
        board.post_message(thread, author="a@s", kind="suggestion", body="x")
        with pytest.raises(redis.ResponseError, match="destination"):
            board.client.fcall("rt_promote", 1, Board.thread_key(thread), "")

    def test_promote_records_chair_approved_item_ids(self) -> None:
        """P2 per-item gates: approved ids land in meta, deduped and sorted."""
        board = _real_board_or_skip()
        thread = _fresh_thread()
        for body in ("q", "pos-a", "pos-b"):
            board.post_message(thread, author="a@s", kind="suggestion", body=body)
        board.promote(thread, "docs/reports/roundtable/test.md", item_ids=[3, 1, 3])
        meta = board.client.hgetall(Board.thread_key(thread) + ":meta")
        assert meta["status"] == "promoted"
        assert json.loads(meta["promoted_ids"]) == [1, 3]

    def test_promote_unknown_item_id_rejected_with_no_meta_change(self) -> None:
        """An out-of-range id rejects the whole call atomically (AC-3 spirit)."""
        redis = pytest.importorskip("redis")
        board = _real_board_or_skip()
        thread = _fresh_thread()
        board.post_message(thread, author="a@s", kind="suggestion", body="only one")
        with pytest.raises(redis.ResponseError, match="unknown item id 2"):
            board.promote(thread, "docs/reports/roundtable/test.md", item_ids=[2])
        meta = board.client.hgetall(Board.thread_key(thread) + ":meta")
        assert "status" not in meta and "promoted_ids" not in meta

    def test_promote_malformed_ids_payload_rejected(self) -> None:
        redis = pytest.importorskip("redis")
        board = _real_board_or_skip()
        thread = _fresh_thread()
        board.post_message(thread, author="a@s", kind="suggestion", body="x")
        with pytest.raises(redis.ResponseError, match="JSON array"):
            board.client.fcall("rt_promote", 1, Board.thread_key(thread), "dest.md", "not-json")

    def test_promote_without_ids_keeps_p1_whole_thread_behavior(self) -> None:
        board = _real_board_or_skip()
        thread = _fresh_thread()
        board.post_message(thread, author="a@s", kind="suggestion", body="x")
        board.promote(thread, "dest.md")
        meta = board.client.hgetall(Board.thread_key(thread) + ":meta")
        assert meta["status"] == "promoted" and "promoted_ids" not in meta
