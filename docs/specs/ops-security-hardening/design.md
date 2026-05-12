# Design — Ops Dashboard Security Hardening

**Status:** complete (2026-05-12, pending Phase 5 smoke)

Technical shape. See `decisions.md` for context, `requirements.md` for stories, `tasks.md` for the phase plan.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Browser / attacker.com (DNS-rebound to 127.0.0.1)           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ TCP to localhost:8766
┌─────────────────────────────────────────────────────────────┐
│ FastAPI app                                                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ TrustedHostMiddleware (NEW)                         │    │
│  │  - reads request.headers["host"]                    │    │
│  │  - case-insensitive lookup in allowlist             │    │
│  │  - allowlist = computed from config at startup      │    │
│  │  - match → next                                     │    │
│  │  - no match → 400 + WARN log                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Existing routes (workflows, specs, runs, telemetry) │    │
│  │ (unchanged)                                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

The middleware is the only new layer. Everything downstream is unchanged.

---

## Module-by-module changes

### `src/attune/ops/config.py`

Add one field to the `Config` dataclass:

```python
trusted_hosts: tuple[str, ...] = ()  # user-specified additions to the allowlist
```

Add `trusted_hosts` parameter to `build_config()`.

### `src/attune/ops/cli.py`

Add the `--trusted-host` flag with `action="append"` (repeatable):

```python
parser.add_argument(
    "--trusted-host",
    action="append",
    default=None,
    metavar="HOST",
    help=(
        "Repeatable. Hostname (optionally with :port) accepted in the "
        "Host: header. Use when reaching the dashboard via a tunnel, "
        "reverse proxy, or non-default hostname. Example: "
        "--trusted-host my-tunnel.example.com"
    ),
)
```

In `main()`, pass `trusted_hosts=tuple(args.trusted_host or ())` to `build_config()`.

Also: detect the `0.0.0.0` + no-trusted-host combination and print a yellow warning to stderr:

```python
if args.host == "0.0.0.0" and not args.trusted_host:
    print(
        "WARNING: Binding to 0.0.0.0 without --trusted-host means any "
        "external hostname will be rejected by the security middleware. "
        "Add --trusted-host <external-hostname> for each hostname you "
        "intend to reach the dashboard at.",
        file=sys.stderr,
    )
```

### `src/attune/ops/middleware.py` (NEW)

The middleware itself:

```python
"""Host header allowlist middleware.

Defends against DNS-rebinding attacks. A browser visiting a malicious
site can be tricked into sending requests to localhost via a DNS
rebind, but the Host: header it sends will still be the original
attacker domain — not localhost. This middleware rejects requests
whose Host header isn't on the allowlist.

See docs/specs/ops-security-hardening/decisions.md for the threat
model walkthrough.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Host header isn't on the allowlist.

    Allowlist comparison is case-insensitive. Missing Host header
    (HTTP/1.0 or pathological clients) is treated as untrusted.
    """

    def __init__(self, app, *, allowed_hosts: Iterable[str]) -> None:
        super().__init__(app)
        # Lowercase for case-insensitive compare. Frozen set for O(1) lookup.
        self._allowed = frozenset(h.lower() for h in allowed_hosts)

    async def dispatch(self, request: Request, call_next):
        host = (request.headers.get("host") or "").lower()
        if host not in self._allowed:
            logger.warning(
                "rejected request: untrusted Host header",
                extra={"host": host[:200] or "<empty>", "path": request.url.path},
            )
            return JSONResponse(
                {"detail": "untrusted Host header"},
                status_code=400,
            )
        return await call_next(request)


def compute_allowlist(host: str, port: int, extras: Iterable[str] = ()) -> set[str]:
    """Compute the default + user-supplied Host allowlist."""
    hosts: set[str] = {f"{host}:{port}"}
    # Loopback aliases — make `localhost` and `127.0.0.1` interchangeable
    # when bound to a loopback or all-interfaces address.
    if host in ("127.0.0.1", "0.0.0.0", "localhost"):
        hosts.add(f"localhost:{port}")
        hosts.add(f"127.0.0.1:{port}")
    for extra in extras:
        hosts.add(extra)
        if ":" not in extra:
            # No port specified: accept both http (80) and https (443)
            hosts.add(f"{extra}:80")
            hosts.add(f"{extra}:443")
    return hosts
```

### `src/attune/ops/server.py`

Mount the middleware in `create_app()`:

```python
from attune.ops.middleware import TrustedHostMiddleware, compute_allowlist

# Inside create_app(), after FastAPI(...) construction:
allowed = compute_allowlist(
    host=config.host,
    port=config.port,
    extras=config.trusted_hosts,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)
```

Order matters: this should be ABOVE any other middleware (CORS, GZip) so untrusted requests get rejected before any other processing.

### `src/attune/ops/runner.py`

One-line change at line ~90:

```python
queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=1000)
```

The existing `except QueueFull` block in `_broadcast` (line ~74) becomes live. No other changes.

### `src/attune/ops/routes/dashboard.py`

Add logging to `run_view_page`:

```python
import logging
logger = logging.getLogger(__name__)

# ... inside run_view_page, in the not-found branch:
if run is None:
    logger.info("run_view: not found", extra={"run_id": run_id})
    raise HTTPException(...)

# In the invalid-slug branch:
if not _re.match(...):
    logger.warning(
        "run_view: invalid run_id",
        extra={"run_id_input": run_id[:64]},
    )
    raise HTTPException(...)
```

---

## Failure modes

| Failure | Behavior |
|---------|----------|
| Browser sends request with rebound Host header | Middleware rejects → 400 + WARN log → no workflow runs |
| User accesses via localhost (default) | Allowlist hit → request proceeds normally |
| User configures `--trusted-host external.example.com` | Both `external.example.com:80` and `:443` added to allowlist; tunneled access works |
| User starts with `--host 0.0.0.0` and no `--trusted-host` | Server starts with WARNING; any non-loopback Host header is rejected |
| Subscriber stops consuming the SSE stream | After 1000 buffered events, `put_nowait` raises `QueueFull`; existing handler drops the subscriber |
| Subscriber drops mid-run | Subscriber's queue is bounded; no leak |
| Direct attempt to call `/api/info` via DNS rebind | 400, never reaches the route |

---

## Security properties

After this hardening:

| Threat | Mitigated? | How |
|--------|------------|-----|
| Direct external network access | Already mitigated by `127.0.0.1` bind | Pre-existing |
| DNS-rebinding attack | YES (new) | TrustedHost middleware |
| CSRF from a same-origin attacker (impossible without compromised localhost) | N/A | Outside threat model |
| Subprocess sandbox escape | No (out of scope) | Future spec |
| Workflow with embedded shell injection | No (out of scope) | Workflow-author responsibility |
| Memory exhaustion via slow subscriber | YES (new) | Queue bound |

---

## Backward compatibility

- `attune ops` (no flags) still works — defaults bind to `127.0.0.1:8765`, default allowlist covers it.
- All existing curl / browser requests against `localhost:<port>` continue to succeed.
- The middleware adds ~50µs of per-request overhead (one set lookup) — negligible.
- The queue bound is invisible to fast subscribers — the existing buffer of 1k events covers any realistic dashboard usage.

---

## Open design notes

- **Starlette's built-in `TrustedHostMiddleware`** exists but supports only wildcard patterns and `allowed_hosts`. We need a custom one because we want to log rejections, support explicit ports, and add the loopback aliases. The custom one is ~30 LOC vs. wrapping starlette's.
- **CORS middleware** is intentionally NOT added. Same-origin baseline lets attackers send the request anyway; CORS would only stop them reading the response. Host validation rejects the request altogether.
- **Pre-flight (OPTIONS)** requests: ATLAS — FastAPI handles OPTIONS for any registered route. The middleware applies to OPTIONS too, so a rebound CORS preflight would also fail. Good.
