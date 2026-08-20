"""Extract public-API surface from source files via AST.

Walks each source file and collects:

- ``__all__`` declarations (if present), which set explicit public API.
- Top-level function definitions whose names don't start with ``_``.
- Top-level class definitions whose names don't start with ``_``.

Output is a single text block formatted for LLM consumption: one entry
per public symbol, with a ``module: name(signature)`` shape so the
ground-truth anchoring rule has something concrete to pin against.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _format_argument(arg: ast.arg) -> str:
    if arg.annotation is None:
        return arg.arg
    try:
        annotation = ast.unparse(arg.annotation)
    except (AttributeError, ValueError):
        annotation = "..."
    return f"{arg.arg}: {annotation}"


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    parts: list[str] = []

    pos = list(args.posonlyargs) + list(args.args)
    pos_defaults = list(args.defaults)
    default_offset = len(pos) - len(pos_defaults)
    for idx, arg in enumerate(pos):
        rendered = _format_argument(arg)
        if idx >= default_offset:
            default = pos_defaults[idx - default_offset]
            try:
                rendered = f"{rendered} = {ast.unparse(default)}"
            except (AttributeError, ValueError):
                rendered = f"{rendered} = ..."
        parts.append(rendered)
        if idx == len(args.posonlyargs) - 1 and args.posonlyargs:
            parts.append("/")

    if args.vararg is not None:
        parts.append(f"*{_format_argument(args.vararg)}")
    elif args.kwonlyargs:
        parts.append("*")

    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=False):
        rendered = _format_argument(arg)
        if default is not None:
            try:
                rendered = f"{rendered} = {ast.unparse(default)}"
            except (AttributeError, ValueError):
                rendered = f"{rendered} = ..."
        parts.append(rendered)

    if args.kwarg is not None:
        parts.append(f"**{_format_argument(args.kwarg)}")

    signature = "(" + ", ".join(parts) + ")"
    if node.returns is not None:
        try:
            signature += f" -> {ast.unparse(node.returns)}"
        except (AttributeError, ValueError):
            signature += " -> ..."
    return signature


def _module_name_for(path: Path) -> str:
    """Best-effort module label for a source file.

    We do not need a fully-qualified dotted name — the polish prompt
    only needs enough to disambiguate two functions with the same
    name. Stem + parent dir is good enough; pathlib resolves it
    cross-platform.
    """
    parent = path.parent.name
    stem = path.stem
    if parent in {"", "src"}:
        return stem
    return f"{parent}.{stem}"


def _extract_all(tree: ast.Module) -> list[str]:
    """Return the list of names from ``__all__`` if present."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = node.targets
        if not (
            len(targets) == 1 and isinstance(targets[0], ast.Name) and targets[0].id == "__all__"
        ):
            continue
        value = node.value
        if isinstance(value, ast.List | ast.Tuple):
            names: list[str] = []
            for element in value.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    names.append(element.value)
            return names
    return []


def _public_symbols(tree: ast.Module) -> tuple[list[str], list[str]]:
    """Return ``(function_lines, class_lines)`` for public symbols."""
    functions: list[str] = []
    classes: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("_"):
                continue
            functions.append(f"def {node.name}{_format_signature(node)}")
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            method_summaries: list[str] = []
            for child in node.body:
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    if child.name.startswith("_") and child.name not in {
                        "__init__",
                        "__call__",
                    }:
                        continue
                    method_summaries.append(f"    def {child.name}{_format_signature(child)}")
            if method_summaries:
                classes.append(f"class {node.name}:\n" + "\n".join(method_summaries))
            else:
                classes.append(f"class {node.name}")

    return functions, classes


def extract_public_api(source_paths: list[Path]) -> str:
    """Build a public-API text block for the polish prompt.

    Args:
        source_paths: Paths to ``.py`` files belonging to the feature.

    Returns:
        A formatted block. Empty string if nothing public was found.
    """
    sections: list[str] = []

    for path in source_paths:
        if path.suffix != ".py":
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.debug("ground_truth.public_api: skip %s (%s)", path, exc)
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except (
            SyntaxError,
            ValueError,
        ) as exc:  # ast.parse: null bytes -> ValueError, not SyntaxError
            logger.debug("ground_truth.public_api: parse failed for %s (%s)", path, exc)
            continue

        module_label = _module_name_for(path)
        all_names = _extract_all(tree)
        functions, classes = _public_symbols(tree)

        section_lines: list[str] = []
        if all_names:
            section_lines.append("__all__ = [" + ", ".join(repr(n) for n in all_names) + "]")
        section_lines.extend(functions)
        section_lines.extend(classes)
        if not section_lines:
            continue
        sections.append(f"# {module_label}\n" + "\n".join(section_lines))

    return "\n\n".join(sections)


__all__ = ["extract_public_api"]
