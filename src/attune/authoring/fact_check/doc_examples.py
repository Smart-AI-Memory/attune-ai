"""Compile + coroutine-misuse check for ``python`` code blocks in docs.

The static ``python_refs`` check proves that symbols and imports
*exist*; it does not prove an example is *runnable*. This check closes
that gap (help-docs-single-source follow-up P5): for every fenced
``python`` block it

1. compiles the block (an illustrative top-level-``await`` fragment is
   re-tried wrapped in ``async def`` so fragments are tolerated), and
2. flags any call to a **coroutine function** that is not awaited (or
   scheduled via ``asyncio.run`` / ``gather`` / ``create_task`` /
   ``ensure_future``).

"Is this callable async?" is grounded in the real code via
``inspect.iscoroutinefunction`` — not a hardcoded list. Unlike the
attune-ai prototype this generalises (``scripts/check_doc_examples.py``,
which scanned a fixed set of ``attune.*`` packages), this check derives
the modules to introspect from the blocks' *own* import statements, so
it stays consumer-agnostic: it never hardcodes a downstream package.

Findings are warn-only by default in the soft-fail flow; a genuine
coroutine-without-await is reported as ``error`` (it definitively will
not run) while a block that fails to compile is reported as
``warning`` (it may be an intentional fragment).
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

from .python_refs import _extract_code_fences
from .report import CHECK_DOC_EXAMPLES, Finding

#: ``asyncio`` entry points that legitimately drive a coroutine call
#: without a syntactic ``await`` — a call passed to one of these (or to
#: a bare ``await``) is correctly scheduled, not a bug.
_SCHEDULERS = frozenset({"run", "gather", "create_task", "ensure_future"})


def _parse_block(src: str) -> tuple[ast.AST | None, str | None]:
    """Parse a block, tolerating top-level-``await`` fragments.

    Returns ``(tree, None)`` on success or ``(None, message)`` when the
    block does not compile even when wrapped in an ``async def`` (a
    genuine syntax error rather than an illustrative fragment).
    """
    try:
        return ast.parse(src), None
    except SyntaxError:
        indented = "\n".join("    " + line for line in src.splitlines())
        try:
            return ast.parse("async def __frag__():\n" + indented), None
        except SyntaxError as exc:
            return None, f"{exc.msg} (line {exc.lineno})"


def _collect_async_names(trees: list[ast.AST]) -> tuple[set[str], set[str]]:
    """Derive coroutine names from the blocks' own import statements.

    Returns ``(funcs, methods)`` where ``funcs`` are names bound by
    ``from M import f`` that are coroutine functions (called bare,
    ``f()``) and ``methods`` are attribute names that are coroutine —
    method names of imported classes and module-level coroutine
    functions reached as ``M.f()`` after ``import M``.

    Every import is best-effort: a module that will not import (a
    missing extra, a downstream package absent from this venv) is
    skipped, exactly like ``python_refs``.
    """
    funcs: set[str] = set()
    methods: set[str] = set()
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module = _safe_import(node.module)
                if module is None:
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    obj = getattr(module, alias.name, None)
                    if obj is None:
                        continue
                    bound = alias.asname or alias.name
                    if inspect.iscoroutinefunction(obj):
                        funcs.add(bound)
                    elif inspect.isclass(obj):
                        methods.update(_coroutine_methods(obj))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = _safe_import(alias.name)
                    if module is None:
                        continue
                    # ``import M`` -> calls read as ``M.f()`` (attribute);
                    # collect module-level coroutine fns and class methods
                    # as attribute names we can flag.
                    for _name, value in vars(module).items():
                        if inspect.iscoroutinefunction(value):
                            methods.add(_name)
                        elif inspect.isclass(value):
                            methods.update(_coroutine_methods(value))
    return funcs, methods


def _safe_import(module: str) -> object | None:
    """Import ``module`` best-effort; ``None`` on any failure."""
    try:
        return importlib.import_module(module)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: a doc may import a module this venv lacks (a
        # missing extra, a downstream package). That is python_refs'
        # job to flag — here we just cannot introspect it, so skip.
        return None


def _coroutine_methods(cls: type) -> set[str]:
    """Names of ``cls``'s own coroutine methods."""
    return {name for name, obj in vars(cls).items() if inspect.iscoroutinefunction(obj)}


def _awaited_or_scheduled(tree: ast.AST) -> set[int]:
    """``id()`` of Call nodes that are awaited or handed to a scheduler."""
    ok: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
            ok.add(id(node.value))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _SCHEDULERS
        ):
            for arg in node.args:
                if isinstance(arg, ast.Call):
                    ok.add(id(arg))
    return ok


def _misused_coroutines(tree: ast.AST, funcs: set[str], methods: set[str]) -> list[str]:
    """Names of coroutine calls in ``tree`` that are neither awaited
    nor scheduled."""
    awaited = _awaited_or_scheduled(tree)
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or id(node) in awaited:
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute):
            # asyncio's own schedulers are sync entry points, never our
            # coroutines — and ``asyncio.run`` vs ``Executor.run`` would
            # otherwise collide on the attr name.
            if fn.attr in _SCHEDULERS:
                continue
            if isinstance(fn.value, ast.Name) and fn.value.id == "asyncio":
                continue
        is_async = (isinstance(fn, ast.Name) and fn.id in funcs) or (
            isinstance(fn, ast.Attribute) and fn.attr in methods
        )
        if is_async:
            problems.append(fn.id if isinstance(fn, ast.Name) else fn.attr)
    return problems


def check(polished_path: Path) -> list[Finding]:
    """Run the doc-examples check on ``polished_path``.

    Returns a ``warning`` for each python block that does not compile
    and an ``error`` for each coroutine call made without ``await``.
    """
    text = polished_path.read_text(encoding="utf-8")
    findings: list[Finding] = []

    parsed: list[tuple[int, ast.AST]] = []
    for fence_line, body in _extract_code_fences(text):
        tree, err = _parse_block(body)
        if tree is None:
            findings.append(
                Finding(
                    check=CHECK_DOC_EXAMPLES,
                    severity="warning",
                    location=f"Line {fence_line} (code fence)",
                    message=f"python example does not compile: {err}",
                )
            )
            continue
        parsed.append((fence_line, tree))

    funcs, methods = _collect_async_names([t for _, t in parsed])
    for fence_line, tree in parsed:
        for name in _misused_coroutines(tree, funcs, methods):
            findings.append(
                Finding(
                    check=CHECK_DOC_EXAMPLES,
                    severity="error",
                    location=f"Line {fence_line} (code fence)",
                    message=(
                        f"coroutine `{name}()` called without `await` — "
                        f"the example would not run"
                    ),
                )
            )
    return findings


__all__ = ["check"]
