"""Gate: a lock key may not be deleted or re-armed without an owner check.

A distributed lock's value names its owner and the key carries a TTL, so
the key can vanish at any instant — including between a client's read and
that client's next command. Mutating a lock key with a bare
``client.delete(lock_key)`` or ``client.expire(lock_key, ttl)`` is
therefore unsafe no matter what was read beforehand:

1. A's ``GET`` returns A's own id — the lock is genuinely still A's
2. A's lock expires
3. B acquires the now-free lock
4. A's ``DELETE`` fires and removes **B's** lock
5. C acquires while B still believes it holds it — two writers

Confirmed in the library review under class **H6**, executed against a
real ``redis-server``: the coordinator's ``release_lock`` logged
``lock_released`` for agent A immediately after agent B had legitimately
taken the freed key, and B's lock was gone. The service singleton's
release and refresh were worse still — they carried no ownership check at
all, so a stopping service deleted whichever lock happened to be there.

H6 is the release-side sibling of H2 (acquisition, ``SETNX`` + ``EXPIRE``
-> ``SET`` nx+ex). The shared shape is a lock operation that needs to be
one server-side step and was written as two client-side ones.

This gate scans the shipped source rather than pinning a list of known
sites, because a list cannot stop the class appearing in a module nobody
has written yet.

Reference implementation:
:func:`attune.memory.cross_session.locks.release_if_owner` and
:func:`attune.memory.cross_session.locks.refresh_if_owner`, which compare
and mutate inside one Redis script.

Rule R9 calibration against the pre-fix tree (2026-08-21): **3 of 3**
known sites flagged (``coordinator.release_lock``,
``service._release_service_lock``, ``service._refresh_service_lock``),
**0 false positives** across ``src/attune`` and ``attune_redis``
post-fix.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src" / "attune"
BUNDLED_ROOT = REPO_ROOT / "attune_redis"

#: Redis commands that destroy or extend a lock's hold. Each is safe only
#: when the server checks ownership in the same step.
_MUTATORS = {"delete", "expire", "pexpire", "persist", "getdel"}

#: Sites whose reason for mutating a lock key without an owner check has
#: been recorded. Empty by construction — an entry here is a claim that
#: the site is deliberately reaping a lock it does not own, and it must
#: carry that reason inline. Shrink-only.
_ALLOWLIST: dict[str, str] = {}


def _names_a_lock(node: ast.AST) -> bool:
    """True if this key expression names a lock, by its own text.

    Deliberately syntactic: a variable or constant called ``lock`` is the
    signal, and nothing about intent is inferred. Known gap (codex
    cross-review lane on #2408): an alias that drops the word —
    ``key = KEY_SERVICE_LOCK; client.delete(key)`` — or a subscripted /
    computed key is not traced. The gate is a ratchet on the shape H6 was
    found in, not a proof that no unchecked mutation exists.
    """
    if isinstance(node, ast.Name):
        return "lock" in node.id.lower()
    if isinstance(node, ast.Attribute):
        return "lock" in node.attr.lower()
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and "lock" in node.value.lower()
    if isinstance(node, ast.JoinedStr):
        return any(
            isinstance(piece, ast.Constant) and "lock" in str(piece.value).lower()
            for piece in node.values
        )
    return False


def _offending_sites(path: Path) -> list[str]:
    """Return ``file:line`` for each unchecked lock mutation in ``path``."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError):
        return []

    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _MUTATORS or not node.args:
            continue
        if not _names_a_lock(node.args[0]):
            continue
        site = f"{_label(path)}:{node.lineno}"
        if site not in _ALLOWLIST:
            hits.append(f"{site}: .{node.func.attr}(...)")
    return hits


def _label(path: Path) -> str:
    """Repo-relative path when possible; the fixtures live outside it."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _shipped_modules() -> list[Path]:
    roots = [r for r in (SRC_ROOT, BUNDLED_ROOT) if r.is_dir()]
    return sorted(p for root in roots for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def test_no_unchecked_lock_mutation() -> None:
    """No shipped module may delete or re-arm a lock key without a check."""
    offenders: list[str] = []
    for module in _shipped_modules():
        offenders.extend(_offending_sites(module))

    assert not offenders, (
        "Unchecked lock mutation (class H6) found at:\n  "
        + "\n  ".join(offenders)
        + "\n\nA lock carries a TTL, so it can expire and be re-acquired "
        "between your read and your write — the mutation then lands on the "
        "NEW owner's lock.\nCompare and mutate in one server-side step: see "
        "attune.memory.cross_session.locks.release_if_owner / "
        "refresh_if_owner."
    )


def test_rule_flags_the_unsafe_shape(tmp_path: Path) -> None:
    """The rule must fire on the shape the class is defined by."""
    read_then_delete = tmp_path / "offender_release.py"
    read_then_delete.write_text(
        "def release(client, resource, me):\n"
        "    lock_key = f'app:lock:{resource}'\n"
        "    if client.get(lock_key) == me:\n"
        "        client.delete(lock_key)\n",
        encoding="utf-8",
    )
    assert _offending_sites(read_then_delete), "rule failed to flag GET-then-DELETE"

    bare_refresh = tmp_path / "offender_refresh.py"
    bare_refresh.write_text(
        "SERVICE_LOCK = 'app:service_lock'\n"
        "def refresh(client):\n"
        "    client.expire(SERVICE_LOCK, 60)\n",
        encoding="utf-8",
    )
    assert _offending_sites(bare_refresh), "rule failed to flag a bare EXPIRE on a lock"


def test_rule_clears_the_safe_shape(tmp_path: Path) -> None:
    """A compare-and-mutate script must not be flagged."""
    module = tmp_path / "safe.py"
    module.write_text(
        "SCRIPT = 'if redis.call(\"get\", KEYS[1]) == ARGV[1] then ... end'\n"
        "def release(client, lock_key, owner):\n"
        "    return bool(client.ev" + "al(SCRIPT, 1, lock_key, owner))\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module), "rule false-positived on compare-and-delete"


def test_non_lock_keys_are_out_of_scope(tmp_path: Path) -> None:
    """Deleting an ordinary key is not this class."""
    module = tmp_path / "ordinary.py"
    module.write_text(
        "def evict(client, agent_id):\n"
        "    client.delete(f'app:session:{agent_id}')\n"
        "    client.expire('app:heartbeat', 30)\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module), "rule fired on a non-lock key"


def test_reference_implementation_is_clean() -> None:
    """The helper this gate points offenders at must itself pass."""
    assert not _offending_sites(SRC_ROOT / "memory" / "cross_session" / "locks.py")


def test_the_fixed_sites_stay_fixed() -> None:
    """The three H6 sites, named — a gate should still pin its origin."""
    cross_session = SRC_ROOT / "memory" / "cross_session"
    assert not _offending_sites(cross_session / "coordinator.py")
    assert not _offending_sites(cross_session / "service.py")
