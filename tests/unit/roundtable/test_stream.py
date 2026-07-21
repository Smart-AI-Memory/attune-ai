"""Unit tests for Visual Debate Theater event broadcaster."""

from attune.roundtable.stream import DebateEventBroadcaster


class TestDebateEventBroadcaster:
    """Tests for DebateEventBroadcaster."""

    def test_broadcast_node_proposed(self) -> None:
        broadcaster = DebateEventBroadcaster()
        received = []

        broadcaster.subscribe(lambda msg: received.append(msg))

        payload = broadcaster.broadcast_node_proposed(
            thread_id="rt-100",
            agent="antigravity",
            node_id="node-1",
            parent_node=None,
            relation="supports",
            topic="AST Skeletonization",
            proposal="Compress method bodies using stdlib ast",
        )

        assert payload["thread_id"] == "rt-100"
        assert payload["agent"] == "antigravity"
        assert len(received) == 1
        assert "node-1" in received[0]
