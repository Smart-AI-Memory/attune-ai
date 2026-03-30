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
    compose: bool = False,
) -> PopulatedTemplate | None:
    """Populate a template with context and audience adaptation.

    Loads the template from disk, resolves cross-links, and
    adapts content for the target audience. When compose=True,
    inlines embedded templates (tips, tool refs) into the body.

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

    # Step 5: Compose embedded templates (max depth 1)
    composed_from: list[str] = []
    if compose:
        links_data = cross_links.get("links", {}).get(template_id, {})
        for embed in links_data.get("embeds", []):
            embed_id = embed["id"]
            embed_result = populate(
                embed_id,
                audience=AudienceProfile(verbosity="compact"),
                generated_dir=generated_dir,
                compose=False,  # no recursive composition
            )
            if embed_result:
                adapted_body += (
                    f"\n\n---\n\n**Related:** {embed_result.title}\n\n{embed_result.body}"
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


# -----------------------------------------------------------
# Progressive depth: auto-escalate on repeated access
# -----------------------------------------------------------

_DEPTH_VERBOSITY = {0: "compact", 1: "normal", 2: "detailed"}

_session_state: dict[str, Any] = {
    "last_template_id": None,
    "depth_level": 0,
}


def populate_progressive(
    template_id: str,
    context: TemplateContext | None = None,
    audience: AudienceProfile | None = None,
    *,
    generated_dir: str | Path | None = None,
) -> PopulatedTemplate | None:
    """Populate with automatic depth escalation.

    On repeated calls with the same template_id, verbosity
    escalates: compact -> normal -> detailed. Switching to
    a different template resets depth to compact.

    Args:
        template_id: Template identifier.
        context: Optional runtime context.
        audience: Optional audience profile (verbosity overridden).
        generated_dir: Override path to generated/ directory.

    Returns:
        PopulatedTemplate with metadata["depth_level"], or None.
    """
    state = _session_state

    if template_id == state["last_template_id"]:
        state["depth_level"] = min(state["depth_level"] + 1, 2)
    else:
        state["last_template_id"] = template_id
        state["depth_level"] = 0

    depth = state["depth_level"]
    verbosity = _DEPTH_VERBOSITY[depth]

    if audience is None:
        audience = AudienceProfile(verbosity=verbosity)
    else:
        audience = AudienceProfile(
            channel=audience.channel,
            verbosity=verbosity,
        )

    result = populate(
        template_id,
        context=context,
        audience=audience,
        generated_dir=generated_dir,
    )

    if result is not None:
        result.metadata["depth_level"] = depth

    return result


# -----------------------------------------------------------
# Workflow chain prediction
# -----------------------------------------------------------


def get_workflow_help(
    workflow_name: str,
    *,
    generated_dir: str | Path | None = None,
    max_results: int = 3,
) -> list[PopulatedTemplate]:
    """Get help templates relevant after a workflow completes.

    Looks up the workflow_map in cross_links.json and returns
    compact templates for the mapped entries.

    Args:
        workflow_name: Workflow slug (e.g. "code-review").
        generated_dir: Override path to generated/ directory.
        max_results: Maximum templates to return.

    Returns:
        List of PopulatedTemplate at compact verbosity.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    workflow_map = cross_links.get("workflow_map", {})

    template_ids = workflow_map.get(workflow_name, [])
    if not template_ids:
        return []

    audience = AudienceProfile(verbosity="compact")
    results: list[PopulatedTemplate] = []

    for tid in template_ids[:max_results]:
        result = populate(tid, audience=audience, generated_dir=generated_dir)
        if result:
            results.append(result)

    return results


# -----------------------------------------------------------
# Error precursor detection
# -----------------------------------------------------------

_EXTENSION_TAG_MAP: dict[str, list[str]] = {
    ".py": ["python", "imports", "testing"],
    ".yml": ["ci"],
    ".yaml": ["ci"],
    ".json": ["packaging"],
    ".toml": ["packaging", "python"],
    ".md": ["claude-code"],
    ".js": [],
    ".ts": [],
}


def get_precursor_warnings(
    file_path: str,
    *,
    generated_dir: str | Path | None = None,
    max_results: int = 3,
) -> list[PopulatedTemplate]:
    """Get warnings relevant to a file being edited.

    Maps the file extension to tags, queries the cross-link
    tag index, and returns matching warning/error templates.

    Args:
        file_path: Path to the file being edited.
        generated_dir: Override path to generated/ directory.
        max_results: Maximum templates to return.

    Returns:
        List of PopulatedTemplate at compact verbosity.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    tag_index = cross_links.get("tag_index", {})

    # Determine relevant tags from file extension
    ext = Path(file_path).suffix.lower()
    relevant_tags = _EXTENSION_TAG_MAP.get(ext, [])
    if not relevant_tags:
        return []

    # Collect candidate template IDs from matching tags
    candidates: dict[str, int] = {}  # template_id -> match count
    for tag in relevant_tags:
        for tid in tag_index.get(tag, []):
            # Only warnings and errors are precursor-relevant
            if tid.startswith(("war-", "err-")):
                candidates[tid] = candidates.get(tid, 0) + 1

    if not candidates:
        return []

    # Sort by match count (more tag overlaps = more relevant)
    sorted_ids = sorted(candidates, key=lambda t: candidates[t], reverse=True)

    audience = AudienceProfile(verbosity="compact")
    results: list[PopulatedTemplate] = []

    for tid in sorted_ids[:max_results]:
        result = populate(tid, audience=audience, generated_dir=generated_dir)
        if result:
            results.append(result)

    return results


def reset_session() -> None:
    """Reset progressive depth session state."""
    _session_state["last_template_id"] = None
    _session_state["depth_level"] = 0


# -----------------------------------------------------------
# Usage-driven priority
# -----------------------------------------------------------


def get_usage_weights(
    days: int = 30,
) -> dict[str, float]:
    """Get template relevance weights from usage telemetry.

    Reads workflow usage from UsageTracker and maps to
    template IDs via the workflow_map in cross_links.json.

    Args:
        days: Number of days to look back.

    Returns:
        Dict of template_id -> weight (0.0-1.0).
        Empty dict if telemetry unavailable.
    """
    try:
        from attune.telemetry.usage_tracker import UsageTracker

        tracker = UsageTracker()
        stats = tracker.get_stats(days=days)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: telemetry is optional
        return {}

    by_workflow = stats.get("by_workflow", {})
    if not by_workflow:
        return {}

    # Normalize to 0.0-1.0 (values may be dicts or floats)
    costs: dict[str, float] = {}
    for wf_name, val in by_workflow.items():
        if isinstance(val, dict):
            costs[wf_name] = float(val.get("total_cost", 0))
        else:
            costs[wf_name] = float(val)

    max_cost = max(costs.values(), default=0)
    if max_cost <= 0:
        return {}

    wf_weights: dict[str, float] = {}
    for wf_name, cost in costs.items():
        wf_weights[wf_name] = cost / max_cost

    # Map workflow weights to template IDs via workflow_map
    cross_links = _load_cross_links(_DEFAULT_GENERATED_DIR)
    workflow_map = cross_links.get("workflow_map", {})

    template_weights: dict[str, float] = {}
    for wf_name, weight in wf_weights.items():
        for tid in workflow_map.get(wf_name, []):
            template_weights[tid] = max(
                template_weights.get(tid, 0),
                weight,
            )

    return template_weights


def search_by_tag(
    tag: str,
    *,
    generated_dir: str | Path | None = None,
    sort_by_usage: bool = False,
) -> list[str]:
    """Find template IDs matching a tag.

    Args:
        tag: Tag to search for.
        generated_dir: Override path to generated/ directory.
        sort_by_usage: Sort results by usage frequency.

    Returns:
        List of matching template IDs.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    results = cross_links.get("tag_index", {}).get(tag, [])

    if sort_by_usage and results:
        weights = get_usage_weights()
        if weights:
            results = sorted(
                results,
                key=lambda tid: weights.get(tid, 0),
                reverse=True,
            )

    return results


def list_tags(
    *,
    generated_dir: str | Path | None = None,
    sort_by_usage: bool = False,
) -> dict[str, int]:
    """List all tags with their template counts.

    Args:
        generated_dir: Override path to generated/ directory.
        sort_by_usage: Sort by aggregate usage weight.

    Returns:
        Dict of tag -> count, sorted by count or usage.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    tag_index = cross_links.get("tag_index", {})

    if sort_by_usage:
        weights = get_usage_weights()
        if weights:
            # Sort by sum of weights for templates in each tag
            def tag_weight(item: tuple[str, list[str]]) -> float:
                tag_name, tids = item
                return sum(weights.get(tid, 0) for tid in tids)

            return {
                tag: len(ids)
                for tag, ids in sorted(
                    tag_index.items(),
                    key=tag_weight,
                    reverse=True,
                )
            }

    return dict(
        sorted(
            ((tag, len(ids)) for tag, ids in tag_index.items()),
            key=lambda x: x[1],
            reverse=True,
        )
    )


# -----------------------------------------------------------
# Feedback loop
# -----------------------------------------------------------

_FEEDBACK_FILE = "feedback.json"


def _load_feedback(generated_dir: Path) -> dict[str, dict]:
    """Load feedback data from feedback.json.

    Args:
        generated_dir: Path to generated/ directory.

    Returns:
        Dict of template_id -> {good: int, bad: int}.
    """
    path = generated_dir / _FEEDBACK_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load feedback.json: %s", e)
        return {}


def _save_feedback(generated_dir: Path, data: dict) -> None:
    """Save feedback data atomically.

    Args:
        generated_dir: Path to generated/ directory.
        data: Feedback dict to save.
    """
    path = generated_dir / _FEEDBACK_FILE
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.rename(path)


def record_template_feedback(
    template_id: str,
    rating: str,
    *,
    generated_dir: str | Path | None = None,
) -> float:
    """Record user feedback on a template.

    Args:
        template_id: Template to rate.
        rating: "good" or "bad".
        generated_dir: Override path to generated/ directory.

    Returns:
        Updated confidence score (0.0-1.0).
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    feedback = _load_feedback(gen_dir)

    if template_id not in feedback:
        feedback[template_id] = {"good": 0, "bad": 0}

    if rating == "good":
        feedback[template_id]["good"] += 1
    elif rating == "bad":
        feedback[template_id]["bad"] += 1

    _save_feedback(gen_dir, feedback)

    return get_template_confidence(template_id, generated_dir=generated_dir)


def get_template_confidence(
    template_id: str,
    *,
    generated_dir: str | Path | None = None,
) -> float:
    """Get confidence score for a template based on feedback.

    Returns good / (good + bad), or 1.0 if no feedback.

    Args:
        template_id: Template to check.
        generated_dir: Override path to generated/ directory.

    Returns:
        Confidence score 0.0-1.0.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    feedback = _load_feedback(gen_dir)

    entry = feedback.get(template_id)
    if not entry:
        return 1.0

    good = entry.get("good", 0)
    bad = entry.get("bad", 0)
    total = good + bad

    if total == 0:
        return 1.0

    return good / total
