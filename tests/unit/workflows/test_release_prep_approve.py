"""Tests for release_prep_approve module — ReleasePrepApproveMixin._approve."""

from __future__ import annotations

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.release_prep_approve import (
    RELEASE_PREP_STEPS,
    ReleasePrepApproveMixin,
)

# ---------------------------------------------------------------------------
# RELEASE_PREP_STEPS config
# ---------------------------------------------------------------------------


class TestStepConfig:
    """Validate the RELEASE_PREP_STEPS configuration dict."""

    def test_approve_step_exists(self):
        assert "approve" in RELEASE_PREP_STEPS

    def test_approve_step_fields(self):
        step = RELEASE_PREP_STEPS["approve"]
        assert step.name == "approve"
        assert step.task_type == "final_review"
        assert step.tier_hint == "premium"
        assert step.max_tokens == 2000


# ---------------------------------------------------------------------------
# Host stub for the mixin
# ---------------------------------------------------------------------------


class _FakeHost(ReleasePrepApproveMixin):
    """Minimal host class satisfying the mixin's expected attributes."""

    def __init__(
        self,
        *,
        has_blockers=False,
        auth_mode_used=None,
        executor=None,
        api_key=None,
        xml_enabled=False,
        xml_response=None,
        llm_response="Looks good to release.",
    ):
        self._has_blockers = has_blockers
        self._auth_mode_used = auth_mode_used
        self._executor = executor
        self._api_key = api_key
        self._xml_enabled = xml_enabled
        self._xml_response = xml_response or {}
        self._llm_response = llm_response

    def _is_xml_enabled(self):
        return self._xml_enabled

    def _render_xml_prompt(self, **kwargs):
        return "XML prompt rendered"

    def _parse_xml_response(self, response):
        return self._xml_response

    async def _call_llm(self, tier, system, user_message, max_tokens=2000):
        return (self._llm_response, 100, 50)

    async def run_step_with_executor(self, step, prompt, system):
        return (self._llm_response, 100, 50, 0.01)


# ---------------------------------------------------------------------------
# Blocker detection
# ---------------------------------------------------------------------------


class TestBlockerDetection:
    """Blockers should cause approved=False."""

    @pytest.mark.asyncio
    async def test_no_blockers_means_approved(self):
        host = _FakeHost()
        input_data = {
            "health": {
                "passed": True,
                "health_score": 90,
                "checks": {"tests": {"test_count": 100}},
            },
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 10, "by_category": {}},
            "path": ".",
        }
        result, inp_tok, out_tok = await host._approve(input_data, ModelTier.PREMIUM)
        assert result["approved"] is True
        assert result["confidence"] == "high"
        assert result["recommendation"] == "Ready for release"

    @pytest.mark.asyncio
    async def test_failed_health_check_creates_blocker(self):
        host = _FakeHost()
        input_data = {
            "health": {
                "passed": False,
                "failed_checks": ["lint", "types"],
                "health_score": 30,
                "checks": {},
            },
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 5, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert result["approved"] is False
        assert len(result["blockers"]) == 2
        assert "lint" in result["blockers"][0]

    @pytest.mark.asyncio
    async def test_security_issues_create_blocker(self):
        host = _FakeHost()
        input_data = {
            "health": {"passed": True, "health_score": 80, "checks": {}},
            "security": {"passed": False, "high_severity": 3, "medium_severity": 1},
            "changelog": {"total_commits": 5, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert result["approved"] is False
        assert any("Security" in b for b in result["blockers"])

    @pytest.mark.asyncio
    async def test_zero_commits_creates_blocker(self):
        host = _FakeHost()
        input_data = {
            "health": {"passed": True, "health_score": 100, "checks": {}},
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 0, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert result["approved"] is False
        assert any("commits" in b.lower() for b in result["blockers"])


# ---------------------------------------------------------------------------
# Warning detection
# ---------------------------------------------------------------------------


class TestWarnings:
    """Warnings affect confidence but not approval."""

    @pytest.mark.asyncio
    async def test_medium_security_generates_warning(self):
        host = _FakeHost()
        input_data = {
            "health": {"passed": True, "health_score": 90, "checks": {}},
            "security": {"passed": True, "high_severity": 0, "medium_severity": 2},
            "changelog": {"total_commits": 10, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert result["approved"] is True
        assert result["confidence"] == "medium"
        assert len(result["warnings"]) >= 1

    @pytest.mark.asyncio
    async def test_low_test_count_generates_warning(self):
        host = _FakeHost()
        input_data = {
            "health": {"passed": True, "health_score": 50, "checks": {"tests": {"test_count": 3}}},
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 10, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert any("test count" in w.lower() for w in result["warnings"])


# ---------------------------------------------------------------------------
# Confidence levels
# ---------------------------------------------------------------------------


class TestConfidence:
    """Confidence levels based on blockers/warnings."""

    @pytest.mark.asyncio
    async def test_high_confidence_no_blockers_no_warnings(self):
        host = _FakeHost()
        input_data = {
            "health": {
                "passed": True,
                "health_score": 100,
                "checks": {"tests": {"test_count": 100}},
            },
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 50, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert result["confidence"] == "high"

    @pytest.mark.asyncio
    async def test_low_confidence_with_blockers(self):
        host = _FakeHost()
        input_data = {
            "health": {"passed": False, "failed_checks": ["x"], "health_score": 20, "checks": {}},
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 5, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert result["confidence"] == "low"


# ---------------------------------------------------------------------------
# XML prompt path
# ---------------------------------------------------------------------------


class TestXMLPath:
    """XML-enhanced prompt path."""

    @pytest.mark.asyncio
    async def test_xml_parsed_data_merged_into_result(self):
        host = _FakeHost(
            xml_enabled=True,
            xml_response={
                "xml_parsed": True,
                "summary": "All good",
                "findings": ["f1"],
                "checklist": ["c1"],
            },
        )
        input_data = {
            "health": {"passed": True, "health_score": 90, "checks": {}},
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 10, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert result["xml_parsed"] is True
        assert result["summary"] == "All good"


# ---------------------------------------------------------------------------
# Auth mode telemetry
# ---------------------------------------------------------------------------


class TestAuthMode:
    """Auth mode propagated to result."""

    @pytest.mark.asyncio
    async def test_auth_mode_included_when_set(self):
        host = _FakeHost(auth_mode_used="subscription")
        input_data = {
            "health": {"passed": True, "health_score": 90, "checks": {}},
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 10, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert result["auth_mode_used"] == "subscription"

    @pytest.mark.asyncio
    async def test_auth_mode_absent_when_none(self):
        host = _FakeHost(auth_mode_used=None)
        input_data = {
            "health": {"passed": True, "health_score": 90, "checks": {}},
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 10, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert "auth_mode_used" not in result


# ---------------------------------------------------------------------------
# Executor fallback
# ---------------------------------------------------------------------------


class TestExecutorFallback:
    """Executor failure falls back to _call_llm."""

    @pytest.mark.asyncio
    async def test_falls_back_on_executor_error(self):
        host = _FakeHost(api_key="test-key")

        # Make executor raise
        async def _broken_executor(**kwargs):
            raise RuntimeError("executor down")

        host.run_step_with_executor = _broken_executor
        input_data = {
            "health": {"passed": True, "health_score": 90, "checks": {}},
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 10, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        # Should still succeed via _call_llm fallback
        assert result["approved"] is True
        assert result["assessment"] == "Looks good to release."


# ---------------------------------------------------------------------------
# Formatted report included
# ---------------------------------------------------------------------------


class TestFormattedReport:
    """Result contains a formatted_report key."""

    @pytest.mark.asyncio
    async def test_formatted_report_present(self):
        host = _FakeHost()
        input_data = {
            "health": {"passed": True, "health_score": 90, "checks": {}},
            "security": {"passed": True, "high_severity": 0, "medium_severity": 0},
            "changelog": {"total_commits": 10, "by_category": {}},
            "path": ".",
        }
        result, _, _ = await host._approve(input_data, ModelTier.PREMIUM)
        assert "formatted_report" in result
        assert "RELEASE PREPARATION REPORT" in result["formatted_report"]
