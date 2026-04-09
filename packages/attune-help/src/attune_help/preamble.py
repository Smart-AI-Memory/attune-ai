"""Context-sensitive preamble extraction.

Reads the "Use X when..." one-liner from a feature's
task template. Works with any template directory — no
manifest or authoring toolkit required.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_preamble(
    feature_name: str,
    template_dir: str | Path,
) -> str | None:
    """Get the one-liner preamble for a feature.

    Reads the task template and returns the first
    non-empty paragraph after the h1 heading.

    Args:
        feature_name: Feature slug (e.g. "security").
        template_dir: Path to templates directory
            (containing feature subdirectories).

    Returns:
        Preamble string, or None if not available.
    """
    if (
        not feature_name
        or "/" in feature_name
        or "\\" in feature_name
        or ".." in feature_name
        or "\x00" in feature_name
    ):
        return None
    task_path = Path(template_dir) / feature_name / "task.md"

    if not task_path.exists():
        return None

    try:
        text = task_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.debug("Cannot read %s: %s", task_path, e)
        return None

    return _extract_preamble(text)


def _extract_preamble(text: str) -> str | None:
    """Extract preamble from task template content.

    Skips YAML frontmatter and the h1 heading, returns
    the first non-empty paragraph.

    Args:
        text: Full task template content.

    Returns:
        Preamble line, or None.
    """
    lines = text.split("\n")

    # Skip frontmatter
    in_frontmatter = False
    content_start = 0
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and line.strip() == "---":
            content_start = i + 1
            break

    # Find first non-empty, non-heading line
    for line in lines[content_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        return stripped

    return None
