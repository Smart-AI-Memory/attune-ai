"""Round-table board: schema, Redis Functions, and the moderator client.

The board is the short-term deliberation surface ratified in
``docs/specs/agent-round-table``. Design constraints it implements:

- **Moderator owns all I/O (R1)** — members never touch Redis; this
  module is called only by the moderator (a live Claude Code session
  in Phase 1).
- **Schema-validated atomic writes (R2, AC-1)** — validation lives in
  the server-side Lua function, so a malformed message is rejected by
  Redis itself with no partial write, regardless of which client
  posts it.
- **Board keyspace only (R3)** — every key starts with
  ``attune:roundtable:``; the derived ``attune:memory:*`` keyspace is
  never written (collaboration contract, PR #1447).
- **TTL'd working state (AC-6)** — threads expire (default 7 days);
  durability comes from chair-approved promotion into tracked
  artifacts, not from Redis.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

#: Message kinds the schema admits (requirements P0; R9 adds
#: member-originated ``question``/``suggestion`` as first-class).
KINDS: tuple[str, ...] = (
    "question",
    "position",
    "synthesis",
    "ruling",
    "suggestion",
    "halt",
)

#: Every board key lives under this prefix (R3).
THREAD_KEY_PREFIX = "attune:roundtable:thread:"

#: Default thread TTL — 7 days, refreshed on each post (AC-6).
THREAD_TTL_SECONDS = 604_800

#: Name of the Redis Function library this module owns. Distinct from
#: the hydration hook's ``attune_memory`` library — FUNCTION LOAD
#: REPLACE only replaces the same-named library, so the two never
#: clobber each other.
LIBRARY_NAME = "attune_roundtable"

#: The server-side library. Validation is deliberately here, not in
#: Python: AC-1 requires Redis itself to reject a malformed message
#: atomically no matter what client sent it.
LIBRARY_SOURCE = """#!lua name=attune_roundtable

local KINDS = {
  question = true, position = true, synthesis = true,
  ruling = true, suggestion = true, halt = true,
}

local function validate(msg)
  if type(msg) ~= 'table' then
    return 'message must be a JSON object'
  end
  if type(msg.author) ~= 'string' or #msg.author == 0 then
    return 'author is required'
  end
  if type(msg.kind) ~= 'string' or not KINDS[msg.kind] then
    return 'kind is required and must be one of: ' ..
      'question|position|synthesis|ruling|suggestion|halt'
  end
  if type(msg.body) ~= 'string' or #msg.body == 0 then
    return 'body is required'
  end
  return nil
end

local function post_message(keys, args)
  local msgs_key = keys[1]
  local meta_key = msgs_key .. ':meta'
  local ok, msg = pcall(cjson.decode, args[1])
  if not ok then
    return redis.error_reply('rt_post_message: body is not valid JSON')
  end
  local err = validate(msg)
  if err then
    return redis.error_reply('rt_post_message: ' .. err)
  end
  local ttl = tonumber(args[2]) or 604800
  local t = redis.call('TIME')
  msg.ts = t[1] .. '.' .. t[2]
  msg.id = redis.call('HINCRBY', meta_key, 'seq', 1)
  redis.call('RPUSH', msgs_key, cjson.encode(msg))
  redis.call('EXPIRE', msgs_key, ttl)
  redis.call('EXPIRE', meta_key, ttl)
  return msg.id
end

local function read_thread(keys, args)
  return redis.call('LRANGE', keys[1], 0, -1)
end

local function promote(keys, args)
  local msgs_key = keys[1]
  local meta_key = msgs_key .. ':meta'
  if redis.call('EXISTS', msgs_key) == 0 then
    return redis.error_reply('rt_promote: thread does not exist')
  end
  local destination = args[1]
  if type(destination) ~= 'string' or #destination == 0 then
    return redis.error_reply('rt_promote: destination is required')
  end
  local ids_json = args[2]
  if ids_json ~= nil and #ids_json > 0 then
    local ok, ids = pcall(cjson.decode, ids_json)
    if not ok or type(ids) ~= 'table' or #ids == 0 then
      return redis.error_reply(
        'rt_promote: item ids must be a non-empty JSON array')
    end
    local seq = tonumber(redis.call('HGET', meta_key, 'seq')) or 0
    for _, id in ipairs(ids) do
      if type(id) ~= 'number' or id < 1 or id ~= math.floor(id)
          or id > seq then
        return redis.error_reply(
          'rt_promote: unknown item id ' .. tostring(id))
      end
    end
    redis.call('HSET', meta_key, 'promoted_ids', cjson.encode(ids))
  end
  local t = redis.call('TIME')
  redis.call('HSET', meta_key, 'status', 'promoted',
    'destination', destination, 'promoted_at', t[1])
  return redis.call('LRANGE', msgs_key, 0, -1)
end

redis.register_function('rt_post_message', post_message)
redis.register_function('rt_read_thread', read_thread)
redis.register_function('rt_promote', promote)
"""


@dataclass
class BoardMessage:
    """One validated board message as stored in a thread.

    ``id`` and ``ts`` are assigned server-side by ``rt_post_message``
    (monotonic per-thread sequence; Redis server clock).
    """

    author: str
    kind: str
    body: str
    id: int | None = None
    ts: str | None = None
    reply_to: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, raw: str | bytes) -> BoardMessage:
        """Parse a stored message; unknown fields are kept in ``extra``."""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        known = {k: data.pop(k, None) for k in ("author", "kind", "body", "id", "ts", "reply_to")}
        return cls(
            author=str(known["author"]),
            kind=str(known["kind"]),
            body=str(known["body"]),
            id=known["id"],
            ts=None if known["ts"] is None else str(known["ts"]),
            reply_to=known["reply_to"],
            extra=data,
        )


class Board:
    """Moderator-side client for the round-table board.

    All methods call the server-side functions; nothing here bypasses
    the schema validation they enforce.

    Args:
        client: A connected ``redis.Redis`` client. When None, one is
            created from ``REDIS_URL`` (default
            ``redis://127.0.0.1:6379/0``).
        ttl_seconds: Thread TTL refreshed on every post.
    """

    def __init__(self, client: Any = None, ttl_seconds: int = THREAD_TTL_SECONDS) -> None:
        if client is None:
            import redis  # noqa: PLC0415 — optional dependency, import at use

            url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
            client = redis.Redis.from_url(url, decode_responses=True)
        self.client = client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def thread_key(thread: str) -> str:
        """Return the messages key for a thread id (R3 keyspace)."""
        if not thread or any(c.isspace() for c in thread):
            raise ValueError(f"invalid thread id: {thread!r}")
        return THREAD_KEY_PREFIX + thread

    def ensure_functions(self) -> None:
        """Idempotently load the ``attune_roundtable`` function library."""
        self.client.function_load(LIBRARY_SOURCE, replace=True)

    def post_message(
        self,
        thread: str,
        author: str,
        kind: str,
        body: str,
        reply_to: int | None = None,
        **extra: Any,
    ) -> int:
        """Post one message; returns its server-assigned id.

        Validation is server-side: a malformed message raises
        ``redis.ResponseError`` and writes nothing (AC-1).
        """
        message: dict[str, Any] = {"author": author, "kind": kind, "body": body, **extra}
        if reply_to is not None:
            message["reply_to"] = reply_to
        reply = self.client.fcall(
            "rt_post_message",
            1,
            self.thread_key(thread),
            json.dumps(message),
            str(self.ttl_seconds),
        )
        return int(reply)

    def read_thread(self, thread: str) -> list[BoardMessage]:
        """Return all messages in a thread, oldest first."""
        raw = self.client.fcall("rt_read_thread", 1, self.thread_key(thread))
        return [BoardMessage.from_json(entry) for entry in raw or []]

    def promote(
        self,
        thread: str,
        destination: str,
        item_ids: list[int] | None = None,
    ) -> list[BoardMessage]:
        """Mark a thread promoted and return its messages for writing out.

        The artifact write itself is the moderator's job (D2 routing;
        chair approval per R4 happens before this is called). The
        board only records that promotion happened and where.

        Args:
            thread: Thread id.
            destination: Tracked artifact path the content goes to.
            item_ids: Chair-approved message ids (P2 per-item gates).
                When given, they are validated server-side against the
                thread's sequence and recorded in the thread meta as
                ``promoted_ids``; an unknown id rejects the whole call
                with no meta change. When omitted, the whole thread is
                promoted (the P1 behavior).
        """
        args: list[str] = [destination]
        if item_ids:
            args.append(json.dumps(sorted(set(item_ids))))
        raw = self.client.fcall("rt_promote", 1, self.thread_key(thread), *args)
        return [BoardMessage.from_json(entry) for entry in raw or []]
