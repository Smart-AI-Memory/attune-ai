"""Tests for release_models module.

Tests Tier enum values, ReleaseAgentResult dataclass defaults and
fields, QualityGate post-init message generation, ReleaseReadinessReport
to_dict serialization, and module-level constants.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Tier enum
# ---------------------------------------------------------------------------


class TestTierEnum:
    """Tests for the Tier enum."""

    def test_tier_cheap_value(self):
        """Tier.CHEAP has value 'cheap'."""
        from attune.agents.release.release_models import Tier

        assert Tier.CHEAP.value == "cheap"

    def test_tier_capable_value(self):
        """Tier.CAPABLE has value 'capable'."""
        from attune.agents.release.release_models import Tier

        assert Tier.CAPABLE.value == "capable"

    def test_tier_premium_value(self):
        """Tier.PREMIUM has value 'premium'."""
        from attune.agents.release.release_models import Tier

        assert Tier.PREMIUM.value == "premium"

    def test_tier_members_count(self):
        """Tier enum has exactly three members."""
        from attune.agents.release.release_models import Tier

        assert len(list(Tier)) == 3

    def test_tier_from_value_cheap(self):
        """Tier can be constructed from its value string."""
        from attune.agents.release.release_models import Tier

        assert Tier("cheap") is Tier.CHEAP

    def test_tier_from_value_premium(self):
        """Tier can be constructed from 'premium' string."""
        from attune.agents.release.release_models import Tier

        assert Tier("premium") is Tier.PREMIUM


# ---------------------------------------------------------------------------
# ReleaseAgentResult
# ---------------------------------------------------------------------------


class TestReleaseAgentResult:
    """Tests for the ReleaseAgentResult dataclass."""

    def test_required_fields_stored(self):
        """Required fields are stored correctly."""
        from attune.agents.release.release_models import ReleaseAgentResult, Tier

        result = ReleaseAgentResult(
            agent_id="test-agent-001",
            agent_role="Security Auditor",
            success=True,
            tier_used=Tier.CHEAP,
        )

        assert result.agent_id == "test-agent-001"
        assert result.agent_role == "Security Auditor"
        assert result.success is True
        assert result.tier_used is Tier.CHEAP

    def test_optional_fields_have_defaults(self):
        """Optional fields default to expected zero-values."""
        from attune.agents.release.release_models import ReleaseAgentResult, Tier

        result = ReleaseAgentResult(
            agent_id="a",
            agent_role="r",
            success=False,
            tier_used=Tier.CAPABLE,
        )

        assert result.findings == {}
        assert result.score == 0.0
        assert result.confidence == 0.0
        assert result.cost == 0.0
        assert result.execution_time_ms == 0.0
        assert result.escalated is False

    def test_findings_dict_not_shared_between_instances(self):
        """Each instance gets its own findings dict (no shared mutable default)."""
        from attune.agents.release.release_models import ReleaseAgentResult, Tier

        r1 = ReleaseAgentResult("a1", "role", True, Tier.CHEAP)
        r2 = ReleaseAgentResult("a2", "role", True, Tier.CHEAP)
        r1.findings["key"] = "value"

        assert "key" not in r2.findings

    def test_escalated_flag_can_be_set_true(self):
        """escalated field can be set to True."""
        from attune.agents.release.release_models import ReleaseAgentResult, Tier

        result = ReleaseAgentResult(
            agent_id="x",
            agent_role="y",
            success=True,
            tier_used=Tier.PREMIUM,
            escalated=True,
        )

        assert result.escalated is True

    def test_score_and_confidence_stored_correctly(self):
        """Score and confidence are stored as provided."""
        from attune.agents.release.release_models import ReleaseAgentResult, Tier

        result = ReleaseAgentResult(
            agent_id="x",
            agent_role="y",
            success=True,
            tier_used=Tier.CAPABLE,
            score=85.5,
            confidence=0.9,
            cost=0.0042,
        )

        assert result.score == pytest.approx(85.5)
        assert result.confidence == pytest.approx(0.9)
        assert result.cost == pytest.approx(0.0042)


# ---------------------------------------------------------------------------
# QualityGate
# ---------------------------------------------------------------------------


class TestQualityGate:
    """Tests for the QualityGate dataclass."""

    def test_message_auto_generated_on_pass(self):
        """Message is auto-generated with PASS when gate passes."""
        from attune.agents.release.release_models import QualityGate

        gate = QualityGate(name="Coverage", threshold=80.0, actual=85.0, passed=True)

        assert "PASS" in gate.message
        assert "Coverage" in gate.message

    def test_message_auto_generated_on_fail(self):
        """Message is auto-generated with FAIL when gate fails."""
        from attune.agents.release.release_models import QualityGate

        gate = QualityGate(name="Security", threshold=0.0, actual=3.0, passed=False)

        assert "FAIL" in gate.message
        assert "Security" in gate.message

    def test_custom_message_not_overwritten(self):
        """User-provided message is not replaced by __post_init__."""
        from attune.agents.release.release_models import QualityGate

        gate = QualityGate(
            name="X",
            threshold=0.0,
            actual=0.0,
            passed=True,
            message="Custom message here",
        )

        assert gate.message == "Custom message here"

    def test_critical_defaults_to_true(self):
        """critical field defaults to True."""
        from attune.agents.release.release_models import QualityGate

        gate = QualityGate(name="X", threshold=0.0)

        assert gate.critical is True

    def test_message_contains_threshold_and_actual(self):
        """Auto-generated message includes threshold and actual values."""
        from attune.agents.release.release_models import QualityGate

        gate = QualityGate(name="Coverage", threshold=80.0, actual=75.0, passed=False)

        assert "80.0" in gate.message
        assert "75.0" in gate.message


# ---------------------------------------------------------------------------
# ReleaseReadinessReport
# ---------------------------------------------------------------------------


class TestReleaseReadinessReport:
    """Tests for the ReleaseReadinessReport dataclass and to_dict."""

    def _make_report(self, approved=True, confidence="high"):
        from attune.agents.release.release_models import ReleaseReadinessReport

        return ReleaseReadinessReport(approved=approved, confidence=confidence)

    def test_approved_and_confidence_stored(self):
        """approved and confidence are stored as-is."""
        report = self._make_report(approved=False, confidence="low")

        assert report.approved is False
        assert report.confidence == "low"

    def test_default_lists_are_empty(self):
        """Default list fields are empty lists."""
        report = self._make_report()

        assert report.quality_gates == []
        assert report.agent_results == []
        assert report.blockers == []
        assert report.warnings == []

    def test_timestamp_is_iso_string(self):
        """timestamp field is a non-empty ISO 8601 string."""
        report = self._make_report()

        assert isinstance(report.timestamp, str)
        assert len(report.timestamp) > 0
        # Should be parseable as ISO format
        from datetime import datetime

        datetime.fromisoformat(report.timestamp)

    def test_to_dict_keys_present(self):
        """to_dict returns dict with all expected keys."""
        report = self._make_report(approved=True, confidence="medium")
        d = report.to_dict()

        expected_keys = {
            "approved",
            "confidence",
            "quality_gates",
            "agent_results",
            "blockers",
            "warnings",
            "summary",
            "timestamp",
            "total_duration",
            "total_cost",
        }
        assert expected_keys.issubset(d.keys())

    def test_to_dict_approved_value(self):
        """to_dict reflects approved=False correctly."""
        report = self._make_report(approved=False)
        d = report.to_dict()

        assert d["approved"] is False

    def test_to_dict_with_agent_result(self):
        """to_dict serializes agent_results keyed by role."""
        from attune.agents.release.release_models import (
            ReleaseAgentResult,
            ReleaseReadinessReport,
            Tier,
        )

        result = ReleaseAgentResult(
            agent_id="sec-001",
            agent_role="Security Auditor",
            success=True,
            tier_used=Tier.CHEAP,
            score=90.0,
            confidence=0.9,
        )
        report = ReleaseReadinessReport(
            approved=True,
            confidence="high",
            agent_results=[result],
        )
        d = report.to_dict()

        assert "Security Auditor" in d["agent_results"]
        agent_dict = d["agent_results"]["Security Auditor"]
        assert agent_dict["success"] is True
        assert agent_dict["score"] == pytest.approx(90.0)
        assert agent_dict["tier_used"] == "cheap"

    def test_to_dict_with_quality_gate(self):
        """to_dict serializes quality_gates as list of dicts."""
        from attune.agents.release.release_models import QualityGate, ReleaseReadinessReport

        gate = QualityGate(
            name="Coverage",
            threshold=80.0,
            actual=85.0,
            passed=True,
            critical=True,
        )
        report = ReleaseReadinessReport(
            approved=True,
            confidence="high",
            quality_gates=[gate],
        )
        d = report.to_dict()

        assert len(d["quality_gates"]) == 1
        gate_dict = d["quality_gates"][0]
        assert gate_dict["name"] == "Coverage"
        assert gate_dict["passed"] is True

    def test_format_console_output_approved(self):
        """format_console_output includes READY FOR RELEASE when approved."""
        report = self._make_report(approved=True, confidence="high")
        output = report.format_console_output()

        assert "READY FOR RELEASE" in output

    def test_format_console_output_not_approved(self):
        """format_console_output includes NOT READY when not approved."""
        report = self._make_report(approved=False, confidence="low")
        output = report.format_console_output()

        assert "NOT READY" in output


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """Tests for module-level configuration constants."""

    def test_anthropic_available_is_bool(self):
        """ANTHROPIC_AVAILABLE is a boolean."""
        from attune.agents.release.release_models import ANTHROPIC_AVAILABLE

        assert isinstance(ANTHROPIC_AVAILABLE, bool)

    def test_llm_mode_is_string(self):
        """LLM_MODE is a string."""
        from attune.agents.release.release_models import LLM_MODE

        assert isinstance(LLM_MODE, str)

    def test_llm_mode_default_is_simulated(self):
        """LLM_MODE defaults to 'simulated' when env var not set."""
        import os

        with patch.dict(os.environ, {}, clear=False):
            # Remove the env var if set, then reimport to check default
            env_backup = os.environ.pop("RELEASE_LLM_MODE", None)
            try:
                import importlib

                import attune.agents.release.release_models as mod

                importlib.reload(mod)
                # The default from os.getenv(..., "simulated")
                assert mod.LLM_MODE in ("simulated", "rule_based", "real")
            finally:
                if env_backup is not None:
                    os.environ["RELEASE_LLM_MODE"] = env_backup

    def test_model_config_has_all_tiers(self):
        """MODEL_CONFIG has keys for all three tiers."""
        from attune.agents.release.release_models import MODEL_CONFIG

        assert "cheap" in MODEL_CONFIG
        assert "capable" in MODEL_CONFIG
        assert "premium" in MODEL_CONFIG

    def test_model_config_uses_current_model_ids(self, monkeypatch):
        """MODEL_CONFIG uses non-deprecated model IDs.

        ``MODEL_CONFIG["premium"]`` resolves through ``attune.model_tiers``
        at IMPORT time (documented in release_models.py), so the autouse
        env scrub cannot reach it — the module may already be imported
        with a developer's ``ATTUNE_MODEL_PREMIUM`` baked in. Clear the
        tier overrides and reload, so this asserts the real DEFAULT
        rather than whatever the ambient shell happened to export.
        """
        import importlib

        import attune.agents.release.release_models as rm

        for var in ("ATTUNE_MODEL_PREMIUM", "ATTUNE_MODEL_CAPABLE", "ATTUNE_MODEL_CHEAP"):
            monkeypatch.delenv(var, raising=False)
        module = importlib.reload(rm)

        # Prevent regression to deprecated model IDs
        assert module.MODEL_CONFIG["cheap"] == "claude-haiku-4-5"
        assert module.MODEL_CONFIG["capable"] == "claude-sonnet-5"
        assert module.MODEL_CONFIG["premium"] == "claude-fable-5"

    def test_default_quality_gates_keys(self):
        """DEFAULT_QUALITY_GATES has expected keys."""
        from attune.agents.release.release_models import DEFAULT_QUALITY_GATES

        assert "max_critical_issues" in DEFAULT_QUALITY_GATES
        assert "min_coverage" in DEFAULT_QUALITY_GATES
        assert "min_quality_score" in DEFAULT_QUALITY_GATES
        assert "min_doc_coverage" in DEFAULT_QUALITY_GATES

    def test_default_quality_gates_min_coverage(self):
        """DEFAULT_QUALITY_GATES min_coverage is 80.0."""
        from attune.agents.release.release_models import DEFAULT_QUALITY_GATES

        assert DEFAULT_QUALITY_GATES["min_coverage"] == pytest.approx(80.0)
