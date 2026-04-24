"""Security tests for authentication system.

Tests coverage:
1. Password hashing with bcrypt
2. JWT token generation and validation
3. Rate limiting (5 failed attempts = 15min lockout)
4. User registration and login
5. Token refresh functionality
6. Failed attempt tracking
7. Duplicate email prevention
8. Password strength validation
9. Token expiration handling
10. Invalid credentials rejection

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import tempfile
import time
from pathlib import Path

import pytest

pytest.importorskip("bcrypt")
import jwt  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from backend.services.auth_service import JWT_ALGORITHM, JWT_SECRET_KEY, AuthService  # noqa: E402
from backend.services.database import AuthDatabase  # noqa: E402


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_auth.db")
        yield AuthDatabase(db_path)


@pytest.fixture
def auth_service(temp_db):
    """Create auth service with temporary database."""
    return AuthService(db=temp_db)


class TestPasswordHashing:
    """Test bcrypt password hashing security."""

    def test_password_is_hashed(self, temp_db):
        """Test that passwords are hashed, not stored in plaintext."""
        user_id = temp_db.create_user("test@example.com", "mypassword123", "Test User")
        assert user_id > 0

        # Verify password hash is stored, not plaintext
        with temp_db._get_connection() as conn:
            cursor = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            password_hash = row["password_hash"]

            # Hash should start with bcrypt prefix
            assert password_hash.startswith("$2b$")
            # Hash should not equal plaintext password
            assert password_hash != "mypassword123"

    def test_bcrypt_cost_factor(self, temp_db):
        """Test that bcrypt uses recommended cost factor (12)."""
        temp_db.create_user("test@example.com", "password123", "Test User")

        with temp_db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT password_hash FROM users WHERE email = ?",
                ("test@example.com",),
            )
            row = cursor.fetchone()
            password_hash = row["password_hash"]

            # Extract cost factor from hash (format: $2b$12$...)
            parts = password_hash.split("$")
            cost_factor = int(parts[2])

            assert cost_factor == 12, "Cost factor should be 12 for security"

    def test_same_password_different_hashes(self, temp_db):
        """Test that same password generates different hashes (salt verification)."""
        password = "samepassword123"

        user1_id = temp_db.create_user("user1@example.com", password, "User 1")
        user2_id = temp_db.create_user("user2@example.com", password, "User 2")

        with temp_db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT password_hash FROM users WHERE id IN (?, ?)",
                (user1_id, user2_id),
            )
            hashes = [row["password_hash"] for row in cursor.fetchall()]

            # Same password should produce different hashes due to salt
            assert hashes[0] != hashes[1]


class TestJWTTokens:
    """Test JWT token generation and validation."""

    def test_token_generation(self, auth_service, temp_db):
        """Test that JWT tokens are generated correctly."""
        temp_db.create_user("test@example.com", "password123", "Test User")

        result = auth_service.login("test@example.com", "password123")

        assert "access_token" in result
        assert "token_type" in result
        assert result["token_type"] == "bearer"
        assert "expires_in" in result
        assert result["expires_in"] == 1800  # 30 minutes

    def test_token_contains_user_info(self, auth_service, temp_db):
        """Test that JWT token contains correct user information."""
        temp_db.create_user("test@example.com", "password123", "Test User")

        result = auth_service.login("test@example.com", "password123")
        token = result["access_token"]

        # Decode token (without verification for testing)
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        assert payload["sub"] == "test@example.com"
        assert payload["name"] == "Test User"
        assert "user_id" in payload
        assert "exp" in payload  # Expiration time
        assert "iat" in payload  # Issued at time

    def test_token_validation(self, auth_service, temp_db):
        """Test that valid tokens are accepted."""
        temp_db.create_user("test@example.com", "password123", "Test User")

        result = auth_service.login("test@example.com", "password123")
        token = result["access_token"]

        # Token should be valid
        user = auth_service.get_current_user(token)
        assert user["email"] == "test@example.com"
        assert user["name"] == "Test User"

    def test_invalid_token_rejected(self, auth_service):
        """Test that invalid tokens are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token("invalid_token_string")

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    def test_token_expiration(self, auth_service):
        """Test that expired tokens are rejected."""
        # Create an expired token (expired 1 hour ago)
        import datetime

        expired_payload = {
            "sub": "test@example.com",
            "user_id": 1,
            "name": "Test User",
            "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1),
            "iat": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2),
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token(expired_token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()


class TestRateLimiting:
    """Test rate limiting and failed attempt tracking."""

    def test_failed_attempts_tracked(self, auth_service, temp_db):
        """Test that failed login attempts are tracked."""
        temp_db.create_user("test@example.com", "correct_password", "Test User")

        # Attempt login with wrong password
        with pytest.raises(HTTPException):
            auth_service.login("test@example.com", "wrong_password")

        # Verify failed attempt was recorded
        failed_count = temp_db.get_failed_attempts("test@example.com", minutes=15)
        assert failed_count == 1

    def test_rate_limit_after_5_failures(self, auth_service, temp_db):
        """Test that account is locked after 5 failed attempts."""
        temp_db.create_user("test@example.com", "correct_password", "Test User")

        # Make 5 failed attempts
        for _i in range(5):
            try:
                auth_service.login("test@example.com", "wrong_password")
            except HTTPException:
                pass

        # 6th attempt should be rate limited
        with pytest.raises(HTTPException) as exc_info:
            auth_service.login("test@example.com", "wrong_password")

        assert exc_info.value.status_code == 429  # Too Many Requests
        assert "too many failed login attempts" in exc_info.value.detail.lower()

    def test_successful_login_after_rate_limit(self, auth_service, temp_db):
        """Test that correct password is also blocked during rate limit."""
        temp_db.create_user("test@example.com", "correct_password", "Test User")

        # Make 5 failed attempts to trigger rate limit
        for _i in range(5):
            try:
                auth_service.login("test@example.com", "wrong_password")
            except HTTPException:
                pass

        # Even correct password should be blocked
        with pytest.raises(HTTPException) as exc_info:
            auth_service.login("test@example.com", "correct_password")

        assert exc_info.value.status_code == 429


class TestUserRegistration:
    """Test user registration security."""

    def test_registration_creates_user(self, auth_service, temp_db):
        """Test that registration creates user and returns token."""
        result = auth_service.register("new@example.com", "password123", "New User")

        assert "access_token" in result
        assert temp_db.user_exists("new@example.com")

    def test_duplicate_email_rejected(self, auth_service, temp_db):
        """Test that duplicate email addresses are rejected."""
        auth_service.register("test@example.com", "password123", "User 1")

        with pytest.raises(HTTPException) as exc_info:
            auth_service.register("test@example.com", "different_pass", "User 2")

        assert exc_info.value.status_code == 400
        assert "already registered" in exc_info.value.detail.lower()

    def test_weak_password_rejected(self, auth_service):
        """Test that passwords under 8 characters are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            auth_service.register("test@example.com", "short", "Test User")

        assert exc_info.value.status_code == 400
        assert "8 characters" in exc_info.value.detail.lower()


class TestTokenRefresh:
    """Test token refresh functionality."""

    def test_token_refresh_works(self, auth_service, temp_db):
        """Test that tokens can be refreshed."""
        temp_db.create_user("test@example.com", "password123", "Test User")

        # Get initial token
        login_result = auth_service.login("test@example.com", "password123")
        initial_token = login_result["access_token"]

        # Wait to ensure different timestamps
        time.sleep(1.1)

        # Refresh token
        refresh_result = auth_service.refresh_token(initial_token)
        new_token = refresh_result["access_token"]

        # New token should be different (due to timestamp change)
        assert new_token != initial_token

        # New token should be valid
        user = auth_service.get_current_user(new_token)
        assert user["email"] == "test@example.com"

    def test_refresh_with_invalid_token_fails(self, auth_service):
        """Test that refresh fails with invalid token."""
        with pytest.raises(HTTPException):
            auth_service.refresh_token("invalid_token")


class TestAuthenticationFlow:
    """Test complete authentication flows."""

    def test_register_login_flow(self, auth_service, temp_db):
        """Test complete register -> login flow."""
        # Register
        register_result = auth_service.register(
            "test@example.com",
            "password123",
            "Test User",
            "LICENSE-KEY-123",
        )

        assert "access_token" in register_result

        # Wait to ensure different timestamps
        time.sleep(1.1)

        # Login with same credentials
        login_result = auth_service.login("test@example.com", "password123")

        assert "access_token" in login_result
        # Tokens should be different (different timestamps)
        assert login_result["access_token"] != register_result["access_token"]

    def test_login_get_user_flow(self, auth_service, temp_db):
        """Test login -> get user info flow."""
        temp_db.create_user("test@example.com", "password123", "Test User")

        # Login
        login_result = auth_service.login("test@example.com", "password123")
        token = login_result["access_token"]

        # Get user info
        user = auth_service.get_current_user(token)

        assert user["email"] == "test@example.com"
        assert user["name"] == "Test User"
        assert "id" in user
