"""Tests for attune.memory.short_term.security (DataSanitizer).

Covers the previously-uncovered branches:
- secrets_detection_enabled init path
- sanitize() with secrets detector active (critical blocking, non-critical pass)
- sanitize() with PII scrubber active (dict, list, str, broken JSON)
- check_secrets() all branches
- scrub_pii_only() all branches
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from attune.memory.short_term.security import DataSanitizer
from attune.memory.types import SecurityError

# ---------------------------------------------------------------------------
# Helpers — lightweight fakes for PIIScrubber / SecretsDetector
# ---------------------------------------------------------------------------


def _make_fake_detection(secret_type_value: str, severity):
    d = MagicMock()
    d.secret_type = MagicMock()
    d.secret_type.value = secret_type_value
    d.severity = severity
    return d


def _make_pii_detection(pii_type: str = "EMAIL"):
    d = MagicMock()
    d.pii_type = pii_type
    return d


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDataSanitizerInit:
    def test_defaults_both_disabled(self):
        s = DataSanitizer()
        assert s.pii_enabled is False
        assert s.secrets_enabled is False
        assert s._pii_scrubber is None
        assert s._secrets_detector is None

    def test_pii_enabled_creates_scrubber(self):
        s = DataSanitizer(pii_scrub_enabled=True)
        assert s.pii_enabled is True
        assert s._pii_scrubber is not None

    def test_secrets_enabled_creates_detector(self):
        s = DataSanitizer(secrets_detection_enabled=True)
        assert s.secrets_enabled is True
        assert s._secrets_detector is not None

    def test_metrics_property(self):
        from attune.memory.types import RedisMetrics

        m = RedisMetrics()
        s = DataSanitizer(metrics=m)
        assert s.metrics is m


# ---------------------------------------------------------------------------
# sanitize() — no scrubbers active
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSanitizePassthrough:
    def setup_method(self):
        self.s = DataSanitizer()

    def test_none_returns_none(self):
        result, count = self.s.sanitize(None)
        assert result is None
        assert count == 0

    def test_dict_passes_through(self):
        data = {"key": "value"}
        result, count = self.s.sanitize(data)
        assert result == data
        assert count == 0

    def test_list_passes_through(self):
        data = [1, 2, 3]
        result, count = self.s.sanitize(data)
        assert result == data
        assert count == 0

    def test_string_passes_through(self):
        data = "hello world"
        result, count = self.s.sanitize(data)
        assert result == data
        assert count == 0

    def test_integer_passes_through(self):
        result, count = self.s.sanitize(42)
        assert result == 42
        assert count == 0


# ---------------------------------------------------------------------------
# sanitize() — secrets detector active
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSanitizeSecretsDetection:
    def setup_method(self):
        self.s = DataSanitizer(secrets_detection_enabled=True)

    def test_critical_secret_raises_security_error(self):
        from attune.memory.security.secrets_detector import Severity

        critical = _make_fake_detection("openai_api_key", Severity.CRITICAL)
        self.s._secrets_detector.detect = MagicMock(return_value=[critical])

        with pytest.raises(SecurityError, match="openai_api_key"):
            self.s.sanitize({"key": "sk-abc123"})

    def test_high_severity_secret_raises_security_error(self):
        from attune.memory.security.secrets_detector import Severity

        high = _make_fake_detection("aws_secret_key", Severity.HIGH)
        self.s._secrets_detector.detect = MagicMock(return_value=[high])

        with pytest.raises(SecurityError):
            self.s.sanitize("AKIA1234567890EXAMPLE")

    def test_no_secrets_passes_through(self):
        self.s._secrets_detector.detect = MagicMock(return_value=[])
        result, count = self.s.sanitize({"safe": "data"})
        assert result == {"safe": "data"}
        assert count == 0

    def test_secrets_blocked_increments_metric(self):
        from attune.memory.security.secrets_detector import Severity

        critical = _make_fake_detection("github_token", Severity.CRITICAL)
        self.s._secrets_detector.detect = MagicMock(return_value=[critical])

        with pytest.raises(SecurityError):
            self.s.sanitize("ghp_abc123")

        assert self.s._metrics.secrets_blocked_total >= 1

    def test_string_input_scanned(self):
        self.s._secrets_detector.detect = MagicMock(return_value=[])
        result, count = self.s.sanitize("plain string")
        assert result == "plain string"

    def test_non_standard_type_converted_to_str(self):
        self.s._secrets_detector.detect = MagicMock(return_value=[])
        result, count = self.s.sanitize(99.9)
        assert count == 0


# ---------------------------------------------------------------------------
# sanitize() — PII scrubber active
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSanitizePIIScrubbing:
    def setup_method(self):
        self.s = DataSanitizer(pii_scrub_enabled=True)

    def test_no_pii_returns_original(self):
        self.s._pii_scrubber.scrub = MagicMock(return_value=('{"key": "value"}', []))
        result, count = self.s.sanitize({"key": "value"})
        assert count == 0
        assert result == {"key": "value"}

    def test_pii_in_dict_scrubbed_and_parsed(self):
        self.s._pii_scrubber.scrub = MagicMock(
            return_value=('{"email": "[EMAIL]"}', [_make_pii_detection("EMAIL")])
        )
        result, count = self.s.sanitize({"email": "user@example.com"})
        assert count == 1
        assert result["email"] == "[EMAIL]"

    def test_pii_in_list_scrubbed_and_parsed(self):
        self.s._pii_scrubber.scrub = MagicMock(
            return_value=('["[EMAIL]"]', [_make_pii_detection("EMAIL")])
        )
        result, count = self.s.sanitize(["user@example.com"])
        assert count == 1
        assert result[0] == "[EMAIL]"

    def test_pii_in_string_returns_scrubbed_str(self):
        self.s._pii_scrubber.scrub = MagicMock(
            return_value=("contact [EMAIL] here", [_make_pii_detection("EMAIL")])
        )
        result, count = self.s.sanitize("contact user@example.com here")
        assert count == 1
        assert "[EMAIL]" in result

    def test_broken_json_after_scrub_returns_original_dict(self):
        self.s._pii_scrubber.scrub = MagicMock(
            return_value=("BROKEN{NOT JSON", [_make_pii_detection("EMAIL")])
        )
        original = {"key": "user@example.com"}
        result, count = self.s.sanitize(original)
        assert result == original
        assert count == 0

    def test_broken_json_after_scrub_returns_original_list(self):
        self.s._pii_scrubber.scrub = MagicMock(
            return_value=("BROKEN[NOT JSON", [_make_pii_detection("EMAIL")])
        )
        original = ["user@example.com"]
        result, count = self.s.sanitize(original)
        assert result == original
        assert count == 0

    def test_pii_scrub_increments_metrics(self):
        self.s._pii_scrubber.scrub = MagicMock(
            return_value=('"[EMAIL]"', [_make_pii_detection("EMAIL")])
        )
        self.s.sanitize("user@example.com")
        assert self.s._metrics.pii_scrubbed_total >= 1
        assert self.s._metrics.pii_scrub_operations >= 1


# ---------------------------------------------------------------------------
# check_secrets()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckSecrets:
    def test_returns_empty_when_no_detector(self):
        s = DataSanitizer()
        assert s.check_secrets({"key": "value"}) == []

    def test_returns_empty_when_data_none(self):
        s = DataSanitizer(secrets_detection_enabled=True)
        assert s.check_secrets(None) == []

    def test_returns_secret_types_for_dict(self):
        s = DataSanitizer(secrets_detection_enabled=True)
        from attune.memory.security.secrets_detector import Severity

        detection = _make_fake_detection("aws_key", Severity.CRITICAL)
        s._secrets_detector.detect = MagicMock(return_value=[detection])
        result = s.check_secrets({"key": "AKIA..."})
        assert "aws_key" in result

    def test_returns_secret_types_for_string(self):
        s = DataSanitizer(secrets_detection_enabled=True)
        from attune.memory.security.secrets_detector import Severity

        detection = _make_fake_detection("github_token", Severity.HIGH)
        s._secrets_detector.detect = MagicMock(return_value=[detection])
        result = s.check_secrets("ghp_abc123")
        assert result == ["github_token"]

    def test_returns_empty_when_no_detections(self):
        s = DataSanitizer(secrets_detection_enabled=True)
        s._secrets_detector.detect = MagicMock(return_value=[])
        result = s.check_secrets({"safe": "data"})
        assert result == []

    def test_list_input_converted_to_json(self):
        s = DataSanitizer(secrets_detection_enabled=True)
        s._secrets_detector.detect = MagicMock(return_value=[])
        result = s.check_secrets(["item1", "item2"])
        assert result == []

    def test_non_standard_type_converted_to_str(self):
        s = DataSanitizer(secrets_detection_enabled=True)
        s._secrets_detector.detect = MagicMock(return_value=[])
        result = s.check_secrets(12345)
        assert result == []


# ---------------------------------------------------------------------------
# scrub_pii_only()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScrubPiiOnly:
    def test_returns_data_unchanged_when_no_scrubber(self):
        s = DataSanitizer()
        result, count = s.scrub_pii_only({"key": "value"})
        assert result == {"key": "value"}
        assert count == 0

    def test_returns_data_unchanged_when_none(self):
        s = DataSanitizer(pii_scrub_enabled=True)
        result, count = s.scrub_pii_only(None)
        assert result is None
        assert count == 0

    def test_no_pii_returns_original(self):
        s = DataSanitizer(pii_scrub_enabled=True)
        s._pii_scrubber.scrub = MagicMock(return_value=('{"key": "val"}', []))
        result, count = s.scrub_pii_only({"key": "val"})
        assert count == 0
        assert result == {"key": "val"}

    def test_pii_in_dict_scrubbed(self):
        s = DataSanitizer(pii_scrub_enabled=True)
        s._pii_scrubber.scrub = MagicMock(
            return_value=('{"email": "[EMAIL]"}', [_make_pii_detection("EMAIL")])
        )
        result, count = s.scrub_pii_only({"email": "user@example.com"})
        assert count == 1
        assert result["email"] == "[EMAIL]"

    def test_pii_in_string_scrubbed(self):
        s = DataSanitizer(pii_scrub_enabled=True)
        s._pii_scrubber.scrub = MagicMock(return_value=("[EMAIL]", [_make_pii_detection("EMAIL")]))
        result, count = s.scrub_pii_only("user@example.com")
        assert count == 1
        assert result == "[EMAIL]"

    def test_broken_json_after_scrub_returns_original(self):
        s = DataSanitizer(pii_scrub_enabled=True)
        s._pii_scrubber.scrub = MagicMock(
            return_value=("BROKEN JSON", [_make_pii_detection("EMAIL")])
        )
        original = {"key": "user@example.com"}
        result, count = s.scrub_pii_only(original)
        assert result == original
        assert count == 0

    def test_metrics_updated(self):
        s = DataSanitizer(pii_scrub_enabled=True)
        s._pii_scrubber.scrub = MagicMock(return_value=("[EMAIL]", [_make_pii_detection("EMAIL")]))
        s.scrub_pii_only("user@example.com")
        assert s._metrics.pii_scrubbed_total >= 1
        assert s._metrics.pii_scrub_operations >= 1

    def test_non_standard_type_converted(self):
        s = DataSanitizer(pii_scrub_enabled=True)
        s._pii_scrubber.scrub = MagicMock(return_value=("12345", []))
        result, count = s.scrub_pii_only(12345)
        assert count == 0
