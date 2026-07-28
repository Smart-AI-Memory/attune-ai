"""Check Python import statements and dotted-path references.

Resolves each candidate through the shared authoritative resolver
(``fact_check/imports.py``, #1586): the repo's own ``src/`` is put
first on ``sys.path`` before resolution, so a symbol that exists in
the checked repo resolves even when the active venv's editable
mapping points at a different checkout (the line-115 false-positive
class). Catches the ``attune.ops._readers`` class of bug where the
path parses fine but doesn't actually exist (spec §1.3).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from . import imports as _imports
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


# Resolution primitives live in the shared authoritative resolver
# (one import verdict for this checker AND the CI doc-import gate).
_try_import = _imports.try_import
_resolve_attr = _imports.resolve_attr
_resolve_dotted = _imports.resolve_dotted


def check(polished_path: Path) -> list[Finding]:
    """Run the python-refs check on ``polished_path``.

    Returns findings for unresolvable imports inside python code
    fences and for unresolvable dotted paths in prose.
    """
    # Authoritative resolution (#1586): the checked repo's own src/
    # wins over the venv's editable mapping for anything not yet
    # imported into this process.
    _imports.ensure_src_on_path(_imports.find_repo_root(polished_path))
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
