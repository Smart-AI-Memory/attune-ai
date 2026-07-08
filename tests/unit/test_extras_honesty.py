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
SRC_ROOT = REPO_ROOT / "src" / "attune"

#: Empty extras that install hints may still reference — each is a
#: deliberate back-compat alias whose deps were promoted to core.
#: Adding an entry is a packaging decision: the pyproject comment for
#: the extra must document the promotion, as [redis]'s does.
EMPTY_ALIAS_ALLOWLIST: dict[str, str] = {
    "redis": "redis client promoted to core deps 2026-07-04 (#1248); alias kept for back-compat",
}


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
    """{extra: [file:line, ...]} for every attune-ai[...] hint in src/.

    Comment-only lines are skipped — a comment describing the pattern
    (doc_audit/checks.py does this) is not a user-facing install hint.
    Comma combos like [memory,redis] expand to individual extras.
    """
    refs: dict[str, list[str]] = {}
    for py in sorted(SRC_ROOT.rglob("*.py")):
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
    """Self-check: the parser must agree with known pyproject facts,
    so the guard's own parsing can't silently rot (developer is
    populated; redis is a defined empty alias)."""
    extras = _extras_with_dep_counts()
    assert extras.get("developer", 0) > 0
    assert "redis" in extras and extras["redis"] == 0


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
