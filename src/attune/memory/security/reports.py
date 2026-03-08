"""Audit Reporting and Compliance

Provides violation summaries and compliance reports for
SOC2, HIPAA, and GDPR audit periods.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any


class AuditReportMixin:
    """Mixin that adds reporting capabilities to AuditLogger.

    Requires the host class to have:
    - self.query(): Query method from AuditQueryMixin
    """

    if TYPE_CHECKING:

        def query(self, **kwargs: Any) -> list[dict[str, Any]]:
            """Query audit log entries."""
            ...

    def get_violation_summary(
        self,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Get summary of security violations.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            Dictionary with violation statistics

        Example:
            >>> summary = logger.get_violation_summary(
            ...     user_id="user@company.com",
            ... )
            >>> print(
            ...     f"Total: {summary['total_violations']}"
            ... )

        """
        violations = self.query(
            event_type="security_violation",
            user_id=user_id,
        )

        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_user: dict[str, int] = {}

        for violation in violations:
            vtype = str(violation.get("violation", {}).get("type", "unknown"))
            severity = str(violation.get("violation", {}).get("severity", "unknown"))
            vid = str(violation.get("user_id", "unknown"))

            by_type[vtype] = by_type.get(vtype, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_user[vid] = by_user.get(vid, 0) + 1

        summary: dict[str, int | dict[str, int]] = {
            "total_violations": len(violations),
            "by_type": by_type,
            "by_severity": by_severity,
            "by_user": by_user,
        }

        return summary

    def get_compliance_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Generate compliance report for audit period.

        Provides statistics for compliance audits
        (SOC2, HIPAA, GDPR).

        Args:
            start_date: Start of audit period
            end_date: End of audit period

        Returns:
            Dictionary with compliance statistics

        Example:
            >>> from datetime import datetime, timedelta
            >>> report = logger.get_compliance_report(
            ...     start_date=datetime.now(timezone.utc)
            ...         - timedelta(days=30),
            ... )
            >>> print(
            ...     f"LLM requests: "
            ...     f"{report['llm_requests']['total']}"
            ... )

        """
        # Query all events in period
        all_events = self.query(
            start_date=start_date,
            end_date=end_date,
            limit=100000,
        )

        report: dict[str, Any] = {
            "period": {
                "start": (start_date.isoformat() if start_date else "all_time"),
                "end": (end_date.isoformat() if end_date else "now"),
            },
            "llm_requests": {
                "total": 0,
                "with_pii_detected": 0,
                "with_secrets_detected": 0,
                "sanitization_applied": 0,
            },
            "pattern_storage": {
                "total": 0,
                "by_classification": {
                    "PUBLIC": 0,
                    "INTERNAL": 0,
                    "SENSITIVE": 0,
                },
                "with_pii_scrubbed": 0,
                "encrypted": 0,
            },
            "pattern_retrieval": {
                "total": 0,
                "by_classification": {
                    "PUBLIC": 0,
                    "INTERNAL": 0,
                    "SENSITIVE": 0,
                },
                "access_denied": 0,
            },
            "security_violations": {
                "total": 0,
                "by_severity": {},
                "by_type": {},
            },
            "compliance_metrics": {
                "gdpr_compliant_rate": 0.0,
                "hipaa_compliant_rate": 0.0,
                "soc2_compliant_rate": 0.0,
            },
        }

        total_compliance_checks = 0
        gdpr_compliant = 0
        hipaa_compliant = 0
        soc2_compliant = 0

        for event in all_events:
            event_type = event.get("event_type")

            if event_type == "llm_request":
                _process_llm_request(report, event)

            elif event_type == "store_pattern":
                _process_store_pattern(report, event)

            elif event_type == "retrieve_pattern":
                _process_retrieve_pattern(report, event)

            elif event_type == "security_violation":
                _process_security_violation(report, event)

            # Track compliance rates
            compliance = event.get("compliance", {})
            if compliance:
                total_compliance_checks += 1
                if compliance.get("gdpr_compliant"):
                    gdpr_compliant += 1
                if compliance.get("hipaa_compliant"):
                    hipaa_compliant += 1
                if compliance.get("soc2_compliant"):
                    soc2_compliant += 1

        # Calculate compliance rates
        if total_compliance_checks > 0:
            report["compliance_metrics"]["gdpr_compliant_rate"] = (
                gdpr_compliant / total_compliance_checks
            )
            report["compliance_metrics"]["hipaa_compliant_rate"] = (
                hipaa_compliant / total_compliance_checks
            )
            report["compliance_metrics"]["soc2_compliant_rate"] = (
                soc2_compliant / total_compliance_checks
            )

        return report


def _process_llm_request(
    report: dict[str, Any],
    event: dict[str, Any],
) -> None:
    """Process an llm_request event into the report.

    Args:
        report: The compliance report dict to update
        event: The audit event dict

    """
    report["llm_requests"]["total"] += 1
    security = event.get("security", {})
    if security.get("pii_detected", 0) > 0:
        report["llm_requests"]["with_pii_detected"] += 1
    if security.get("secrets_detected", 0) > 0:
        report["llm_requests"]["with_secrets_detected"] += 1
    if security.get("sanitization_applied"):
        report["llm_requests"]["sanitization_applied"] += 1


def _process_store_pattern(
    report: dict[str, Any],
    event: dict[str, Any],
) -> None:
    """Process a store_pattern event into the report.

    Args:
        report: The compliance report dict to update
        event: The audit event dict

    """
    report["pattern_storage"]["total"] += 1
    pattern = event.get("pattern", {})
    classification = pattern.get("classification", "INTERNAL")
    report["pattern_storage"]["by_classification"][classification] = (
        report["pattern_storage"]["by_classification"].get(classification, 0) + 1
    )
    if event.get("security", {}).get("pii_scrubbed", 0) > 0:
        report["pattern_storage"]["with_pii_scrubbed"] += 1
    if pattern.get("encrypted"):
        report["pattern_storage"]["encrypted"] += 1


def _process_retrieve_pattern(
    report: dict[str, Any],
    event: dict[str, Any],
) -> None:
    """Process a retrieve_pattern event into the report.

    Args:
        report: The compliance report dict to update
        event: The audit event dict

    """
    report["pattern_retrieval"]["total"] += 1
    pattern = event.get("pattern", {})
    classification = pattern.get("classification", "INTERNAL")
    report["pattern_retrieval"]["by_classification"][classification] = (
        report["pattern_retrieval"]["by_classification"].get(classification, 0) + 1
    )
    if not event.get("access", {}).get("granted", True):
        report["pattern_retrieval"]["access_denied"] += 1


def _process_security_violation(
    report: dict[str, Any],
    event: dict[str, Any],
) -> None:
    """Process a security_violation event into the report.

    Args:
        report: The compliance report dict to update
        event: The audit event dict

    """
    report["security_violations"]["total"] += 1
    violation = event.get("violation", {})
    vtype = violation.get("type", "unknown")
    severity = violation.get("severity", "unknown")
    report["security_violations"]["by_type"][vtype] = (
        report["security_violations"]["by_type"].get(vtype, 0) + 1
    )
    report["security_violations"]["by_severity"][severity] = (
        report["security_violations"]["by_severity"].get(severity, 0) + 1
    )
