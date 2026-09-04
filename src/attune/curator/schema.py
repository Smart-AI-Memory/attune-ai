"""JSON schema for the curator's tool-use output.

The orchestrator has the model call a single ``emit_curation`` tool
whose ``input`` is guaranteed to match :data:`_CURATION_SCHEMA` (per
the CLAUDE.md lesson "Forced Anthropic tool-use is the cleanest path to
guaranteed-schema JSON"; on Fable 5.1, which rejects forced
``tool_choice``, the guarantee comes from strict tool use instead). The
schema is the ``docs/specs/bulletin-curator/design.md`` "Output schema"
plus ``additionalProperties: false`` on every object — strict tool use
requires it.

``output_schema(max_items)`` returns the schema with the
``items.maxItems`` cap set dynamically so callers can bound how many
attention items the briefing surfaces.
"""

from __future__ import annotations

import copy
from typing import Any

# Verbatim from design.md "Output schema". The maxItems default is a
# safety ceiling; output_schema() overrides it per call.
_CURATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "items"],
    "properties": {
        "summary": {
            "type": "string",
            "description": (
                "2-3 paragraph executive summary of what needs attention "
                "now. Every claim must cite at least one source item_id "
                "with an inline marker like [bulletin-r1]."
            ),
        },
        "items": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "title", "severity", "rationale", "sources"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "severity": {"enum": ["info", "nudge", "warn", "block"]},
                    "rationale": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "suggested_action": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["kind"],
                        "properties": {
                            "kind": {"enum": ["ask", "open", "run", "dismiss"]},
                            "label": {"type": "string"},
                            "question": {"type": "string"},
                            "choices": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "url": {"type": "string"},
                            "workflow": {"type": "string"},
                            "scope": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


def output_schema(max_items: int = 5) -> dict[str, Any]:
    """Return the curation schema with ``items.maxItems`` set to ``max_items``.

    Args:
        max_items: Maximum number of attention items the briefing may
            contain. Coerced to at least 1.

    Returns:
        A deep copy of :data:`_CURATION_SCHEMA` with the dynamic cap
        applied. A copy is returned so callers can't mutate the
        module-level template.
    """
    schema = copy.deepcopy(_CURATION_SCHEMA)
    schema["properties"]["items"]["maxItems"] = max(1, int(max_items))
    return schema
