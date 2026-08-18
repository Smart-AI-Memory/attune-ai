"""Drift-guard: every session-start subprocess call site is time-bounded.

Roundtable ``q-context-mgmt-next-001`` (2026-08-18), unanimous item 1:
the cross-review lane caught an unbounded preflight subprocess; this
guard makes timeout-presence a mechanical property of the whole
session-start path instead of a per-review catch. AST-based, no
execution — every ``subprocess.run`` call in the scanned files must
carry an explicit ``timeout=`` keyword (or live inside a function
whose body is already timeout-bounded via ``subprocess.run``'s
kwarg). Shrink-only: add new files to SCAN_FILES as the path grows;
never remove one to silence a failure.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Session-start-path files whose subprocess.run calls must be bounded.
SCAN_FILES = (
    "scripts/collaboration_preflight.py",
    "scripts/sync_session_hooks.py",
    "src/attune/hooks/scripts/starter_reconciler.py",
    "src/attune/hooks/scripts/starter_prompt_nudge.py",
    "plugin/hooks/spec_orient.py",
    "plugin/hooks/_state.py",
)


def _subprocess_run_calls(tree: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "run"
            and isinstance(func.value, ast.Name)
            and func.value.id == "subprocess"
        ):
            calls.append(node)
    return calls


def test_all_session_start_subprocess_calls_have_timeouts() -> None:
    offenders: list[str] = []
    scanned_any = False
    for rel in SCAN_FILES:
        path = REPO_ROOT / rel
        assert path.is_file(), f"scanned file moved or deleted: {rel}"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in _subprocess_run_calls(tree):
            scanned_any = True
            if not any(kw.arg == "timeout" for kw in call.keywords):
                offenders.append(f"{rel}:{call.lineno}")
    assert scanned_any, "no subprocess.run calls found — scan set stale?"
    assert not offenders, (
        "subprocess.run without an explicit timeout in the session-start "
        f"path: {offenders} — a hung command must fail its check, never "
        "hang session preflight (q-context-mgmt-next-001 item 1)"
    )
