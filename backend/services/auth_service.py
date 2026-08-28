"""Authentication service with JWT tokens and rate limiting.

Provides secure authentication with:
- JWT token generation (HS256)
- Token validation and refresh
- Rate limiting (5 failed attempts = 15min lockout)
- Secure password requirements

Security:
- JWT_SECRET_KEY must be set via environment variable
- Minimum 32 bytes required for HS256 security
- No default/fallback value (fails explicitly)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status

from backend.services.database import AuthDatabase

logger = logging.getLogger(__name__)


def _get_jwt_secret_key() -> str:
    """Get JWT secret key from environment with validation.

    Returns:
        Validated JWT secret key

    Raises:
        ValueError: If JWT_SECRET_KEY not set or too weak

    Security:
        - Requires explicit configuration (no defaults)
        - Enforces minimum 32 bytes for HS256 security
        - Fails fast at startup, not during request handling

    """
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        error_msg = (
            "JWT_SECRET_KEY environment variable not set. "
            "This is required for authentication security. "
            "Generate a secure key with: "
            "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
        logger.critical("jwt_secret_key_missing")
        raise ValueError(error_msg)

    # HS256 requires minimum 256 bits (32 bytes) for security
    if len(secret) < 32:
        error_msg = (
            f"JWT_SECRET_KEY too weak ({len(secret)} chars). "
            "Minimum 32 characters required for HS256 security. "
            "Generate a secure key with: "
            "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
        logger.critical("jwt_secret_key_too_weak", length=len(secret))
        raise ValueError(error_msg)

    return secret


# JWT Configuration - validated at module load time
JWT_SECRET_KEY = _get_jwt_secret_key()
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 30


def verify_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Stateless single-source of token verification, reused by both
    ``AuthService.verify_token`` and the ``require_principal`` FastAPI
    dependency so protected routes reject forged/expired bearers without
    constructing the auth database.

    Args:
        token: JWT token string extracted from the ``Authorization`` header.

    Returns:
        The decoded token payload (``sub``, ``user_id``, ``name``, ...).

    Raises:
        HTTPException: 401 if the token is invalid or expired.

    """
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Rate limiting configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class AuthService:
    """Authentication service with JWT and rate limiting."""

    def __init__(self, db: AuthDatabase | None = None):
        """Initialize authentication service.

        Args:
            db: AuthDatabase instance (creates default if None)

        """
        self.db = db or AuthDatabase()

    def _create_access_token(self, user_data: dict[str, Any]) -> tuple[str, int]:
        """Create JWT access token.

        Args:
            user_data: User information to encode in token

        Returns:
            Tuple of (token_string, expires_in_seconds)

        """
        expires_at = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        expires_in = JWT_EXPIRATION_MINUTES * 60

        payload = {
            "sub": user_data["email"],  # Subject (user identifier)
            "user_id": user_data["id"],
            "name": user_data["name"],
            "exp": expires_at,  # Expiration time
            "iat": datetime.utcnow(),  # Issued at
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token, expires_in

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired

        """
        return verify_access_token(token)

    def login(self, email: str, password: str, ip_address: str | None = None) -> dict[str, Any]:
        """Authenticate user and return access token.

        Args:
            email: User email
            password: User password
            ip_address: Optional IP address for rate limiting

        Returns:
            Dict with access_token, token_type, expires_in

        Raises:
            HTTPException: If authentication fails or rate limit exceeded

        """
        # Check rate limiting
        failed_attempts = self.db.get_failed_attempts(email, LOCKOUT_MINUTES)
        if failed_attempts >= MAX_FAILED_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Please try again in {LOCKOUT_MINUTES} minutes.",
            )

        # Verify credentials
        user = self.db.verify_user(email, password)

        if user is None:
            # Record failed attempt
            self.db.record_login_attempt(email, success=False, ip_address=ip_address)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Record successful login
        self.db.record_login_attempt(email, success=True, ip_address=ip_address)

        # Generate token
        access_token, expires_in = self._create_access_token(user)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    def register(
        self,
        email: str,
        password: str,
        name: str,
        license_key: str | None = None,
    ) -> dict[str, Any]:
        """Register new user account.

        Args:
            email: User email (must be unique)
            password: User password (minimum 8 characters)
            name: User's full name
            license_key: Optional license key

        Returns:
            Dict with access_token, token_type, expires_in

        Raises:
            HTTPException: If registration fails

        """
        # Validate password strength
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters",
            )

        # Check if user already exists
        if self.db.user_exists(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create user
        try:
            user_id = self.db.create_user(email, password, name, license_key)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {e!s}",
            ) from e

        # Generate token for new user
        user_data = {
            "id": user_id,
            "email": email,
            "name": name,
            "license_key": license_key,
        }
        access_token, expires_in = self._create_access_token(user_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    def refresh_token(self, current_token: str) -> dict[str, Any]:
        """Refresh access token.

        Args:
            current_token: Current JWT token

        Returns:
            Dict with new access_token, token_type, expires_in

        Raises:
            HTTPException: If token is invalid

        """
        # Verify current token
        payload = self.verify_token(current_token)

        # Create new token with same user data
        user_data = {
            "id": payload["user_id"],
            "email": payload["sub"],
            "name": payload["name"],
        }
        access_token, expires_in = self._create_access_token(user_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    def get_current_user(self, token: str) -> dict[str, Any]:
        """Get current user from token.

        Args:
            token: JWT access token

        Returns:
            User information

        Raises:
            HTTPException: If token is invalid

        """
        payload = self.verify_token(token)

        return {
            "id": payload["user_id"],
            "email": payload["sub"],
            "name": payload["name"],
        }
