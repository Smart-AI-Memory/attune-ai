"""Tests for compliance_db.py exception handling and audit trail.

This test suite verifies the compliance database exception handling
and audit trail logging implemented in Sprint 1 of the bug remediation plan.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
import sqlite3
from datetime import datetime

import pytest

from agents.compliance_db import ComplianceDatabase


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_compliance.db")
    return ComplianceDatabase(db_path)


@pytest.fixture
def populated_db(temp_db):
    """Create a database with some test data."""
    # Add a test audit
    temp_db.record_audit(
        audit_date=datetime(2026, 1, 5, 10, 0, 0),
        audit_type="HIPAA",
        findings='{"issues": []}',
        risk_score=25,
        auditor="test_auditor",
    )

    # Add a test gap
    temp_db.record_gap(
        gap_type="missing_policy",
        severity="high",
        description="Test gap",
        compliance_framework="HIPAA",
    )

    return temp_db


class TestConnectionExceptionHandling:
    """Test exception handling in database connection management."""

    def test_integrity_error_logs_and_rollsback(self, temp_db, caplog):
        """IntegrityError should log, rollback, and re-raise."""
        with caplog.at_level(logging.ERROR), pytest.raises(sqlite3.IntegrityError):
            with temp_db._get_connection() as conn:
                # Violate unique constraint (if we had one)
                # For now, trigger error by executing invalid SQL
                conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
                conn.execute("INSERT INTO test VALUES (1)")
                conn.execute("INSERT INTO test VALUES (1)")  # Duplicate

        # Should log error
        assert any("integrity error" in record.message.lower() for record in caplog.records)

    def test_operational_error_logs_critical_and_raises(self, tmp_path, caplog):
        """OperationalError should log critical and re-raise."""
        # Create a read-only file to trigger OperationalError
        db_path = tmp_path / "readonly.db"
        db_path.touch()
        db_path.chmod(0o444)  # Read-only

        with caplog.at_level(logging.CRITICAL), pytest.raises(sqlite3.OperationalError):
            db = ComplianceDatabase(str(db_path))
            db.record_audit(
                audit_date=datetime(2026, 1, 5),
                audit_type="HIPAA",
            )

        # Should log critical error
        assert any("operational error" in record.message.lower() for record in caplog.records)

    def test_database_error_logs_and_raises(self, temp_db, caplog):
        """SQL syntax errors should log and re-raise as OperationalError."""
        with caplog.at_level(logging.CRITICAL), pytest.raises(sqlite3.OperationalError):
            with temp_db._get_connection() as conn:
                # Trigger an operational error (SQL syntax error)
                conn.execute("INVALID SQL STATEMENT")

        # Should log error (as operational error for SQL syntax issues)
        assert any(
            "operational error" in record.message.lower()
            or "database error" in record.message.lower()
            for record in caplog.records
        )

    def test_file_system_error_logs_critical(self, caplog):
        """File system errors should log critical and re-raise."""
        # Try to create DB in non-existent directory without parent creation
        with caplog.at_level(logging.CRITICAL):
            with pytest.raises((OSError, IOError, sqlite3.OperationalError)):
                db_path = "/nonexistent/directory/that/does/not/exist/test.db"
                db = ComplianceDatabase(db_path)
                db.record_audit(
                    audit_date=datetime(2026, 1, 5),
                    audit_type="HIPAA",
                )

    def test_unexpected_error_logs_with_traceback(self, temp_db, caplog):
        """Unexpected errors should log with full exception traceback."""
        with caplog.at_level(logging.ERROR), pytest.raises(Exception):
            with temp_db._get_connection():
                # Trigger unexpected error
                raise RuntimeError("Unexpected database operation error")

        # Should log exception with traceback
        assert any("unexpected error" in record.message.lower() for record in caplog.records)

    def test_rollback_occurs_on_exception(self, temp_db):
        """Database should rollback on exception, not commit partial changes."""
        initial_audits = len((temp_db.get_last_audit() is not None and [1]) or [])

        with pytest.raises(sqlite3.IntegrityError), temp_db._get_connection() as conn:
            conn.execute(
                "INSERT INTO compliance_audits (audit_date, audit_type) VALUES (?, ?)",
                (datetime(2026, 1, 5), "HIPAA"),
            )
            # Trigger error before commit
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.execute("INSERT INTO test VALUES (1)")  # Duplicate

        # Changes should be rolled back
        final_audits = len((temp_db.get_last_audit() is not None and [1]) or [])
        assert final_audits == initial_audits  # No new audits committed

    def test_connection_cleanup_on_error(self, temp_db):
        """Connection should be closed even when exception occurs."""
        try:
            with temp_db._get_connection() as conn:
                original_conn = conn
                raise ValueError("Test error")
        except ValueError:
            pass

        # Connection should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            original_conn.execute("SELECT 1")


class TestAuditTrailLogging:
    """Test audit trail logging for compliance operations."""

    def test_record_audit_logs_operation(self, temp_db, caplog):
        """Recording audit should log the operation."""
        with caplog.at_level(logging.INFO):
            audit_id = temp_db.record_audit(
                audit_date=datetime(2026, 1, 5),
                audit_type="HIPAA",
                findings='{"issues": []}',
                risk_score=25,
                auditor="test_auditor",
            )

        # Should log recording operation
        assert any(
            "recording compliance audit" in record.message.lower()
            and "hipaa" in record.message.lower()
            for record in caplog.records
        )

        # Should log successful completion
        assert any(
            "audit recorded successfully" in record.message.lower()
            and str(audit_id) in record.message
            for record in caplog.records
        )

    def test_record_gap_logs_as_warning(self, temp_db, caplog):
        """Recording compliance gap should log as WARNING (important event)."""
        with caplog.at_level(logging.WARNING):
            gap_id = temp_db.record_gap(
                gap_type="missing_policy",
                severity="critical",
                description="Missing encryption policy",
                compliance_framework="HIPAA",
            )

        # Should log gap recording as warning
        assert any(
            "recording compliance gap" in record.message.lower()
            and record.levelno == logging.WARNING
            for record in caplog.records
        )

        # Should log gap recorded with severity
        assert any(
            "compliance gap recorded" in record.message.lower()
            and "critical" in record.message.lower()
            and str(gap_id) in record.message
            for record in caplog.records
        )

    def test_record_compliant_status_logs_info(self, temp_db, caplog):
        """Compliant status should log at INFO level."""
        with caplog.at_level(logging.INFO):
            temp_db.record_compliance_status(
                compliance_framework="HIPAA",
                status="compliant",
                effective_date=datetime(2026, 1, 5),
                notes="All requirements met",
            )

        # Should log at INFO level for compliant status
        assert any(
            "recording compliance status" in record.message.lower()
            and record.levelno == logging.INFO
            and "compliant" in record.message.lower()
            for record in caplog.records
        )

    def test_record_noncompliant_status_logs_warning(self, temp_db, caplog):
        """Non-compliant status should log at WARNING level."""
        with caplog.at_level(logging.WARNING):
            temp_db.record_compliance_status(
                compliance_framework="HIPAA",
                status="non_compliant",
                effective_date=datetime(2026, 1, 5),
                notes="Missing required controls",
            )

        # Should log at WARNING level for non-compliant status
        assert any(
            "recording compliance status" in record.message.lower()
            and record.levelno == logging.WARNING
            and "non_compliant" in record.message.lower()
            for record in caplog.records
        )

    def test_critical_gap_audit_trail(self, temp_db, caplog):
        """Critical compliance gaps should have full audit trail."""
        with caplog.at_level(logging.WARNING):
            temp_db.record_gap(
                gap_type="data_breach_risk",
                severity="critical",
                description="Unencrypted PHI storage detected",
                affected_systems='["database", "backup"]',
                compliance_framework="HIPAA",
                detection_source="automated_scan",
            )

        # Verify audit trail contains all critical information
        gap_logs = [r for r in caplog.records if "compliance gap" in r.message.lower()]
        assert len(gap_logs) >= 2  # Recording + recorded messages

        # Check recording message contains key details
        recording_log = [r for r in gap_logs if "recording" in r.message.lower()][0]
        assert "critical" in recording_log.message.lower()
        assert "hipaa" in recording_log.message.lower()

    def test_database_error_preserves_context(self, temp_db, caplog):
        """Database errors should preserve context for audit purposes."""
        with caplog.at_level(logging.ERROR), pytest.raises(sqlite3.DatabaseError):
            with temp_db._get_connection() as conn:
                conn.execute("INVALID SQL FOR TESTING")

        # Error log should contain context
        error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_logs) > 0
        assert any("compliance database" in r.message.lower() for r in error_logs)


class TestComplianceOperations:
    """Test that compliance operations work correctly with exception handling."""

    def test_successful_audit_recording(self, temp_db):
        """Audit should be recorded successfully with proper error handling."""
        audit_id = temp_db.record_audit(
            audit_date=datetime(2026, 1, 5, 14, 30),
            audit_type="GDPR",
            findings='{"violations": 0}',
            risk_score=10,
            auditor="compliance_team",
        )

        assert audit_id is not None
        assert audit_id > 0

        # Verify it can be retrieved
        last_audit = temp_db.get_last_audit("GDPR")
        assert last_audit is not None
        assert last_audit["audit_type"] == "GDPR"
        assert last_audit["risk_score"] == 10

    def test_successful_gap_recording(self, temp_db):
        """Gap should be recorded successfully with proper error handling."""
        gap_id = temp_db.record_gap(
            gap_type="expired_certification",
            severity="high",
            description="SSL certificate expired",
            compliance_framework="SOC2",
        )

        assert gap_id is not None
        assert gap_id > 0

        # Verify it can be retrieved
        gaps = temp_db.get_active_gaps(framework="SOC2")
        assert len(gaps) > 0
        assert gaps[0]["gap_type"] == "expired_certification"

    def test_successful_status_recording(self, temp_db):
        """Status should be recorded successfully with proper error handling."""
        status_id = temp_db.record_compliance_status(
            compliance_framework="HIPAA",
            status="compliant",
            effective_date=datetime(2026, 1, 5),
            notes="Annual audit passed",
        )

        assert status_id is not None
        assert status_id > 0

        # Verify it can be retrieved
        status = temp_db.get_current_compliance_status("HIPAA")
        assert status is not None
        assert status["status"] == "compliant"

    def test_append_only_integrity(self, populated_db):
        """Database should maintain append-only integrity."""
        # Record initial audit
        audit1_id = populated_db.record_audit(
            audit_date=datetime(2026, 1, 5),
            audit_type="HIPAA",
            findings='{"test": 1}',
        )

        # Record another audit
        audit2_id = populated_db.record_audit(
            audit_date=datetime(2026, 1, 6),
            audit_type="HIPAA",
            findings='{"test": 2}',
        )

        # Both should exist (append-only, no updates/deletes)
        assert audit2_id > audit1_id
        assert audit1_id is not None
        assert audit2_id is not None


class TestErrorPropagation:
    """Test that errors are properly propagated for audit trail."""

    def test_database_error_reaches_caller(self, temp_db):
        """Database errors should propagate to caller, not be silently swallowed."""
        with pytest.raises(sqlite3.DatabaseError), temp_db._get_connection() as conn:
            conn.execute("COMPLETELY INVALID SQL STATEMENT")

    def test_integrity_error_reaches_caller(self, temp_db):
        """Integrity errors should propagate to caller."""
        with pytest.raises(sqlite3.IntegrityError), temp_db._get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.execute("INSERT INTO test VALUES (1)")  # Duplicate

    def test_file_error_reaches_caller(self, caplog):
        """File system errors should propagate to caller."""
        with pytest.raises((OSError, sqlite3.OperationalError)):
            db = ComplianceDatabase("/invalid/path/that/does/not/exist/test.db")
            db.record_audit(audit_date=datetime(2026, 1, 5), audit_type="TEST")
