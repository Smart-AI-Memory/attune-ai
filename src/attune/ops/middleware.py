"""Host header allowlist middleware — DNS-rebinding defense.

Defends against DNS-rebinding attacks. A browser visiting a malicious site
can be tricked into sending requests to localhost via a DNS rebind, but
the Host: header the browser sends still names the attacker's domain —
not localhost. This middleware rejects requests whose Host header isn't on
the allowlist.

Threat-model walkthrough lives in
``docs/specs/ops-security-hardening/decisions.md``.

Architectural notes:
- This is mounted FIRST in ``create_app()`` so untrusted requests are
  rejected before any other middleware or route processing.
- Comparison is case-insensitive and uses a frozen set for O(1) lookup.
- Missing Host header (HTTP/1.0, pathological clients) is treated as
  untrusted — same outcome as a wrong Host header.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """Reject requests whose ``Host`` header isn't on the allowlist.

    Allowlist comparison is case-insensitive. Empty / missing Host
    header is treated as untrusted.
    """

    def __init__(self, app: object, *, allowed_hosts: Iterable[str]) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        # Lowercase for case-insensitive compare. Frozen set for O(1) lookup.
        self._allowed = frozenset(h.lower() for h in allowed_hosts)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        host = (request.headers.get("host") or "").lower()
        if host not in self._allowed:
            # Truncate to 200 chars so a pathological header can't bloat
            # the log line. Path is bounded by the URL parser already.
            logger.warning(
                "ops.middleware: rejected untrusted Host header: " "host=%s path=%s",
                host[:200] or "<empty>",
                request.url.path,
            )
            return JSONResponse(
                {"detail": "untrusted Host header"},
                status_code=400,
            )
        return await call_next(request)


def compute_allowlist(
    host: str,
    port: int,
    extras: Iterable[str] = (),
) -> set[str]:
    """Compute the default + user-supplied Host allowlist.

    Args:
        host: Bind address from ``Config.host`` (e.g. ``"127.0.0.1"``,
            ``"0.0.0.0"``, ``"localhost"``).
        port: Bind port from ``Config.port``.
        extras: User-supplied trusted hostnames (from ``--trusted-host``).

    Returns:
        Set of ``"host:port"`` strings to accept in the Host header.
        Each extra without a port adds both ``:80`` and ``:443`` so
        http/https reverse-proxy setups work without each user having
        to think about ports.
    """
    hosts: set[str] = {f"{host}:{port}"}
    # Loopback aliases — make `localhost`, `127.0.0.1`, and `0.0.0.0`
    # interchangeable when bound to a loopback or all-interfaces address.
    # Without this, `attune ops` binds to 127.0.0.1 but browser typing
    # `localhost:8765` would 400.
    if host in ("127.0.0.1", "0.0.0.0", "localhost"):  # nosec B104
        hosts.add(f"localhost:{port}")
        hosts.add(f"127.0.0.1:{port}")
    for extra in extras:
        hosts.add(extra)
        if ":" not in extra:
            # No port specified: accept both http (80) and https (443).
            hosts.add(f"{extra}:80")
            hosts.add(f"{extra}:443")
    return hosts
