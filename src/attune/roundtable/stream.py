"""Debate event broadcaster for the round-table (rescue).

In-process, synchronous pub/sub of typed debate-graph events. NOTE:
despite the originating plan's "WebSocket broadcaster" framing, there
is no transport here — subscribers are plain callables receiving JSON
strings. A WebSocket (or SSE) transport would subscribe its own
forwarding callback; that belongs to the GUI project, not this module.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class DebateEventBroadcaster:
    """Broadcaster for multi-agent roundtable graph events."""

    def __init__(self) -> None:
        self.subscribers: list[Callable[[str], None]] = []

    def subscribe(self, callback: Callable[[str], None]) -> None:
        """Subscribe a listener callback to the event stream."""
        self.subscribers.append(callback)

    def broadcast_node_proposed(
        self,
        thread_id: str,
        agent: str,
        node_id: str,
        parent_node: str | None,
        relation: str,
        topic: str,
        proposal: str,
    ) -> dict[str, Any]:
        """Broadcasts a new proposal node from an agent.

        Args:
            thread_id: ID of roundtable thread.
            agent: Name of agent (claude, antigravity, codex).
            node_id: Unique node identifier.
            parent_node: Parent node ID if replying/challenging.
            relation: Relationship type ('supports', 'challenges', 'refines').
            topic: High-level topic title.
            proposal: Proposal text content.

        Returns:
            Event payload dictionary.
        """
        payload = {
            "event_type": "node_proposed",
            "thread_id": thread_id,
            "agent": agent,
            "node_id": node_id,
            "parent_node": parent_node or "",
            "relation": relation,
            "topic": topic,
            "proposal": proposal,
        }

        json_str = json.dumps(payload)
        for sub in self.subscribers:
            try:
                sub(json_str)
            except Exception:  # noqa: BLE001 — one bad subscriber must not break the rest
                logger.exception("debate subscriber failed for node %s", node_id)

        return payload
