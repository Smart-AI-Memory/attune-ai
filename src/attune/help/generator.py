"""Template generation from source files.

Generates concept, task, and reference markdown templates
for a feature by reading its source files. Creates the
.help/templates/<feature>/ directory structure with YAML
frontmatter for staleness tracking.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from attune.help.manifest import Feature
from attune.help.staleness import _read_frontmatter_value, compute_source_hash

logger = logging.getLogger(__name__)

_DEPTH_NAMES = ("concept", "task", "reference")


@dataclass
class GeneratedTemplate:
    """Result of generating one template file.

    Attributes:
        feature: Feature name.
        depth: Template depth (concept/task/reference).
        path: Path where the file was written.
        source_hash: Hash of source files at generation time.
    """

    feature: str
    depth: str
    path: Path
    source_hash: str


@dataclass
class GenerationResult:
    """Result of generating templates for a feature.

    Attributes:
        feature: Feature name.
        templates: List of generated template files.
        source_hash: Hash of source files.
        matched_files: Source files that were read.
    """

    feature: str
    templates: list[GeneratedTemplate] = field(default_factory=list)
    source_hash: str = ""
    matched_files: list[str] = field(default_factory=list)


def generate_feature_templates(
    feature: Feature,
    help_dir: str | Path,
    project_root: str | Path,
    depths: list[str] | None = None,
    overwrite: bool = False,
) -> GenerationResult:
    """Generate help templates for a feature.

    Creates concept.md, task.md, and reference.md in the
    feature's template directory. Skips files with
    status: manual unless overwrite=True.

    Args:
        feature: The feature to generate for.
        help_dir: Path to the .help/ directory.
        project_root: Project root for resolving globs.
        depths: Which depths to generate (default: all 3).
        overwrite: If True, overwrite manual templates.

    Returns:
        GenerationResult with paths and metadata.
    """
    help_path = Path(help_dir)
    root = Path(project_root)
    target_depths = depths or list(_DEPTH_NAMES)

    # Guard against path traversal via crafted feature names
    if (
        not feature.name
        or "/" in feature.name
        or "\\" in feature.name
        or ".." in feature.name
        or "\x00" in feature.name
    ):
        raise ValueError(f"Invalid feature name: {feature.name!r}")

    # Compute source hash
    source_hash, matched_files = compute_source_hash(feature, root)

    # Extract info from source files
    source_info = _extract_source_info(matched_files, root)

    result = GenerationResult(
        feature=feature.name,
        source_hash=source_hash,
        matched_files=matched_files,
    )

    template_dir = help_path / "templates" / feature.name
    template_dir.mkdir(parents=True, exist_ok=True)

    for depth in target_depths:
        if depth not in _DEPTH_NAMES:
            logger.warning("Unknown depth '%s', skipping", depth)
            continue

        out_path = template_dir / f"{depth}.md"

        # Respect manual templates
        if out_path.exists() and not overwrite:
            if _is_manual(out_path):
                logger.info(
                    "Skipping %s/%s.md (status: manual)",
                    feature.name,
                    depth,
                )
                continue

        content = _render_template(
            feature=feature,
            depth=depth,
            source_hash=source_hash,
            source_info=source_info,
        )

        out_path.write_text(content, encoding="utf-8")
        result.templates.append(
            GeneratedTemplate(
                feature=feature.name,
                depth=depth,
                path=out_path,
                source_hash=source_hash,
            )
        )

    return result


def _is_manual(path: Path) -> bool:
    """Check if a template has status: manual in frontmatter.

    Args:
        path: Path to the template file.

    Returns:
        True if the template is hand-written.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False

    return _read_frontmatter_value(text, "status") == "manual"


@dataclass
class _SourceInfo:
    """Extracted information from source files."""

    public_functions: list[dict[str, str]] = field(default_factory=list)
    public_classes: list[dict[str, str]] = field(default_factory=list)
    module_docstrings: list[str] = field(default_factory=list)
    config_keys: list[str] = field(default_factory=list)
    file_count: int = 0


def _extract_source_info(
    matched_files: list[str],
    project_root: Path,
) -> _SourceInfo:
    """Extract public API info from Python source files.

    Reads AST to find public functions, classes, and
    module docstrings. Non-Python files are counted
    but not parsed.

    Args:
        matched_files: Relative paths to source files.
        project_root: Project root directory.

    Returns:
        Extracted source information.
    """
    info = _SourceInfo(file_count=len(matched_files))

    for rel_path in matched_files:
        if not rel_path.endswith(".py"):
            continue

        full_path = project_root / rel_path
        try:
            source = full_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel_path)
        except (OSError, SyntaxError) as e:
            logger.debug("Cannot parse %s: %s", rel_path, e)
            continue

        # Module docstring
        docstring = ast.get_docstring(tree)
        if docstring:
            first_line = docstring.split("\n")[0].strip()
            if first_line:
                info.module_docstrings.append(first_line)

        # Public functions and classes
        for node in ast.iter_child_nodes(tree):
            if isinstance(
                node, ast.FunctionDef | ast.AsyncFunctionDef
            ) and not node.name.startswith("_"):
                doc = ast.get_docstring(node) or ""
                first_line = doc.split("\n")[0].strip() if doc else ""
                info.public_functions.append(
                    {"name": node.name, "doc": first_line, "file": rel_path}
                )
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                doc = ast.get_docstring(node) or ""
                first_line = doc.split("\n")[0].strip() if doc else ""
                info.public_classes.append({"name": node.name, "doc": first_line, "file": rel_path})

    return info


def _render_template(
    feature: Feature,
    depth: str,
    source_hash: str,
    source_info: _SourceInfo,
) -> str:
    """Render a help template for a feature at a given depth.

    Args:
        feature: The feature.
        depth: concept, task, or reference.
        source_hash: SHA-256 of source files.
        source_info: Extracted source information.

    Returns:
        Markdown string with YAML frontmatter.
    """
    now = datetime.now(timezone.utc).isoformat()
    title = feature.name.replace("-", " ").replace("_", " ").title()

    frontmatter = (
        f"---\n"
        f"feature: {feature.name}\n"
        f"depth: {depth}\n"
        f"generated_at: {now}\n"
        f"source_hash: {source_hash}\n"
        f"status: generated\n"
        f"---\n"
    )

    if depth == "concept":
        body = _render_concept(title, feature, source_info)
    elif depth == "task":
        body = _render_task(title, feature, source_info)
    else:
        body = _render_reference(title, feature, source_info)

    result = frontmatter + "\n" + body
    if not result.endswith("\n"):
        result += "\n"
    return result


def _render_concept(
    title: str,
    feature: Feature,
    info: _SourceInfo,
) -> str:
    """Render a concept template."""
    lines = [f"# {title}\n"]

    # What
    lines.append("## What\n")
    if feature.description:
        lines.append(f"{feature.description}\n")
    elif info.module_docstrings:
        lines.append(f"{info.module_docstrings[0]}\n")
    else:
        lines.append(f"{title} feature.\n")

    # Why
    lines.append("## Why\n")
    lines.append(f"This feature provides {title.lower()} " f"functionality for the project.\n")

    # How
    lines.append("## How\n")
    if info.public_classes:
        lines.append("Key components:\n")
        for cls in info.public_classes[:5]:
            doc_part = f" — {cls['doc']}" if cls["doc"] else ""
            lines.append(f"- `{cls['name']}`{doc_part}\n")
        lines.append("")
    elif info.public_functions:
        lines.append("Key functions:\n")
        for fn in info.public_functions[:5]:
            doc_part = f" — {fn['doc']}" if fn["doc"] else ""
            lines.append(f"- `{fn['name']}()`{doc_part}\n")
        lines.append("")
    else:
        lines.append(
            f"See the source files ({info.file_count} files) " f"for implementation details.\n"
        )

    return "\n".join(lines)


def _render_task(
    title: str,
    feature: Feature,
    info: _SourceInfo,
) -> str:
    """Render a task template."""
    lines = [f"# Working with {title}\n"]

    lines.append("## Overview\n")
    lines.append(f"Common tasks for modifying or extending " f"{title.lower()}.\n")

    lines.append("## Key Files\n")
    if feature.files:
        for pattern in feature.files:
            lines.append(f"- `{pattern}`\n")
        lines.append("")

    lines.append("## Common Modifications\n")
    if info.public_functions:
        lines.append("Functions you may need to modify:\n")
        for fn in info.public_functions[:8]:
            lines.append(f"- `{fn['name']}()` in `{fn['file']}`\n")
        lines.append("")
    else:
        lines.append("Review the source files listed above for " "modification points.\n")

    return "\n".join(lines)


def _render_reference(
    title: str,
    feature: Feature,
    info: _SourceInfo,
) -> str:
    """Render a reference template."""
    lines = [f"# {title} Reference\n"]

    # Classes
    if info.public_classes:
        lines.append("## Classes\n")
        lines.append("| Class | Description | File |\n")
        lines.append("|-------|-------------|------|\n")
        for cls in info.public_classes:
            doc = cls["doc"] or "—"
            lines.append(f"| `{cls['name']}` | {doc} | `{cls['file']}` |\n")
        lines.append("")

    # Functions
    if info.public_functions:
        lines.append("## Functions\n")
        lines.append("| Function | Description | File |\n")
        lines.append("|----------|-------------|------|\n")
        for fn in info.public_functions:
            doc = fn["doc"] or "—"
            lines.append(f"| `{fn['name']}()` | {doc} | `{fn['file']}` |\n")
        lines.append("")

    # Source files
    lines.append("## Source Files\n")
    if feature.files:
        for pattern in feature.files:
            lines.append(f"- `{pattern}`\n")
    else:
        lines.append("No file patterns configured.\n")

    # Tags
    if feature.tags:
        lines.append("\n## Tags\n")
        lines.append(", ".join(f"`{t}`" for t in feature.tags) + "\n")

    return "\n".join(lines)
