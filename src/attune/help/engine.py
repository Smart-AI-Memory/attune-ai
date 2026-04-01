"""Template engine for the documentation help system.

Facade module — re-exports all public APIs from the
split modules so existing imports continue to work:

    from attune.help.engine import populate, TemplateContext
    from attune.help.engine import populate_progressive
    from attune.help.engine import get_workflow_help
"""

from __future__ import annotations

# Re-export from feedback.py (ratings, search, workflows)
from attune.help.feedback import (
    get_precursor_warnings,
    get_template_confidence,
    get_usage_weights,
    get_workflow_help,
    list_tags,
    record_template_feedback,
    search_by_tag,
)

# Re-export from progression.py (type-driven depth)
from attune.help.progression import (
    _extract_topic,
    _resolve_topic_at_level,
    populate_progressive,
    reset_session,
)

# Re-export from templates.py (core loading/population)
from attune.help.templates import (
    AudienceProfile,
    PopulatedTemplate,
    TemplateContext,
    _adapt_for_audience,
    _find_template_file,
    _load_cross_links,
    _parse_template_file,
    _resolve_related,
    populate,
)

__all__ = [
    # Dataclasses
    "AudienceProfile",
    "PopulatedTemplate",
    "TemplateContext",
    # Core
    "populate",
    "populate_progressive",
    "reset_session",
    # Queries
    "get_workflow_help",
    "get_precursor_warnings",
    "search_by_tag",
    "list_tags",
    # Feedback
    "record_template_feedback",
    "get_template_confidence",
    "get_usage_weights",
    # Internal (used by tests)
    "_find_template_file",
    "_parse_template_file",
    "_load_cross_links",
    "_resolve_related",
    "_adapt_for_audience",
    "_extract_topic",
    "_resolve_topic_at_level",
]
