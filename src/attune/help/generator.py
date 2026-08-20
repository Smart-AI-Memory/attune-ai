"""Template generation from source files.

DEPRECATED: this module is the in-repo 3-depth generator
(concept / task / reference only). New work should use the
absorbed ``attune.authoring.generator`` (via ``/coach maintain``
at release-prep cadence), which produces the full 11-kind
template set and is the canonical generator for ``.help/``
content. (The ``attune-author`` CLI was retired 2026-07-27 —
author-consolidation T4.)

The in-repo generator is retained as an internal-only escape
hatch for the MCP ``help_update`` tool and the help
maintenance workflow. Calls to ``generate_feature_templates``
emit a ``DeprecationWarning``.

See the project CLAUDE.md lesson on "Two parallel help-
template generators in the attune ecosystem drift silently"
for context.

Meta template resolution order:
1. Project's .help/meta_templates/ (if exists)
2. Package defaults in src/attune/help/meta_templates/
"""

from __future__ import annotations

import ast
import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import jinja2

from attune.help.manifest import Feature
from attune.help.staleness import _read_frontmatter_value, compute_source_hash

logger = logging.getLogger(__name__)

_DEPTH_NAMES = ("concept", "task", "reference")

# Package-level default meta templates
_DEFAULT_META_DIR = Path(__file__).resolve().parent / "meta_templates"


def _build_jinja_env(
    help_dir: Path | None = None,
) -> jinja2.Environment:
    """Build a Jinja2 environment with template resolution.

    Looks for meta templates in the project's .help/meta_templates/
    first, then falls back to package defaults.

    Args:
        help_dir: Path to the project's .help/ directory.

    Returns:
        Configured Jinja2 Environment.
    """
    search_paths: list[Path] = []

    # Project-local meta templates take priority
    if help_dir:
        project_meta = help_dir / "meta_templates"
        if project_meta.is_dir():
            search_paths.append(project_meta)

    # Package defaults as fallback
    search_paths.append(_DEFAULT_META_DIR)

    loader = jinja2.FileSystemLoader(
        [str(p) for p in search_paths],
    )
    return jinja2.Environment(  # nosec B701 — outputs markdown, not HTML
        loader=loader,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


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


@dataclass(order=True)
class GenerationResult:
    """Result of generating templates for a feature.

    Attributes:
        feature: Feature name.
        templates: List of generated template files.
        source_hash: Hash of source files.
        matched_files: Source files that were read.
    """

    feature: str
    templates: list[GeneratedTemplate] = field(default_factory=list, compare=False)
    source_hash: str = field(default="", compare=False)
    matched_files: list[str] = field(default_factory=list, compare=False)


def generate_feature_templates(
    feature: Feature,
    help_dir: str | Path,
    project_root: str | Path,
    depths: list[str] | None = None,
    overwrite: bool = False,
) -> GenerationResult:
    """Generate help templates for a feature.

    .. deprecated::
        This is the 3-depth generator (concept/task/reference only).
        Prefer the absorbed ``attune.authoring.generator``
        (``generate_feature_templates``), which produces the full
        11-kind template set.

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
    warnings.warn(
        "attune.help.generator.generate_feature_templates produces only "
        "3 depths and is deprecated. Use "
        "attune.authoring.generator.generate_feature_templates for the "
        "canonical 11-kind help template set.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    # Build Jinja2 environment with project-first resolution
    env = _build_jinja_env(help_path)

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
            env=env,
            feature=feature,
            depth=depth,
            source_hash=source_hash,
            source_info=source_info,
        )

        # LLM polish pass — improves writing quality
        content = _maybe_polish(content, feature, source_info)

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


def _maybe_polish(
    content: str,
    feature: Feature,
    source_info: _SourceInfo,
) -> str:
    """Run the LLM polish pass if an API key is available.

    Args:
        content: Jinja2-rendered template content.
        feature: The feature being documented.
        source_info: Extracted source information.

    Returns:
        Polished content, or original if polish unavailable.
    """
    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return content

    from attune.help.polish import build_source_summary, polish_template

    summary = build_source_summary(
        public_classes=source_info.public_classes,
        public_functions=source_info.public_functions,
        module_docstrings=source_info.module_docstrings,
        file_count=source_info.file_count,
    )

    return polish_template(content, feature.name, summary)


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
        except (
            OSError,
            SyntaxError,
            ValueError,
        ) as e:  # ast.parse: null bytes -> ValueError, not SyntaxError
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
    env: jinja2.Environment,
    feature: Feature,
    depth: str,
    source_hash: str,
    source_info: _SourceInfo,
) -> str:
    """Render a help template using Jinja2 meta templates.

    Args:
        env: Jinja2 environment with template search paths.
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

    template = env.get_template(f"{depth}.md.j2")
    body = template.render(
        title=title,
        feature_name=feature.name,
        description=feature.description,
        file_patterns=feature.files,
        tags=feature.tags,
        public_classes=source_info.public_classes,
        public_functions=source_info.public_functions,
        module_docstrings=source_info.module_docstrings,
        config_keys=source_info.config_keys,
        file_count=source_info.file_count,
    )

    # Strip trailing whitespace per line to avoid
    # perpetual pre-commit failures
    body = "\n".join(line.rstrip() for line in body.splitlines())

    result = frontmatter + "\n" + body
    if not result.endswith("\n"):
        result += "\n"
    return result
