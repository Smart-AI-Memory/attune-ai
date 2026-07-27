#!/usr/bin/env python3
"""Compile + coroutine-misuse lint for ``python`` code blocks in docs.

The static fact-check (`attune.authoring.fact_check`) proves that symbols
and imports exist; it does not prove a code example is *runnable*. This
closes that gap (help-docs-single-source follow-up P5): for every
fenced ``python`` block in the given files it

1. compiles the block (catching syntax errors, including ``await``
   outside a function), and
2. flags any call to a **coroutine function** that is not awaited
   (or scheduled via ``asyncio.run`` / ``gather`` / ``create_task`` /
   ``ensure_future``).

"Is this callable async?" is grounded in the real code via
``inspect.iscoroutinefunction`` over the attune packages, not a
hardcoded list — so it stays correct as the code changes.

A block that legitimately uses ``await`` at top level (an illustrative
fragment) is compiled wrapped in an ``async def`` before being flagged,
so fragments are tolerated while genuinely broken blocks are not.

Usage::

    python scripts/check_doc_examples.py <file.md> [<file.md> ...]

Exit code is the number of problems found (0 = clean).
"""

from __future__ import annotations

import ast
import inspect
import re
import sys
from pathlib import Path

_BLOCK_RE = re.compile(r"```python\n(.*?)\n```", re.DOTALL)
_SCHEDULERS = {"run", "gather", "create_task", "ensure_future"}


def _async_names() -> tuple[set[str], set[str]]:
    """Return (module-level coroutine fn names, coroutine method names)."""
    funcs: set[str] = set()
    methods: set[str] = set()
    for mod_name in (
        "attune.pipeline",
        "attune.spec",
        "attune.spec.runner",
        "attune.models",
    ):
        try:
            mod = __import__(mod_name, fromlist=["*"])
        except Exception:  # noqa: BLE001 - a missing extra must not break the lint
            continue
        for name, obj in vars(mod).items():
            if inspect.iscoroutinefunction(obj):
                funcs.add(name)
            elif inspect.isclass(obj):
                for m_name, m_obj in vars(obj).items():
                    if inspect.iscoroutinefunction(m_obj):
                        methods.add(m_name)
    return funcs, methods


def _awaited_or_scheduled(tree: ast.AST) -> set[int]:
    """ids of Call nodes that are awaited or passed to an asyncio scheduler."""
    ok: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
            ok.add(id(node.value))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _SCHEDULERS:
                for arg in node.args:
                    if isinstance(arg, ast.Call):
                        ok.add(id(arg))
    return ok


def _check_block(src: str, funcs: set[str], methods: set[str]) -> list[str]:
    problems: list[str] = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        # Tolerate top-level-await fragments: retry wrapped in async def.
        indented = "\n".join("    " + line for line in src.splitlines())
        try:
            tree = ast.parse("async def __frag__():\n" + indented)
        except SyntaxError as exc:
            return [f"does not compile: {exc.msg} (line {exc.lineno})"]
    awaited = _awaited_or_scheduled(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or id(node) in awaited:
            continue
        fn = node.func
        # asyncio's own schedulers (asyncio.run/gather/create_task/...) are
        # SYNC entrypoints, not our coroutines — never flag them. This also
        # avoids the `asyncio.run` vs `Executor.run` attr-name collision.
        if isinstance(fn, ast.Attribute):
            if fn.attr in _SCHEDULERS:
                continue
            if isinstance(fn.value, ast.Name) and fn.value.id == "asyncio":
                continue
        is_async = (isinstance(fn, ast.Name) and fn.id in funcs) or (
            isinstance(fn, ast.Attribute) and fn.attr in methods
        )
        if is_async:
            name = fn.id if isinstance(fn, ast.Name) else fn.attr
            problems.append(f"coroutine '{name}()' called without await (line {node.lineno})")
    return problems


def check_file(path: str | Path) -> list[str]:
    """Return example problems for one file, one string per problem.

    Each entry is prefixed ``block <n>: …`` so callers can fold them
    into their own warning stream. Empty list = clean. Importable by
    other drivers (e.g. ``scripts/project_features.py``) to run the
    gate inline.
    """
    funcs, methods = _async_names()
    text = Path(path).read_text(encoding="utf-8")
    problems: list[str] = []
    for i, src in enumerate(_BLOCK_RE.findall(text), 1):
        for prob in _check_block(src, funcs, methods):
            problems.append(f"block {i}: {prob}")
    return problems


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: check_doc_examples.py <file.md> ...", file=sys.stderr)
        return 2
    total = 0
    for arg in argv:
        path = Path(arg)
        problems = check_file(path)
        for prob in problems:
            print(f"{path}: {prob}")
        n_blocks = len(_BLOCK_RE.findall(path.read_text(encoding="utf-8")))
        status = "OK" if not problems else f"{len(problems)} PROBLEM(S)"
        print(f"{path}: {n_blocks} python block(s) — {status}")
        total += len(problems)
    print(f"\nTotal problems: {total}")
    return total


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
