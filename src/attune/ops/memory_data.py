"""Read-only view of the Redis-derived memory index (framework-free).

C1 of ``docs/specs/ops-dashboard-polish/``, premise re-validated
2026-07-21: the original row targeted ``~/.attune/memory/`` key files,
which memory-unification (#1239) retired. The serving layer today is
the local-Redis derived index — ``attune:memory:*`` hashes hydrated at
session start from the tracked corpus (curated nodes, lessons, file
pointers, edges). This module reads THAT, read-only.

Degradation contract (mirrors the corpus rule "degrade silently when
Redis is unreachable"): every public function returns ``None`` when
Redis is absent/unreachable — the page renders an explanatory empty
state, never a 500. No function here ever writes a key; the index is
DERIVED and its writers are the hydration scripts only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

#: Prefix every served memory key carries. Also the detail-view guard:
#: a requested key outside this namespace is refused (the ops page must
#: never become a generic Redis browser).
MEMORY_KEY_PREFIX = "attune:memory:"

#: Family → human label, in display order. A key's family is the
#: segment after the prefix (``attune:memory:<family>:...``).
FAMILY_LABELS: dict[str, str] = {
    "curated": "Curated nodes",
    "lesson": "Lessons",
    "file": "File pointers",
    "edges": "Edges",
}

_SCAN_COUNT = 500

#: Per-page rows for the node table.
PAGE_SIZE = 50


@dataclass
class MemoryNodeRow:
    """One row in the /memory node table."""

    key: str
    family: str
    name: str
    node_type: str = ""
    description: str = ""
    updated_at: str = ""


@dataclass
class MemoryOverview:
    """Family counts + one page of node rows."""

    total: int
    family_counts: dict[str, int] = field(default_factory=dict)
    rows: list[MemoryNodeRow] = field(default_factory=list)
    family: str | None = None
    page: int = 1
    pages: int = 1


def connect(url: str | None = None) -> Any | None:
    """Return a pinging Redis client, or None when unavailable.

    Import and connection failures both degrade to ``None`` — the
    caller renders the unreachable empty state.
    """
    try:
        import redis  # noqa: PLC0415
    except ImportError:
        logger.debug("redis package not importable; /memory degrades")
        return None
    try:
        client = redis.Redis.from_url(
            url or "redis://localhost:6379/0",
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=1.0,
        )
        client.ping()
    except Exception:  # noqa: BLE001
        # INTENTIONAL: any connection-layer surprise (refused, auth,
        # timeout) is the same user-facing fact — index unreachable.
        logger.debug("Redis unreachable; /memory degrades", exc_info=True)
        return None
    return client


def _family_of(key: str) -> str:
    rest = key[len(MEMORY_KEY_PREFIX) :]
    return rest.split(":", 1)[0] if rest else ""


def _display_name(key: str) -> str:
    rest = key[len(MEMORY_KEY_PREFIX) :]
    parts = rest.split(":", 1)
    return parts[1] if len(parts) > 1 else rest


def _scan_keys(client: Any) -> list[str]:
    return sorted(k for k in client.scan_iter(match=MEMORY_KEY_PREFIX + "*", count=_SCAN_COUNT))


def read_overview(
    family: str | None = None,
    page: int = 1,
    client: Any | None = None,
) -> MemoryOverview | None:
    """Family counts plus one page of node rows.

    Args:
        family: Restrict the row table to one family (counts always
            cover every family). Unknown families yield zero rows.
        page: 1-based page over the (sorted) filtered keys.
        client: Injected Redis client (tests); ``None`` connects.

    Returns:
        The overview, or ``None`` when Redis is unreachable.
    """
    client = client or connect()
    if client is None:
        return None
    try:
        keys = _scan_keys(client)
        counts: dict[str, int] = {}
        for key in keys:
            fam = _family_of(key)
            counts[fam] = counts.get(fam, 0) + 1

        filtered = [k for k in keys if family is None or _family_of(k) == family]
        pages = max(1, -(-len(filtered) // PAGE_SIZE))
        page = min(max(1, page), pages)
        window = filtered[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

        rows = []
        pipe = client.pipeline(transaction=False)
        for key in window:
            pipe.hmget(key, "type", "description", "updated_at")
        # raise_on_error=False: a non-hash key in the namespace (e.g. a
        # plain-string marker like attune:memory:context) yields a
        # WRONGTYPE entry in the result list instead of failing the
        # whole page — dogfooded live 2026-07-21.
        for key, fields in zip(window, pipe.execute(raise_on_error=False), strict=False):
            if isinstance(fields, Exception):
                fields = (None, None, None)
            node_type, description, updated_at = fields
            rows.append(
                MemoryNodeRow(
                    key=key,
                    family=_family_of(key),
                    name=_display_name(key),
                    node_type=node_type or "",
                    description=(description or "")[:300],
                    updated_at=updated_at or "",
                )
            )
        return MemoryOverview(
            total=len(keys),
            family_counts=counts,
            rows=rows,
            family=family,
            page=page,
            pages=pages,
        )
    except Exception:  # noqa: BLE001
        # INTENTIONAL: a mid-read connection drop degrades exactly like
        # an initial connect failure.
        logger.debug("Redis read failed; /memory degrades", exc_info=True)
        return None


def read_node(key: str, client: Any | None = None) -> dict[str, str] | None:
    """All hash fields of one memory node, or None.

    ``None`` covers three cases the page renders identically as
    not-found/unreachable: key outside the memory namespace, missing
    key, or Redis unreachable. The namespace guard is the security
    boundary — the detail view must never read arbitrary keys.
    """
    if not key.startswith(MEMORY_KEY_PREFIX):
        return None
    client = client or connect()
    if client is None:
        return None
    try:
        # Most nodes are hashes; a few namespace keys are plain strings
        # (e.g. hydration markers). Dispatch on the actual type so a
        # non-hash node renders its value instead of degrading.
        key_type = client.type(key)
        if key_type == "hash":
            fields = client.hgetall(key)
        elif key_type == "string":
            value = client.get(key)
            fields = {"value": value} if value is not None else {}
        elif key_type in ("none", None):
            fields = {}
        else:
            fields = {"type": key_type, "note": "unsupported value type for display"}
    except Exception:  # noqa: BLE001
        # INTENTIONAL: same degradation contract as read_overview.
        logger.debug("Redis node read failed; /memory degrades", exc_info=True)
        return None
    return fields or None


def node_count(client: Any | None = None) -> int | None:
    """Total served memory keys, or None when Redis is unreachable.

    Cheap enough for the Home KPI (one SCAN over ~1k keys); the KPI
    hides itself on ``None`` rather than showing a lying zero.
    """
    client = client or connect()
    if client is None:
        return None
    try:
        return sum(1 for _ in client.scan_iter(match=MEMORY_KEY_PREFIX + "*", count=_SCAN_COUNT))
    except Exception:  # noqa: BLE001
        # INTENTIONAL: same degradation contract as read_overview.
        logger.debug("Redis count failed; /memory degrades", exc_info=True)
        return None
