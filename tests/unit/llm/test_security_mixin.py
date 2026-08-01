"""Behavioral tests for attune.llm.security.SecurityMixin.

Covers production-environment detection, the input security pipeline
(PII scrubbing, secrets detection, blocking, audit-violation logging),
and the post-interaction audit log write. Uses real PIIScrubber,
SecretsDetector, and AuditLogger collaborators (writing to a tmp_path
audit log) so the guard behavior is tested as the security feature it
is, not mocked away.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from attune.llm.security import SecurityMixin
from attune.memory import AuditLogger, PIIScrubber, SecretsDetector, SecurityError

# All environment variables _detect_production_environment inspects.
# Cleared in every test so a developer's or CI's real environment
# can't leak a false positive/negative into the assertions.
_PRODUCTION_ENV_VARS = [
    "NODE_ENV",
    "ENVIRONMENT",
    "FLASK_ENV",
    "DJANGO_ENV",
    "RAILWAY_ENVIRONMENT",
    "VERCEL_ENV",
    "AWS_EXECUTION_ENV",
    "KUBERNETES_SERVICE_HOST",
    "DYNO",
    "RENDER_SERVICE_ID",
    "FLY_APP_NAME",
]


@pytest.fixture(autouse=True)
def _clean_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no ambient production indicator pollutes these tests."""
    for var in _PRODUCTION_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


class _Host(SecurityMixin):
    """Minimal concrete host exercising the SecurityMixin contract."""

    def __init__(
        self,
        *,
        enable_security: bool = True,
        security_config: dict[str, Any] | None = None,
        pii_scrubber: PIIScrubber | None = None,
        secrets_detector: SecretsDetector | None = None,
        audit_logger: AuditLogger | None = None,
        provider: Any = None,
        cached_memory: Any = None,
    ) -> None:
        self.enable_security = enable_security
        self.security_config = security_config if security_config is not None else {}
        self.pii_scrubber = pii_scrubber
        self.secrets_detector = secrets_detector
        self.audit_logger = audit_logger
        self.provider = provider or SimpleNamespace(
            __class__=SimpleNamespace(__name__="AnthropicProvider")
        )
        if cached_memory is not None:
            self._cached_memory = cached_memory


def _read_last_event(log_path) -> dict[str, Any]:
    lines = log_path.read_text().strip().splitlines()
    assert lines, "expected at least one audit event written"
    return json.loads(lines[-1])


@pytest.mark.unit
class TestDetectProductionEnvironment:
    """_detect_production_environment: tuple-valued, scalar, and platform indicators."""

    def test_tuple_indicator_production_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ENVIRONMENT=production matches the (production, prod) tuple branch."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        host = _Host()
        assert host._detect_production_environment() is True

    def test_tuple_indicator_prod_alias(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ENVIRONMENT=prod is the tuple's second accepted value."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        host = _Host()
        assert host._detect_production_environment() is True

    def test_tuple_indicator_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Values are lower()-ed before comparison."""
        monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
        host = _Host()
        assert host._detect_production_environment() is True

    def test_scalar_indicator_matches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NODE_ENV=production hits the scalar-equality elif branch."""
        monkeypatch.setenv("NODE_ENV", "production")
        host = _Host()
        assert host._detect_production_environment() is True

    def test_scalar_indicator_wrong_value_no_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A non-production value for a scalar var must not false-positive."""
        monkeypatch.setenv("NODE_ENV", "staging")
        host = _Host()
        assert host._detect_production_environment() is False

    def test_platform_indicator_presence_implies_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Heroku's DYNO var is a presence-only platform indicator."""
        monkeypatch.setenv("DYNO", "web.1")
        host = _Host()
        assert host._detect_production_environment() is True

    def test_no_indicators_returns_false(self) -> None:
        """Baseline: nothing set anywhere means not production."""
        host = _Host()
        assert host._detect_production_environment() is False


@pytest.mark.unit
class TestRunSecurityInputPipeline:
    """_run_security_input_pipeline: PII scrub, secrets detect, block, audit."""

    def test_security_disabled_passes_input_through_unchanged(self) -> None:
        """When enable_security is False, the pipeline is a no-op."""
        host = _Host(
            enable_security=False,
            pii_scrubber=PIIScrubber(),
            secrets_detector=SecretsDetector(),
        )
        raw = "contact me at test@example.com"
        sanitized, pii, secrets, meta = host._run_security_input_pipeline("user-1", raw)
        assert sanitized == raw
        assert pii == []
        assert secrets == []
        assert meta == {}

    def test_pii_scrubbed_and_recorded_in_metadata(self) -> None:
        """A real email address is detected and scrubbed by PIIScrubber."""
        host = _Host(
            enable_security=True,
            pii_scrubber=PIIScrubber(),
            secrets_detector=None,
        )
        sanitized, pii, _secrets, meta = host._run_security_input_pipeline(
            "user-1",
            "reach me at jane.doe@example.com please",
        )
        assert "jane.doe@example.com" not in sanitized
        assert len(pii) >= 1
        assert meta["pii_detected"] == len(pii)
        assert meta["pii_scrubbed"] is True

    def test_secret_detected_blocks_by_default_and_logs_violation(self, tmp_path) -> None:
        """A live-looking secret is blocked (default) and audit-logged as HIGH."""
        audit_logger = AuditLogger(log_dir=str(tmp_path))
        host = _Host(
            enable_security=True,
            secrets_detector=SecretsDetector(),
            audit_logger=audit_logger,
            security_config={},  # block_on_secrets defaults to True
        )
        malicious_input = (
            "api_key = 'zzz_not_a_real_secret_padding_chars_1234567890'"  # pragma: allowlist secret
        )

        with pytest.raises(SecurityError, match="secret"):
            host._run_security_input_pipeline("user-1", malicious_input)

        event = _read_last_event(audit_logger.log_path)
        assert event["event_type"] == "security_violation"
        assert event["violation"]["type"] == "secrets_detected"
        assert event["violation"]["severity"] == "HIGH"
        assert event["violation"]["blocked"] is True

    def test_secret_detected_not_blocked_when_configured_off(self, tmp_path) -> None:
        """block_on_secrets=False still detects+logs but does not raise."""
        audit_logger = AuditLogger(log_dir=str(tmp_path))
        host = _Host(
            enable_security=True,
            secrets_detector=SecretsDetector(),
            audit_logger=audit_logger,
            security_config={"block_on_secrets": False},
        )
        malicious_input = (
            "api_key = 'zzz_not_a_real_secret_padding_chars_1234567890'"  # pragma: allowlist secret
        )

        sanitized, _pii, secrets, meta = host._run_security_input_pipeline(
            "user-1", malicious_input
        )

        assert sanitized == malicious_input
        assert len(secrets) >= 1
        assert meta["secrets_detected"] == len(secrets)

        event = _read_last_event(audit_logger.log_path)
        assert event["violation"]["blocked"] is False

    def test_secret_detected_without_audit_logger_still_blocks(self) -> None:
        """No audit_logger configured must not prevent the raise (guard is optional)."""
        host = _Host(
            enable_security=True,
            secrets_detector=SecretsDetector(),
            audit_logger=None,
        )
        malicious_input = (
            "api_key = 'zzz_not_a_real_secret_padding_chars_1234567890'"  # pragma: allowlist secret
        )

        with pytest.raises(SecurityError):
            host._run_security_input_pipeline("user-1", malicious_input)

    def test_clean_input_produces_no_detections(self) -> None:
        """Benign input passes through with empty detection lists."""
        host = _Host(
            enable_security=True,
            pii_scrubber=PIIScrubber(),
            secrets_detector=SecretsDetector(),
        )
        sanitized, pii, secrets, meta = host._run_security_input_pipeline(
            "user-1",
            "what's a good recipe for banana bread?",
        )
        assert sanitized == "what's a good recipe for banana bread?"
        assert pii == []
        assert secrets == []
        assert meta.get("secrets_detected", 0) == 0


@pytest.mark.unit
class TestRunSecurityAuditLog:
    """_run_security_audit_log: post-interaction audit write, memory source tagging."""

    def test_noop_when_security_disabled(self, tmp_path) -> None:
        """Guard clause: disabled security means no audit event is written."""
        audit_logger = AuditLogger(log_dir=str(tmp_path))
        host = _Host(enable_security=False, audit_logger=audit_logger)

        host._run_security_audit_log(
            user_id="user-1",
            user_input="hello",
            result={"content": "hi there", "metadata": {"model": "test-model"}},
            level=2,
            pii_detections=[],
            secrets_detections=[],
            start_time=0.0,
        )

        assert not audit_logger.log_path.exists()

    def test_noop_when_no_audit_logger(self) -> None:
        """Guard clause: no audit_logger configured means nothing to write to."""
        host = _Host(enable_security=True, audit_logger=None)

        # Must not raise even though there's no logger to call.
        host._run_security_audit_log(
            user_id="user-1",
            user_input="hello",
            result={"content": "hi there", "metadata": {"model": "test-model"}},
            level=2,
            pii_detections=[],
            secrets_detections=[],
            start_time=0.0,
        )

    def test_cached_memory_present_tags_claude_memory_source(self, tmp_path) -> None:
        """A truthy _cached_memory attribute adds 'claude_memory' to memory_sources."""
        audit_logger = AuditLogger(log_dir=str(tmp_path))
        host = _Host(
            enable_security=True,
            audit_logger=audit_logger,
            cached_memory={"some": "cached-context"},
        )

        host._run_security_audit_log(
            user_id="user-1",
            user_input="hello",
            result={"content": "hi there", "metadata": {"model": "test-model"}},
            level=2,
            pii_detections=[],
            secrets_detections=[],
            start_time=0.0,
        )

        event = _read_last_event(audit_logger.log_path)
        assert event["memory"]["sources"] == ["claude_memory"]

    def test_no_cached_memory_yields_empty_memory_sources(self, tmp_path) -> None:
        """Without _cached_memory set at all, memory_sources stays empty."""
        audit_logger = AuditLogger(log_dir=str(tmp_path))
        host = _Host(enable_security=True, audit_logger=audit_logger)

        host._run_security_audit_log(
            user_id="user-1",
            user_input="hello",
            result={"content": "hi there", "metadata": {"model": "test-model"}},
            level=2,
            pii_detections=[],
            secrets_detections=[],
            start_time=0.0,
        )

        event = _read_last_event(audit_logger.log_path)
        assert event["memory"]["sources"] == []

    def test_falsy_cached_memory_does_not_tag_source(self, tmp_path) -> None:
        """An explicitly falsy (e.g. empty dict) _cached_memory must not tag the source."""
        audit_logger = AuditLogger(log_dir=str(tmp_path))
        host = _Host(
            enable_security=True,
            audit_logger=audit_logger,
            cached_memory={},
        )

        host._run_security_audit_log(
            user_id="user-1",
            user_input="hello",
            result={"content": "hi there", "metadata": {"model": "test-model"}},
            level=2,
            pii_detections=[],
            secrets_detections=[],
            start_time=0.0,
        )

        event = _read_last_event(audit_logger.log_path)
        assert event["memory"]["sources"] == []
