"""Context-sensitive preamble for workflow skills.

Extracts the opening "Use X when..." line from a feature's
task template. Displayed automatically when a user invokes
a workflow, before the Socratic scoping questions.

Also provides related feature suggestions based on shared
tags for post-workflow help.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_HELP_DIR = Path.cwd() / ".help"


def get_preamble(
    feature_name: str,
    help_dir: str | Path | None = None,
) -> str | None:
    """Get the one-liner preamble for a feature.

    Reads the task template and returns the first
    non-empty paragraph after the h1 heading — typically
    the "Use X when..." sentence.

    Args:
        feature_name: Feature slug (e.g. "security").
        help_dir: Path to .help/ directory.

    Returns:
        Preamble string, or None if not available.
    """
    base = Path(help_dir) if help_dir else _DEFAULT_HELP_DIR
    task_path = base / "templates" / feature_name / "task.md"

    if not task_path.exists():
        logger.debug("No task template for %s", feature_name)
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


def get_related_preambles(
    feature_name: str,
    help_dir: str | Path | None = None,
    max_results: int = 3,
) -> list[dict[str, str]]:
    """Get preambles for features related by shared tags.

    Finds features that share tags with the given feature,
    ranked by number of shared tags. Useful for post-workflow
    "you might also want..." suggestions.

    Args:
        feature_name: The current feature slug.
        help_dir: Path to .help/ directory.
        max_results: Maximum related features to return.

    Returns:
        List of dicts with 'feature' and 'preamble' keys.
    """
    base = Path(help_dir) if help_dir else _DEFAULT_HELP_DIR
    manifest_path = base / "features.yaml"

    if not manifest_path.exists():
        return []

    try:
        from attune.help.manifest import load_manifest

        manifest = load_manifest(base)
    except (FileNotFoundError, ValueError) as e:
        logger.debug("Cannot load manifest: %s", e)
        return []

    current = manifest.features.get(feature_name)
    if not current or not current.tags:
        return []

    current_tags = set(current.tags)

    scored: list[tuple[int, str]] = []
    for name, feat in manifest.features.items():
        if name == feature_name:
            continue
        if not feat.tags:
            continue
        overlap = len(current_tags & set(feat.tags))
        if overlap > 0:
            scored.append((overlap, name))

    scored.sort(reverse=True)

    results: list[dict[str, str]] = []
    for _score, name in scored[:max_results]:
        preamble = get_preamble(name, help_dir)
        if preamble:
            results.append({"feature": name, "preamble": preamble})

    return results
