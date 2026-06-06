"""Per-process client-token gate for the ops dashboard's mutating routes.

The ops server binds to loopback and serves a single local user, but
once ``--allow-run`` is on (the default) any client that can reach the
bind can issue mutations (`PUT .../status`, `POST .../run`, etc.).
A drive-by trigger — a stray ``curl``, a browser extension, an
a11y-traversing tool — could mutate state with no explicit user
action (see ops-specs-features Finding 0).

Defense in depth, mirrored from attune-gui's ``security.py``: mint a
per-process session token at startup, expose it via
``GET /api/session/token`` (and a ``<meta>`` tag the page reads at
load), and require it as the ``X-Attune-Client`` header on every
mutating route. A client that never loaded the page (raw ``curl``,
automation that didn't bootstrap the token) cannot mutate.

Not a multi-user or network-exposure security story — the loopback
bind + trusted-host middleware own that; this closes the
accidental-mutation-from-a-non-page-client bug class.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

# Minted once per process start. A new ops run invalidates old tokens,
# which is fine — the page reloads and picks up the new one.
_SESSION_TOKEN = secrets.token_urlsafe(32)


def current_session_token() -> str:
    """Return the in-process session token.

    Exposed via ``GET /api/session/token`` and injected into rendered
    pages as a ``<meta name="attune-client-token">`` tag.
    """
    return _SESSION_TOKEN


def require_client_token(
    x_attune_client: str | None = Header(default=None),
) -> None:
    """FastAPI dependency: 403 unless ``X-Attune-Client`` matches the token.

    Applied via ``Depends(require_client_token)`` on every mutating
    route. A missing or mismatched header is rejected before the route
    body runs.
    """
    if x_attune_client != _SESSION_TOKEN:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "invalid_client",
                "message": "Missing or invalid X-Attune-Client header.",
            },
        )
