"""MCP tool schema definitions for attune-author.

Each tool is a JSON schema describing its inputs. Handlers
in handlers.py implement the actual logic.
"""

from __future__ import annotations

from typing import Any


def get_tools() -> dict[str, dict[str, Any]]:
    """Return all attune-author MCP tool definitions.

    Returns:
        Dict mapping tool name to schema definition.
    """
    return {
        "author_init": {
            "description": (
                "Bootstrap a .help/ directory in the project. "
                "Scans for features and creates features.yaml with "
                "discovered modules. Use when setting up a help "
                "system for the first time."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": "Project root directory (default: cwd).",
                        "default": ".",
                    },
                },
            },
        },
        "author_status": {
            "description": (
                "Report which feature templates are stale by "
                "comparing source file hashes against template "
                "frontmatter. Returns markdown with stale and "
                "current feature lists."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "help_dir": {
                        "type": "string",
                        "description": "Path to .help/ directory.",
                        "default": ".help",
                    },
                    "project_root": {
                        "type": "string",
                        "description": "Project root directory.",
                        "default": ".",
                    },
                },
            },
        },
        "author_generate": {
            "description": (
                "Generate concept, task, and reference templates "
                "for a single feature. Uses Jinja2 meta templates "
                "and optional LLM polish if ANTHROPIC_API_KEY is set."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "feature": {
                        "type": "string",
                        "description": "Feature name from features.yaml.",
                    },
                    "help_dir": {
                        "type": "string",
                        "description": "Path to .help/ directory.",
                        "default": ".help",
                    },
                    "project_root": {
                        "type": "string",
                        "description": "Project root directory.",
                        "default": ".",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Overwrite manual templates.",
                        "default": False,
                    },
                },
                "required": ["feature"],
            },
        },
        "author_maintain": {
            "description": (
                "Detect and regenerate all stale feature templates "
                "in one pass. Useful after large refactors or "
                "before a release. Use dry_run=true to preview "
                "without writing files."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "help_dir": {
                        "type": "string",
                        "description": "Path to .help/ directory.",
                        "default": ".help",
                    },
                    "project_root": {
                        "type": "string",
                        "description": "Project root directory.",
                        "default": ".",
                    },
                    "features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional subset of feature names.",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Report stale features without regenerating.",
                        "default": False,
                    },
                },
            },
        },
        "author_docs": {
            "description": (
                "Generate documentation from a source file using "
                "the 3-stage pipeline (outline -> write -> review). "
                "Requires ANTHROPIC_API_KEY. Use for API references, "
                "guides, or README sections."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Source file path or raw content.",
                    },
                    "doc_type": {
                        "type": "string",
                        "description": "Documentation type (api-reference, guide, readme).",
                        "default": "api-reference",
                    },
                    "audience": {
                        "type": "string",
                        "description": "Target audience.",
                        "default": "developers",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to write the result.",
                    },
                },
                "required": ["target"],
            },
        },
        "author_lookup": {
            "description": (
                "Look up help for a topic by name or tag. Resolves "
                "the query against features.yaml and returns the "
                "concept, task, or reference template content."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Topic to look up (feature name, tag, or substring).",
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["concept", "task", "reference"],
                        "description": "Template depth.",
                        "default": "concept",
                    },
                    "help_dir": {
                        "type": "string",
                        "description": "Path to .help/ directory.",
                        "default": ".help",
                    },
                },
                "required": ["query"],
            },
        },
    }
