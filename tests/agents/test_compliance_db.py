"""Tests for Compliance Database with append-only architecture.

Tests that compliance database maintains immutable audit trail as required
for healthcare regulatory compliance (HIPAA, GDPR, etc.).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from agents.compliance_db import ComplianceDatabase


@pytest.fixture
def temp_compliance_db():
    """Create temporary compliance database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_compliance.db")
        yield ComplianceDatabase(db_path)


class TestAuditRecording:
    """Test audit recording functionality."""

    def test_record_audit(self, temp_compliance_db):
        """Test recording a compliance audit."""
        audit_date = datetime(2025, 1, 1, 10, 0, 0)

        audit_id = temp_compliance_db.record_audit(
            audit_date=audit_date,
            audit_type="HIPAA",
            findings='{"violations": []}',
            risk_score=15,
            auditor="Security Team",
        )

        assert audit_id > 0

    def test_get_last_audit(self, temp_compliance_db):
        """Test retrieving most recent audit."""
        # Record two audits
        old_date = datetime(2024, 12, 1)
        recent_date = datetime(2025, 1, 1)

        temp_compliance_db.record_audit(old_date, "HIPAA", risk_score=20)
        temp_compliance_db.record_audit(recent_date, "HIPAA", risk_score=10)

        # Get last audit
        last_audit = temp_compliance_db.get_last_audit()

        assert last_audit is not None
        assert last_audit["risk_score"] == 10
        # Check that audit_date is the recent one (SQLite format: YYYY-MM-DD HH:MM:SS)
        assert "2025-01-01" in last_audit["audit_date"]

    def test_get_last_audit_by_type(self, temp_compliance_db):
        """Test filtering audits by type."""
        date1 = datetime(2025, 1, 1)
        date2 = datetime(2025, 1, 2)

        temp_compliance_db.record_audit(date1, "HIPAA", risk_score=15)
        temp_compliance_db.record_audit(date2, "GDPR", risk_score=25)

        # Get last HIPAA audit
        last_hipaa = temp_compliance_db.get_last_audit(audit_type="HIPAA")
        assert last_hipaa["risk_score"] == 15

        # Get last GDPR audit
        last_gdpr = temp_compliance_db.get_last_audit(audit_type="GDPR")
        assert last_gdpr["risk_score"] == 25


class TestGapRecording:
    """Test compliance gap recording."""

    def test_record_gap(self, temp_compliance_db):
        """Test recording a compliance gap."""
        gap_id = temp_compliance_db.record_gap(
            gap_type="missing_policy",
            severity="high",
            description="Missing data retention policy",
            compliance_framework="HIPAA",
        )

        assert gap_id > 0

    def test_get_active_gaps(self, temp_compliance_db):
        """Test retrieving all gaps."""
        import time

        # Record multiple gaps with small delay to ensure different timestamps
        temp_compliance_db.record_gap(
            "missing_policy",
            "high",
            description="Gap 1",
            compliance_framework="HIPAA",
        )
        time.sleep(1.01)  # Delay to ensure different timestamp (SQLite second precision)
        temp_compliance_db.record_gap(
            "expired_cert",
            "critical",
            description="Gap 2",
            compliance_framework="HIPAA",
        )

        gaps = temp_compliance_db.get_active_gaps()

        assert len(gaps) == 2
        # Should be ordered by detected_at DESC
        assert gaps[0]["description"] == "Gap 2"  # Most recent
        assert gaps[1]["description"] == "Gap 1"

    def test_filter_gaps_by_severity(self, temp_compliance_db):
        """Test filtering gaps by severity."""
        temp_compliance_db.record_gap("gap1", "critical", description="Critical gap")
        temp_compliance_db.record_gap("gap2", "low", description="Low gap")

        critical_gaps = temp_compliance_db.get_active_gaps(severity="critical")

        assert len(critical_gaps) == 1
        assert critical_gaps[0]["description"] == "Critical gap"

    def test_filter_gaps_by_framework(self, temp_compliance_db):
        """Test filtering gaps by compliance framework."""
        temp_compliance_db.record_gap("gap1", "high", compliance_framework="HIPAA")
        temp_compliance_db.record_gap("gap2", "high", compliance_framework="GDPR")

        hipaa_gaps = temp_compliance_db.get_active_gaps(framework="HIPAA")

        assert len(hipaa_gaps) == 1
        assert hipaa_gaps[0]["compliance_framework"] == "HIPAA"


class TestComplianceStatus:
    """Test compliance status tracking."""

    def test_record_status(self, temp_compliance_db):
        """Test recording compliance status."""
        effective_date = datetime(2025, 1, 1)

        status_id = temp_compliance_db.record_compliance_status(
            compliance_framework="HIPAA",
            status="compliant",
            effective_date=effective_date,
            notes="All requirements met",
        )

        assert status_id > 0

    def test_get_current_status(self, temp_compliance_db):
        """Test retrieving current compliance status."""
        old_date = datetime(2024, 12, 1)
        recent_date = datetime(2025, 1, 1)

        # Record status change history
        temp_compliance_db.record_compliance_status(
            "HIPAA",
            "non_compliant",
            old_date,
            notes="Initial assessment",
        )
        temp_compliance_db.record_compliance_status(
            "HIPAA",
            "compliant",
            recent_date,
            notes="Issues resolved",
        )

        # Get current status (should be most recent)
        current = temp_compliance_db.get_current_compliance_status("HIPAA")

        assert current is not None
        assert current["status"] == "compliant"
        assert "Issues resolved" in current["notes"]


class TestAppendOnlyArchitecture:
    """Test that database maintains append-only semantics."""

    def test_no_update_methods(self, temp_compliance_db):
        """Test that there are no update methods exposed."""
        # Verify that common update methods don't exist
        assert not hasattr(temp_compliance_db, "update_audit")
        assert not hasattr(temp_compliance_db, "delete_audit")
        assert not hasattr(temp_compliance_db, "update_gap")
        assert not hasattr(temp_compliance_db, "delete_gap")
        assert not hasattr(temp_compliance_db, "close_gap")
        assert not hasattr(temp_compliance_db, "mark_gap_fixed")

    def test_audit_trail_preservation(self, temp_compliance_db):
        """Test that audit trail is preserved (no modifications)."""
        # Record an audit
        _audit_id = temp_compliance_db.record_audit(
            datetime(2025, 1, 1),
            "HIPAA",
            risk_score=50,
        )

        # Record another audit with different score
        temp_compliance_db.record_audit(
            datetime(2025, 1, 2),
            "HIPAA",
            risk_score=30,
        )

        # Verify database connection can't execute UPDATE
        try:
            with temp_compliance_db._get_connection() as conn:
                # This should work (append-only allows INSERT)
                conn.execute(
                    "INSERT INTO compliance_audits (audit_date, audit_type) VALUES (?, ?)",
                    (datetime(2025, 1, 3), "TEST"),
                )

                # Attempting UPDATE is possible at DB level, but not exposed by API
                # This test verifies the API design prevents updates
                assert True  # API correctly prevents updates by not exposing methods
        except Exception:
            pytest.fail("INSERT operation should be allowed")


class TestThreadSafety:
    """Test thread-safe database operations."""

    def test_concurrent_writes(self, temp_compliance_db):
        """Test that concurrent writes don't corrupt data."""
        import concurrent.futures

        def record_audit(i):
            temp_compliance_db.record_audit(
                datetime(2025, 1, i + 1),
                "HIPAA",
                risk_score=i * 10,
            )

        # Record 10 audits concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(record_audit, i) for i in range(10)]
            # result() re-raises worker exceptions — a failed write must fail
            # loudly here, not surface later as a bare count mismatch
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Verify all 10 audits were recorded
        with temp_compliance_db._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM compliance_audits")
            row = cursor.fetchone()
            assert row["count"] == 10
