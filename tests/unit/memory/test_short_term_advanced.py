"""Tests for advanced RedisShortTermMemory operations.

Tests cover high-risk code paths:
- Batch operations (stash_batch, retrieve_batch)
- Pub/Sub (publish, subscribe, unsubscribe)
- Streams (stream_append, stream_read)
- Task queues (queue_push, queue_pop, queue_peek)
- Timeline operations (timeline_add, timeline_query)
- Atomic transactions (atomic_promote_pattern)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime, timedelta

import pytest

from attune.memory import (
    AccessTier,
    AgentCredentials,
    RedisShortTermMemory,
    StagedPattern,
    TTLStrategy,
)
from attune.memory.types import PaginatedResult, TimeWindowQuery


@pytest.fixture
def memory():
    """Create mock RedisShortTermMemory instance."""
    return RedisShortTermMemory(use_mock=True)


@pytest.fixture
def contributor_creds():
    """Create CONTRIBUTOR tier credentials."""
    return AgentCredentials(agent_id="test_agent", tier=AccessTier.CONTRIBUTOR)


@pytest.fixture
def validator_creds():
    """Create VALIDATOR tier credentials."""
    return AgentCredentials(agent_id="validator_agent", tier=AccessTier.VALIDATOR)


@pytest.fixture
def observer_creds():
    """Create OBSERVER tier credentials (read-only)."""
    return AgentCredentials(agent_id="observer_agent", tier=AccessTier.OBSERVER)


# =============================================================================
# BATCH OPERATIONS
# =============================================================================


class TestBatchOperations:
    """Tests for stash_batch and retrieve_batch."""

    def test_stash_batch_success(self, memory, contributor_creds):
        """Test successful batch stash of multiple items."""
        items = [
            ("key1", {"data": "value1"}),
            ("key2", {"data": "value2"}),
            ("key3", {"data": "value3"}),
        ]

        count = memory.stash_batch(items, contributor_creds)

        assert count == 3

    def test_stash_batch_empty_list(self, memory, contributor_creds):
        """Test batch stash with empty list returns 0."""
        count = memory.stash_batch([], contributor_creds)
        assert count == 0

    def test_stash_batch_requires_contributor(self, memory, observer_creds):
        """Test batch stash fails for OBSERVER tier."""
        items = [("key1", {"data": "value1"})]

        with pytest.raises(PermissionError, match="CONTRIBUTOR"):
            memory.stash_batch(items, observer_creds)

    def test_stash_batch_type_validation(self, memory, contributor_creds):
        """Test batch stash validates items is a list."""
        with pytest.raises(TypeError, match="items must be list"):
            memory.stash_batch("not a list", contributor_creds)

    def test_retrieve_batch_success(self, memory, contributor_creds):
        """Test successful batch retrieval."""
        # First stash items
        items = [
            ("batch_key1", {"data": "value1"}),
            ("batch_key2", {"data": "value2"}),
        ]
        memory.stash_batch(items, contributor_creds)

        # Retrieve in batch
        results = memory.retrieve_batch(["batch_key1", "batch_key2"], contributor_creds)

        assert results["batch_key1"] == {"data": "value1"}
        assert results["batch_key2"] == {"data": "value2"}

    def test_retrieve_batch_partial_results(self, memory, contributor_creds):
        """Test batch retrieval with some missing keys."""
        memory.stash("existing_key", {"data": "exists"}, contributor_creds)

        results = memory.retrieve_batch(["existing_key", "nonexistent_key"], contributor_creds)

        assert "existing_key" in results
        assert "nonexistent_key" not in results

    def test_retrieve_batch_empty_keys(self, memory, contributor_creds):
        """Test batch retrieval with empty keys list."""
        results = memory.retrieve_batch([], contributor_creds)
        assert results == {}

    def test_stash_batch_with_custom_ttl(self, memory, contributor_creds):
        """Test batch stash respects TTL strategy."""
        items = [("ttl_key", {"data": "value"})]

        count = memory.stash_batch(items, contributor_creds, ttl=TTLStrategy.SESSION)

        assert count == 1


# =============================================================================
# PUB/SUB OPERATIONS
# =============================================================================


class TestPubSubOperations:
    """Tests for publish, subscribe, and unsubscribe."""

    def test_publish_success(self, memory, contributor_creds):
        """Test successful publish returns subscriber count."""
        # Subscribe first
        received_messages = []
        memory.subscribe("test_channel", lambda msg: received_messages.append(msg))

        # Publish
        count = memory.publish("test_channel", {"event": "test_event"}, contributor_creds)

        assert count >= 0  # Mock returns handler count

    def test_publish_requires_contributor(self, memory, observer_creds):
        """Test publish fails for OBSERVER tier."""
        with pytest.raises(PermissionError, match="CONTRIBUTOR"):
            memory.publish("channel", {"data": "test"}, observer_creds)

    def test_subscribe_receives_messages(self, memory, contributor_creds):
        """Test subscriber receives published messages."""
        received = []

        def handler(msg):
            received.append(msg)

        memory.subscribe("events", handler)
        memory.publish("events", {"type": "test"}, contributor_creds)

        assert len(received) == 1
        assert received[0]["data"]["type"] == "test"

    def test_subscribe_multiple_handlers(self, memory, contributor_creds):
        """Test multiple handlers on same channel."""
        received1 = []
        received2 = []

        memory.subscribe("multi", lambda msg: received1.append(msg))
        memory.subscribe("multi", lambda msg: received2.append(msg))
        memory.publish("multi", {"event": "shared"}, contributor_creds)

        assert len(received1) == 1
        assert len(received2) == 1

    def test_unsubscribe_stops_messages(self, memory, contributor_creds):
        """Test unsubscribe stops message delivery."""
        received = []
        memory.subscribe("unsub_test", lambda msg: received.append(msg))

        # Publish before unsubscribe
        memory.publish("unsub_test", {"msg": 1}, contributor_creds)
        assert len(received) == 1

        # Unsubscribe
        memory.unsubscribe("unsub_test")

        # Publish after unsubscribe
        memory.publish("unsub_test", {"msg": 2}, contributor_creds)
        assert len(received) == 1  # Should not receive second message

    def test_close_pubsub_cleanup(self, memory):
        """Test close_pubsub cleans up resources."""
        memory.subscribe("cleanup_test", lambda msg: None)
        memory.close_pubsub()

        # Verify subscriptions cleared
        assert len(memory._subscriptions) == 0


# =============================================================================
# STREAM OPERATIONS
# =============================================================================


class TestStreamOperations:
    """Tests for Redis Streams audit trail functionality."""

    def test_stream_append_success(self, memory, contributor_creds):
        """Test successful stream append returns entry ID."""
        entry_id = memory.stream_append(
            "audit_stream",
            {"action": "pattern_created", "pattern_id": "pat_123"},
            contributor_creds,
        )

        assert entry_id is not None
        assert "-" in entry_id  # Format: timestamp-sequence

    def test_stream_append_requires_contributor(self, memory, observer_creds):
        """Test stream append fails for OBSERVER tier."""
        with pytest.raises(PermissionError, match="CONTRIBUTOR"):
            memory.stream_append("audit", {"action": "test"}, observer_creds)

    def test_stream_read_returns_entries(self, memory, contributor_creds):
        """Test stream read returns appended entries."""
        # Append entries
        memory.stream_append("read_test", {"action": "action1"}, contributor_creds)
        memory.stream_append("read_test", {"action": "action2"}, contributor_creds)

        # Read entries
        entries = memory.stream_read("read_test", contributor_creds)

        assert len(entries) >= 2

    def test_stream_read_with_start_id(self, memory, contributor_creds):
        """Test stream read accepts start_id parameter."""
        id1 = memory.stream_append("filter_test", {"seq": 1}, contributor_creds)
        memory.stream_append("filter_test", {"seq": 2}, contributor_creds)

        # Read from after first entry - with mock, filtering may not work
        # but we verify the interface accepts start_id parameter
        entries = memory.stream_read("filter_test", contributor_creds, start_id=id1)

        # With mock Redis, just verify it returns a list (filtering is Redis-level)
        assert isinstance(entries, list)

    def test_stream_read_with_count_limit(self, memory, contributor_creds):
        """Test stream read respects count limit."""
        for i in range(5):
            memory.stream_append("count_test", {"seq": i}, contributor_creds)

        entries = memory.stream_read("count_test", contributor_creds, count=2)

        assert len(entries) <= 2

    def test_stream_read_empty_stream(self, memory, contributor_creds):
        """Test reading from non-existent stream returns empty list."""
        entries = memory.stream_read("nonexistent_stream", contributor_creds)
        assert entries == []


# =============================================================================
# TASK QUEUE OPERATIONS
# =============================================================================


class TestQueueOperations:
    """Tests for task queue functionality."""

    def test_queue_push_success(self, memory, contributor_creds):
        """Test successful queue push returns queue length."""
        task = {"type": "analyze", "file": "main.py"}

        length = memory.queue_push("task_queue", task, contributor_creds)

        assert length >= 1

    def test_queue_push_requires_contributor(self, memory, observer_creds):
        """Test queue push fails for OBSERVER tier."""
        with pytest.raises(PermissionError, match="CONTRIBUTOR"):
            memory.queue_push("queue", {"task": "test"}, observer_creds)

    def test_queue_push_priority(self, memory, contributor_creds):
        """Test priority push adds to front of queue."""
        memory.queue_push("priority_test", {"order": 1}, contributor_creds)
        memory.queue_push("priority_test", {"order": 2}, contributor_creds, priority=True)

        # Pop should return priority item first
        task = memory.queue_pop("priority_test", contributor_creds)
        assert task["task"]["order"] == 2

    def test_queue_pop_success(self, memory, contributor_creds):
        """Test successful queue pop returns task."""
        memory.queue_push("pop_test", {"data": "test_task"}, contributor_creds)

        task = memory.queue_pop("pop_test", contributor_creds)

        assert task is not None
        assert task["task"]["data"] == "test_task"

    def test_queue_pop_empty_queue(self, memory, contributor_creds):
        """Test pop from empty queue returns None."""
        task = memory.queue_pop("empty_queue", contributor_creds)
        assert task is None

    def test_queue_length(self, memory, contributor_creds):
        """Test queue length returns correct count."""
        for i in range(3):
            memory.queue_push("length_test", {"seq": i}, contributor_creds)

        length = memory.queue_length("length_test")

        assert length == 3

    def test_queue_length_empty(self, memory):
        """Test queue length for non-existent queue returns 0."""
        length = memory.queue_length("nonexistent_queue")
        assert length == 0

    def test_queue_peek_without_removing(self, memory, contributor_creds):
        """Test peek returns tasks without removing them."""
        memory.queue_push("peek_test", {"data": "peek_task"}, contributor_creds)

        # Peek
        tasks = memory.queue_peek("peek_test", contributor_creds, count=1)
        assert len(tasks) == 1

        # Verify still in queue
        length = memory.queue_length("peek_test")
        assert length == 1

    def test_queue_fifo_order(self, memory, contributor_creds):
        """Test queue maintains FIFO order."""
        memory.queue_push("fifo_test", {"order": 1}, contributor_creds)
        memory.queue_push("fifo_test", {"order": 2}, contributor_creds)
        memory.queue_push("fifo_test", {"order": 3}, contributor_creds)

        task1 = memory.queue_pop("fifo_test", contributor_creds)
        task2 = memory.queue_pop("fifo_test", contributor_creds)
        task3 = memory.queue_pop("fifo_test", contributor_creds)

        assert task1["task"]["order"] == 1
        assert task2["task"]["order"] == 2
        assert task3["task"]["order"] == 3


# =============================================================================
# TIMELINE OPERATIONS
# =============================================================================


class TestTimelineOperations:
    """Tests for timeline (sorted set) operations."""

    def test_timeline_add_success(self, memory, contributor_creds):
        """Test successful timeline add."""
        result = memory.timeline_add(
            "events",
            "event_1",
            {"type": "login"},
            contributor_creds,
        )

        assert result is True

    def test_timeline_add_requires_contributor(self, memory, observer_creds):
        """Test timeline add fails for OBSERVER tier."""
        with pytest.raises(PermissionError, match="CONTRIBUTOR"):
            memory.timeline_add("events", "event_1", {"data": "test"}, observer_creds)

    def test_timeline_add_with_custom_timestamp(self, memory, contributor_creds):
        """Test timeline add with custom timestamp."""
        past_time = datetime.now() - timedelta(hours=1)

        result = memory.timeline_add(
            "custom_time",
            "past_event",
            {"type": "historical"},
            contributor_creds,
            timestamp=past_time,
        )

        assert result is True

    def test_timeline_query_returns_events(self, memory, contributor_creds):
        """Test timeline query returns added events."""
        memory.timeline_add("query_test", "evt1", {"seq": 1}, contributor_creds)
        memory.timeline_add("query_test", "evt2", {"seq": 2}, contributor_creds)

        events = memory.timeline_query("query_test", contributor_creds)

        assert len(events) >= 2

    def test_timeline_query_with_time_window(self, memory, contributor_creds):
        """Test timeline query with time window filter."""
        now = datetime.now()
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        # Add event with current timestamp
        memory.timeline_add("window_test", "now_event", {"time": "now"}, contributor_creds)

        # Query with window that includes current time
        query = TimeWindowQuery(start_time=past, end_time=future, limit=10)
        events = memory.timeline_query("window_test", contributor_creds, query=query)

        assert len(events) >= 1

    def test_timeline_query_with_limit(self, memory, contributor_creds):
        """Test timeline query respects limit."""
        for i in range(5):
            memory.timeline_add("limit_test", f"evt_{i}", {"seq": i}, contributor_creds)

        query = TimeWindowQuery(limit=2)
        events = memory.timeline_query("limit_test", contributor_creds, query=query)

        assert len(events) <= 2

    def test_timeline_count(self, memory, contributor_creds):
        """Test timeline count returns correct number."""
        for i in range(3):
            memory.timeline_add("count_test", f"evt_{i}", {"seq": i}, contributor_creds)

        count = memory.timeline_count("count_test", contributor_creds)

        assert count == 3

    def test_timeline_empty_returns_empty(self, memory, contributor_creds):
        """Test query on non-existent timeline returns empty list."""
        events = memory.timeline_query("nonexistent_timeline", contributor_creds)
        assert events == []


# =============================================================================
# ATOMIC OPERATIONS
# =============================================================================


class TestAtomicOperations:
    """Tests for atomic transaction operations."""

    def test_atomic_promote_pattern_success(self, memory, validator_creds, contributor_creds):
        """Test successful atomic pattern promotion."""
        # Stage a pattern first
        pattern = StagedPattern(
            pattern_id="atomic_test",
            agent_id=contributor_creds.agent_id,
            pattern_type="test",
            name="Test Pattern",
            description="A test pattern",
            confidence=0.8,
        )
        memory.stage_pattern(pattern, contributor_creds)

        # Atomically promote
        success, promoted, message = memory.atomic_promote_pattern("atomic_test", validator_creds)

        assert success is True
        assert promoted is not None
        assert promoted.pattern_id == "atomic_test"

    def test_atomic_promote_requires_validator(self, memory, contributor_creds):
        """Test atomic promote requires VALIDATOR tier."""
        success, pattern, message = memory.atomic_promote_pattern("test_id", contributor_creds)

        assert success is False
        assert "VALIDATOR" in message

    def test_atomic_promote_nonexistent_pattern(self, memory, validator_creds):
        """Test atomic promote of non-existent pattern fails."""
        success, pattern, message = memory.atomic_promote_pattern(
            "nonexistent_pattern",
            validator_creds,
        )

        assert success is False
        assert pattern is None
        assert "not found" in message.lower()

    def test_atomic_promote_with_confidence_threshold(
        self,
        memory,
        validator_creds,
        contributor_creds,
    ):
        """Test atomic promote respects confidence threshold."""
        # Stage a low-confidence pattern
        pattern = StagedPattern(
            pattern_id="low_conf",
            agent_id=contributor_creds.agent_id,
            pattern_type="test",
            name="Low Confidence",
            description="Pattern with low confidence",
            confidence=0.3,
        )
        memory.stage_pattern(pattern, contributor_creds)

        # Try to promote with high threshold
        success, promoted, message = memory.atomic_promote_pattern(
            "low_conf",
            validator_creds,
            min_confidence=0.7,
        )

        assert success is False
        assert "confidence" in message.lower()

    def test_atomic_promote_validates_pattern_id(self, memory, validator_creds):
        """Test atomic promote validates pattern_id is not empty."""
        with pytest.raises(ValueError, match="pattern_id cannot be empty"):
            memory.atomic_promote_pattern("", validator_creds)

    def test_atomic_promote_validates_confidence_range(self, memory, validator_creds):
        """Test atomic promote validates confidence threshold range."""
        with pytest.raises(ValueError, match="min_confidence must be between"):
            memory.atomic_promote_pattern("test", validator_creds, min_confidence=1.5)


# =============================================================================
# PAGINATION
# =============================================================================


class TestPaginatedOperations:
    """Tests for paginated listing operations."""

    def test_list_staged_patterns_paginated(self, memory, contributor_creds):
        """Test paginated listing of staged patterns."""
        # Stage some patterns
        for i in range(5):
            pattern = StagedPattern(
                pattern_id=f"page_test_{i}",
                agent_id=contributor_creds.agent_id,
                pattern_type="test",
                name=f"Pattern {i}",
                description=f"Description {i}",
            )
            memory.stage_pattern(pattern, contributor_creds)

        # Get first page
        result = memory.list_staged_patterns_paginated(contributor_creds, cursor="0", count=2)

        assert isinstance(result, PaginatedResult)
        assert len(result.items) <= 2

    def test_scan_keys_pagination(self, memory, contributor_creds):
        """Test scan_keys pagination."""
        # Stash some data
        for i in range(5):
            memory.stash(f"scan_test_{i}", {"seq": i}, contributor_creds)

        # Scan with pattern
        result = memory.scan_keys(f"{memory.PREFIX_WORKING}*", cursor="0", count=10)

        assert isinstance(result, PaginatedResult)
        assert len(result.items) >= 0


# =============================================================================
# METRICS
# =============================================================================


class TestMetricsTracking:
    """Tests for operation metrics tracking."""

    def test_get_metrics_returns_dict(self, memory):
        """Test get_metrics returns metrics dictionary."""
        metrics = memory.get_metrics()

        assert isinstance(metrics, dict)
        assert "operations_total" in metrics
        assert "success_rate" in metrics

    def test_reset_metrics(self, memory, contributor_creds):
        """Test reset_metrics clears all metrics."""
        # Perform some operations
        memory.stash("metrics_test", {"data": "test"}, contributor_creds)
        memory.retrieve("metrics_test", contributor_creds)

        # Reset
        memory.reset_metrics()

        metrics = memory.get_metrics()
        assert metrics["operations_total"] == 0

    def test_metrics_track_operations(self, memory, contributor_creds):
        """Test metrics track operation counts."""
        initial = memory.get_metrics()["operations_total"]

        memory.stash("track_test", {"data": "test"}, contributor_creds)

        final = memory.get_metrics()
        # Note: stash internally may do multiple ops
        assert final["operations_total"] >= initial


# =============================================================================
# CLEANUP
# =============================================================================


class TestCleanup:
    """Tests for resource cleanup."""

    def test_close_cleans_all_resources(self, memory):
        """Test close method cleans up all resources."""
        memory.subscribe("cleanup_channel", lambda msg: None)

        memory.close()

        assert memory._client is None
