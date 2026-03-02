"""Real-Time Event Streaming Demo (Pattern 4).

This script demonstrates Redis Streams event streaming for:
- Real-time heartbeat monitoring
- Live coordination signal tracking
- Event consumption and processing

Requires Redis running locally.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
import time
from datetime import datetime

from attune.telemetry import CoordinationSignals, HeartbeatCoordinator
from attune.telemetry.event_streaming import EventStreamer


def demo_heartbeat_streaming():
    """Demo: Heartbeat events published to Redis Streams."""
    print("=" * 70)
    print("DEMO 1: HEARTBEAT EVENT STREAMING")
    print("=" * 70)
    print()

    # Initialize coordinator with streaming enabled
    coordinator = HeartbeatCoordinator(enable_streaming=True)
    streamer = EventStreamer()

    print("📡 Starting agent with event streaming enabled...")
    coordinator.start_heartbeat(
        agent_id="demo-agent-001",
        metadata={"workflow": "event-demo", "run_id": "xyz123"},
    )

    print("🔄 Publishing heartbeat updates...")
    for i in range(3):
        progress = (i + 1) / 3
        coordinator.beat(
            status="running", progress=progress, current_task=f"Processing step {i+1}/3"
        )
        time.sleep(0.5)

    print("✅ Agent completed\n")
    coordinator.stop_heartbeat(final_status="completed")

    # Retrieve recent heartbeat events
    print("📊 Recent heartbeat events from stream:")
    events = streamer.get_recent_events(event_type="agent_heartbeat", count=5)

    for event in events:
        data = event.data
        timestamp = event.timestamp.strftime("%H:%M:%S")
        print(
            f"  [{timestamp}] {data.get('agent_id')}: {data.get('status')} ({data.get('progress', 0)*100:.0f}%)"
        )

    print()


def demo_coordination_streaming():
    """Demo: Coordination signals published to Redis Streams."""
    print("=" * 70)
    print("DEMO 2: COORDINATION SIGNAL STREAMING")
    print("=" * 70)
    print()

    # Initialize coordination with streaming enabled
    coordinator_a = CoordinationSignals(agent_id="agent-a", enable_streaming=True)
    coordinator_b = CoordinationSignals(agent_id="agent-b", enable_streaming=True)
    streamer = EventStreamer()

    print("📡 Agent A sending signals to Agent B...")

    # Send multiple signals
    coordinator_a.signal(
        signal_type="task_start", target_agent="agent-b", payload={"task_id": "task-1"}
    )
    time.sleep(0.3)

    coordinator_a.signal(
        signal_type="progress_update",
        target_agent="agent-b",
        payload={"task_id": "task-1", "progress": 0.5},
    )
    time.sleep(0.3)

    coordinator_a.signal(
        signal_type="task_complete",
        target_agent="agent-b",
        payload={"task_id": "task-1", "result": "success"},
    )

    print("📊 Recent coordination signal events from stream:")
    events = streamer.get_recent_events(event_type="coordination_signal", count=10)

    for event in events:
        data = event.data
        timestamp = event.timestamp.strftime("%H:%M:%S")
        signal_type = data.get("signal_type", "unknown")
        source = data.get("source_agent", "unknown")
        target = data.get("target_agent", "unknown")
        print(f"  [{timestamp}] {source} → {target}: {signal_type}")

    print()


def demo_broadcast_streaming():
    """Demo: Broadcast signals via event streaming."""
    print("=" * 70)
    print("DEMO 3: BROADCAST EVENT STREAMING")
    print("=" * 70)
    print()

    orchestrator = CoordinationSignals(agent_id="orchestrator", enable_streaming=True)
    streamer = EventStreamer()

    print("📡 Orchestrator broadcasting to all agents...")

    # Broadcast start signal
    orchestrator.broadcast(
        signal_type="workflow_start",
        payload={"workflow_id": "demo-workflow", "timestamp": datetime.now().isoformat()},
    )
    time.sleep(0.5)

    # Broadcast checkpoint
    orchestrator.broadcast(
        signal_type="checkpoint",
        payload={"checkpoint_id": "checkpoint-1", "message": "All agents sync here"},
    )
    time.sleep(0.5)

    # Broadcast completion
    orchestrator.broadcast(
        signal_type="workflow_complete",
        payload={"workflow_id": "demo-workflow", "status": "success"},
    )

    print("📊 Recent broadcast events from stream:")
    events = streamer.get_recent_events(event_type="coordination_signal", count=10)

    # Filter for broadcasts (target_agent is None)
    broadcasts = [e for e in events if e.data.get("target_agent") is None]

    for event in broadcasts:
        data = event.data
        timestamp = event.timestamp.strftime("%H:%M:%S")
        signal_type = data.get("signal_type", "unknown")
        source = data.get("source_agent", "unknown")
        print(f"  [{timestamp}] {source} → [ALL]: {signal_type}")

    print()


def demo_live_consumption():
    """Demo: Live event consumption (iterator pattern)."""
    print("=" * 70)
    print("DEMO 4: LIVE EVENT CONSUMPTION")
    print("=" * 70)
    print()

    print("⚠️  This demo requires Redis Streams and blocks for real-time consumption.")
    print("    Press Ctrl+C to stop.\n")

    streamer = EventStreamer()

    # Start a background task that publishes events
    async def publish_events():
        """Publish test events periodically."""
        coordinator = HeartbeatCoordinator(enable_streaming=True)
        coordinator.start_heartbeat(agent_id="live-demo-agent", metadata={"demo": True})

        for i in range(5):
            await asyncio.sleep(2)
            coordinator.beat(
                status="running", progress=(i + 1) / 5, current_task=f"Live update {i+1}"
            )

        coordinator.stop_heartbeat(final_status="completed")

    # Consume events in real-time
    print("📡 Starting live event consumer...")
    print("    (Will consume events for 12 seconds)\n")

    try:
        # Start publisher in background
        asyncio.create_task(publish_events())

        # Consume events (blocking iterator)
        event_count = 0
        for event in streamer.consume_events(
            event_types=["agent_heartbeat"], block_ms=12000, count=10
        ):
            event_count += 1
            timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
            data = event.data
            agent_id = data.get("agent_id", "unknown")
            status = data.get("status", "unknown")
            progress = data.get("progress", 0.0)

            print(f"  [{timestamp}] {agent_id}: {status} ({progress*100:.0f}%)")

            # Stop after consuming 5 events
            if event_count >= 5:
                break

    except KeyboardInterrupt:
        print("\n⚠️  Event consumption interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during event consumption: {e}")

    print()


def demo_stream_management():
    """Demo: Stream management operations."""
    print("=" * 70)
    print("DEMO 5: STREAM MANAGEMENT")
    print("=" * 70)
    print()

    streamer = EventStreamer()

    # Publish some test events
    print("📡 Publishing test events...")
    for i in range(15):
        streamer.publish_event(
            event_type="test_event", data={"index": i, "message": f"Test event {i}"}
        )

    # Get stream info
    print("📊 Stream information:")
    info = streamer.get_stream_info(event_type="test_event")

    if info:
        print(f"  Stream length: {info.get('length', 'N/A')}")
        print(f"  First entry: {info.get('first-entry', 'N/A')}")
        print(f"  Last entry: {info.get('last-entry', 'N/A')}")
    else:
        print("  (No stream info available - Redis may not be running)")

    # Trim stream
    print("\n🔧 Trimming stream to max 10 events...")
    trimmed = streamer.trim_stream(event_type="test_event", max_length=10)
    print(f"  Trimmed {trimmed} events")

    # Get updated info
    info_after = streamer.get_stream_info(event_type="test_event")
    if info_after:
        print(f"  New stream length: {info_after.get('length', 'N/A')}")

    # Clean up - delete test stream
    print("\n🧹 Cleaning up test stream...")
    deleted = streamer.delete_stream(event_type="test_event")
    print(f"  Stream deleted: {deleted}")

    print()


def main():
    """Run all event streaming demos."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 12 + "EVENT STREAMING DEMONSTRATION (PATTERN 4)" + " " * 15 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    print("This demo shows Redis Streams integration for real-time monitoring.")
    print()

    try:
        # Demo 1: Heartbeat streaming
        demo_heartbeat_streaming()

        # Demo 2: Coordination signal streaming
        demo_coordination_streaming()

        # Demo 3: Broadcast streaming
        demo_broadcast_streaming()

        # Demo 4: Live consumption (commented out - requires async context)
        # Note: Uncomment and run with asyncio.run() for live demo
        # demo_live_consumption()

        # Demo 5: Stream management
        demo_stream_management()

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("    Make sure Redis is running: redis-server")
        print("    Or run: empathy memory start")
        return

    print()
    print("=" * 70)
    print("✅ EVENT STREAMING DEMO COMPLETE")
    print("=" * 70)
    print()
    print("💡 Key Takeaways:")
    print("  1. Heartbeats and coordination signals automatically publish to streams")
    print("  2. Events can be consumed in real-time using the iterator pattern")
    print("  3. Historical events can be retrieved with get_recent_events()")
    print("  4. Streams auto-trim to prevent unbounded growth (MAXLEN)")
    print()
    print("📖 Next Steps:")
    print("  - View live events: empathy telemetry events --follow")
    print("  - Build monitoring tools with WebSocket integration")
    print("  - Enable streaming in workflows: enable_streaming=True")
    print()
    print("📚 Documentation:")
    print("  - docs/AGENT_TRACKING_AND_COORDINATION.md")
    print("  - docs/WORKFLOW_COORDINATION.md")
    print()


if __name__ == "__main__":
    main()
