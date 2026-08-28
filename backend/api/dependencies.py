"""Shared FastAPI dependencies for the backend API.

Provides a single verified-principal dependency so protected routes reject
forged, invalid, or expired bearer tokens instead of accepting any non-empty
``Authorization`` header. Replaces the bare ``HTTPBearer`` injection that only
proved a header was *present*, never that the token was *valid*.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.services.auth_service import verify_access_token

# ``auto_error=True`` (default) rejects a missing/malformed Authorization
# header with 403 before ``require_principal`` runs.
security = HTTPBearer()


def require_principal(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Verify the bearer token and return the authenticated principal.

    Use as ``principal: dict[str, Any] = Depends(require_principal)`` on any
    route that must be authenticated. The returned payload is the decoded JWT
    (``sub``, ``user_id``, ``name``, ...).

    Args:
        credentials: Bearer credentials extracted by ``HTTPBearer``.

    Returns:
        The decoded, verified token payload.

    Raises:
        HTTPException: 401 if the token is invalid or expired (403 for a
            missing/malformed header, raised earlier by ``HTTPBearer``).

    """
    return verify_access_token(credentials.credentials)
