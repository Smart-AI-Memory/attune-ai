"""Tests for auth_db.py exception handling and audit trail.

This test suite verifies the authentication database exception handling
and security audit trail logging implemented in Sprint 1 of the bug remediation plan.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
import sqlite3

import pytest

from backend.services.database.auth_db import AuthDatabase


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_auth.db")
    return AuthDatabase(db_path)


@pytest.fixture
def populated_db(temp_db):
    """Create a database with a test user."""
    temp_db.create_user(
        email="test@example.com",
        password="test_password_123",
        name="Test User",
        license_key="TEST-LICENSE-123",
    )
    return temp_db


class TestConnectionExceptionHandling:
    """Test exception handling in database connection management."""

    def test_integrity_error_logs_and_rollsback(self, temp_db, caplog):
        """IntegrityError should log, rollback, and re-raise."""
        with caplog.at_level(logging.ERROR), pytest.raises(sqlite3.IntegrityError):
            with temp_db._get_connection() as conn:
                # Create duplicate primary keys to trigger IntegrityError
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
            db = AuthDatabase(str(db_path))
            db.create_user(email="test@example.com", password="password", name="Test User")

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
                db = AuthDatabase(db_path)
                db.create_user(email="test@example.com", password="password", name="Test User")

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
        with pytest.raises(sqlite3.IntegrityError), temp_db._get_connection() as conn:
            conn.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                ("test@example.com", "hash", "Test User"),
            )
            # Trigger error before commit
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.execute("INSERT INTO test VALUES (1)")  # Duplicate

        # Changes should be rolled back - user should not exist
        assert not temp_db.user_exists("test@example.com")

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


class TestSecurityAuditTrail:
    """Test security audit trail logging for authentication operations."""

    def test_create_user_logs_operation(self, temp_db, caplog):
        """Creating user should log the operation."""
        with caplog.at_level(logging.INFO):
            user_id = temp_db.create_user(
                email="newuser@example.com",
                password="secure_password_123",
                name="New User",
                license_key="LICENSE-KEY-456",
            )

        # Should log user creation
        assert any(
            "creating new user account" in record.message.lower()
            and "newuser@example.com" in record.message.lower()
            for record in caplog.records
        )

        # Should log successful completion
        assert any(
            "user account created successfully" in record.message.lower()
            and str(user_id) in record.message
            for record in caplog.records
        )

    def test_verify_user_success_logs_auth_success(self, populated_db, caplog):
        """Successful authentication should log INFO."""
        with caplog.at_level(logging.INFO):
            result = populated_db.verify_user("test@example.com", "test_password_123")

        assert result is not None
        assert result["email"] == "test@example.com"

        # Should log authentication attempt
        assert any(
            "authentication attempt" in record.message.lower()
            and "test@example.com" in record.message.lower()
            for record in caplog.records
        )

        # Should log successful authentication
        assert any(
            "authentication successful" in record.message.lower()
            and "test@example.com" in record.message.lower()
            for record in caplog.records
        )

    def test_verify_user_invalid_password_logs_warning(self, populated_db, caplog):
        """Failed authentication (wrong password) should log WARNING."""
        with caplog.at_level(logging.WARNING):
            result = populated_db.verify_user("test@example.com", "wrong_password")

        assert result is None

        # Should log authentication failure at WARNING level
        assert any(
            "authentication failed" in record.message.lower()
            and "invalid password" in record.message.lower()
            and record.levelno == logging.WARNING
            for record in caplog.records
        )

    def test_verify_user_unknown_email_logs_warning(self, populated_db, caplog):
        """Failed authentication (unknown user) should log WARNING."""
        with caplog.at_level(logging.WARNING):
            result = populated_db.verify_user("unknown@example.com", "any_password")

        assert result is None

        # Should log authentication failure at WARNING level
        assert any(
            "authentication failed" in record.message.lower()
            and "user not found" in record.message.lower()
            and record.levelno == logging.WARNING
            for record in caplog.records
        )

    def test_record_successful_login_logs_info(self, temp_db, caplog):
        """Successful login attempt should log at INFO level."""
        with caplog.at_level(logging.INFO):
            temp_db.record_login_attempt(
                email="test@example.com",
                success=True,
                ip_address="192.168.1.100",
            )

        # Should log at INFO level for successful login
        assert any(
            "recording login attempt" in record.message.lower()
            and record.levelno == logging.INFO
            and "success=true" in record.message.lower()
            for record in caplog.records
        )

    def test_record_failed_login_logs_warning(self, temp_db, caplog):
        """Failed login attempt should log at WARNING level."""
        with caplog.at_level(logging.WARNING):
            temp_db.record_login_attempt(
                email="attacker@example.com",
                success=False,
                ip_address="192.168.1.200",
            )

        # Should log at WARNING level for failed login (security event)
        assert any(
            "recording login attempt" in record.message.lower()
            and record.levelno == logging.WARNING
            and "success=false" in record.message.lower()
            for record in caplog.records
        )

    def test_complete_auth_flow_audit_trail(self, temp_db, caplog):
        """Complete authentication flow should have full audit trail."""
        with caplog.at_level(logging.INFO):
            # Create user
            temp_db.create_user(
                email="audit@example.com",
                password="password123",
                name="Audit User",
            )

            # Successful login
            temp_db.verify_user("audit@example.com", "password123")

            # Record attempt
            temp_db.record_login_attempt("audit@example.com", success=True, ip_address="127.0.0.1")

        # Verify complete audit trail
        messages = [r.message.lower() for r in caplog.records]

        # User creation logged
        assert any(
            "creating new user account" in msg and "audit@example.com" in msg for msg in messages
        )
        assert any("user account created successfully" in msg for msg in messages)

        # Authentication logged
        assert any(
            "authentication attempt" in msg and "audit@example.com" in msg for msg in messages
        )
        assert any("authentication successful" in msg for msg in messages)

        # Login attempt logged
        assert any("recording login attempt" in msg and "success=true" in msg for msg in messages)


class TestAuthenticationOperations:
    """Test that authentication operations work correctly with exception handling."""

    def test_successful_user_creation(self, temp_db):
        """User should be created successfully with proper error handling."""
        user_id = temp_db.create_user(
            email="success@example.com",
            password="secure_pass_123",
            name="Success User",
            license_key="LICENSE-789",
        )

        assert user_id is not None
        assert user_id > 0
        assert temp_db.user_exists("success@example.com")

    def test_duplicate_email_raises_integrity_error(self, populated_db, caplog):
        """Duplicate email should raise IntegrityError and log it."""
        with caplog.at_level(logging.ERROR), pytest.raises(sqlite3.IntegrityError):
            populated_db.create_user(
                email="test@example.com",  # Already exists
                password="another_password",
                name="Duplicate User",
            )

        # Should log integrity error
        assert any("integrity error" in record.message.lower() for record in caplog.records)

    def test_successful_authentication(self, populated_db):
        """Successful authentication should return user dict."""
        result = populated_db.verify_user("test@example.com", "test_password_123")

        assert result is not None
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["license_key"] == "TEST-LICENSE-123"
        assert "password" not in result  # Password should not be returned
        assert "password_hash" not in result

    def test_failed_attempts_tracking(self, temp_db):
        """Failed login attempts should be tracked."""
        email = "tracker@example.com"

        # Record 3 failed attempts
        for _i in range(3):
            temp_db.record_login_attempt(email, success=False)

        # Check failed attempts count
        failed_count = temp_db.get_failed_attempts(email, minutes=15)
        assert failed_count == 3


class TestErrorPropagation:
    """Test that errors are properly propagated for security audit."""

    def test_database_error_reaches_caller(self, temp_db):
        """Database errors should propagate to caller, not be silently swallowed."""
        with pytest.raises(sqlite3.DatabaseError), temp_db._get_connection() as conn:
            conn.execute("COMPLETELY INVALID SQL STATEMENT")

    def test_integrity_error_reaches_caller(self, populated_db):
        """Integrity errors should propagate to caller."""
        with pytest.raises(sqlite3.IntegrityError):
            # Try to create user with duplicate email
            populated_db.create_user(
                email="test@example.com",
                password="password",
                name="Duplicate",
            )

    def test_file_error_reaches_caller(self, caplog):
        """File system errors should propagate to caller."""
        with pytest.raises((OSError, sqlite3.OperationalError)):
            db = AuthDatabase("/invalid/path/that/does/not/exist/test.db")
            db.create_user(email="test@example.com", password="password", name="Test")


class TestPasswordSecurity:
    """Test that password handling is secure."""

    def test_password_not_stored_in_plain_text(self, temp_db):
        """Password should be hashed, not stored in plain text."""
        temp_db.create_user(
            email="secure@example.com",
            password="my_secret_password",
            name="Secure User",
        )

        # Verify password is hashed in database
        with temp_db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT password_hash FROM users WHERE email = ?",
                ("secure@example.com",),
            )
            row = cursor.fetchone()
            password_hash = row["password_hash"]

            # Hash should not be the plain text password
            assert password_hash != "my_secret_password"
            # Hash should start with bcrypt prefix
            assert password_hash.startswith("$2b$")

    def test_password_not_returned_in_verify(self, populated_db):
        """Password hash should never be returned to caller."""
        result = populated_db.verify_user("test@example.com", "test_password_123")

        assert result is not None
        assert "password" not in result
        assert "password_hash" not in result
