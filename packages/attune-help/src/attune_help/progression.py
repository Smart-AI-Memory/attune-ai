"""Type-driven progressive depth for help templates.

Resolves topics across template types: concept (level 0),
procedural/task (level 1), reference (level 2). Session
state tracks depth and auto-advances on repeat calls.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from attune_help.storage import SessionStorage
from attune_help.templates import (
    AudienceProfile,
    PopulatedTemplate,
    _find_template_file,
    populate,
)

logger = logging.getLogger(__name__)

_DEPTH_VERBOSITY = {0: "compact", 1: "normal", 2: "detailed"}
_LEVEL_LABELS = {0: "concept", 1: "procedural", 2: "reference"}

_TOPIC_PATTERNS: dict[int, list[str]] = {
    0: ["con-tool-{topic}", "con-{topic}"],
    1: ["tas-use-{topic}", "tas-tool-{topic}", "tas-{topic}"],
    2: ["ref-skill-{topic}", "ref-tool-{topic}", "ref-{topic}"],
}

# Ordered longest-first so compound prefixes match before
# their shorter components (e.g. "ref-skill-" before "ref-").
_COMPOUND_PREFIXES = [
    "ref-skill-",
    "ref-tool-",
    "ref-",
    "tas-use-",
    "tas-tool-",
    "tas-",
    "con-tool-",
    "con-",
    "err-",
    "war-",
    "tip-",
    "faq-",
    "not-",
    "qui-",
    "tro-",
    "com-",
]


def _extract_topic(template_id: str) -> str | None:
    """Extract the base topic slug from a template ID.

    Args:
        template_id: Full template ID or bare topic slug.

    Returns:
        Base topic slug, or None if invalid.
    """
    for prefix in _COMPOUND_PREFIXES:
        if template_id.startswith(prefix):
            topic = template_id[len(prefix) :]
            return topic if topic else None

    return template_id if template_id else None


def _resolve_topic_at_level(
    topic: str,
    level: int,
    generated_dir: Path,
) -> str | None:
    """Resolve a topic to a template ID at a depth level.

    Args:
        topic: Base topic slug (e.g. 'security-audit').
        level: Depth level (0=concept, 1=task, 2=reference).
        generated_dir: Path to generated/ directory.

    Returns:
        Template ID string, or None if no match.
    """
    patterns = _TOPIC_PATTERNS.get(level, [])
    for pattern in patterns:
        candidate = pattern.format(topic=topic)
        if _find_template_file(candidate, generated_dir) is not None:
            return candidate
    return None


def populate_progressive(
    template_id: str,
    storage: SessionStorage,
    user_id: str = "default",
    context: Any = None,
    audience: AudienceProfile | None = None,
    *,
    generated_dir: str | Path,
    starting_level: int | None = None,
) -> PopulatedTemplate | None:
    """Populate with type-driven depth escalation.

    First call serves concept, repeat calls escalate to
    task then reference. Falls back to verbosity-based if
    type-specific templates don't exist.

    Args:
        template_id: Template identifier or bare topic slug.
        storage: Session storage backend.
        user_id: User identifier for session tracking.
        context: Optional TemplateContext.
        audience: Optional audience profile.
        generated_dir: Path to generated/ directory.
        starting_level: Override starting depth (0-2).

    Returns:
        PopulatedTemplate with depth metadata, or None.
    """
    gen_dir = Path(generated_dir)

    topic = _extract_topic(template_id)
    if not topic:
        return None

    # Compute depth from session state (but don't persist yet)
    session = storage.get_session(user_id)
    if topic == session.get("last_topic"):
        depth = min(session.get("depth_level", 0) + 1, 2)
    else:
        depth = starting_level if starting_level is not None else 0

    # Try type-driven resolution
    resolved_id = _resolve_topic_at_level(topic, depth, gen_dir)
    if resolved_id is not None:
        result = populate(
            resolved_id,
            context=context,
            audience=audience,
            generated_dir=generated_dir,
        )
        if result is not None:
            # Only persist after successful resolution
            storage.set_session(
                user_id,
                {"last_topic": topic, "depth_level": depth},
            )
            result.metadata["depth_level"] = depth
            result.metadata["level_label"] = _LEVEL_LABELS.get(depth, "")
            result.metadata["topic"] = topic
            return result

    # Fallback: verbosity-based on the original template ID
    verbosity = _DEPTH_VERBOSITY.get(depth, "normal")
    fallback_audience = AudienceProfile(
        channel=audience.channel if audience else "claude-code",
        verbosity=verbosity,
    )

    result = populate(
        template_id,
        context=context,
        audience=fallback_audience,
        generated_dir=generated_dir,
    )

    if result is not None:
        # Persist only on successful fallback too
        storage.set_session(
            user_id,
            {"last_topic": topic, "depth_level": depth},
        )
        result.metadata["depth_level"] = depth
        result.metadata["level_label"] = _LEVEL_LABELS.get(depth, "")
        result.metadata["topic"] = topic

    return result
