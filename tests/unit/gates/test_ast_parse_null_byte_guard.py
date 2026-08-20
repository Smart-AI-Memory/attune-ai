"""Gate: every guarded ``ast.parse`` must also catch ``ValueError``.

``ast.parse`` rejects a source containing a null byte — but WHICH
exception it raises depends on the interpreter: CPython <= 3.11 raises
``ValueError``, newer versions raise ``SyntaxError``. This repo's CI
matrix spans 3.10-3.14, so a handler must cover BOTH to behave the same
way on every supported interpreter. Catching only ``SyntaxError`` is
silently correct on 3.12+ and broken on 3.10/3.11 — the worst shape of
bug to find by hand.

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


def test_null_byte_rejection_is_covered_by_both_handlers() -> None:
    """Pin the premise: the exception CLASS is interpreter-dependent.

    CPython <= 3.11 raises ValueError; 3.12+ raises SyntaxError. Only a
    handler naming both behaves identically across the supported range,
    which is exactly what the gate above enforces.
    """
    with pytest.raises((ValueError, SyntaxError)):
        ast.parse("x = 1\x00y = 2\n")

    # A (SyntaxError, ValueError) handler catches it on ANY interpreter.
    try:
        ast.parse("x = 1\x00y = 2\n")
    except (SyntaxError, ValueError):
        caught = True
    assert caught


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
    # The recorded class follows the interpreter (see the premise
    # test): ValueError on <= 3.11, SyntaxError on 3.12+.
    assert analyzer.last_error
    assert ("ValueError" in analyzer.last_error) or ("SyntaxError" in analyzer.last_error)


# ---------------------------------------------------------------------------
# Behavioural coverage at the fixed sites
#
# The gate above proves the handler SHAPE at every site; these prove the
# resulting BEHAVIOUR — a corrupt file is skipped and its clean siblings
# still get processed, which is the property the fix exists to protect.
# ---------------------------------------------------------------------------

NULL_BYTE_SOURCE = b"x = 1\x00y = 2\n"
GOOD_SOURCE = "def good():\n    return 1\n"


def _corpus(tmp_path: Path) -> tuple[Path, Path]:
    """A clean module beside a null-byte-corrupt one."""
    good = tmp_path / "good.py"
    good.write_text(GOOD_SOURCE, encoding="utf-8")
    bad = tmp_path / "corrupt.py"
    bad.write_bytes(NULL_BYTE_SOURCE)
    return good, bad


def test_extract_public_api_skips_corrupt_module(tmp_path: Path) -> None:
    from attune.authoring.ground_truth.public_api import extract_public_api

    good, bad = _corpus(tmp_path)
    out = extract_public_api([good, bad])

    # The clean sibling still contributes; the corrupt file is skipped.
    assert "good" in out


def test_extract_dataclasses_skips_corrupt_module(tmp_path: Path) -> None:
    from attune.authoring.ground_truth.dataclass_refs import extract_dataclasses

    good = tmp_path / "good.py"
    good.write_text(
        "from dataclasses import dataclass\n\n\n@dataclass\nclass Thing:\n    a: int\n",
        encoding="utf-8",
    )
    bad = tmp_path / "corrupt.py"
    bad.write_bytes(NULL_BYTE_SOURCE)

    assert "Thing" in extract_dataclasses([good, bad])


def test_architecture_import_scan_skips_corrupt_module(tmp_path: Path) -> None:
    from attune.orchestration.tools.architecture import RealArchitectureAnalyzer

    _, bad = _corpus(tmp_path)
    analyzer = RealArchitectureAnalyzer.__new__(RealArchitectureAnalyzer)

    assert analyzer._extract_imports(bad) == set()


def test_python_refs_check_survives_corrupt_fence(tmp_path: Path) -> None:
    """A null byte inside a ```python fence must not abort the check."""
    from attune.authoring.fact_check import python_refs

    doc = tmp_path / "polished.md"
    doc.write_bytes(b"# Doc\n\n```python\nx = 1\x00y = 2\n```\n")

    python_refs.check(doc)  # must not raise


def test_tutorial_static_check_reports_corrupt_fence(tmp_path: Path) -> None:
    """The fence is REPORTED, not raised past — and without .msg/.lineno."""
    from attune.authoring.fact_check import tutorial_static_check

    doc = tmp_path / "polished.md"
    doc.write_bytes(b"# Doc\n\n```python\nx = 1\x00y = 2\n```\n")

    tutorial_static_check.check(doc)  # must not raise


def test_doc_examples_parse_block_returns_error_not_raise() -> None:
    """_parse_block reports the failure in its error slot."""
    from attune.authoring.fact_check.doc_examples import _parse_block

    tree, error = _parse_block("x = 1\x00y = 2\n")

    assert tree is None
    assert error


def test_api_reference_extraction_returns_empty_on_corrupt_source() -> None:
    """A corrupt source yields no functions rather than raising."""
    from attune.workflows.document_gen.api_reference import APIReferenceMixin

    mixin = APIReferenceMixin.__new__(APIReferenceMixin)

    assert mixin._extract_functions_from_source("x = 1\x00y = 2\n") == []


def test_source_introspection_skips_corrupt_module(tmp_path: Path) -> None:
    """The originally-confirmed site (F5) keeps its behavioural check."""
    from attune.authoring.source_introspection import _extract_source_info

    _corpus(tmp_path)
    _extract_source_info(["good.py", "corrupt.py"], tmp_path)  # must not raise
