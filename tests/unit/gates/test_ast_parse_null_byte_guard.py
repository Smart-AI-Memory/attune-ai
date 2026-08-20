"""Gate: every guarded ``ast.parse`` must also catch ``ValueError``.

``ast.parse`` raises ``ValueError`` — not ``SyntaxError`` — when the
source contains a null byte::

    >>> ast.parse("x = 1\\x00")
    Traceback (most recent call last):
    ValueError: source code string cannot contain null bytes

Every AST-analysis path in this tree (doc generators, fact-checkers,
test generators, architecture tools) walks a *set* of files and intends
to SKIP the ones it cannot parse. A handler set of ``SyntaxError``
alone silently breaks that intent: one corrupt or binary file with a
``.py`` extension aborts the entire batch.

Confirmed once in the library review (``source_introspection.py``,
PR #2121) and then found at 14 more sites by the R7a sweep rule. This
gate is the mechanical guard so the class cannot come back — it scans
the shipped tree rather than pinning a list of known sites.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "attune"

#: Catching either of these subsumes ``ValueError``.
_CATCH_ALL = {"Exception", "BaseException"}


def _handler_names(handler: ast.ExceptHandler) -> set[str]:
    """Exception names a handler catches (bare ``except`` catches all)."""
    node = handler.type
    if node is None:
        return {"BaseException"}
    parts = node.elts if isinstance(node, ast.Tuple) else [node]
    names: set[str] = set()
    for part in parts:
        if isinstance(part, ast.Name):
            names.add(part.id)
        elif isinstance(part, ast.Attribute):
            names.add(part.attr)
    return names


def _calls_ast_parse(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "parse"
            and isinstance(func.value, ast.Name)
            and func.value.id == "ast"
        ):
            return True
    return False


def _unguarded_sites(path: Path) -> list[str]:
    """Return ``file:line`` for each ast.parse under a ValueError-blind try."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try) or not node.handlers:
            continue
        if not any(_calls_ast_parse(stmt) for stmt in node.body):
            continue
        caught: set[str] = set()
        for handler in node.handlers:
            caught |= _handler_names(handler)
        if "ValueError" in caught or caught & _CATCH_ALL:
            continue
        hits.append(f"{path.relative_to(SRC_ROOT.parent.parent)}:{node.lineno}")
    return hits


def test_guarded_ast_parse_also_catches_value_error() -> None:
    """A try/except around ast.parse must cover the null-byte ValueError."""
    offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        offenders.extend(_unguarded_sites(path))

    assert not offenders, (
        "ast.parse guarded by a handler set that misses ValueError — a "
        "null-byte source would abort the batch instead of skipping the "
        "file:\n  " + "\n  ".join(offenders)
    )


def test_null_byte_source_raises_value_error_not_syntax_error() -> None:
    """Pin the premise the gate rests on (a CPython behaviour, not ours)."""
    with pytest.raises(ValueError):
        ast.parse("x = 1\x00y = 2\n")

    # And specifically NOT a SyntaxError, which is what the old handlers
    # were written for.
    try:
        ast.parse("x = 1\x00y = 2\n")
    except ValueError as exc:  # noqa: BLE001 - asserting the concrete type
        assert not isinstance(exc, SyntaxError)


def test_skeleton_passes_through_null_byte_source() -> None:
    """Representative behavioural check at one of the fixed sites."""
    from attune.context.skeleton import ASTSkeletonGenerator

    source = "def good():\n    return 1\n\x00"
    assert ASTSkeletonGenerator().generate_skeleton(source) == source


def test_ast_analyzer_records_error_instead_of_raising() -> None:
    """Representative check at the site whose handler reads .msg/.lineno."""
    from attune.workflows.test_gen.ast_analyzer import ASTFunctionAnalyzer

    analyzer = ASTFunctionAnalyzer()
    functions, classes = analyzer.analyze("x = 1\x00y = 2\n")

    assert functions == []
    assert classes == []
    assert analyzer.last_error and "ValueError" in analyzer.last_error
