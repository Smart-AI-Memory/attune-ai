"""Check Python import statements and dotted-path references.

Resolves each candidate against the active venv via
``importlib.import_module`` — see spec §1.3, "catches the
``attune.ops._readers`` class of bug where the path parses fine
but doesn't actually exist."
"""

from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

from .report import CHECK_PYTHON_REFS, Finding

#: Match prose references like ``attune.ops._readers.Foo`` or
#: ``attune.workflows.bug_predict`` — a dotted attune-style path
#: ending in either a snake_case module or a CapWord class. Group
#: 1 captures the full path.
_PROSE_DOTTED = re.compile(r"`(attune(?:_[a-z]+)?(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)`")


def _extract_code_fences(text: str) -> list[tuple[int, str]]:
    """Pull all ```python fenced blocks. Returns (line, body) pairs.

    Line is the 1-indexed line number of the opening fence so
    findings can point at it.
    """
    fences: list[tuple[int, str]] = []
    in_fence = False
    fence_start = 0
    buf: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if not in_fence and stripped.startswith("```") and "python" in stripped:
            in_fence = True
            fence_start = i
            buf = []
            continue
        if in_fence and stripped.startswith("```"):
            fences.append((fence_start, "\n".join(buf)))
            in_fence = False
            buf = []
            continue
        if in_fence:
            buf.append(line)
    return fences


def _try_import(module: str) -> bool:
    """Best-effort import test. Returns True if importable."""
    try:
        importlib.import_module(module)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: any failure (ImportError, syntax error in a
        # broken dep, ValueError on a bad dotted path) means the
        # reference is unresolvable from the active venv — exactly
        # what we want to surface to the doc author.
        return False
    return True


def _resolve_attr(module_path: str, attr: str) -> bool:
    """Import ``module_path`` and verify ``attr`` exists on it."""
    try:
        module = importlib.import_module(module_path)
    except Exception:  # noqa: BLE001
        return False
    return hasattr(module, attr)


def _resolve_dotted(path: str) -> bool:
    """Resolve a full dotted path like ``attune.ops._readers.Foo``.

    Walks from longest module prefix down: tries to import each
    prefix; if a prefix imports, checks that the suffix attribute
    chain exists on the resulting object.
    """
    parts = path.split(".")
    # Try progressively shorter module prefixes.
    for split in range(len(parts), 0, -1):
        module_path = ".".join(parts[:split])
        try:
            obj = importlib.import_module(module_path)
        except Exception:  # noqa: BLE001
            continue
        # Walk remaining attributes.
        ok = True
        for attr in parts[split:]:
            if not hasattr(obj, attr):
                ok = False
                break
            obj = getattr(obj, attr)
        if ok:
            return True
    return False


def check(polished_path: Path) -> list[Finding]:
    """Run the python-refs check on ``polished_path``.

    Returns findings for unresolvable imports inside python code
    fences and for unresolvable dotted paths in prose.
    """
    text = polished_path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    for fence_line, body in _extract_code_fences(text):
        try:
            tree = ast.parse(body)
        except SyntaxError:
            # Not all python fences are valid stand-alone modules
            # (snippets often omit imports or use ``...``); skip
            # silently. Tutorial static checks belong to Phase 4.
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
                if not _try_import(module):
                    key = (module, "")
                    if key not in seen:
                        seen.add(key)
                        findings.append(
                            Finding(
                                check=CHECK_PYTHON_REFS,
                                severity="error",
                                location=f"Line {fence_line} (code fence)",
                                message=f"`from {module} import …` — module not importable",
                            )
                        )
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if not _resolve_attr(module, alias.name):
                        key = (module, alias.name)
                        if key not in seen:
                            seen.add(key)
                            findings.append(
                                Finding(
                                    check=CHECK_PYTHON_REFS,
                                    severity="error",
                                    location=f"Line {fence_line} (code fence)",
                                    message=(
                                        f"`from {module} import {alias.name}` — "
                                        f"`{alias.name}` not found in `{module}`"
                                    ),
                                )
                            )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if not _try_import(module):
                        key = (module, "")
                        if key not in seen:
                            seen.add(key)
                            findings.append(
                                Finding(
                                    check=CHECK_PYTHON_REFS,
                                    severity="error",
                                    location=f"Line {fence_line} (code fence)",
                                    message=f"`import {module}` — module not importable",
                                )
                            )

    # Prose dotted refs.
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _PROSE_DOTTED.finditer(line):
            path = match.group(1)
            if path in {key[0] for key in seen}:
                continue
            if not _resolve_dotted(path):
                key = (path, "prose")
                if key not in seen:
                    seen.add(key)
                    findings.append(
                        Finding(
                            check=CHECK_PYTHON_REFS,
                            severity="error",
                            location=f"Line {lineno} (prose)",
                            message=f"`{path}` — dotted path not resolvable",
                        )
                    )

    return findings


__all__ = ["check"]
