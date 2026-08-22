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
    # Constant-time compare: ``!=`` short-circuits on the first differing
    # byte, so response latency leaks a matching prefix and the token can
    # be recovered byte by byte. Compared as BYTES because
    # ``compare_digest`` raises TypeError on non-ASCII str — a header the
    # caller controls — which would surface as a 500 instead of a 403.
    expected = _SESSION_TOKEN
    if expected is None:
        # No token minted. Unreachable in production — the module global
        # is set at import — but the ops route tests null it to disable
        # the gate. Historical semantics preserved EXACTLY: only a
        # header-less request passes. Making this deny outright is a
        # defensible tightening (principle #7) but is a test-fixture
        # change, not part of the timing fix, and moves 92 tests.
        if x_attune_client is None:
            return
        raise HTTPException(
            status_code=403,
            detail={
                "code": "invalid_client",
                "message": "Missing or invalid X-Attune-Client header.",
            },
        )

    supplied = (x_attune_client or "").encode("utf-8", "surrogateescape")
    if not secrets.compare_digest(supplied, expected.encode("utf-8")):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "invalid_client",
                "message": "Missing or invalid X-Attune-Client header.",
            },
        )
