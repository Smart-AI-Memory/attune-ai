"""Gate: a Redis client must dial the RESOLVED endpoint, never a literal
or implicit one (library-review class H1).

H1 is the *split-brain reachability oracle*: a probe that answers about a
different endpoint than the one real clients use. It has two shapes, and
the second is subtle enough that it was reintroduced by H1's own fix:

1. **Implicit or literal endpoint.** ``redis.Redis()`` with no host/port
   silently defaults to ``localhost:6379``. A health command built that
   way reports "Redis server reachable" about a server the user does not
   use — found live in ``attune doctor`` (2026-08-21).
2. **Decomposing a resolved URL into host+port.** host+port cannot carry
   the scheme, db or username, so ``rediss://alice:pw@cache:6380/3`` gets
   probed over a plain socket at db 0 with no user. Every TLS, ACL and
   unix-socket deployment reads DOWN. Caught by the codex D11 lane on the
   tier-1 fix branch — "H1, one layer up, introduced by the H1 fix."

The rule therefore targets the *endpoint source*, not the call site: a
client construction whose endpoint is implicit or literal cannot reflect
a resolved URL, so it is a candidate second oracle. Constructions that
splat a resolved config (``Redis(**cfg.to_redis_kwargs())``) or pass
resolver-derived names are correct and must not trip.

Canonical factories, which every caller should prefer:
``attune.memory.config.redis_probe_client`` / ``ping_redis`` and
``attune.memory.recall_redis.connect_recall_redis`` — all of which reach
``redis.Redis.from_url(resolved_url)`` and preserve scheme, db and user.

``from_url`` is never flagged: it takes the whole URL by construction.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOTS = (REPO_ROOT / "src" / "attune", REPO_ROOT / "attune_redis")

#: Direct client constructors. ``from_url`` is deliberately absent — it
#: consumes a full URL and is the shape this gate steers callers toward.
_CLIENT_CTORS = {"Redis", "StrictRedis"}

#: Keywords that name an endpoint. A literal here pins the probe to an
#: address the resolver never saw.
_ENDPOINT_KWARGS = {"host", "port", "unix_socket_path", "url"}

#: Modules permitted to construct a client directly, each with its reason.
#: Ratchets shrink-only, like the path-validation allowlist.
#:
#: EMPTY, and that is the finding. The class register carries a standing
#: caution to "delete or allowlist the deprecated
#: redis_memory_{coordination,storage}.py twins first — they trip any rule
#: written for the live code." They do not trip THIS rule: they take host
#: and port as function PARAMETERS, and a parameter is not a literal. Nor
#: does the canonical resolver, whose host/port branch passes
#: resolver-derived names. Keying the rule on where the endpoint COMES
#: FROM, rather than on which call sites are allowed to construct clients,
#: makes the exemption unnecessary — so the gate needs no escape hatch,
#: and there is no allowlist entry to review later.
ALLOWLIST: dict[str, str] = {}


def _is_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str | int)


def _endpoint_is_resolved(call: ast.Call) -> bool:
    """True if the endpoint plausibly comes from the resolver.

    A ``**kwargs`` splat carries a resolved config wholesale; a non-literal
    host/port is a name or call, i.e. computed rather than pinned.
    """
    if any(kw.arg is None for kw in call.keywords):  # **splat
        return True
    endpoint_kws = [kw for kw in call.keywords if kw.arg in _ENDPOINT_KWARGS]
    if not endpoint_kws:
        return False  # implicit endpoint -> localhost:6379
    return all(not _is_literal(kw.value) for kw in endpoint_kws)


def _offending_sites(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError):
        return []

    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name not in _CLIENT_CTORS:
            continue
        if _endpoint_is_resolved(node):
            continue
        how = "implicit (defaults to localhost:6379)"
        lits = [
            f"{kw.arg}={kw.value.value!r}"
            for kw in node.keywords
            if kw.arg in _ENDPOINT_KWARGS and _is_literal(kw.value)
        ]
        if lits:
            how = "literal " + ", ".join(lits)
        hits.append(f"{_label(path)}:{node.lineno}  {name}(...) — {how}")
    return hits


def _label(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _shipped_modules() -> list[Path]:
    out: list[Path] = []
    for root in SRC_ROOTS:
        if root.exists():
            out.extend(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(out)


def _current_offenders() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for module in _shipped_modules():
        hits = _offending_sites(module)
        if hits:
            found[_label(module)] = hits
    return found


def test_no_unresolved_redis_endpoint() -> None:
    """No shipped module may dial a literal or implicit Redis endpoint."""
    offenders = {k: v for k, v in _current_offenders().items() if k not in ALLOWLIST}
    detail = "\n".join(f"  {line}" for lines in offenders.values() for line in lines)
    assert not offenders, (
        "Redis client dialing an unresolved endpoint (class H1 — split-brain "
        f"reachability oracle):\n{detail}\n\n"
        "A probe built this way answers about a different server than real "
        "clients use: an implicit endpoint is localhost:6379 regardless of "
        "REDIS_URL, and a literal one ignores scheme, db and username.\n"
        "Use attune.memory.config.ping_redis / redis_probe_client, or "
        "attune.memory.recall_redis.connect_recall_redis — all reach "
        "redis.Redis.from_url(resolved_url)."
    )


def test_allowlist_entries_are_still_needed() -> None:
    """The allowlist ratchets down: stale entries must be removed."""
    offenders = _current_offenders()
    missing = sorted(m for m in ALLOWLIST if not (REPO_ROOT / m).exists())
    assert not missing, f"ALLOWLIST entries for deleted modules — remove them: {missing}"
    stale = sorted(m for m in ALLOWLIST if m not in offenders)
    assert not stale, (
        "ALLOWLIST entries no longer needed (module now resolves its "
        f"endpoint or dropped its client construction) — remove them: {stale}"
    )


def test_rule_flags_the_implicit_endpoint(tmp_path: Path) -> None:
    """The zero-arg form is the shape that bit `attune doctor`."""
    module = tmp_path / "implicit.py"
    module.write_text(
        "import redis\n"
        "def check() -> bool:\n"
        "    client = redis.Redis(socket_connect_timeout=2)\n"
        "    return bool(client.ping())\n",
        encoding="utf-8",
    )
    hits = _offending_sites(module)
    assert hits and "implicit" in hits[0], hits


def test_rule_flags_a_literal_endpoint(tmp_path: Path) -> None:
    module = tmp_path / "literal.py"
    module.write_text(
        "import redis\n"
        "def check() -> bool:\n"
        "    client = redis.Redis(host='localhost', port=6379)\n"
        "    return bool(client.ping())\n",
        encoding="utf-8",
    )
    hits = _offending_sites(module)
    assert hits and "literal" in hits[0], hits


def test_rule_clears_resolved_shapes(tmp_path: Path) -> None:
    """from_url, a config splat, and resolver-derived names all pass."""
    module = tmp_path / "resolved.py"
    module.write_text(
        "import redis\n"
        "def a(url):\n"
        "    return redis.Redis.from_url(url)\n"
        "def b(cfg):\n"
        "    return redis.Redis(**cfg.to_redis_kwargs())\n"
        "def c(env):\n"
        "    h, p = resolved_redis_endpoint(env)\n"
        "    return redis.Redis(host=h, port=p)\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module)


def test_canonical_factories_are_clean() -> None:
    """The factories this gate points callers at must not be offenders."""
    recall = REPO_ROOT / "src/attune/memory/recall_redis.py"
    if recall.exists():
        assert not _offending_sites(recall)
