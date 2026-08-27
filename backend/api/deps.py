"""Shared authentication dependencies for API routers.

Every protected endpoint must depend on ``get_verified_principal`` —
it both extracts the bearer token AND verifies it. A bare
``Depends(HTTPBearer())`` only checks that the Authorization header is
syntactically valid, so any forged token would authenticate.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()


async def get_verified_principal(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Extract and verify the bearer token, returning the decoded principal.

    Args:
        credentials: Bearer token from the Authorization header

    Returns:
        Decoded JWT payload (sub, user_id, name, exp, iat)

    Raises:
        HTTPException 401: If the token is invalid, expired, or forged

    """
    # Imported lazily so routers that share this dependency do not pull
    # the auth service (jwt/bcrypt/database) into their import graph.
    from .auth import get_auth_service

    return get_auth_service().verify_token(credentials.credentials)
