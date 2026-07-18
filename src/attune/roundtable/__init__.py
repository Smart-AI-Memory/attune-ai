"""Agent round table — moderated multi-LLM deliberation substrate.

Phase 0 of ``docs/specs/agent-round-table``: the board keyspace
(``attune:roundtable:*``), the message schema, and the server-side
Redis Functions (``rt_post_message`` / ``rt_read_thread`` /
``rt_promote``) that make every board write atomic and
schema-validated.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from attune.roundtable.board import (
    KINDS,
    THREAD_KEY_PREFIX,
    THREAD_TTL_SECONDS,
    Board,
    BoardMessage,
)

__all__ = [
    "KINDS",
    "THREAD_KEY_PREFIX",
    "THREAD_TTL_SECONDS",
    "Board",
    "BoardMessage",
]
