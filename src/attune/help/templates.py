"""Template loading, parsing, and population.

Core I/O layer for the help system. Handles template file
resolution, YAML frontmatter parsing, cross-link loading
(with caching), audience adaptation, and template composition.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_GENERATED_DIR = Path(__file__).resolve().parents[3] / "plugin" / "help" / "generated"

# Single-source projector output (feature-organized:
# .help/templates/<feature>/<kind>.md). The resolver falls back here
# when an ID is absent from the type-organized bundle, so the
# in-conversation help surface serves the single-sourced content.
# (help-serving-bridge spec, D1, 2026-06-24.)
_DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / ".help" / "templates"

# Cross-links cache: loaded once per process, thread-safe.
# Call invalidate_cross_links_cache() to force a reload.
_CROSS_LINKS_CACHE: dict[str, dict[str, Any]] = {}
_CROSS_LINKS_LOCK = threading.Lock()


def invalidate_cross_links_cache() -> None:
    """Clear the cross-links cache so the next lookup re-reads disk.

    Call after regenerating templates in a long-running process
    (e.g., MCP server) to pick up changes without restart.
    """
    with _CROSS_LINKS_LOCK:
        _CROSS_LINKS_CACHE.clear()


@dataclass(frozen=True)
class TemplateContext:
    """Runtime parameters for template population."""

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
        channel: claude-code, marketplace, or cli.
        verbosity: compact, normal, or detailed.
    """

    channel: str = "claude-code"
    verbosity: str = "normal"


@dataclass
class PopulatedTemplate:
    """Result of template population."""

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


# ------------------------------------------------------------------
# Template file resolution
# ------------------------------------------------------------------

_PREFIX_MAP = {
    "err": "errors",
    "war": "warnings",
    "tip": "tips",
    "ref": "references",
    "tas": "tasks",
    "faq": "faqs",
    "not": "notes",
    "qui": "quickstarts",
    "con": "concepts",
    "tro": "troubleshooting",
    "com": "comparisons",
}

# ID prefix -> singular kind filename in the single-source layout
# (.help/templates/<feature>/<kind>.md). Mirrors _PREFIX_MAP, whose
# values are the type-organized bundle's plural directory names.
_PREFIX_TO_KIND = {
    "err": "error",
    "war": "warning",
    "tip": "tip",
    "ref": "reference",
    "tas": "task",
    "faq": "faq",
    "not": "note",
    "qui": "quickstart",
    "con": "concept",
    "tro": "troubleshooting",
    "com": "comparison",
}


def _templates_dir_for(generated_dir: Path) -> Path | None:
    """Derive the single-source templates dir paired with a bundle dir.

    The canonical bundle is ``<root>/plugin/help/generated``; the
    single-source projector writes to ``<root>/.help/templates``. Only
    the canonical bundle layout gets an implicit fallback, so a custom
    ``generated_dir`` (e.g. a test tmp dir) resolves deterministically
    with no surprise fallback.

    Args:
        generated_dir: The bundle directory being resolved against.

    Returns:
        The paired ``.help/templates`` dir, or None for non-canonical
        layouts.
    """
    resolved = generated_dir.resolve()
    if resolved.parts[-3:] == ("plugin", "help", "generated"):
        return resolved.parents[2] / ".help" / "templates"
    return None


def _find_template_file(
    template_id: str,
    generated_dir: Path,
) -> Path | None:
    """Locate a template file on disk.

    Resolves an ID against the type-organized bundle first; if absent,
    falls back to the single-source layout
    (``.help/templates/<feature>/<kind>.md``) so the in-conversation
    help surface serves single-sourced content (help-serving-bridge D1).

    Args:
        template_id: Template identifier string.
        generated_dir: Path to generated/ directory.

    Returns:
        Path to the template file, or None.
    """
    parts = template_id.split("-", 1)
    if len(parts) != 2:
        return None

    prefix, name = parts
    type_dir = _PREFIX_MAP.get(prefix)
    if not type_dir:
        return None

    filepath = generated_dir / type_dir / f"{name}.md"

    # Containment check: prevent path traversal (CWE-22)
    try:
        filepath.resolve().relative_to(generated_dir.resolve())
    except ValueError:
        logger.warning("Path traversal blocked: %s", template_id)
        return None

    if filepath.exists():
        return filepath

    # Fallback: single-source content (help-serving-bridge D1).
    fallback = _find_single_source_file(prefix, name, generated_dir)
    if fallback is not None:
        return fallback
    return None


def _find_single_source_file(
    prefix: str,
    name: str,
    generated_dir: Path,
) -> Path | None:
    """Resolve an ID to a single-source template, or None.

    Args:
        prefix: ID type prefix (e.g. ``con``).
        name: Feature slug (the ID's second segment).
        generated_dir: The bundle dir being resolved against.

    Returns:
        Path to ``.help/templates/<name>/<kind>.md`` if it exists and is
        contained within the templates dir, else None.
    """
    kind = _PREFIX_TO_KIND.get(prefix)
    if kind is None:
        return None

    templates_dir = _templates_dir_for(generated_dir)
    if templates_dir is None:
        return None

    candidate = templates_dir / name / f"{kind}.md"

    # Containment check: prevent path traversal (CWE-22)
    try:
        candidate.resolve().relative_to(templates_dir.resolve())
    except ValueError:
        logger.warning("Path traversal blocked (fallback): %s-%s", prefix, name)
        return None

    if candidate.exists():
        return candidate
    return None


def _parse_template_file(filepath: Path) -> dict[str, Any]:
    """Parse a template file into structured data.

    Args:
        filepath: Path to the template .md file.

    Returns:
        Dict with frontmatter fields and parsed sections.
    """
    import frontmatter as fm

    post = fm.load(str(filepath))

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

    title = ""
    for line in post.content.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

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


# ------------------------------------------------------------------
# Cross-links (cached)
# ------------------------------------------------------------------


def _load_cross_links(generated_dir: Path) -> dict[str, Any]:
    """Load cross-links index with caching.

    Loaded once per process; subsequent calls return the
    cached copy. Thread-safe.

    Args:
        generated_dir: Path to generated/ directory.

    Returns:
        Parsed cross_links.json, or empty dict.
    """
    cache_key = str(generated_dir)
    with _CROSS_LINKS_LOCK:
        if cache_key in _CROSS_LINKS_CACHE:
            return _CROSS_LINKS_CACHE[cache_key]

        index_path = generated_dir / "cross_links.json"
        if not index_path.exists():
            return {}

        try:
            data = json.loads(
                index_path.read_text(encoding="utf-8"),
            )
            # Callers (_resolve_related) .get this straight away, so a
            # valid-JSON non-dict from a corrupt/partial write would
            # crash template rendering (library-review F4).
            if not isinstance(data, dict):
                logger.warning(
                    "cross_links.json is %s, expected mapping — ignoring",
                    type(data).__name__,
                )
                return {}
            _CROSS_LINKS_CACHE[cache_key] = data
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to load cross_links.json: %s",
                e,
            )
            return {}


def _resolve_related(
    template_id: str,
    cross_links: dict[str, Any],
) -> list[dict[str, str]]:
    """Resolve cross-links for a template.

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


# ------------------------------------------------------------------
# Audience adaptation
# ------------------------------------------------------------------


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
        parts = [body.split("\n")[0]]
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

    return body


# ------------------------------------------------------------------
# populate()
# ------------------------------------------------------------------


def populate(
    template_id: str,
    context: TemplateContext | None = None,
    audience: AudienceProfile | None = None,
    *,
    generated_dir: str | Path | None = None,
    compose: bool = False,
) -> PopulatedTemplate | None:
    """Populate a template with context and audience adaptation.

    Args:
        template_id: Template identifier (e.g. "err-shadow-dirs").
        context: Optional runtime context parameters.
        audience: Optional audience profile (defaults to claude-code).
        generated_dir: Override path to generated/ directory.
        compose: If True, inline embedded templates (max depth 1).

    Returns:
        PopulatedTemplate, or None if template not found.
    """
    if audience is None:
        audience = AudienceProfile()

    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR

    filepath = _find_template_file(template_id, gen_dir)
    if filepath is None:
        logger.debug("Template not found: %s", template_id)
        return None

    data = _parse_template_file(filepath)
    cross_links = _load_cross_links(gen_dir)
    related = _resolve_related(template_id, cross_links)

    adapted_body = _adapt_for_audience(
        data["body"],
        data["sections"],
        audience,
    )

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

    composed_from: list[str] = []
    if compose:
        links_data = cross_links.get("links", {}).get(template_id, {})
        for embed in links_data.get("embeds", []):
            embed_id = embed["id"]
            embed_result = populate(
                embed_id,
                audience=AudienceProfile(verbosity="compact"),
                generated_dir=generated_dir,
                compose=False,
            )
            if embed_result:
                adapted_body += (
                    f"\n\n---\n\n**Related:** " f"{embed_result.title}\n\n{embed_result.body}"
                )
                composed_from.append(embed_id)

    if composed_from:
        metadata["composed_from"] = composed_from

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
