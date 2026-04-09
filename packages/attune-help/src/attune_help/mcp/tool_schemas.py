"""MCP tool schema definitions for attune-help.

Each tool is a JSON schema describing its inputs. Handlers
in handlers.py implement the actual logic.

All tools use the `lookup_*` prefix to avoid colliding with
attune-ai's `help_*` tools when both plugins are installed.
"""

from __future__ import annotations

from typing import Any


def get_tools() -> dict[str, dict[str, Any]]:
    """Return all attune-help MCP tool definitions.

    Returns:
        Dict mapping tool name to schema definition.
    """
    return {
        "lookup_topic": {
            "description": (
                "Progressive depth lookup for a help topic. "
                "First call returns the concept view, repeat "
                "calls escalate to task then reference. Reads "
                "templates from the bundled set or an optional "
                "user-provided template_dir."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": ("Topic slug or template ID " "(e.g. 'progressive-depth')."),
                    },
                    "template_dir": {
                        "type": "string",
                        "description": (
                            "Optional override directory "
                            "(e.g. '.help/templates'). "
                            "Defaults to bundled templates."
                        ),
                    },
                    "user_id": {
                        "type": "string",
                        "description": (
                            "Session identifier for progression "
                            "tracking. Defaults to 'mcp-session'."
                        ),
                        "default": "mcp-session",
                    },
                    "renderer": {
                        "type": "string",
                        "enum": ["plain", "claude_code", "cli", "marketplace"],
                        "description": ("Output renderer. Defaults to 'plain'."),
                        "default": "plain",
                    },
                },
                "required": ["topic"],
            },
        },
        "lookup_list": {
            "description": (
                "Enumerate available help topics. Reads the "
                "cross_links index for the active template "
                "directory and returns a markdown table grouped "
                "by category. Optional filtering by tag."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "template_dir": {
                        "type": "string",
                        "description": (
                            "Optional override directory. " "Defaults to bundled templates."
                        ),
                    },
                    "tag": {
                        "type": "string",
                        "description": (
                            "Optional tag to filter by " "(e.g. 'python', 'security')."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": ("Maximum number of topics to return. " "Defaults to 100."),
                        "default": 100,
                    },
                },
            },
        },
        "lookup_warn": {
            "description": (
                "Get file-context warnings for a file path. "
                "Maps the file extension and name to relevant "
                "tags, then returns the top N matching warning "
                "and task templates."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": (
                            "File to compute warnings for " "(does not need to exist on disk)."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum warnings to return.",
                        "default": 3,
                    },
                    "template_dir": {
                        "type": "string",
                        "description": (
                            "Optional override directory. " "Defaults to bundled templates."
                        ),
                    },
                },
                "required": ["file_path"],
            },
        },
        "lookup_preamble": {
            "description": (
                "Get the one-line 'Use X when...' preamble for "
                "a feature. Useful as a context tooltip wherever "
                "a feature name appears."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "feature_name": {
                        "type": "string",
                        "description": ("Feature slug (e.g. 'security')."),
                    },
                    "template_dir": {
                        "type": "string",
                        "description": (
                            "Optional override directory. " "Defaults to bundled templates."
                        ),
                    },
                },
                "required": ["feature_name"],
            },
        },
        "lookup_reset": {
            "description": (
                "Clear progression state for a topic so the next "
                "lookup_topic call starts at the concept view "
                "again. With no topic, clears the entire session."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "Topic to reset. If absent, the " "entire session is reset."
                        ),
                    },
                    "user_id": {
                        "type": "string",
                        "description": ("Session identifier. Defaults to " "'mcp-session'."),
                        "default": "mcp-session",
                    },
                },
            },
        },
        "lookup_status": {
            "description": (
                "Return the current progression state for a session "
                "without advancing it. Useful for answering 'where "
                "am I?' without triggering a depth escalation. "
                "Read-only — never mutates session state."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": (
                            "Session identifier to inspect. " "Defaults to 'mcp-session'."
                        ),
                        "default": "mcp-session",
                    },
                },
            },
        },
    }
