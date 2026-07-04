"""Regression guard: the dead orchestration engine stays deleted (R7).

The generic-agent-teams spec generalizes the *working* ReleasePrepTeam
pattern; it must never resurrect the fake-success engine removed in
#1096. This guard asserts that the deleted symbols do not reappear
anywhere under ``src/`` — if a future change re-introduces one (even in
a docstring), this test fails loudly.

See ``.claude/rules-tail/attune/removing-dead-code.md`` and
``docs/specs/generic-agent-teams/decisions.md``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from pathlib import Path

import pytest

#: Symbols from the engine removed in #1096 — must stay deleted.
_DEAD_SYMBOLS = ("StubAgent", "DynamicTeam", "SDKAgent")


def _src_root() -> Path:
    """Locate the ``src/attune`` package root from this test file."""
    # tests/unit/agents/test_no_revived_dead_code.py -> repo root is parents[3]
    root = Path(__file__).resolve().parents[3] / "src" / "attune"
    assert root.is_dir(), f"expected package root at {root}"
    return root


@pytest.mark.parametrize("symbol", _DEAD_SYMBOLS)
def test_dead_engine_symbol_absent_from_src(symbol):
    """No deleted-engine symbol appears anywhere under src/ (R7)."""
    offenders: list[str] = []
    for py_file in _src_root().rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if symbol in line:
                offenders.append(f"{py_file}:{lineno}: {line.strip()}")

    assert not offenders, (
        f"Revived dead symbol '{symbol}' found in src/ — the engine removed "
        f"in #1096 must stay deleted (generalize the working sibling, never "
        f"resurrect the stub):\n" + "\n".join(offenders)
    )
