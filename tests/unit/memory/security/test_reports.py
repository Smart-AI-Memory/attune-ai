"""Tests for `attune.memory.security.reports.AuditReportMixin`.

Strategy: real `AuditLogger` instances against a `tmp_path` log
file. The mixin composes via `AuditLogger` which mixes in both
`AuditQueryMixin` (for self.query()) and `AuditReportMixin`.

Covers:
- AuditReportMixin.get_violation_summary — empty log, single
  user, multiple users, multi-severity, missing nested fields.
- AuditReportMixin.get_compliance_report — period bounds,
  every event_type branch (llm_request, store_pattern,
  retrieve_pattern, security_violation), compliance metric
  ratios, divide-by-zero guard on empty period.
- Module-level helpers _process_llm_request,
  _process_store_pattern, _process_retrieve_pattern,
  _process_security_violation — direct calls so we can exercise
  optional/missing fields without staging full event scenarios.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from attune.memory.security.audit_logger import AuditLogger
from attune.memory.security.reports import (
    _process_llm_request,
    _process_retrieve_pattern,
    _process_security_violation,
    _process_store_pattern,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def logger(tmp_path: Path) -> AuditLogger:
    return AuditLogger(
        log_dir=str(tmp_path),
        log_filename="audit.jsonl",
        enable_rotation=False,
    )


def _write_events(logger: AuditLogger, events: list[dict[str, Any]]) -> None:
    logger.log_path.parent.mkdir(parents=True, exist_ok=True)
    with logger.log_path.open("a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def _empty_report() -> dict[str, Any]:
    """Fresh report skeleton matching what get_compliance_report builds.

    Used by the _process_* helper tests so we can exercise one
    helper in isolation without going through the full report
    pipeline.
    """
    return {
        "llm_requests": {
            "total": 0,
            "with_pii_detected": 0,
            "with_secrets_detected": 0,
            "sanitization_applied": 0,
        },
        "pattern_storage": {
            "total": 0,
            "by_classification": {"PUBLIC": 0, "INTERNAL": 0, "SENSITIVE": 0},
            "with_pii_scrubbed": 0,
            "encrypted": 0,
        },
        "pattern_retrieval": {
            "total": 0,
            "by_classification": {"PUBLIC": 0, "INTERNAL": 0, "SENSITIVE": 0},
            "access_denied": 0,
        },
        "security_violations": {"total": 0, "by_severity": {}, "by_type": {}},
    }


# ---------------------------------------------------------------------------
# get_violation_summary
# ---------------------------------------------------------------------------


class TestGetViolationSummary:
    def test_empty_log_returns_zero_summary(self, logger: AuditLogger) -> None:
        summary = logger.get_violation_summary()
        assert summary == {
            "total_violations": 0,
            "by_type": {},
            "by_severity": {},
            "by_user": {},
        }

    def test_single_violation(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "security_violation",
                    "user_id": "alice",
                    "violation": {"type": "pii_leak", "severity": "high"},
                },
            ],
        )
        summary = logger.get_violation_summary()
        assert summary["total_violations"] == 1
        assert summary["by_type"] == {"pii_leak": 1}
        assert summary["by_severity"] == {"high": 1}
        assert summary["by_user"] == {"alice": 1}

    def test_multiple_violations_aggregated(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "security_violation",
                    "user_id": "alice",
                    "violation": {"type": "pii_leak", "severity": "high"},
                },
                {
                    "event_type": "security_violation",
                    "user_id": "alice",
                    "violation": {"type": "pii_leak", "severity": "medium"},
                },
                {
                    "event_type": "security_violation",
                    "user_id": "bob",
                    "violation": {"type": "secrets", "severity": "high"},
                },
            ],
        )
        summary = logger.get_violation_summary()
        assert summary["total_violations"] == 3
        assert summary["by_type"] == {"pii_leak": 2, "secrets": 1}
        assert summary["by_severity"] == {"high": 2, "medium": 1}
        assert summary["by_user"] == {"alice": 2, "bob": 1}

    def test_filter_by_user_id(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "security_violation",
                    "user_id": "alice",
                    "violation": {"type": "pii_leak", "severity": "high"},
                },
                {
                    "event_type": "security_violation",
                    "user_id": "bob",
                    "violation": {"type": "secrets", "severity": "high"},
                },
            ],
        )
        summary = logger.get_violation_summary(user_id="alice")
        assert summary["total_violations"] == 1
        assert summary["by_user"] == {"alice": 1}

    def test_non_violation_events_ignored(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {"event_type": "llm_request", "user_id": "alice"},
                {"event_type": "store_pattern", "user_id": "alice"},
                {
                    "event_type": "security_violation",
                    "user_id": "alice",
                    "violation": {"type": "x", "severity": "low"},
                },
            ],
        )
        summary = logger.get_violation_summary()
        assert summary["total_violations"] == 1

    def test_missing_violation_subfields_default_to_unknown(self, logger: AuditLogger) -> None:
        # Violation event with no `violation` sub-dict at all.
        # The defensive `.get("violation", {}).get("type", "unknown")`
        # path coerces missing fields to "unknown" rather than crashing.
        _write_events(
            logger,
            [
                {"event_type": "security_violation", "user_id": "alice"},
            ],
        )
        summary = logger.get_violation_summary()
        assert summary["total_violations"] == 1
        assert summary["by_type"] == {"unknown": 1}
        assert summary["by_severity"] == {"unknown": 1}

    def test_non_string_violation_fields_coerced(self, logger: AuditLogger) -> None:
        # `str(violation.get("violation", {}).get("type", "unknown"))`
        # coerces any non-string value. Important because audit logs
        # are JSON and could contain integer "type" codes.
        _write_events(
            logger,
            [
                {
                    "event_type": "security_violation",
                    "user_id": "alice",
                    "violation": {"type": 42, "severity": 1},
                },
            ],
        )
        summary = logger.get_violation_summary()
        assert "42" in summary["by_type"]
        assert "1" in summary["by_severity"]


# ---------------------------------------------------------------------------
# get_compliance_report — period bounds and structure
# ---------------------------------------------------------------------------


class TestComplianceReportStructure:
    def test_empty_log_returns_zeroed_report(self, logger: AuditLogger) -> None:
        report = logger.get_compliance_report()
        assert report["period"] == {"start": "all_time", "end": "now"}
        assert report["llm_requests"]["total"] == 0
        assert report["pattern_storage"]["total"] == 0
        assert report["pattern_retrieval"]["total"] == 0
        assert report["security_violations"]["total"] == 0
        # Divide-by-zero guard: rates stay 0.0 when no compliance
        # events occurred in the period.
        assert report["compliance_metrics"]["gdpr_compliant_rate"] == 0.0
        assert report["compliance_metrics"]["hipaa_compliant_rate"] == 0.0
        assert report["compliance_metrics"]["soc2_compliant_rate"] == 0.0

    def test_period_uses_explicit_dates_when_given(self, logger: AuditLogger) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 6, 30, tzinfo=timezone.utc)
        report = logger.get_compliance_report(start_date=start, end_date=end)
        assert report["period"]["start"] == start.isoformat()
        assert report["period"]["end"] == end.isoformat()


# ---------------------------------------------------------------------------
# get_compliance_report — each event_type branch
# ---------------------------------------------------------------------------


class TestComplianceReportEventBranches:
    def test_llm_request_counters(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "llm_request",
                    "security": {
                        "pii_detected": 2,
                        "secrets_detected": 0,
                        "sanitization_applied": True,
                    },
                },
                {
                    "event_type": "llm_request",
                    "security": {
                        "pii_detected": 0,
                        "secrets_detected": 1,
                        "sanitization_applied": False,
                    },
                },
            ],
        )
        report = logger.get_compliance_report()
        assert report["llm_requests"]["total"] == 2
        assert report["llm_requests"]["with_pii_detected"] == 1
        assert report["llm_requests"]["with_secrets_detected"] == 1
        assert report["llm_requests"]["sanitization_applied"] == 1

    def test_store_pattern_counters(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "store_pattern",
                    "pattern": {"classification": "SENSITIVE", "encrypted": True},
                    "security": {"pii_scrubbed": 3},
                },
                {
                    "event_type": "store_pattern",
                    "pattern": {"classification": "PUBLIC", "encrypted": False},
                    "security": {"pii_scrubbed": 0},
                },
            ],
        )
        report = logger.get_compliance_report()
        assert report["pattern_storage"]["total"] == 2
        assert report["pattern_storage"]["by_classification"]["SENSITIVE"] == 1
        assert report["pattern_storage"]["by_classification"]["PUBLIC"] == 1
        assert report["pattern_storage"]["with_pii_scrubbed"] == 1
        assert report["pattern_storage"]["encrypted"] == 1

    def test_retrieve_pattern_counters(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "retrieve_pattern",
                    "pattern": {"classification": "INTERNAL"},
                    "access": {"granted": True},
                },
                {
                    "event_type": "retrieve_pattern",
                    "pattern": {"classification": "SENSITIVE"},
                    "access": {"granted": False},
                },
            ],
        )
        report = logger.get_compliance_report()
        assert report["pattern_retrieval"]["total"] == 2
        assert report["pattern_retrieval"]["by_classification"]["INTERNAL"] == 1
        assert report["pattern_retrieval"]["by_classification"]["SENSITIVE"] == 1
        assert report["pattern_retrieval"]["access_denied"] == 1

    def test_retrieve_pattern_access_granted_default_true(self, logger: AuditLogger) -> None:
        # When `access.granted` is missing, the helper defaults to
        # True (not denying access just because the field is
        # absent). This is an intentional defensive default.
        _write_events(
            logger,
            [
                {"event_type": "retrieve_pattern", "pattern": {}},
            ],
        )
        report = logger.get_compliance_report()
        assert report["pattern_retrieval"]["access_denied"] == 0

    def test_security_violation_counters(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "security_violation",
                    "violation": {"type": "pii_leak", "severity": "high"},
                },
                {
                    "event_type": "security_violation",
                    "violation": {"type": "pii_leak", "severity": "medium"},
                },
            ],
        )
        report = logger.get_compliance_report()
        assert report["security_violations"]["total"] == 2
        assert report["security_violations"]["by_type"]["pii_leak"] == 2
        assert report["security_violations"]["by_severity"]["high"] == 1
        assert report["security_violations"]["by_severity"]["medium"] == 1

    def test_unknown_classification_extends_dict(self, logger: AuditLogger) -> None:
        # Classifications outside the pre-seeded {PUBLIC, INTERNAL,
        # SENSITIVE} should be added dynamically.
        _write_events(
            logger,
            [
                {
                    "event_type": "store_pattern",
                    "pattern": {"classification": "CONFIDENTIAL", "encrypted": False},
                    "security": {"pii_scrubbed": 0},
                },
            ],
        )
        report = logger.get_compliance_report()
        assert report["pattern_storage"]["by_classification"]["CONFIDENTIAL"] == 1

    def test_missing_classification_defaults_to_INTERNAL(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "store_pattern",
                    "pattern": {"encrypted": False},
                    "security": {"pii_scrubbed": 0},
                },
            ],
        )
        report = logger.get_compliance_report()
        assert report["pattern_storage"]["by_classification"]["INTERNAL"] == 1

    def test_unknown_event_type_ignored(self, logger: AuditLogger) -> None:
        # Events with event_type not in the dispatch (llm_request,
        # store_pattern, retrieve_pattern, security_violation) are
        # silently skipped; only compliance fields still contribute
        # to the rate calculation if present.
        _write_events(
            logger,
            [
                {"event_type": "future_event_type"},
                {"event_type": "another_unknown"},
            ],
        )
        report = logger.get_compliance_report()
        assert report["llm_requests"]["total"] == 0
        assert report["pattern_storage"]["total"] == 0
        assert report["pattern_retrieval"]["total"] == 0
        assert report["security_violations"]["total"] == 0


# ---------------------------------------------------------------------------
# get_compliance_report — compliance metric rates
# ---------------------------------------------------------------------------


class TestComplianceMetrics:
    def test_all_compliant_rates_are_1(self, logger: AuditLogger) -> None:
        _write_events(
            logger,
            [
                {
                    "event_type": "llm_request",
                    "security": {},
                    "compliance": {
                        "gdpr_compliant": True,
                        "hipaa_compliant": True,
                        "soc2_compliant": True,
                    },
                },
                {
                    "event_type": "llm_request",
                    "security": {},
                    "compliance": {
                        "gdpr_compliant": True,
                        "hipaa_compliant": True,
                        "soc2_compliant": True,
                    },
                },
            ],
        )
        report = logger.get_compliance_report()
        assert report["compliance_metrics"]["gdpr_compliant_rate"] == 1.0
        assert report["compliance_metrics"]["hipaa_compliant_rate"] == 1.0
        assert report["compliance_metrics"]["soc2_compliant_rate"] == 1.0

    def test_partial_compliance_rate(self, logger: AuditLogger) -> None:
        # 2 of 4 GDPR-compliant → 0.5
        _write_events(
            logger,
            [
                {
                    "event_type": "llm_request",
                    "security": {},
                    "compliance": {"gdpr_compliant": True},
                },
                {
                    "event_type": "llm_request",
                    "security": {},
                    "compliance": {"gdpr_compliant": True},
                },
                {
                    "event_type": "llm_request",
                    "security": {},
                    "compliance": {"gdpr_compliant": False},
                },
                {
                    "event_type": "llm_request",
                    "security": {},
                    "compliance": {"gdpr_compliant": False},
                },
            ],
        )
        report = logger.get_compliance_report()
        assert report["compliance_metrics"]["gdpr_compliant_rate"] == 0.5

    def test_events_without_compliance_field_dont_count(self, logger: AuditLogger) -> None:
        # Only events with a non-empty `compliance` dict contribute
        # to total_compliance_checks; the rates therefore reflect
        # actual compliance-tagged events, not all events.
        _write_events(
            logger,
            [
                {
                    "event_type": "llm_request",
                    "security": {},
                    "compliance": {"gdpr_compliant": True},
                },
                {"event_type": "llm_request", "security": {}},
            ],
        )
        report = logger.get_compliance_report()
        assert report["compliance_metrics"]["gdpr_compliant_rate"] == 1.0


# ---------------------------------------------------------------------------
# Module-level _process_* helpers
# ---------------------------------------------------------------------------


class TestProcessHelpers:
    def test_process_llm_request_no_security_dict(self) -> None:
        # Event has no `security` field at all — counters stay at
        # their initial value except `total`.
        report = _empty_report()
        _process_llm_request(report, {"event_type": "llm_request"})
        assert report["llm_requests"]["total"] == 1
        assert report["llm_requests"]["with_pii_detected"] == 0
        assert report["llm_requests"]["with_secrets_detected"] == 0
        assert report["llm_requests"]["sanitization_applied"] == 0

    def test_process_llm_request_with_zero_pii_count(self) -> None:
        # `pii_detected: 0` must NOT increment the counter — the
        # check is `> 0`, not truthy.
        report = _empty_report()
        _process_llm_request(
            report,
            {
                "event_type": "llm_request",
                "security": {"pii_detected": 0, "secrets_detected": 0},
            },
        )
        assert report["llm_requests"]["with_pii_detected"] == 0
        assert report["llm_requests"]["with_secrets_detected"] == 0

    def test_process_store_pattern_no_classification(self) -> None:
        # Missing classification defaults to "INTERNAL" via .get().
        report = _empty_report()
        _process_store_pattern(
            report,
            {"event_type": "store_pattern", "pattern": {}},
        )
        assert report["pattern_storage"]["by_classification"]["INTERNAL"] == 1

    def test_process_retrieve_pattern_no_access_field(self) -> None:
        # Missing `access` defaults to {}, and `.get("granted", True)`
        # defaults to True → access NOT denied → counter unchanged.
        report = _empty_report()
        _process_retrieve_pattern(
            report,
            {"event_type": "retrieve_pattern", "pattern": {}},
        )
        assert report["pattern_retrieval"]["access_denied"] == 0
        assert report["pattern_retrieval"]["total"] == 1

    def test_process_security_violation_missing_subfields(self) -> None:
        report = _empty_report()
        _process_security_violation(
            report,
            {"event_type": "security_violation"},
        )
        assert report["security_violations"]["total"] == 1
        assert report["security_violations"]["by_type"]["unknown"] == 1
        assert report["security_violations"]["by_severity"]["unknown"] == 1
