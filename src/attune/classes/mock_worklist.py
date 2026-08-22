"""Class-M AST worklist detector — three shapes, never a verdict.

Release-audit-stage R6: the detector flags test functions whose
shape SUGGESTS the mock defined the contract. Every hit is a
worklist item for a tree-holding reviewer; the detector itself
renders no verdict (adjudicating a mock against the code under test
is defect-reading, which seats and scanners don't do).

Shapes (each earned from a live instance, register ruling M):

1. ``patched-call-site`` — a test that patches something and whose
   only assertions are mock assertions (``assert_called*``,
   ``call_count``): the patched call site stops testing anything
   the moment the code moves.
2. ``literal-fixture`` — a dict literal passed straight to a
   reader/deserializer: a record fixture must come from the
   writer's own serializer, or the shape drifts from the writer's.
3. ``patched-refusal`` — a "cannot write" test that induces failure
   by patching a write call with an OSError side effect instead of
   making the filesystem actually refuse (chmod / read-only dir).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_MOCK_ASSERT_PREFIXES = ("assert_called", "assert_not_called", "assert_any_call", "assert_awaited")
_READER_NAMES = frozenset(
    {"from_dict", "load", "loads", "deserialize", "parse_obj", "model_validate", "read_record"}
)
#: Final attribute segment of a patch target that names a FILE write
#: op. Matched exactly on the last dotted segment — substring matching
#: falsely flagged ``urllib.request.urlopen`` and ``subprocess.Popen``
#: (network/subprocess error tests are not filesystem-refusal
#: candidates; calibration probe 2026-08-22).
_WRITE_TARGET_SEGMENTS = frozenset(
    {"write_text", "write_bytes", "open", "replace", "rename", "mkdir", "unlink"}
)
_ERROR_NAMES = frozenset({"OSError", "PermissionError", "IOError"})


@dataclass
class WorklistItem:
    """One flagged test-shape occurrence."""

    path: str
    line: int
    shape: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} [{self.shape}] {self.detail}"


def _is_patch_call(node: ast.Call) -> str | None:
    """Return the patch target string if ``node`` is ``patch("...")``."""
    func = node.func
    name = None
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr
    if name not in {"patch", "object"}:
        return None
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    if name == "object" and len(node.args) >= 2:
        attr = node.args[1]
        if isinstance(attr, ast.Constant) and isinstance(attr.value, str):
            return attr.value
    return None


def _mock_asserts_only(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the function asserts ONLY through mock assertions."""
    saw_mock_assert = False
    for node in ast.walk(func):
        if isinstance(node, ast.Assert):
            return False
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr.startswith(_MOCK_ASSERT_PREFIXES):
                saw_mock_assert = True
    return saw_mock_assert


def _patch_targets(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[int, str]]:
    targets: list[tuple[int, str]] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            target = _is_patch_call(node)
            if target:
                targets.append((node.lineno, target))
    for decorator in func.decorator_list:
        if isinstance(decorator, ast.Call):
            target = _is_patch_call(decorator)
            if target:
                targets.append((decorator.lineno, target))
    return targets


def _has_error_side_effect(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.keyword) and node.arg == "side_effect":
            for inner in ast.walk(node.value):
                if isinstance(inner, ast.Name) and inner.id in _ERROR_NAMES:
                    return True
    return False


def _literal_fixture_hits(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        name = None
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
        elif isinstance(node.func, ast.Name):
            name = node.func.id
        if name in _READER_NAMES and any(isinstance(a, ast.Dict) for a in node.args):
            hits.append((node.lineno, name))
    return hits


def scan_file(path: Path) -> list[WorklistItem]:
    """Scan one test file for the three class-M shapes.

    Args:
        path: A Python test file.

    Returns:
        Worklist items; empty when no shape matches. Unparseable
        files return empty (the sweep's job is shapes, not syntax).
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError, OSError):
        return []
    items: list[WorklistItem] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("test"):
            continue
        targets = _patch_targets(node)
        if targets and _mock_asserts_only(node):
            line, target = targets[0]
            items.append(
                WorklistItem(
                    str(path),
                    node.lineno,
                    "patched-call-site",
                    f"{node.name} patches {target!r} and asserts only on the mock",
                )
            )
        for line, name in _literal_fixture_hits(node):
            items.append(
                WorklistItem(
                    str(path),
                    line,
                    "literal-fixture",
                    f"{node.name} feeds a dict literal to {name}()",
                )
            )
        if _has_error_side_effect(node):
            write_targets = [
                (line, t) for line, t in targets if t.rsplit(".", 1)[-1] in _WRITE_TARGET_SEGMENTS
            ]
            if write_targets:
                line, target = write_targets[0]
                items.append(
                    WorklistItem(
                        str(path),
                        line,
                        "patched-refusal",
                        f"{node.name} patches {target!r} with an error side_effect "
                        "instead of a real filesystem refusal",
                    )
                )
    return items


def scan_paths(paths: list[Path]) -> list[WorklistItem]:
    """Scan test files under the given paths (files or directories)."""
    items: list[WorklistItem] = []
    for root in paths:
        files = [root] if root.is_file() else sorted(root.rglob("test_*.py"))
        for f in files:
            items.extend(scan_file(f))
    return items


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m attune.classes.mock_worklist <paths...>``."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)
    items = scan_paths(args.paths)
    for item in items:
        print(item)
    print(f"{len(items)} worklist item(s) — worklist, not verdicts")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
