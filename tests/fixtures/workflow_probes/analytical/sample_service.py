"""Shared multi-defect fixture for the analytical-workflow probes.

DO NOT FIX the defects below — the defects ARE the fixture (see
tests/fixtures/workflow_probes/README.md). One file carries several
DISTINCT defect classes so the analytical probes can share a single
fixture workdir; each probe asserts its OWN class is surfaced:

    perf-audit      -> the O(n^2) membership scan in find_duplicates
    refactor-plan   -> the duplicated validate_* blocks
    simplify-code   -> the deeply-nested conditional in categorize
    code-review     -> the mutable default argument in append_tag
    deep-review     -> the same, plus the swallowed exception
    test-audit      -> every function here is public and untested
    doc-audit       -> summarize() is public with NO docstring

Not collected by pytest (filename avoids test_* / *_test patterns).
No security defects here — that class lives in ../security/.
"""

from __future__ import annotations


def find_duplicates(items: list[int]) -> list[int]:
    """Return values that appear more than once.

    SEEDED BUG (perf): O(n^2) — ``seen`` is a list and ``in`` scans it
    on every iteration. A set makes this O(n).
    """
    seen: list[int] = []
    dups: list[int] = []
    for item in items:
        if item in seen:  # linear scan every iteration
            dups.append(item)
        seen.append(item)
    return dups


def validate_name(value: str) -> bool:
    # SEEDED BUG (duplication): this block is copy-pasted in
    # validate_label and validate_tag below, differing only in the field
    # name — a refactor target.
    if value is None:
        return False
    if len(value.strip()) == 0:
        return False
    if len(value) > 64:
        return False
    return True


def validate_label(value: str) -> bool:
    if value is None:
        return False
    if len(value.strip()) == 0:
        return False
    if len(value) > 64:
        return False
    return True


def validate_tag(value: str) -> bool:
    if value is None:
        return False
    if len(value.strip()) == 0:
        return False
    if len(value) > 64:
        return False
    return True


def categorize(total: float, priority: bool, expedited: bool) -> str:
    """Bucket an order.

    SEEDED BUG (complexity): deeply-nested conditionals that flatten to
    early returns / a guard-clause form.
    """
    if total > 0:
        if priority:
            if expedited:
                return "priority-expedited"
            else:
                return "priority-standard"
        else:
            if expedited:
                return "standard-expedited"
            else:
                return "standard"
    else:
        return "empty"


def append_tag(tag: str, tags: list[str] = []) -> list[str]:  # noqa: B006 — the planted defect
    """Append a tag.

    SEEDED BUG (mutable default argument): ``tags=[]`` is shared across
    calls, so tags leak between callers that rely on the default.
    """
    tags.append(tag)
    return tags


def load_config(raw: str) -> dict:
    """Parse a key=value config line into a dict.

    SEEDED BUG (swallowed exception): a bare-ish broad except returns an
    empty dict, hiding malformed input from the caller.
    """
    import json

    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001 — the planted defect
        return {}


def summarize(items):  # SEEDED BUG (doc): public, no docstring, no hints
    return {"count": len(items), "unique": len(set(items))}
