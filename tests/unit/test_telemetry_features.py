"""Tests for telemetry feature availability checking.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import patch

import pytest

from attune.telemetry.features import FeatureInfo, FeatureStatus, TelemetryFeatures


class TestTelemetryFeatures:
    """Test suite for TelemetryFeatures availability checking."""

    def test_is_redis_available_delegates_to_memory(self):
        """Test that is_redis_available calls attune.memory.is_redis_available."""
        with patch("attune.memory.is_redis_available", return_value=True) as mock_check:
            result = TelemetryFeatures.is_redis_available()

            assert result is True
            mock_check.assert_called_once()

    def test_get_feature_status_core_features(self):
        """Test that core telemetry features are always available."""
        core_features = ["usage_tracking", "feedback_loop", "cli"]

        for feature in core_features:
            info = TelemetryFeatures.get_feature_status(feature)

            assert isinstance(info, FeatureInfo)
            assert info.status == FeatureStatus.AVAILABLE
            assert "Core feature" in info.message or "always available" in info.message.lower()
            assert info.install_command is None

    def test_get_feature_status_redis_features_missing(self):
        """Test Redis-dependent features when Redis is not available."""
        with patch("attune.memory.is_redis_available", return_value=False):
            redis_features = [
                "event_streaming",
                "agent_heartbeats",
                "agent_coordination",
                "approval_gates",
            ]

            for feature in redis_features:
                info = TelemetryFeatures.get_feature_status(feature)

                assert isinstance(info, FeatureInfo)
                assert info.status == FeatureStatus.MISSING_DEPENDENCY
                assert "not importable" in info.message
                assert info.install_command is not None
                # See test_memory_features for why this must not point at
                # `attune-ai[redis]`: that extra was an empty alias, so the
                # remediation was a no-op (the #758 trap).
                assert "redis" in info.install_command
                assert "attune-ai[" not in info.install_command

    def test_get_feature_status_redis_features_available(self):
        """Test Redis-dependent features when Redis is available."""
        with patch("attune.memory.is_redis_available", return_value=True):
            redis_features = [
                "event_streaming",
                "agent_heartbeats",
                "agent_coordination",
                "approval_gates",
            ]

            for feature in redis_features:
                info = TelemetryFeatures.get_feature_status(feature)

                assert isinstance(info, FeatureInfo)
                assert info.status == FeatureStatus.AVAILABLE
                assert "available" in info.message.lower()

    def test_get_feature_status_unknown_feature(self):
        """Test get_feature_status with unknown feature name."""
        info = TelemetryFeatures.get_feature_status("nonexistent_feature")

        assert isinstance(info, FeatureInfo)
        assert info.status == FeatureStatus.DISABLED
        assert "Unknown feature" in info.message

    def test_require_redis_when_available(self):
        """Test require_redis doesn't raise when Redis is available."""
        with patch("attune.memory.is_redis_available", return_value=True):
            # Should not raise
            TelemetryFeatures.require_redis("Event streaming")

    def test_require_redis_when_missing(self):
        """Test require_redis raises ImportError when Redis is missing."""
        with patch("attune.memory.is_redis_available", return_value=False):
            with pytest.raises(ImportError) as exc_info:
                TelemetryFeatures.require_redis("Event streaming")

            error_message = str(exc_info.value)
            assert "Event streaming" in error_message
            assert "requires the redis package" in error_message
            assert "pip install" in error_message
            # Assert the exact URL rather than a bare-domain substring
            # (CodeQL py/incomplete-url-substring-sanitization, alert #179).
            assert "https://redis.io/docs/install/" in error_message
            # The fix offered must be able to work: `attune-ai[redis]` was
            # an empty alias, so suggesting it could never resolve a
            # missing import (the #758 trap).
            assert "attune-ai[" not in error_message

    def test_list_all_features_returns_dict(self):
        """Test listing all telemetry features returns dict."""
        features = TelemetryFeatures.list_all_features()

        assert isinstance(features, dict)
        assert len(features) > 0

        # Check required features are present
        expected_features = [
            "event_streaming",
            "agent_heartbeats",
            "usage_tracking",
            "feedback_loop",
        ]
        for feature in expected_features:
            assert feature in features
            assert isinstance(features[feature], FeatureInfo)

    def test_list_all_features_structure(self):
        """Test that all listed features have required attributes."""
        features = TelemetryFeatures.list_all_features()

        for _name, info in features.items():
            assert isinstance(info, FeatureInfo)
            assert hasattr(info, "status")
            assert hasattr(info, "message")
            assert hasattr(info, "install_command")
            assert isinstance(info.status, FeatureStatus)
            assert isinstance(info.message, str)

    def test_redis_features_have_install_command_when_missing(self):
        """Test that Redis features include install command when unavailable."""
        with patch("attune.memory.is_redis_available", return_value=False):
            redis_features = [
                "event_streaming",
                "agent_heartbeats",
                "agent_coordination",
                "approval_gates",
            ]

            for feature in redis_features:
                info = TelemetryFeatures.get_feature_status(feature)
                assert info.install_command is not None
                assert "pip install" in info.install_command

    def test_core_features_no_install_command(self):
        """Test that core features don't have install command."""
        core_features = ["usage_tracking", "feedback_loop", "cli"]

        for feature in core_features:
            info = TelemetryFeatures.get_feature_status(feature)
            assert info.install_command is None

    def test_feature_info_dataclass_structure(self):
        """Test that FeatureInfo has expected structure."""
        info = TelemetryFeatures.get_feature_status("usage_tracking")

        assert hasattr(info, "name")
        assert hasattr(info, "status")
        assert hasattr(info, "message")
        assert hasattr(info, "install_command")

        assert isinstance(info.name, str)
        assert isinstance(info.status, FeatureStatus)
        assert isinstance(info.message, str)

    def test_consistency_between_features_and_list(self):
        """Test that individual feature queries match list_all_features."""
        all_features = TelemetryFeatures.list_all_features()

        for feature_name in all_features:
            individual = TelemetryFeatures.get_feature_status(feature_name)
            from_list = all_features[feature_name]

            assert individual.status == from_list.status
            assert individual.message == from_list.message
            assert individual.install_command == from_list.install_command
