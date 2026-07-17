"""Extras-honesty guard — install hints in src/ point at real extras.

pip only warns on UNDEFINED extras; a defined-but-EMPTY extra installs
silently with no warning. That combination once produced an unfixable
loop: the rag-code-gen error said ``pip install 'attune-ai[rag]'``
while ``rag = []`` was a no-op alias — the command succeeded, installed
nothing, and the error persisted (fixed in #758 by pointing the message
at the real package). Nothing has enforced the property since: a
message referencing a new extra, or an extra being emptied out from
under an existing message, both ship green.

Policy pinned here:

1. Every ``attune-ai[X]`` reference in ``src/`` (non-comment lines)
   names a DEFINED extra in pyproject.
2. A reference to an EMPTY extra is allowed only via
   ``EMPTY_ALIAS_ALLOWLIST`` — a deliberate, documented back-compat
   alias whose deps moved to core (e.g. ``[redis]`` after #1248).
   Emptying an extra that live messages still point at fails loudly.
3. Stale allowlist entries prune themselves: each entry must still be
   defined-and-empty AND still referenced.

Related-but-different enforcer (checked before building this — see the
"grep for an existing enforcer" lesson): doc_audit's
``check_install_extras_consistency`` compares README extras to
pyproject, but it is a workflow check (not CI-required), covers only
README, and does not catch the empty-extra trap.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
#: Every Python package that SHIPS IN THE WHEEL (packages.find scans
#: both `src` and `.`). Scanning only src/attune left attune_redis's
#: 6 MCP error hints invisible — the #758 trap survived #1418 there
#: precisely because this list used to be one root. If a new bundled
#: package is added, add it here.
SCAN_ROOTS = [
    REPO_ROOT / "src" / "attune",
    REPO_ROOT / "attune_redis",
    REPO_ROOT / "attune_software",
]

#: Empty extras that are allowed to exist — each must be a deliberate
#: back-compat alias whose deps were promoted to core, documented by the
#: pyproject comment on the extra itself.
#:
#: Deliberately EMPTY since 2026-07-17: the six empty aliases (rag,
#: memory, redis, cache, agent-sdk, software) were deleted. They were
#: compat shims for install scripts that, at 8 external stargazers, no
#: user has — and they inflated the extras menu by 37% (22 -> 16).
#: Deleting them is safe precisely BECAUSE their deps are core: pip
#: warns on the unknown extra and still installs everything the user
#: wanted.
#:
#: Before adding an entry back, note what the [redis] entry got wrong:
#: an alias is defensible as an INSTALL target ("want redis? core
#: delivers it") but never as a REMEDIATION ("redis missing? run this")
#: — the second is a no-op that cannot fix the stated problem, which is
#: the #758 trap this guard exists to prevent. It shipped anyway,
#: allowlisted, for three months.
EMPTY_ALIAS_ALLOWLIST: dict[str, str] = {}


def _extras_with_dep_counts() -> dict[str, int]:
    """Parse [project.optional-dependencies] → {extra: dep count}.

    Line-based bracket tracking, not a single non-greedy regex across
    the block — dep specs like ``"pkg[extra]>=1"`` contain ``]`` and
    silently truncate greedy/non-greedy DOTALL matches (that exact bug
    produced a false "redis is not core" reading while building this
    test).
    """
    text = PYPROJECT.read_text(encoding="utf-8")
    block_match = re.search(
        r"^\[project\.optional-dependencies\]\n(.*?)(?=^\[)", text, re.MULTILINE | re.DOTALL
    )
    assert block_match, "pyproject.toml has no [project.optional-dependencies] table"

    extras: dict[str, int] = {}
    current: str | None = None
    depth = 0
    for line in block_match.group(1).splitlines():
        stripped = line.strip()
        if current is None:
            m = re.match(r"^([\w-]+)\s*=\s*\[", stripped)
            if not m:
                continue
            current = m.group(1)
            extras[current] = 0
            depth = stripped.count("[") - stripped.count("]")
        if current is not None:
            extras[current] += len(re.findall(r'"[^"]+"', stripped))
            if depth <= 0 or stripped.endswith("]"):
                # single-line array, or the closing bracket line
                if stripped.count("]") >= stripped.count("[") or depth <= 0:
                    current = None
                    continue
            depth += (
                stripped.count("[") - stripped.count("]")
                if not stripped.startswith(current or "")
                else 0
            )
    return extras


def _referenced_extras() -> dict[str, list[str]]:
    """{extra: [file:line, ...]} for every attune-ai[...] hint in the
    wheel's Python packages (see SCAN_ROOTS).

    Comment-only lines are skipped — a comment describing the pattern
    (doc_audit/checks.py does this) is not a user-facing install hint.
    Comma combos like [memory,redis] expand to individual extras.
    """
    refs: dict[str, list[str]] = {}
    files = (py for root in SCAN_ROOTS if root.is_dir() for py in sorted(root.rglob("*.py")))
    for py in files:
        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip().startswith("#"):
                continue
            for combo in re.findall(r"attune-ai\[([^\]]+)\]", line):
                for part in combo.split(","):
                    name = part.strip()
                    if name and not name.startswith("{"):  # skip f-string placeholders
                        where = f"{py.relative_to(REPO_ROOT)}:{lineno}"
                        refs.setdefault(name, []).append(where)
    return refs


def test_extras_parser_sees_known_ground_truth():
    """Self-check: the parser must agree with known pyproject facts, so
    the guard's own parsing can't silently rot (`developer` and `all`
    are populated; the deleted `redis` alias is gone)."""
    extras = _extras_with_dep_counts()
    assert extras.get("developer", 0) > 0
    assert extras.get("all", 0) > 0
    assert "redis" not in extras, (
        "the [redis] empty alias was deleted 2026-07-17 — if it is back, "
        "it needs an EMPTY_ALIAS_ALLOWLIST entry and a pyproject comment"
    )


def test_no_undocumented_empty_extras():
    """No extra may be empty unless it is an allowlisted back-compat alias.

    The pre-existing guard only caught empty extras that a src/ message
    REFERENCED. That left a blind spot: `rag`, `memory`, `cache`,
    `agent-sdk` and `software` were all empty AND unreferenced, so they
    sat in the menu as items that install nothing and nothing pointed
    at — invisible to every test here. This closes that: an empty extra
    is a fake menu item whether or not a message names it.
    """
    extras = _extras_with_dep_counts()
    empty = sorted(name for name, count in extras.items() if count == 0)
    undocumented = [name for name in empty if name not in EMPTY_ALIAS_ALLOWLIST]
    assert not undocumented, (
        f"extras defined with zero deps and no allowlist entry: "
        f"{undocumented}. `pip install 'attune-ai[X]'` would succeed and "
        f"install nothing. Either give the extra real deps, delete it, or "
        f"— only if its deps genuinely moved to core — add an "
        f"EMPTY_ALIAS_ALLOWLIST entry naming the promoting PR."
    )


def test_referenced_extras_are_defined():
    """Every install hint names an extra pyproject actually defines.

    An undefined extra makes the suggested pip command WARN and
    install nothing useful — the user followed our instruction and got
    nowhere.
    """
    extras = _extras_with_dep_counts()
    refs = _referenced_extras()
    undefined = {name: sites for name, sites in refs.items() if name not in extras}
    assert not undefined, (
        f"src/ install hints reference extras pyproject does not define: "
        f"{undefined}. Fix the message (point at the real extra or "
        f"package) — do not add a placeholder extra."
    )


def test_referenced_empty_extras_are_deliberate_aliases():
    """Referencing an EMPTY extra is the unfixable-loop trap unless the
    emptiness is a documented back-compat alias (deps now core).

    If this fails because you emptied an extra: either restore its
    deps, update every message that points at it, or — only if the
    deps genuinely moved to core — add an allowlist entry with the
    promoting PR.
    """
    extras = _extras_with_dep_counts()
    refs = _referenced_extras()
    bad = {
        name: sites
        for name, sites in refs.items()
        if extras.get(name) == 0 and name not in EMPTY_ALIAS_ALLOWLIST
    }
    assert not bad, (
        f"src/ install hints point at EMPTY extras (pip installs nothing, "
        f"silently — the #758 rag-loop trap): {bad}. See this test's "
        f"docstring for the three legitimate fixes."
    )


def test_empty_alias_allowlist_stays_true():
    """Prune allowlist entries when reality moves: each must still be
    defined, still empty, and still referenced by at least one hint."""
    extras = _extras_with_dep_counts()
    refs = _referenced_extras()
    stale = [name for name in EMPTY_ALIAS_ALLOWLIST if extras.get(name) != 0 or name not in refs]
    assert not stale, (
        f"EMPTY_ALIAS_ALLOWLIST entries no longer match reality (extra "
        f"gained deps, was removed, or nothing references it anymore): "
        f"{stale}. Remove them so the allowlist stays a true inventory."
    )
