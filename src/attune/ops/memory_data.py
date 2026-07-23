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
#: Families verified against the live index 2026-07-21: curated
#: nodes hydrate under ``node``, not ``curated``.
FAMILY_LABELS: dict[str, str] = {
    "node": "Curated nodes",
    "lesson": "Lessons",
    "file": "File pointers",
    "rule": "Rules",
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
    kind: str = ""
    description: str = ""
    size: str = ""


@dataclass
class MemoryOverview:
    """Family counts, kind counts, and one page of node rows."""

    total: int
    family_counts: dict[str, int] = field(default_factory=dict)
    kind_counts: dict[str, int] = field(default_factory=dict)
    rows: list[MemoryNodeRow] = field(default_factory=list)
    family: str | None = None
    kind: str | None = None
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


def _candidate_types(client: Any, candidates: list[str]) -> list[str]:
    """TYPE for every candidate key, one pipelined roundtrip.

    The index holds three value shapes; an HMGET-only pass rendered
    every non-hash row blank (live catch 2026-07-21).
    raise_on_error=False keeps one odd key from degrading the page.
    """
    pipe = client.pipeline(transaction=False)
    for key in candidates:
        pipe.type(key)
    return [
        t if not isinstance(t, Exception) else "none" for t in pipe.execute(raise_on_error=False)
    ]


def _hash_kinds(client: Any, candidates: list[str], key_types: list[str]) -> dict[str, str]:
    """The ``type`` hash field for hash candidates — each key's KIND.

    Resolves the kind counts and the kind filter. Local index ≤ a few
    thousand keys — one pipelined roundtrip.
    """
    hash_keys = [k for k, t in zip(candidates, key_types, strict=False) if t == "hash"]
    pipe = client.pipeline(transaction=False)
    for key in hash_keys:
        pipe.hmget(key, "type")
    kinds: dict[str, str] = {}
    for key, result in zip(hash_keys, pipe.execute(raise_on_error=False), strict=False):
        raw = None if isinstance(result, Exception) else (result or [None])[0]
        kinds[key] = raw or _family_of(key)
    return kinds


def _fetch_window_rows(
    client: Any,
    window: list[tuple[str, str]],
    hash_kinds: dict[str, str],
) -> list[MemoryNodeRow]:
    """Full row data for the visible page window only, type-dispatched."""
    pipe = client.pipeline(transaction=False)
    for key, key_type in window:
        if key_type == "hash":
            pipe.hmget(key, "type", "description", "text")
        elif key_type == "list":
            pipe.lrange(key, 0, -1)
        elif key_type == "string":
            pipe.get(key)
        elif key_type == "set":
            pipe.smembers(key)
        else:
            pipe.exists(key)
    return [
        _build_row(key, key_type, result, hash_kinds)
        for (key, key_type), result in zip(window, pipe.execute(raise_on_error=False), strict=False)
    ]


def read_overview(
    family: str | None = None,
    kind: str | None = None,
    page: int = 1,
    client: Any | None = None,
) -> MemoryOverview | None:
    """Family counts, kind counts, and one page of node rows.

    A key's *kind* is its content type: the ``type`` hash field for
    node/file hashes (``project``/``feedback``/…), the family itself
    for hashes without one (lessons), ``edge list`` for the JSON-edge
    lists, ``marker`` / ``set`` for the marker keys. Kinds are the
    second-level filter under the family tiles.

    Args:
        family: Restrict rows to one family (family counts always
            cover every family).
        kind: Restrict rows to one kind within the family selection
            (kind counts always cover the whole family selection).
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

        candidates = [k for k in keys if family is None or _family_of(k) == family]
        key_types = _candidate_types(client, candidates)
        hash_kinds = _hash_kinds(client, candidates, key_types)

        kinds = [
            _kind_of(key, key_type, hash_kinds)
            for key, key_type in zip(candidates, key_types, strict=False)
        ]
        kind_counts: dict[str, int] = {}
        for k in kinds:
            kind_counts[k] = kind_counts.get(k, 0) + 1

        selected = [
            (key, key_type)
            for key, key_type, k in zip(candidates, key_types, kinds, strict=False)
            if kind is None or k == kind
        ]
        pages = max(1, -(-len(selected) // PAGE_SIZE))
        page = min(max(1, page), pages)
        window = selected[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
        rows = _fetch_window_rows(client, window, hash_kinds)
        return MemoryOverview(
            total=len(keys),
            family_counts=counts,
            kind_counts=kind_counts,
            rows=rows,
            family=family,
            kind=kind,
            page=page,
            pages=pages,
        )
    except Exception:  # noqa: BLE001
        # INTENTIONAL: a mid-read connection drop degrades exactly like
        # an initial connect failure.
        logger.debug("Redis read failed; /memory degrades", exc_info=True)
        return None


def _kind_of(key: str, key_type: str, hash_kinds: dict[str, str]) -> str:
    if key_type == "hash":
        return hash_kinds.get(key, _family_of(key))
    if key_type == "list":
        return "edge list"
    if key_type == "set":
        return "set"
    if key_type == "string":
        return "marker"
    return "unknown"


def _human_size(chars: int) -> str:
    if chars >= 1024:
        return f"{chars / 1024:.1f} KB"
    return f"{chars} chars"


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _edge_preview(items: list[str]) -> str:
    """Human summary of a JSON edge list: ``→ target (TYPE)``."""
    import json  # noqa: PLC0415

    parts = []
    for raw in items[:2]:
        try:
            edge = json.loads(raw)
        except (TypeError, ValueError):
            continue
        target = edge.get("target", "?")
        edge_type = edge.get("type", "")
        parts.append(f"→ {target}" + (f" ({edge_type})" if edge_type else ""))
    return "; ".join(parts)


def _build_row(
    key: str,
    key_type: str,
    result: object,
    hash_kinds: dict[str, str],
) -> MemoryNodeRow:
    """One table row from a key's TYPE + type-appropriate fetch."""
    family = _family_of(key)
    name = _display_name(key)
    kind = _kind_of(key, key_type, hash_kinds)
    description = ""
    size = ""
    if isinstance(result, Exception):
        result = None
    if key_type == "hash" and isinstance(result, list | tuple):
        _raw_type, raw_desc, raw_text = (list(result) + [None] * 3)[:3]
        # Lessons (and some pointers) carry only ``text`` — fall back
        # to its first line so the column is informative, not blank.
        description = raw_desc or _first_line(raw_text or "")
        size = _human_size(len(raw_text or raw_desc or ""))
    elif key_type == "list" and isinstance(result, list | tuple):
        count = len(result)
        description = _edge_preview(list(result))
        size = f"{count} edge{'s' if count != 1 else ''}"
    elif key_type == "string":
        description = str(result or "")
        size = _human_size(len(description))
    elif key_type == "set" and isinstance(result, list | set | tuple | frozenset):
        members = sorted(str(m) for m in result)
        description = ", ".join(members[:5]) + ("…" if len(members) > 5 else "")
        size = f"{len(members)} member{'s' if len(members) != 1 else ''}"
    return MemoryNodeRow(
        key=key,
        family=family,
        name=name,
        kind=kind,
        description=description[:300],
        size=size,
    )


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
        # Dispatch on the actual type: hashes (nodes/lessons/files),
        # LISTS of JSON edge objects (edges family), plain-string and
        # set markers all live in the namespace.
        key_type = client.type(key)
        if key_type == "hash":
            fields = client.hgetall(key)
        elif key_type == "list":
            items = client.lrange(key, 0, 199)
            fields = {f"edge {i + 1}": item for i, item in enumerate(items)}
        elif key_type == "set":
            members = sorted(str(m) for m in client.smembers(key))
            fields = {"members": "\n".join(members)}
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


# --- Attention header (roundtable-ruled evolution, issue #1612) ---

#: Hydration older than this is flagged stale.
STALE_AFTER_HOURS = 24.0

#: Repo-relative corpus sources whose modification AFTER the last
#: hydration means the index is behind the corpus. Exact and
#: portable — no re-parse of the hydrator's discovery rules, so no
#: false drift from parsing mismatches.
CORPUS_SOURCES = (
    ".claude/lessons.md",
    ".claude/rules-tail",
)

_HYDRATED_AT_KEY = "attune:memory:hydrated_at"
_THREAD_KEY_MATCH = "attune:roundtable:thread:*"
_THREAD_META_SUFFIX = ":meta"


@dataclass
class MemoryAttention:
    """Exceptions-first header state for the /memory page."""

    hydrated_at: str | None = None
    age_hours: float | None = None
    stale: bool = False
    changed_since: list[str] = field(default_factory=list)
    pending_threads: int = 0

    @property
    def has_exceptions(self) -> bool:
        """True when any card should demand attention."""
        return self.stale or bool(self.changed_since) or self.pending_threads > 0


def _parse_stamp(raw: str | None) -> Any | None:
    from datetime import datetime, timezone

    if not raw:
        return None
    try:
        stamp = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _changed_since(project_root: Any, hydrated: Any) -> list[str]:
    """Repo corpus files modified after the hydration stamp."""
    from pathlib import Path

    changed: list[str] = []
    root = Path(project_root)
    for rel in CORPUS_SOURCES:
        source = root / rel
        candidates = source.rglob("*.md") if source.is_dir() else [source]
        for path in candidates:
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime > hydrated.timestamp():
                changed.append(str(path.relative_to(root)))
    return sorted(changed)


def _pending_threads(client: Any) -> int:
    """Board threads not yet promoted (best-effort count)."""
    pending = 0
    try:
        for key in client.scan_iter(match=_THREAD_KEY_MATCH, count=_SCAN_COUNT):
            if not str(key).endswith(_THREAD_META_SUFFIX):
                continue
            meta = client.hgetall(key)
            if isinstance(meta, dict) and meta.get("status") != "promoted":
                pending += 1
    except Exception:  # noqa: BLE001
        # INTENTIONAL: attention is advisory; board absence is not an error.
        return 0
    return pending


def read_attention(project_root: Any, url: str | None = None) -> MemoryAttention | None:
    """Exceptions-first facts for the attention header, or None.

    Same degradation contract as the rest of this module: ``None``
    when Redis is unreachable (the header simply doesn't render).
    Every fact is exact — hydration age from the hydrator's own
    stamp, drift from file mtimes vs that stamp, pending count from
    board thread meta. Nothing here re-parses corpus content.
    """
    from datetime import datetime, timezone

    client = connect(url)
    if client is None:
        return None

    attention = MemoryAttention()
    try:
        raw = client.get(_HYDRATED_AT_KEY)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: degradation contract.
        return None
    attention.hydrated_at = raw
    hydrated = _parse_stamp(raw)
    if hydrated is None:
        attention.stale = True
    else:
        age = (datetime.now(timezone.utc) - hydrated).total_seconds() / 3600.0
        attention.age_hours = round(age, 1)
        attention.stale = age > STALE_AFTER_HOURS
        attention.changed_since = _changed_since(project_root, hydrated)
    attention.pending_threads = _pending_threads(client)
    return attention
