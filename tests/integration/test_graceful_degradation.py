"""Integration tests for graceful degradation when Redis is not available.

Tests that core features work without Redis and Redis features fail gracefully
with helpful error messages.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import patch

import pytest


class TestGracefulDegradationMemory:
    """Test memory module graceful degradation without Redis."""

    def test_file_session_memory_works_without_redis(self):
        """Test FileSessionMemory works without Redis package."""
        from attune.memory import FileSessionMemory

        # Should work without Redis (creates new session when no session_id given)
        memory = FileSessionMemory(user_id="test_user")

        # Basic operations should work
        memory.stash("test_key", {"data": "value"})
        result = memory.retrieve("test_key")

        assert result == {"data": "value"}

    def test_redis_short_term_memory_requires_redis(self):
        """Test RedisShortTermMemory raises helpful error without Redis."""
        with patch("attune.memory.is_redis_available", return_value=False):
            with pytest.raises(ImportError) as exc_info:
                from attune.memory import RedisShortTermMemory

                # Should fail with helpful message
                RedisShortTermMemory()

            error_message = str(exc_info.value)
            assert "requires Redis" in error_message
            assert "pip install" in error_message

    def test_cross_session_coordinator_requires_redis(self):
        """Test CrossSessionCoordinator raises error without Redis."""
        with patch("attune.memory.is_redis_available", return_value=False):
            from attune.memory import CrossSessionCoordinator
            from attune.memory.types import RedisConfig

            # Create mock memory with use_mock=True
            with pytest.raises(ImportError) as exc_info:
                from attune.memory.short_term import RedisShortTermMemory

                memory = RedisShortTermMemory(config=RedisConfig(use_mock=True))
                CrossSessionCoordinator(memory)

            error_message = str(exc_info.value)
            assert "requires Redis" in error_message

    def test_long_term_memory_works_without_redis(self, tmp_path):
        """Test long-term memory works without Redis."""
        from attune.memory import SecureMemDocsIntegration

        # Should work without Redis
        storage_dir = str(tmp_path / "memdocs")
        memory = SecureMemDocsIntegration(
            storage_dir=storage_dir,
            enable_encryption=False,  # Disable for testing
        )

        # Store and retrieve pattern
        result = memory.store_pattern(
            content="Test pattern",
            pattern_type="test",
            user_id="test_user",
        )

        assert "pattern_id" in result
        assert result["classification"] == "PUBLIC"
        pattern_id = result["pattern_id"]

        # Retrieve pattern
        pattern = memory.retrieve_pattern(pattern_id, user_id="test_user")
        assert pattern is not None
        assert pattern["content"] == "Test pattern"


class TestGracefulDegradationTelemetry:
    """Test telemetry module graceful degradation without Redis."""

    def test_usage_tracker_works_without_redis(self, tmp_path):
        """Test UsageTracker works without Redis (file-based)."""
        from attune.telemetry import UsageTracker

        # Should work without Redis - uses file storage
        tracker = UsageTracker(telemetry_dir=tmp_path / "telemetry")

        # Track an LLM call
        tracker.track_llm_call(
            workflow="test-workflow",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        # Verify file was created
        assert (tmp_path / "telemetry" / "usage.jsonl").exists()

    def test_event_streamer_degrades_gracefully_without_redis(self):
        """Test EventStreamer degrades gracefully without Redis."""
        from attune.telemetry import EventStreamer

        # Should not crash without Redis - just logs warning
        streamer = EventStreamer(memory=None)

        # publish_event should return empty string instead of crashing
        event_id = streamer.publish_event("test_event", {"data": "value"})

        assert event_id == ""

    def test_heartbeat_coordinator_degrades_gracefully(self):
        """Test HeartbeatCoordinator works without Redis memory."""
        from attune.telemetry import HeartbeatCoordinator

        # Should not crash without memory backend
        coordinator = HeartbeatCoordinator(memory=None)

        # Methods should not crash
        coordinator.start_heartbeat(
            agent_id="test-agent",
            metadata={"test": "data"},
        )

        # Should handle gracefully (log warning but not crash)
        # The actual heartbeat won't be stored, but code should not error


class TestUnifiedMemoryFallback:
    """Test UnifiedMemory automatically falls back to FileSessionMemory."""

    def test_unified_memory_without_redis_uses_file_session(self):
        """Test UnifiedMemory falls back to FileSessionMemory when Redis unavailable."""
        with patch("attune.memory.is_redis_available", return_value=False):
            from attune.memory import UnifiedMemory

            memory = UnifiedMemory(user_id="test_user")

            # Should still work with file-based storage
            memory.stash("test_key", {"data": "value"})
            result = memory.retrieve("test_key")

            assert result == {"data": "value"}

    def test_unified_memory_long_term_always_works(self, tmp_path):
        """Test UnifiedMemory long-term operations work without Redis."""
        with patch("attune.memory.is_redis_available", return_value=False):
            from attune.memory import MemoryConfig, UnifiedMemory

            # Create config with custom settings
            config = MemoryConfig(
                file_session_dir=str(tmp_path / ".empathy"),
                storage_dir=str(tmp_path / "memdocs"),
                encryption_enabled=False,
            )
            memory = UnifiedMemory(user_id="test_user", config=config)

            # Long-term operations should work
            result = memory.persist_pattern(
                content="Important pattern",
                pattern_type="algorithm",
            )

            assert result is not None
            assert "pattern_id" in result

            # Recall should work
            pattern = memory.recall_pattern(result["pattern_id"])
            assert pattern is not None
            assert pattern["content"] == "Important pattern"


class TestFeatureAvailabilityAPI:
    """Test feature availability API integration."""

    def test_memory_features_api_works(self):
        """Test MemoryFeatures API provides accurate information."""
        from attune.memory.features import MemoryFeatures

        # Should not crash
        features = MemoryFeatures.list_all_features()

        assert isinstance(features, dict)
        assert "long_term" in features
        assert "file_session" in features
        assert "short_term" in features

        # Core features should always be available
        long_term_info = MemoryFeatures.get_feature_status("long_term")
        assert long_term_info.status.value == "available"

    def test_telemetry_features_api_works(self):
        """Test TelemetryFeatures API provides accurate information."""
        from attune.telemetry.features import TelemetryFeatures

        # Should not crash
        features = TelemetryFeatures.list_all_features()

        assert isinstance(features, dict)
        assert "usage_tracking" in features
        assert "event_streaming" in features

        # Core features should always be available
        usage_info = TelemetryFeatures.get_feature_status("usage_tracking")
        assert usage_info.status.value == "available"
