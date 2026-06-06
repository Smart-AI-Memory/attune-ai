"""Session-token bootstrap route for the ops dashboard.

``GET /api/session/token`` returns the per-process client token. It is
intentionally **unauthenticated** — it's how a freshly-loaded page
bootstraps the token it then echoes on mutating requests. The token
grants nothing on its own; it only lets a client pass
``require_client_token`` on the mutating routes.
"""

from __future__ import annotations

from fastapi import APIRouter

from attune.ops.security import current_session_token

router = APIRouter()


@router.get("/api/session/token")
async def get_session_token() -> dict[str, str]:
    """Return the in-process client token for page bootstrap."""
    return {"token": current_session_token()}
