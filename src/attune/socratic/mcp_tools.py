"""MCP Tool definitions for the Socratic Agent Generation System.

Defines the tool schemas exposed by the Socratic MCP server
for use with Claude Desktop/Code.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

# MCP Protocol Version
MCP_VERSION = "2024-11-05"

# Tool definitions for the Socratic system
SOCRATIC_TOOLS = [
    {
        "name": "socratic_start_session",
        "description": "Start a new Socratic workflow builder session. Returns a session ID and initial state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Optional initial goal. If not provided, session starts in AWAITING_GOAL state.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "socratic_set_goal",
        "description": "Set or update the goal for a session. Triggers goal analysis and domain detection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "The session ID to update"},
                "goal": {"type": "string", "description": "The user's goal in free-form text"},
            },
            "required": ["session_id", "goal"],
        },
    },
    {
        "name": "socratic_get_questions",
        "description": "Get the next set of clarifying questions for a session.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string", "description": "The session ID"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "socratic_submit_answers",
        "description": "Submit answers to clarifying questions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "The session ID"},
                "answers": {
                    "type": "object",
                    "description": "Dictionary of field_id -> answer value",
                },
            },
            "required": ["session_id", "answers"],
        },
    },
    {
        "name": "socratic_generate_workflow",
        "description": "Generate the workflow once all questions are answered. Returns agent blueprints and success criteria.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string", "description": "The session ID"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "socratic_list_sessions",
        "description": "List all saved Socratic sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["all", "active", "completed"],
                    "description": "Filter sessions by status",
                }
            },
            "required": [],
        },
    },
    {
        "name": "socratic_get_session",
        "description": "Get details of a specific session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID to retrieve",
                }
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "socratic_list_blueprints",
        "description": "List all saved workflow blueprints.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain_filter": {
                    "type": "string",
                    "description": "Optional domain to filter by (e.g., 'code_review', 'security')",
                }
            },
            "required": [],
        },
    },
    {
        "name": "socratic_analyze_goal",
        "description": "Analyze a goal using LLM to detect domains, requirements, and ambiguities without starting a full session.",
        "inputSchema": {
            "type": "object",
            "properties": {"goal": {"type": "string", "description": "The goal to analyze"}},
            "required": ["goal"],
        },
    },
    {
        "name": "socratic_recommend_agents",
        "description": "Get agent recommendations based on requirements and historical success data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of domains (e.g., ['code_review', 'security'])",
                },
                "languages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Programming languages involved",
                },
                "quality_focus": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Quality focus areas (e.g., ['security', 'performance'])",
                },
            },
            "required": ["domains"],
        },
    },
]
