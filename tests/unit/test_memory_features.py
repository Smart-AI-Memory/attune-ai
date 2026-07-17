"""Tests for memory feature availability checking.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import patch

import pytest

from attune.memory.features import FeatureInfo, FeatureStatus, MemoryFeatures


class TestMemoryFeatures:
    """Test suite for MemoryFeatures availability checking."""

    def test_is_redis_available_when_installed(self):
        """Test Redis availability check when package is installed."""
        # This test will pass/fail based on actual Redis installation
        result = MemoryFeatures.is_redis_available()
        assert isinstance(result, bool)

    def test_is_redis_available_when_missing(self):
        """Test Redis availability check when package is missing."""
        with patch("importlib.import_module", side_effect=ImportError):
            assert MemoryFeatures.is_redis_available() is False

    def test_is_redis_running_when_not_available(self):
        """Test is_redis_running returns False when Redis package missing."""
        with patch.object(MemoryFeatures, "is_redis_available", return_value=False):
            assert MemoryFeatures.is_redis_running() is False

    def test_get_feature_status_core_feature(self):
        """Test that core features are always available."""
        core_features = ["long_term", "file_session", "security", "graph", "encryption"]

        for feature in core_features:
            info = MemoryFeatures.get_feature_status(feature)
            assert isinstance(info, FeatureInfo)
            assert info.status == FeatureStatus.AVAILABLE
            assert "always available" in info.message.lower()
            assert info.install_command is None

    def test_get_feature_status_redis_feature_missing(self):
        """Test Redis feature status when Redis is not available."""
        with patch.object(MemoryFeatures, "is_redis_available", return_value=False):
            info = MemoryFeatures.get_feature_status("short_term")

            assert isinstance(info, FeatureInfo)
            assert info.status == FeatureStatus.MISSING_DEPENDENCY
            assert info.install_command is not None
            assert "pip install" in info.install_command
            # Must target the `redis` package directly. Pointing at
            # `attune-ai[redis]` was the #758 trap: redis ships as a core
            # dep, so that extra was an empty alias and the suggested
            # command was a no-op that could never fix the stated problem.
            assert "redis" in info.install_command
            assert "attune-ai[" not in info.install_command

    def test_get_feature_status_redis_feature_available(self):
        """Test Redis feature status when Redis is available and running."""
        with patch.object(MemoryFeatures, "is_redis_available", return_value=True):
            with patch.object(MemoryFeatures, "is_redis_running", return_value=True):
                info = MemoryFeatures.get_feature_status("short_term")

                assert isinstance(info, FeatureInfo)
                assert info.status == FeatureStatus.AVAILABLE
                assert "available" in info.message.lower()

    def test_get_feature_status_redis_not_running(self):
        """Test Redis feature status when package installed but server not running."""
        with patch.object(MemoryFeatures, "is_redis_available", return_value=True):
            with patch.object(MemoryFeatures, "is_redis_running", return_value=False):
                info = MemoryFeatures.get_feature_status("short_term")

                assert isinstance(info, FeatureInfo)
                assert info.status == FeatureStatus.NOT_CONFIGURED
                assert "not running" in info.message.lower()
                assert "redis.io" in info.install_command.lower()

    def test_get_feature_status_unknown_feature(self):
        """Test get_feature_status with unknown feature name."""
        info = MemoryFeatures.get_feature_status("unknown_feature")

        assert isinstance(info, FeatureInfo)
        assert info.status == FeatureStatus.DISABLED
        assert "unknown" in info.message.lower()

    def test_require_redis_when_available(self):
        """Test require_redis doesn't raise when Redis is available."""
        with patch.object(MemoryFeatures, "is_redis_available", return_value=True):
            with patch.object(MemoryFeatures, "is_redis_running", return_value=True):
                # Should not raise
                MemoryFeatures.require_redis("Test feature")

    def test_require_redis_when_missing(self):
        """Test require_redis raises ImportError when Redis is missing."""
        with patch.object(MemoryFeatures, "is_redis_available", return_value=False):
            with pytest.raises(ImportError) as exc_info:
                MemoryFeatures.require_redis("Test feature")

            error_message = str(exc_info.value)
            assert "requires Redis" in error_message
            assert "Test feature" in error_message
            assert "pip install" in error_message

    def test_require_redis_when_not_running(self):
        """Test require_redis raises ImportError when Redis server not running."""
        with patch.object(MemoryFeatures, "is_redis_available", return_value=True):
            with patch.object(MemoryFeatures, "is_redis_running", return_value=False):
                with pytest.raises(ImportError) as exc_info:
                    MemoryFeatures.require_redis("Test feature")

                error_message = str(exc_info.value)
                assert "requires Redis" in error_message

    def test_list_all_features_returns_dict(self):
        """Test listing all features returns dict with FeatureInfo."""
        features = MemoryFeatures.list_all_features()

        assert isinstance(features, dict)
        assert len(features) > 0

        # Check required features are present
        expected_features = ["short_term", "long_term", "file_session", "security", "graph"]
        for feature in expected_features:
            assert feature in features
            assert isinstance(features[feature], FeatureInfo)

    def test_list_all_features_structure(self):
        """Test that all listed features have required attributes."""
        features = MemoryFeatures.list_all_features()

        for _name, info in features.items():
            assert isinstance(info, FeatureInfo)
            assert hasattr(info, "status")
            assert hasattr(info, "message")
            assert hasattr(info, "install_command")
            assert isinstance(info.status, FeatureStatus)
            assert isinstance(info.message, str)
            assert info.install_command is None or isinstance(info.install_command, str)

    def test_feature_status_enum_values(self):
        """Test that FeatureStatus enum has expected values."""
        expected_statuses = ["available", "missing_dependency", "not_configured", "disabled"]

        for status in expected_statuses:
            assert hasattr(FeatureStatus, status.upper())

    def test_redis_features_consistency(self):
        """Test that all Redis features return consistent statuses."""
        redis_features = [
            "short_term",
            "cross_session",
            "event_streaming",
            "agent_heartbeats",
            "control_panel",
        ]

        with patch.object(MemoryFeatures, "is_redis_available", return_value=False):
            for feature in redis_features:
                info = MemoryFeatures.get_feature_status(feature)
                assert info.status == FeatureStatus.MISSING_DEPENDENCY
                assert info.install_command is not None

    def test_core_features_consistency(self):
        """Test that all core features return AVAILABLE status."""
        core_features = ["long_term", "file_session", "security", "graph", "encryption"]

        for feature in core_features:
            info = MemoryFeatures.get_feature_status(feature)
            assert info.status == FeatureStatus.AVAILABLE
            assert "Core feature" in info.message or "always available" in info.message

    def test_list_all_features_probes_redis_once(self):
        # Per-feature probing previously called is_redis_running() 5 times
        # per list_all_features() invocation. Under xdist on Windows, the
        # concurrent localhost socket probes crashed workers. The fix caches
        # the result for the duration of one call.
        with (
            patch.object(MemoryFeatures, "is_redis_available", return_value=True) as mock_avail,
            patch.object(MemoryFeatures, "is_redis_running", return_value=False) as mock_running,
        ):
            MemoryFeatures.list_all_features()

        assert mock_avail.call_count == 1
        assert mock_running.call_count == 1
