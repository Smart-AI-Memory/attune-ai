"""Template engine for the documentation help system.

Loads generated templates, fills context parameters, resolves
cross-links, and adapts output for different audiences.

This is a runtime module — contextual.py and discovery.py can
import and use it to query templates instead of maintaining
hardcoded pattern lists.

Usage:
    from attune.help.engine import populate, TemplateContext, AudienceProfile

    result = populate("err-shadow-directories-at-repo-root-break-imports")
    print(result.title, result.body)

    result = populate(
        "ref-skill-security-audit",
        audience=AudienceProfile(channel="cli"),
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default location relative to repo root
_DEFAULT_GENERATED_DIR = Path(__file__).resolve().parents[3] / "plugin" / "help" / "generated"


@dataclass(frozen=True)
class TemplateContext:
    """Runtime parameters for template population.

    Pass context to customize template output based on
    what the user is currently working on.
    """

    file_path: str | None = None
    error_message: str | None = None
    workflow_name: str | None = None
    tool_name: str | None = None
    skill_name: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AudienceProfile:
    """Target audience for output adaptation.

    Attributes:
        channel: Output channel — claude-code, marketplace, or cli.
        verbosity: Detail level — compact, normal, or detailed.
    """

    channel: str = "claude-code"
    verbosity: str = "normal"


@dataclass
class PopulatedTemplate:
    """Result of template population.

    Contains the fully resolved template with cross-links
    and audience-adapted content.
    """

    template_id: str
    type: str
    subtype: str
    name: str
    title: str
    body: str
    sections: dict[str, str]
    tags: list[str]
    related: list[dict[str, str]]
    confidence: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _find_template_file(
    template_id: str,
    generated_dir: Path,
) -> Path | None:
    """Locate the template file on disk.

    Template IDs use the format: {type_prefix}-{name}
    - err-shadow-dirs -> errors/shadow-dirs.md
    - war-shadow-dirs -> warnings/shadow-dirs.md
    - tip-after-code-review -> tips/after-code-review.md
    - ref-skill-security-audit -> references/skill-security-audit.md

    Args:
        template_id: Template identifier string.
        generated_dir: Path to generated/ directory.

    Returns:
        Path to the template file, or None.
    """
    prefix_map = {
        "err": "errors",
        "war": "warnings",
        "tip": "tips",
        "ref": "references",
    }

    parts = template_id.split("-", 1)
    if len(parts) != 2:
        return None

    prefix, name = parts
    type_dir = prefix_map.get(prefix)
    if not type_dir:
        return None

    filepath = generated_dir / type_dir / f"{name}.md"
    if filepath.exists():
        return filepath

    return None


def _parse_template_file(filepath: Path) -> dict[str, Any]:
    """Parse a generated template file into structured data.

    Extracts YAML frontmatter and markdown body sections.

    Args:
        filepath: Path to the template .md file.

    Returns:
        Dict with frontmatter fields and parsed sections.
    """
    import frontmatter as fm

    post = fm.load(str(filepath))

    # Extract sections from body
    sections: dict[str, str] = {}
    current_heading = ""
    current_lines: list[str] = []

    for line in post.content.split("\n"):
        if line.startswith("## "):
            if current_heading:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = line[3:].strip()
            current_lines = []
        elif current_heading:
            current_lines.append(line)

    if current_heading:
        sections[current_heading] = "\n".join(current_lines).strip()

    # Extract title from # heading
    title = ""
    for line in post.content.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Parse tags — may be list or string
    tags_raw = post.get("tags", [])
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",")]
    else:
        tags = list(tags_raw)

    return {
        "type": post.get("type", ""),
        "subtype": post.get("subtype", ""),
        "name": post.get("name", filepath.stem),
        "title": title,
        "confidence": post.get("confidence", ""),
        "source": post.get("source", ""),
        "category": post.get("category", ""),
        "tags": tags,
        "sections": sections,
        "body": post.content,
    }


def _load_cross_links(generated_dir: Path) -> dict[str, Any]:
    """Load the cross-links index.

    Args:
        generated_dir: Path to generated/ directory.

    Returns:
        Parsed cross_links.json, or empty dict.
    """
    index_path = generated_dir / "cross_links.json"
    if not index_path.exists():
        return {}

    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load cross_links.json: %s", e)
        return {}


def _resolve_related(
    template_id: str,
    cross_links: dict[str, Any],
) -> list[dict[str, str]]:
    """Resolve cross-links for a template into related items.

    Args:
        template_id: The template's ID.
        cross_links: The full cross-links index.

    Returns:
        List of dicts with 'type' and 'id' keys.
    """
    links = cross_links.get("links", {}).get(template_id, {})
    related: list[dict[str, str]] = []

    relationship_types = {
        "related_warning": "Warning",
        "related_error": "Error",
        "prevented_by": "Tip",
        "references_tools": "Tool Reference",
        "referenced_by_skills": "Skill Reference",
    }

    for key, label in relationship_types.items():
        for ref_id in links.get(key, []):
            related.append({"type": label, "id": ref_id})

    return related


def _adapt_for_audience(
    body: str,
    sections: dict[str, str],
    audience: AudienceProfile,
) -> str:
    """Adapt template content for the target audience.

    Args:
        body: Full markdown body.
        sections: Parsed sections dict.
        audience: Target audience profile.

    Returns:
        Adapted body string.
    """
    if audience.verbosity == "compact":
        # Compact: title + first section only
        parts = [body.split("\n")[0]]  # # Title line
        if "Signature" in sections:
            parts.append(f"\n**Signature:** {sections['Signature']}")
        elif "Description" in sections:
            parts.append(f"\n{sections['Description']}")

        if "Resolution" in sections:
            parts.append(f"\n**Fix:** {sections['Resolution']}")
        elif "Mitigation" in sections:
            parts.append(f"\n**Fix:** {sections['Mitigation']}")

        return "\n".join(parts)

    if audience.channel == "claude-code":
        # Strip Related Topics section — Claude Code will
        # handle navigation itself
        lines = []
        skip = False
        for line in body.split("\n"):
            if line.startswith("## Related Topics"):
                skip = True
                continue
            if skip and line.startswith("## "):
                skip = False
            if not skip:
                lines.append(line)
        return "\n".join(lines).rstrip()

    # Normal/detailed: return full body
    return body


def populate(
    template_id: str,
    context: TemplateContext | None = None,
    audience: AudienceProfile | None = None,
    *,
    generated_dir: str | Path | None = None,
) -> PopulatedTemplate | None:
    """Populate a template with context and audience adaptation.

    Loads the template from disk, resolves cross-links, and
    adapts content for the target audience.

    Args:
        template_id: Template identifier (e.g. "err-shadow-dirs").
        context: Optional runtime context parameters.
        audience: Optional audience profile (defaults to claude-code).
        generated_dir: Override path to generated/ directory.

    Returns:
        PopulatedTemplate, or None if template not found.
    """
    if audience is None:
        audience = AudienceProfile()

    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR

    # Step 1: Find and load template
    filepath = _find_template_file(template_id, gen_dir)
    if filepath is None:
        logger.debug("Template not found: %s", template_id)
        return None

    data = _parse_template_file(filepath)

    # Step 2: Resolve cross-links
    cross_links = _load_cross_links(gen_dir)
    related = _resolve_related(template_id, cross_links)

    # Step 3: Adapt for audience
    adapted_body = _adapt_for_audience(
        data["body"],
        data["sections"],
        audience,
    )

    # Step 4: Build metadata from context
    metadata: dict[str, Any] = {}
    if context:
        if context.file_path:
            metadata["file_path"] = context.file_path
        if context.error_message:
            metadata["error_message"] = context.error_message
        if context.workflow_name:
            metadata["workflow_name"] = context.workflow_name
        if context.extra:
            metadata.update(context.extra)

    return PopulatedTemplate(
        template_id=template_id,
        type=data["type"],
        subtype=data["subtype"],
        name=data["name"],
        title=data["title"],
        body=adapted_body,
        sections=data["sections"],
        tags=data["tags"],
        related=related,
        confidence=data["confidence"],
        source=data["source"],
        metadata=metadata,
    )


def search_by_tag(
    tag: str,
    *,
    generated_dir: str | Path | None = None,
) -> list[str]:
    """Find template IDs matching a tag.

    Args:
        tag: Tag to search for.
        generated_dir: Override path to generated/ directory.

    Returns:
        List of matching template IDs.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    return cross_links.get("tag_index", {}).get(tag, [])


def list_tags(
    *,
    generated_dir: str | Path | None = None,
) -> dict[str, int]:
    """List all tags with their template counts.

    Args:
        generated_dir: Override path to generated/ directory.

    Returns:
        Dict of tag -> count, sorted by count descending.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    tag_index = cross_links.get("tag_index", {})
    return dict(
        sorted(
            ((tag, len(ids)) for tag, ids in tag_index.items()),
            key=lambda x: x[1],
            reverse=True,
        )
    )
