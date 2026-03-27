"""Unit tests for attune.workflows.code_review_scan module.

Tests cover:
- ScanMixin._scan: LLM-based security scanning, finding extraction
- ScanMixin._merge_external_audit: merging SecurityAuditCrew results

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.code_review_scan import ScanMixin
from attune.workflows.compat import ModelTier


class _FakeHost(ScanMixin):
    """Minimal host providing attributes expected by the mixin."""

    def __init__(self) -> None:
        self._auth_mode_used: str | None = None

    async def _call_llm(self, tier, system, user_msg, max_tokens=2048) -> tuple[str, int, int]:
        """Mock LLM call returning no critical findings."""
        return "No significant issues found.", 100, 200

    def _extract_findings_from_response(
        self, response: str, files_changed: list, code_context: str
    ) -> list[dict]:
        """Mock finding extraction."""
        return []


@pytest.fixture
def host() -> _FakeHost:
    """Create a mixin host instance."""
    return _FakeHost()


# ---------------------------------------------------------------------------
# _scan stage
# ---------------------------------------------------------------------------


class TestScanStage:
    """Tests for ScanMixin._scan."""

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_scan.format_code_review_report",
        return_value="report text",
    )
    async def test_scan_no_issues(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test scan with no critical findings."""
        input_data = {
            "code_to_review": "def foo(): pass",
            "classification": "standard",
        }

        result, in_t, out_t = await host._scan(input_data, ModelTier.CAPABLE)

        assert result["has_critical_issues"] is False
        assert result["security_score"] == 90
        assert result["verdict"] == "approve"
        assert result["formatted_report"] == "report text"

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_scan.format_code_review_report",
        return_value="report",
    )
    async def test_scan_critical_issues(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test scan detects critical issues from LLM response."""
        host._call_llm = AsyncMock(
            return_value=("CRITICAL: SQL injection found in user_input", 100, 200)
        )

        result, _, _ = await host._scan(
            {"code_to_review": "bad code", "classification": "security"},
            ModelTier.CAPABLE,
        )

        assert result["has_critical_issues"] is True
        assert result["security_score"] == 70
        assert result["verdict"] == "request_changes"
        assert result["needs_architect_review"] is True

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_scan.format_code_review_report",
        return_value="report",
    )
    async def test_scan_with_external_audit(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test scan merges external audit results."""
        external_audit = {
            "summary": "Found 2 issues",
            "findings": [
                {
                    "severity": "high",
                    "title": "XSS Vulnerability",
                    "description": "Unescaped output",
                },
                {
                    "severity": "low",
                    "title": "Minor issue",
                    "description": "Style problem",
                },
            ],
            "risk_score": 45,
        }

        result, _, _ = await host._scan(
            {
                "code_to_review": "code here",
                "classification": "security",
                "external_audit_results": external_audit,
            },
            ModelTier.CAPABLE,
        )

        assert result["external_audit_included"] is True
        assert result["external_audit_risk_score"] == 45
        assert result["has_critical_issues"] is True  # high finding

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_scan.format_code_review_report",
        return_value="report",
    )
    async def test_scan_uses_diff_fallback(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test scan falls back to 'diff' key for code."""
        result, _, _ = await host._scan(
            {"diff": "diff content here", "classification": "review"},
            ModelTier.CAPABLE,
        )

        assert result["code_to_review"] == "diff content here"

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_scan.format_code_review_report",
        return_value="report",
    )
    async def test_scan_empty_findings_has_message(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test empty findings include a helpful message."""
        result, _, _ = await host._scan(
            {"code_to_review": "clean code", "classification": ""},
            ModelTier.CAPABLE,
        )

        assert "message" in result["summary"]
        assert result["summary"]["total_findings"] == 0

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.code_review_scan.format_code_review_report",
        return_value="report",
    )
    async def test_scan_tracks_model_tier(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that model tier is tracked in result."""
        result, _, _ = await host._scan(
            {"code_to_review": "code"},
            ModelTier.CAPABLE,
        )
        assert result["model_tier_used"] == ModelTier.CAPABLE.value


# ---------------------------------------------------------------------------
# _merge_external_audit
# ---------------------------------------------------------------------------


class TestMergeExternalAudit:
    """Tests for ScanMixin._merge_external_audit."""

    def test_merge_empty_audit(self, host: _FakeHost) -> None:
        """Test merge with empty external audit."""
        merged, findings, has_critical = host._merge_external_audit(
            "llm response",
            {"findings": [], "summary": "", "risk_score": 0},
        )

        assert "llm response" in merged
        assert findings == []
        assert has_critical is False

    def test_merge_critical_findings(self, host: _FakeHost) -> None:
        """Test merge detects critical findings."""
        external = {
            "findings": [
                {"severity": "critical", "title": "RCE", "description": "remote code exec"},
            ],
            "summary": "Critical vulnerability found",
            "risk_score": 95,
        }

        merged, findings, has_critical = host._merge_external_audit("base response", external)

        assert has_critical is True
        assert len(findings) == 1
        assert "Critical Findings" in merged

    def test_merge_high_findings(self, host: _FakeHost) -> None:
        """Test merge includes high severity findings section."""
        external = {
            "findings": [
                {
                    "severity": "high",
                    "title": "SQLi",
                    "description": "injection",
                    "file": "a.py",
                    "line": 10,
                },
            ],
            "summary": "High severity issue",
            "risk_score": 70,
        }

        merged, findings, has_critical = host._merge_external_audit("base", external)

        assert has_critical is True
        assert "High Severity" in merged

    def test_merge_includes_risk_score(self, host: _FakeHost) -> None:
        """Test that risk score appears in merged output."""
        external = {
            "findings": [],
            "summary": "All clear",
            "risk_score": 10,
        }

        merged, _, _ = host._merge_external_audit("base", external)

        assert "10/100" in merged

    def test_merge_with_remediation(self, host: _FakeHost) -> None:
        """Test that remediation text is included for critical findings."""
        external = {
            "findings": [
                {
                    "severity": "critical",
                    "title": "Vuln",
                    "description": "desc",
                    "remediation": "Fix by updating library",
                },
            ],
            "summary": "",
            "risk_score": 90,
        }

        merged, _, _ = host._merge_external_audit("base", external)

        assert "Fix by updating library" in merged
