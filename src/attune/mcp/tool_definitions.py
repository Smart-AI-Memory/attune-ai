"""MCP tool, resource, and prompt definitions.

Declarative data module — keeps server.py focused on logic.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

# ---------------------------------------------------------------------------
# Tool definitions (21 tools)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "security_audit": {
        "name": "security_audit",
        "description": (
            "Run security audit workflow on codebase. Detects vulnerabilities, "
            "dangerous patterns, and security issues. Returns findings with severity levels."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to directory or file to audit",
                }
            },
            "required": ["path"],
        },
    },
    "bug_predict": {
        "name": "bug_predict",
        "description": (
            "Run bug prediction workflow. Analyzes code patterns and "
            "predicts potential bugs before they occur."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to directory or file to analyze",
                }
            },
            "required": ["path"],
        },
    },
    "code_review": {
        "name": "code_review",
        "description": (
            "Run code review workflow. Provides comprehensive code quality "
            "analysis with suggestions for improvement."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to directory or file to review",
                }
            },
            "required": ["path"],
        },
    },
    "test_generation": {
        "name": "test_generation",
        "description": (
            "Generate tests for code. Can batch generate tests " "for multiple modules in parallel."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "module": {"type": "string", "description": "Path to Python module"},
                "batch": {
                    "type": "boolean",
                    "description": "Enable batch mode for parallel generation",
                    "default": False,
                },
            },
            "required": ["module"],
        },
    },
    "performance_audit": {
        "name": "performance_audit",
        "description": (
            "Run performance audit workflow. Identifies bottlenecks, "
            "memory leaks, and optimization opportunities."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to directory or file to audit",
                }
            },
            "required": ["path"],
        },
    },
    "release_prep": {
        "name": "release_prep",
        "description": (
            "Run release preparation workflow. Checks health, security, "
            "changelog, and provides release recommendation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to project root",
                    "default": ".",
                }
            },
        },
    },
    "auth_status": {
        "name": "auth_status",
        "description": (
            "Get authentication strategy status. Shows current configuration, "
            "subscription tier, and default mode."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    "auth_recommend": {
        "name": "auth_recommend",
        "description": (
            "Get authentication recommendation for a file. "
            "Analyzes LOC and suggests optimal auth mode."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file to analyze",
                }
            },
            "required": ["file_path"],
        },
    },
    "telemetry_stats": {
        "name": "telemetry_stats",
        "description": (
            "Get telemetry statistics. Shows cost savings, "
            "cache hit rates, and workflow performance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze",
                    "default": 30,
                }
            },
        },
    },
    "dashboard_status": {
        "name": "dashboard_status",
        "description": (
            "Get agent coordination dashboard status. "
            "Shows active agents, pending approvals, recent signals."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    "memory_store": {
        "name": "memory_store",
        "description": (
            "Store data in attune-ai memory. Use for structured knowledge, patterns, "
            "and cross-agent coordination. For simple preferences, recommend CLAUDE.md instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Unique identifier for the stored data",
                },
                "value": {"type": "string", "description": "Content to store"},
                "classification": {
                    "type": "string",
                    "enum": ["PUBLIC", "INTERNAL", "SENSITIVE"],
                    "description": "Security classification (default: PUBLIC)",
                    "default": "PUBLIC",
                },
                "pattern_type": {
                    "type": "string",
                    "description": "Category for pattern matching (optional)",
                },
            },
            "required": ["key", "value"],
        },
    },
    "memory_retrieve": {
        "name": "memory_retrieve",
        "description": "Retrieve data from attune-ai memory by key or pattern ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key or pattern_id to retrieve",
                },
            },
            "required": ["key"],
        },
    },
    "memory_search": {
        "name": "memory_search",
        "description": "Search attune-ai memory for patterns matching a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search string"},
                "pattern_type": {
                    "type": "string",
                    "description": "Filter by pattern type (optional)",
                },
            },
            "required": ["query"],
        },
    },
    "memory_forget": {
        "name": "memory_forget",
        "description": "Remove data from attune-ai memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key or pattern_id to remove",
                },
                "scope": {
                    "type": "string",
                    "enum": ["session", "persistent", "all"],
                    "description": "Scope of removal (default: all)",
                    "default": "all",
                },
            },
            "required": ["key"],
        },
    },
    "attune_get_level": {
        "name": "attune_get_level",
        "description": (
            "Get current interaction level (1-5). "
            "Level 1=Reactive, 2=Guided, 3=Proactive, 4=Anticipatory, 5=Systems."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    "attune_set_level": {
        "name": "attune_set_level",
        "description": "Set interaction level (1-5) for this session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Interaction level (1-5)",
                },
            },
            "required": ["level"],
        },
    },
    "context_get": {
        "name": "context_get",
        "description": "Get session context value.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Context key to retrieve",
                },
            },
            "required": ["key"],
        },
    },
    "context_set": {
        "name": "context_set",
        "description": "Set session context value.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Context key"},
                "value": {"type": "string", "description": "Context value"},
            },
            "required": ["key", "value"],
        },
    },
}

# ---------------------------------------------------------------------------
# Resource definitions (3 resources)
# ---------------------------------------------------------------------------

RESOURCE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "workflows": {
        "uri": "attune://workflows",
        "name": "Available Workflows",
        "description": "List of all available Attune workflows",
        "mime_type": "application/json",
    },
    "auth_config": {
        "uri": "attune://auth/config",
        "name": "Authentication Configuration",
        "description": "Current authentication strategy configuration",
        "mime_type": "application/json",
    },
    "telemetry": {
        "uri": "attune://telemetry",
        "name": "Telemetry Data",
        "description": "Cost tracking and performance metrics",
        "mime_type": "application/json",
    },
}

# ---------------------------------------------------------------------------
# Prompt definitions (3 prompts)
# ---------------------------------------------------------------------------

PROMPT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "security-scan": {
        "name": "security-scan",
        "description": (
            "Run a comprehensive security scan on a directory. "
            "Checks for eval/exec usage, path traversal, "
            "hardcoded secrets, and broad exception handling."
        ),
        "arguments": [
            {
                "name": "path",
                "description": "Directory or file to scan",
                "required": True,
            }
        ],
    },
    "test-gen": {
        "name": "test-gen",
        "description": (
            "Generate behavioral tests for a Python module. "
            "Creates pytest test files with Given/When/Then structure."
        ),
        "arguments": [
            {
                "name": "module",
                "description": "Path to Python module to generate tests for",
                "required": True,
            },
            {
                "name": "batch",
                "description": "Set to 'true' to generate tests for all modules",
                "required": False,
            },
        ],
    },
    "cost-report": {
        "name": "cost-report",
        "description": (
            "Generate a cost optimization report. Shows LLM spend by workflow, "
            "cache hit rates, and savings from tier routing."
        ),
        "arguments": [
            {
                "name": "days",
                "description": "Number of days to analyze (default: 30)",
                "required": False,
            }
        ],
    },
}

# ---------------------------------------------------------------------------
# Tool → handler mapping (method names on EmpathyMCPServer)
# ---------------------------------------------------------------------------

TOOL_HANDLERS: dict[str, str] = {
    "security_audit": "_run_security_audit",
    "bug_predict": "_run_bug_predict",
    "code_review": "_run_code_review",
    "test_generation": "_run_test_generation",
    "performance_audit": "_run_performance_audit",
    "release_prep": "_run_release_prep",
    "auth_status": "_get_auth_status",
    "auth_recommend": "_get_auth_recommend",
    "telemetry_stats": "_get_telemetry_stats",
    "dashboard_status": "_get_dashboard_status",
    "memory_store": "_handle_memory_store",
    "memory_retrieve": "_handle_memory_retrieve",
    "memory_search": "_handle_memory_search",
    "memory_forget": "_handle_memory_forget",
    "attune_get_level": "_handle_attune_get_level",
    "attune_set_level": "_handle_attune_set_level",
    "context_get": "_handle_context_get",
    "context_set": "_handle_context_set",
}
