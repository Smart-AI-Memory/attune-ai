"""JSON schemas for Agent SDK structured output.

Passed via ``ClaudeAgentOptions.output_format`` so the agent
returns structured JSON in ``ResultMessage.structured_output``
instead of free-form markdown.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

WORKFLOW_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
            "findings": {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line": {"type": "integer"},
                            "severity": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["description"],
                    },
                },
            },
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "priority": {"type": "string"},
                    },
                    "required": ["description"],
                },
            },
        },
        "required": ["summary", "findings", "suggestions"],
    },
}
