"""Authentication API endpoints.

Handles user authentication, tokens, and license validation.

Features:
- Secure password hashing with bcrypt (cost factor 12)
- JWT token generation (HS256, 30min expiry)
- Rate limiting (5 failed attempts = 15min lockout)
- SQLite user database

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

# Initialize auth service (singleton)
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Get or create AuthService instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


class LoginRequest(BaseModel):
    """Login request model."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request model."""

    email: EmailStr
    password: str
    name: str
    license_key: str | None = None


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, http_request: Request):
    """Authenticate user and return access token.

    Security Features:
    - Bcrypt password hashing (cost factor 12)
    - JWT tokens with 30-minute expiration
    - Rate limiting (5 failed attempts = 15min lockout)
    - Failed attempt tracking

    Args:
        request: Login credentials (email and password)
        http_request: HTTP request for IP address extraction

    Returns:
        Access token and metadata

    Raises:
        HTTPException 400: Invalid input
        HTTPException 401: Invalid credentials
        HTTPException 429: Rate limit exceeded (too many failed attempts)

    """
    # Input validation
    if not request.email or not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )

    # Get client IP for rate limiting
    ip_address = http_request.client.host if http_request.client else None

    # Authenticate using secure service
    auth_service = get_auth_service()
    result = auth_service.login(request.email, request.password, ip_address)

    return TokenResponse(**result)


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """Register new user account.

    Security Features:
    - Password strength validation (min 8 characters)
    - Bcrypt password hashing (cost factor 12)
    - Duplicate email prevention
    - Automatic token generation

    Args:
        request: Registration details (email, password, name, optional license_key)

    Returns:
        Access token for new account

    Raises:
        HTTPException 400: Invalid input or email already exists
        HTTPException 500: Database error

    """
    # Input validation
    if not request.email or not request.password or not request.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email, password, and name are required",
        )

    # Register using secure service
    auth_service = get_auth_service()
    result = auth_service.register(
        email=request.email,
        password=request.password,
        name=request.name,
        license_key=request.license_key,
    )

    return TokenResponse(**result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Refresh access token.

    Args:
        credentials: Current bearer token

    Returns:
        New access token with extended expiration

    Raises:
        HTTPException 401: Invalid or expired token

    """
    auth_service = get_auth_service()
    result = auth_service.refresh_token(credentials.credentials)

    return TokenResponse(**result)


@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user info.

    Args:
        credentials: Bearer token

    Returns:
        User information (id, email, name)

    Raises:
        HTTPException 401: Invalid or expired token

    """
    auth_service = get_auth_service()
    user = auth_service.get_current_user(credentials.credentials)

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
    }


@router.post("/validate-license")
async def validate_license(
    license_key: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Validate a license key.

    Note: This is a placeholder. Implement real license validation
    by connecting to license database or API.

    Args:
        license_key: License key to validate
        credentials: Bearer token

    Returns:
        License validation result

    """
    # Verify user is authenticated
    auth_service = get_auth_service()
    auth_service.verify_token(credentials.credentials)

    # Placeholder implementation
    # TODO: Implement real license validation
    return {
        "valid": True,
        "license_type": "developer",
        "plugins": ["software", "healthcare"],
        "expires_at": None,  # Perpetual license
    }
