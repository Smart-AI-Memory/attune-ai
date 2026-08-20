"""Extract ``@dataclass`` field names and types via AST.

The polished docs commonly describe configuration shapes and result
types by listing field names. Without ground-truth injection, the
model invents plausible-sounding field names that don't exist. This
module surfaces the real field list so the model has something to
anchor against.

Module name is ``dataclass_refs`` (not ``dataclasses``) to avoid
shadowing the stdlib module of the same name within this package.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_dataclass_decorator(decorator: ast.expr) -> bool:
    """Match ``@dataclass`` and ``@dataclass(...)`` forms."""
    if isinstance(decorator, ast.Name):
        return decorator.id == "dataclass"
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Name):
            return func.id == "dataclass"
        if isinstance(func, ast.Attribute):
            return func.attr == "dataclass"
    if isinstance(decorator, ast.Attribute):
        return decorator.attr == "dataclass"
    return False


def _annotation_str(annotation: ast.expr | None) -> str:
    if annotation is None:
        return "..."
    try:
        return ast.unparse(annotation)
    except (AttributeError, ValueError):
        return "..."


def _default_str(value: ast.expr | None) -> str | None:
    if value is None:
        return None
    try:
        return ast.unparse(value)
    except (AttributeError, ValueError):
        return "..."


def _format_class(node: ast.ClassDef) -> str | None:
    """Render a single dataclass as a text block. Returns None if no fields."""
    fields: list[str] = []
    for child in node.body:
        if not isinstance(child, ast.AnnAssign):
            continue
        target = child.target
        if not isinstance(target, ast.Name):
            continue
        name = target.id
        if name.startswith("_"):
            continue
        annotation = _annotation_str(child.annotation)
        default = _default_str(child.value)
        if default is None:
            fields.append(f"    {name}: {annotation}")
        else:
            fields.append(f"    {name}: {annotation} = {default}")
    if not fields:
        return None
    return f"@dataclass\nclass {node.name}:\n" + "\n".join(fields)


def _module_label(path: Path) -> str:
    parent = path.parent.name
    stem = path.stem
    if parent in {"", "src"}:
        return stem
    return f"{parent}.{stem}"


def extract_dataclasses(source_paths: list[Path]) -> str:
    """Build a dataclass-fields text block for the polish prompt.

    Args:
        source_paths: Paths to ``.py`` files belonging to the feature.

    Returns:
        Formatted block grouped by module. Empty string when no source
        file contains a dataclass with public fields.
    """
    sections: list[str] = []

    for path in source_paths:
        if path.suffix != ".py":
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.debug("ground_truth.dataclass_refs: skip %s (%s)", path, exc)
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except (
            SyntaxError,
            ValueError,
        ) as exc:  # ast.parse: null bytes -> ValueError, not SyntaxError
            logger.debug("ground_truth.dataclass_refs: parse failed for %s (%s)", path, exc)
            continue

        class_blocks: list[str] = []
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not any(_is_dataclass_decorator(d) for d in node.decorator_list):
                continue
            if node.name.startswith("_"):
                continue
            block = _format_class(node)
            if block is not None:
                class_blocks.append(block)

        if not class_blocks:
            continue
        sections.append(f"# {_module_label(path)}\n" + "\n\n".join(class_blocks))

    return "\n\n".join(sections)


__all__ = ["extract_dataclasses"]
