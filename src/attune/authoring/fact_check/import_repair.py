"""Repair example-code imports to canonical dotted module paths.

The polish pass writes example code from the source-info it is fed
(symbol *names* and the *file* each lives in) but has to guess the
importable module path — and it guesses the directory basename
(``from pipeline import …``) instead of the real package
(``from attune.pipeline import …``). The fact-check ``python_refs``
pass then correctly flags those as unresolvable, publishing a noisy
``## Unresolved references`` block into user-facing docs.

This module repairs that class deterministically *before* the file is
written, using the authoritative symbol -> module map built from the
same source files the generator already parsed. Symbols with no known
module are left untouched, so genuinely-fictional references still get
flagged by the fact-check pass.

Only repairs single-line ``from X import a, b`` statements inside
``python`` code fences — the shape the polish pass emits. Multi-line
parenthesized imports and bare ``import X`` are left to the
fact-checker.
"""

from __future__ import annotations

import importlib
import re
from collections import OrderedDict
from collections.abc import Callable

#: A single-line ``from MODULE import NAMES`` statement. Group 1 is the
#: leading indentation, 2 the module, 3 the imported-names clause. The
#: trailing-char guard rejects continuation lines (``import (`` / ``\``)
#: so multi-line imports fall through untouched.
_FROM_IMPORT = re.compile(r"^(\s*)from\s+(\S+)\s+import\s+(.+?)\s*$")


def _file_to_module(rel_path: str) -> str:
    """Convert a source file path to its dotted import module.

    ``src/attune/spec/runner.py`` -> ``attune.spec.runner``;
    ``src/attune/pipeline/__init__.py`` -> ``attune.pipeline``.
    A leading ``src/`` segment and a trailing ``__init__`` are
    stripped. Returns ``""`` for a path that reduces to nothing.
    """
    path = rel_path.replace("\\", "/")
    if path.endswith(".py"):
        path = path[:-3]
    parts = [p for p in path.split("/") if p]
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def build_symbol_module_map(
    source_info: object,
    *,
    importer: Callable[[str], object] = importlib.import_module,
) -> dict[str, str]:
    """Map each public symbol name to its shallowest importable module.

    For a symbol defined in ``attune.spec.runner``, prefer the
    immediate package ``attune.spec`` when it re-exports the symbol
    (cleaner, matches the package's public API) and fall back to the
    defining module otherwise. The re-export probe uses ``importer``;
    any failure degrades to the defining module, which always resolves.

    Args:
        source_info: A ``_SourceInfo`` with ``public_functions``,
            ``public_classes``, and ``module_constants`` lists of
            ``{"name", "file", ...}`` dicts.
        importer: Import callable, injectable for testing.

    Returns:
        ``{symbol_name: dotted_module}``. Later entries win on name
        collisions across modules.
    """
    entries: list[dict] = []
    for attr in ("public_functions", "public_classes", "module_constants"):
        entries.extend(getattr(source_info, attr, []) or [])

    out: dict[str, str] = {}
    for entry in entries:
        name = entry.get("name")
        rel = entry.get("file")
        if not name or not rel:
            continue
        defining = _file_to_module(rel)
        if not defining:
            continue
        chosen = defining
        if "." in defining:
            parent = defining.rsplit(".", 1)[0]
            try:
                if hasattr(importer(parent), name):
                    chosen = parent
            except Exception:  # noqa: BLE001
                # INTENTIONAL: re-export probe is best-effort; a missing
                # package or import-time error means we keep the defining
                # module, which still resolves and kills the false block.
                pass
        out[name] = chosen
    return out


def _imported_name(clause: str) -> str:
    """Return the bound-from name of an import clause.

    ``load_state`` -> ``load_state``; ``load_state as ls`` ->
    ``load_state`` (the name looked up in the source module).
    """
    tokens = clause.split()
    return tokens[0] if tokens else clause


def _repair_line(
    indent: str,
    module: str,
    names_clause: str,
    symbol_module_map: dict[str, str],
) -> str | None:
    """Repair one ``from MODULE import NAMES`` line, or None to keep it.

    Re-groups the imported clauses by their mapped module, emitting one
    ``from M import …`` line per distinct module (insertion order
    preserved). Clauses whose name is unmapped stay under the original
    module. Returns None when nothing maps to a different module (a
    no-op repair), so callers can leave the original line verbatim.
    """
    clauses = [c.strip() for c in names_clause.split(",") if c.strip()]
    if not clauses:
        return None

    grouped: OrderedDict[str, list[str]] = OrderedDict()
    changed = False
    for clause in clauses:
        target = symbol_module_map.get(_imported_name(clause), module)
        if target != module:
            changed = True
        grouped.setdefault(target, []).append(clause)

    if not changed:
        return None

    return "\n".join(
        f"{indent}from {mod} import {', '.join(items)}" for mod, items in grouped.items()
    )


def repair_imports(content: str, symbol_module_map: dict[str, str]) -> str:
    """Rewrite mis-pathed ``from X import …`` lines in python fences.

    Walks ``content`` line by line, tracking ``python`` code-fence
    boundaries (matching the ``python_refs`` convention). Inside a
    fence, each single-line ``from X import …`` whose symbols resolve
    to a different module via ``symbol_module_map`` is rewritten to the
    canonical path. Everything else — prose, other fences, stdlib
    imports, unmapped symbols — is left unchanged.

    Args:
        content: The polished markdown.
        symbol_module_map: ``{symbol_name: dotted_module}`` from
            :func:`build_symbol_module_map`.

    Returns:
        The repaired markdown (unchanged if nothing matched).
    """
    if not symbol_module_map:
        return content

    out_lines: list[str] = []
    in_fence = False
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = "python" in stripped
            else:
                in_fence = False
            out_lines.append(line)
            continue

        if in_fence:
            match = _FROM_IMPORT.match(line)
            if match:
                repaired = _repair_line(
                    match.group(1), match.group(2), match.group(3), symbol_module_map
                )
                if repaired is not None:
                    out_lines.append(repaired)
                    continue
        out_lines.append(line)

    repaired_content = "\n".join(out_lines)
    if content.endswith("\n"):
        repaired_content += "\n"
    return repaired_content


__all__ = ["build_symbol_module_map", "repair_imports"]
