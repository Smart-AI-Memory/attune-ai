"""MCP tool, resource, and prompt schema definitions.

Pure data — no runtime logic. Imported by server.py to keep
schema declarations separate from dispatch and handler code.
"""

from __future__ import annotations

from typing import Any


def _path_tool(
    description: str,
    *,
    param_name: str = "path",
    param_desc: str = "Path to directory or file",
    required: bool = False,
    default: str = ".",
) -> dict[str, Any]:
    """Build a tool definition with a single path parameter."""
    schema: dict[str, Any] = {
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": {
                param_name: {
                    "type": "string",
                    "description": param_desc,
                },
            },
        },
    }
    if required:
        schema["input_schema"]["required"] = [param_name]
    else:
        schema["input_schema"]["properties"][param_name]["default"] = default
    return schema


def get_workflow_tools() -> dict[str, dict[str, Any]]:
    """Tool definitions for workflow execution tools."""
    _pt = _path_tool
    return {
        "security_audit": _pt(
            "Run security audit workflow on codebase. Detects vulnerabilities, dangerous patterns, and security issues. Returns findings with severity levels.",
            param_desc="Path to directory or file to audit",
            required=True,
        ),
        "bug_predict": _pt(
            "Run bug prediction workflow. Analyzes code patterns and predicts potential bugs before they occur.",
            param_desc="Path to directory or file to analyze",
            required=True,
        ),
        "discovery_sweep": {
            "description": (
                "Run the discovery-sweep meta-workflow: fans out across all "
                "audit sources (pattern scan, bug-predict, security, deps, "
                "perf, docs, tests), dedups, and triages findings into "
                "queue / questions / rejected buckets. Use for a full "
                "'what should I fix' pass; single-purpose audits have their "
                "own tools (security_audit, bug_predict, deep_review)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory or file to sweep",
                    },
                    "budget_usd": {
                        "type": "number",
                        "description": "Total LLM spend cap (default 10.00)",
                        "default": 10.0,
                    },
                    "no_llm": {
                        "type": "boolean",
                        "description": "Fast pattern-only sweep (skip LLM sources)",
                        "default": False,
                    },
                },
                "required": ["path"],
            },
        },
        "code_review": _pt(
            "Run code review workflow. Provides comprehensive code quality analysis with suggestions for improvement.",
            param_desc="Path to directory or file to review",
            required=True,
        ),
        "test_generation": {
            "description": "Generate tests for code. Can batch generate tests for multiple modules in parallel.",
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
        "performance_audit": _pt(
            "Run performance audit workflow. Identifies bottlenecks, memory leaks, and optimization opportunities.",
            param_desc="Path to directory or file to audit",
            required=True,
        ),
        "release_notes": _pt(
            "Run the release-notes advisory workflow. Drafts a changelog from git history and gives a go/no-go recommendation. Advisory only — not a gate; the deterministic 4-agent gate is CLI-only (attune workflow run release-gate).",
            param_desc="Path to project root",
        ),
        "doc_audit": _pt(
            "Audit existing documentation for staleness, broken links, and drift from source code.",
            param_desc="Project root path",
        ),
        "doc_gen": {
            "description": "Generate new documentation from source code. Produces API references, guides, or READMEs.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "source_path": {
                        "type": "string",
                        "description": "Path to source file to document",
                    },
                    "doc_type": {
                        "type": "string",
                        "description": "Type of documentation (api_reference, guide, readme)",
                        "default": "api_reference",
                    },
                    "audience": {
                        "type": "string",
                        "description": "Target audience (developers, users, contributors)",
                        "default": "developers",
                    },
                },
                "required": ["source_path"],
            },
        },
        "doc_orchestrator": _pt(
            "End-to-end documentation maintenance: scout gaps, prioritize, generate, and update docs.",
            param_desc="Project root path",
        ),
        "test_audit": _pt(
            "Deep test coverage audit with prioritized test generation. Runs audit, plan, execute, and verify stages.",
            param_desc="Source directory to audit",
            default="src/",
        ),
        "test_gen_parallel": {
            "description": "Batch-generate tests for 10-50 modules in parallel using multi-tier LLM orchestration.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "top": {
                        "type": "integer",
                        "description": "Number of low-coverage modules to process",
                        "default": 200,
                    },
                    "batch_size": {
                        "type": "integer",
                        "description": "Modules to process concurrently per batch",
                        "default": 10,
                    },
                },
            },
        },
        "refactor_plan": _pt(
            "Scan for tech debt, analyze trends, and generate a prioritized refactoring plan.",
            param_desc="Directory to scan for refactoring opportunities",
        ),
        "dependency_check": _pt(
            "Inventory dependencies, assess vulnerabilities, and report risk with recommendations.",
            param_desc="Project root to check dependencies",
        ),
        "simplify_code": _pt(
            "Find complex code hotspots and suggest simplifications to reduce cognitive load.",
            param_desc="Directory to scan for complexity",
        ),
        "deep_review": _pt(
            "Multi-pass deep code review: security, quality, and test gap analysis with prioritized findings.",
            param_desc="Path to directory or file to review",
            required=True,
        ),
        "secure_release": _pt(
            "Full secure release pipeline: security audit, code review, and go/no-go decision.",
            param_desc="Project root path",
        ),
        "health_check": _pt(
            "Orchestrated project health check with score, grade, and recommendations across multiple categories.",
            param_name="project_root",
            param_desc="Project root to check",
        ),
        "research_synthesis": {
            "description": "Synthesize insights from local source documents at a path. A 3-agent pipeline summarizes, analyzes patterns across, and produces a unified answer from the documents found at the given directory or file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory or file of source documents to analyze",
                        "default": ".",
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["quick", "standard", "deep"],
                        "description": "Synthesis depth / agent budget (default: standard)",
                        "default": "standard",
                    },
                },
            },
        },
        "analyze_batch": {
            "description": "Submit tasks to the Anthropic Batch API for 50% cost savings. Processes asynchronously (up to 24 hours). Best for non-urgent bulk analysis.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "requests": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "task_id": {
                                    "type": "string",
                                    "description": "Unique task identifier",
                                },
                                "task_type": {
                                    "type": "string",
                                    "description": "Task type (e.g., analyze_logs, generate_report)",
                                },
                                "input_data": {
                                    "type": "object",
                                    "description": "Task input data",
                                },
                                "model_tier": {
                                    "type": "string",
                                    "enum": ["cheap", "capable", "premium"],
                                    "description": "Model tier (default: capable)",
                                },
                            },
                            "required": ["task_id", "task_type", "input_data"],
                        },
                        "description": "List of tasks to process in batch",
                    },
                },
                "required": ["requests"],
            },
        },
        "analyze_image": {
            "description": "Analyze an image (screenshot, diagram, UI mockup) using Claude's vision capabilities. Supports PNG, JPEG, GIF, and WebP.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file to analyze",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Analysis prompt (default: describe what you see, focusing on errors or notable elements)",
                    },
                },
                "required": ["image_path"],
            },
        },
        "rag_knowledge_query": {
            "description": (
                "Query the RAG knowledge corpus (attune-help by default) for "
                "a given question. Returns ranked hits plus an augmented "
                "prompt string ready to feed to any LLM. Does NOT call an "
                "LLM itself — use the rag-code-gen workflow for end-to-end "
                "generation."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or request to ground against the corpus",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Max hits to return (1-10)",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        },
    }


def get_utility_tools() -> dict[str, dict[str, Any]]:
    """Tool definitions for auth, telemetry, and session management."""
    return {
        "auth_status": {
            "description": "Get authentication strategy status. Shows current configuration, subscription tier, and default mode.",
            "input_schema": {"type": "object", "properties": {}},
        },
        "auth_recommend": {
            "description": "Get authentication recommendation for a file. Analyzes LOC and suggests optimal auth mode.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to analyze"},
                },
                "required": ["file_path"],
            },
        },
        "telemetry_stats": {
            "description": "Get telemetry statistics. Shows cost savings, cache hit rates, and workflow performance.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze",
                        "default": 30,
                    },
                },
            },
        },
        "attune_get_level": {
            "description": (
                "Get current interaction level (1-5). "
                "Level 1=Reactive, 2=Guided, 3=Proactive, 4=Anticipatory, 5=Systems."
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
        "attune_set_level": {
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
            "description": "Get session context value.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Context key to retrieve"},
                },
                "required": ["key"],
            },
        },
        "context_set": {
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
        "list_capabilities": {
            "description": (
                "Enumerate everything attune offers, read live from the "
                "registries: every workflow (list_workflows), wizard "
                "(list_wizards), and registered MCP tool. Returns grouped "
                "name+description lists "
                "so a catalog never drifts from the code. Use to answer 'what "
                "can attune do?' / 'list all capabilities'. For routing to one "
                "workflow, use the attune-hub skill instead."
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
    }


def get_elicitation_tools() -> dict[str, dict[str, Any]]:
    """Tool definitions for the declarative-form ↔ AskUserQuestion bridge.

    Live wiring of ``attune.elicitation`` (the salvaged, surface-agnostic
    ``FormSchema`` model). ``render_form`` validates a declarative form
    and returns batched question payloads; ``collect_response`` validates
    the answers. The agent calls the real ``AskUserQuestion`` tool in
    between — the surface mapping rules live in the driving skill (D6).
    """
    field_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Stable key for the answer"},
            "text": {"type": "string", "description": "Question text shown to the user"},
            "type": {
                "type": "string",
                "enum": ["text_input", "single_select", "multi_select", "boolean"],
                "description": "Control type; multi_select is the headline v1 control",
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Choices for (multi_)select fields",
            },
            "default": {"type": "string", "description": "Default value if unanswered"},
            "help_text": {"type": "string", "description": "Supplemental help"},
            "required": {"type": "boolean", "description": "Defaults to true"},
        },
        "required": ["id", "text", "type"],
    }
    form_schema = {
        "type": "object",
        "description": "Declarative form artifact (data, not code — D3).",
        "properties": {
            "title": {"type": "string", "description": "Form title"},
            "description": {"type": "string", "description": "Optional form description"},
            "fields": {
                "type": "array",
                "items": field_schema,
                "description": "The form's fields (alias: 'questions')",
            },
        },
        "required": ["title", "fields"],
    }
    # The v2 rich surfaces (elicitation_ask, render_widget) render all 7
    # controls, so their field schema exposes the full type enum + the
    # v2.1 numeric/length bounds. v1 (render_form/collect_response) stays on
    # the 4-type schema above — AskUserQuestion has no native number/date,
    # so it would only degrade them to free text (D10 enum-honesty fix).
    rich_field_schema = {
        "type": "object",
        "properties": {
            **field_schema["properties"],
            "type": {
                "type": "string",
                "enum": [
                    "text_input",
                    "textarea",
                    "single_select",
                    "multi_select",
                    "boolean",
                    "number",
                    "date",
                    "decision",
                ],
                "description": (
                    "Control type. v1: text_input/single_select/multi_select/"
                    "boolean. v2.1 rich: textarea, number (min/max), date "
                    "(YYYY-MM-DD). v3: decision (a recommended single-select "
                    "with rationale + per-option tradeoffs, widget surface)."
                ),
            },
            "minimum": {"type": "number", "description": "Lower bound for number"},
            "maximum": {"type": "number", "description": "Upper bound for number"},
            "max_length": {
                "type": "integer",
                "description": "Max length for text_input/textarea",
            },
            "rationale": {
                "type": "string",
                "description": "decision: the 'why this recommendation' callout",
            },
            "recommended": {
                "type": "string",
                "description": "decision: option to badge recommended (must be in options)",
            },
            "option_notes": {
                "type": "object",
                "description": "decision: {option: one-line tradeoff} shown under each card",
            },
        },
        "required": ["id", "text", "type"],
    }
    rich_form_schema = {
        "type": "object",
        "description": "Declarative form artifact (data, not code — D3).",
        "properties": {
            **form_schema["properties"],
            "fields": {
                "type": "array",
                "items": rich_field_schema,
                "description": "The form's fields (alias: 'questions')",
            },
        },
        "required": ["title", "fields"],
    }
    return {
        "elicitation_render_form": {
            "description": (
                "Validate a declarative form and return batched question "
                "payloads (<=4 per batch) ready for the AskUserQuestion tool. "
                "Use to turn N sequential button-turns into one multi-question "
                "form for Socratic discovery. Returns {success, batches} or "
                "{success: false, problems} so you re-fix the definition. "
                "Map each payload to AskUserQuestion per the driving skill: "
                "type multi_select -> multiSelect true; recommendation-first; "
                "free text via the built-in 'Other' option."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"form": form_schema},
                "required": ["form"],
            },
        },
        "elicitation_collect_response": {
            "description": (
                "Validate the user's answers against a declarative form and "
                "return a normalized {field_id: value} response. Enforces "
                "required fields and option membership (R4 — never silently "
                "accept malformed input); returns {success: false, problems} "
                "listing exactly which fields to re-ask."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    # rich_form_schema (7 types): collect_response is the
                    # shared validator for BOTH the v1 AskUserQuestion path
                    # (4-type forms) AND the widget round-trip, which posts
                    # back number/date/textarea answers — so its input enum
                    # must accept the rich controls or the round-trip breaks
                    # at the validation step (the underlying
                    # collect_form_response already validates all 7).
                    "form": rich_form_schema,
                    "answers": {
                        "type": "object",
                        "description": "{field_id: value} the user selected/typed",
                    },
                },
                "required": ["form", "answers"],
            },
        },
        "elicitation_ask": {
            "description": (
                "Render a declarative form as a NATIVE MCP elicitation "
                "dialog and return the user's validated answers in one call "
                "(the v2 rich surface — supports number/date/textarea + "
                "multi-select with a structured return). Builds the "
                "requestedSchema, sends elicitation/create, and on accept "
                "validates the response via collect_form_response. Returns "
                "{success, action, responses} or {success: false, problems}. "
                "If the client can't elicit, returns {success: false, "
                "action: 'unsupported'} — fall back to elicitation_render_form "
                "(AskUserQuestion)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "form": rich_form_schema,
                    "message": {
                        "type": "string",
                        "description": "Optional prompt shown above the form",
                    },
                },
                "required": ["form"],
            },
        },
        "elicitation_render_widget": {
            "description": (
                "Render a declarative form as an inline HTML form for "
                "show_widget (the v2 rich surface for clients that render "
                "widgets, e.g. Cowork/claude.ai). Returns {success, html, "
                "title, field_ids} — pass 'html' straight to "
                "mcp__visualize__show_widget. The form renders ALL 7 controls "
                "richly (number spinner, date picker, multi-line textarea, "
                "multi-select checkboxes) and posts answers back via "
                "sendPrompt as a sentinel-marked JSON block "
                "('__elicitation_response__'); parse that block and validate "
                "it with elicitation_collect_response (R4). Returns {success: "
                "false, problems} on a malformed form. Use when native MCP "
                "elicitation is unavailable but the client can render widgets."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "form": rich_form_schema,
                    "message": {
                        "type": "string",
                        "description": "Optional prompt shown above the form",
                    },
                },
                "required": ["form"],
            },
        },
    }


def get_help_tools() -> dict[str, dict[str, Any]]:
    """Tool definitions for contextual help and progressive documentation."""
    return {
        "help_lookup": {
            "description": (
                "Look up contextual help for a topic, workflow, or error. "
                "Progressive mode escalates across template types: "
                "concept (what is it?) -> procedural (how to use it) -> "
                "reference (full detail). Repeated calls auto-advance. "
                "Can also return post-workflow tips and file-based warnings."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "Topic slug (e.g. 'security-audit', "
                            "'code-review'), template ID "
                            "(e.g. 'ref-tool-code-review'), "
                            "workflow name, or tag (e.g. 'security')"
                        ),
                    },
                    "mode": {
                        "type": "string",
                        "enum": [
                            "progressive",
                            "preamble",
                            "related",
                            "workflow_help",
                            "precursor",
                            "search_tag",
                        ],
                        "description": (
                            "progressive: type-driven depth (default). "
                            "preamble: one-liner context sentence. "
                            "related: preambles for related features. "
                            "workflow_help: tips after a workflow. "
                            "precursor: warnings for a file. "
                            "search_tag: find templates by tag."
                        ),
                        "default": "progressive",
                    },
                    "file_path": {
                        "type": "string",
                        "description": (
                            "File path for precursor mode (returns "
                            "warnings relevant to the file extension)"
                        ),
                    },
                    "last_workflow": {
                        "type": "string",
                        "description": (
                            "Name of the last workflow the user ran. "
                            "When set, progressive mode starts at the "
                            "procedural level (skipping the concept)."
                        ),
                    },
                    "reset": {
                        "type": "boolean",
                        "description": (
                            "Reset depth to concept level. Use when "
                            "the user says 'start from the beginning'."
                        ),
                        "default": False,
                    },
                },
                "required": ["topic"],
            },
        },
        "help_maintain": {
            "description": (
                "Check for stale help templates and regenerate them. "
                "Detects when source files (CLAUDE.md, SKILL.md, "
                "tool_schemas.py) have changed since last generation, "
                "then regenerates only the stale templates. "
                "If ANTHROPIC_API_KEY is set, runs an LLM polish "
                "pass to improve prose quality."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "description": (
                            "Only report stale templates without "
                            "regenerating. Defaults to false."
                        ),
                        "default": False,
                    },
                    "batch": {
                        "type": "boolean",
                        "description": (
                            "Submit to Anthropic Batch API for "
                            "50% cost savings (async, up to 24h). "
                            "Defaults to false."
                        ),
                        "default": False,
                    },
                },
            },
        },
        "help_init": {
            "description": (
                "Bootstrap a project-local help system. Scans the "
                "project to discover features, returns proposals for "
                "the user to review. After review, pass accepted "
                "proposals back to create .help/features.yaml and "
                "generate initial templates."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["scan", "accept"],
                        "description": (
                            "scan: discover features and return "
                            "proposals. accept: save manifest and "
                            "generate templates from accepted list."
                        ),
                    },
                    "accepted": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "files": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["name", "description", "files"],
                        },
                        "description": (
                            "List of accepted feature proposals " "(only used with action=accept)."
                        ),
                    },
                },
                "required": ["action"],
            },
        },
        "help_status": {
            "description": (
                "Show staleness report for the project-local help "
                "system (.help/features.yaml). Reports which features "
                "have current vs stale templates."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional list of feature names to check. "
                            "If omitted, checks all features."
                        ),
                    },
                },
            },
        },
        "help_update": {
            "description": (
                "Regenerate help templates for specific features or "
                "all stale features in the project-local help system. "
                "If ANTHROPIC_API_KEY is set, runs an LLM polish "
                "pass to improve prose quality."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Feature names to regenerate. If omitted, "
                            "regenerates all stale features."
                        ),
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": (
                            "Only report what would change without "
                            "regenerating. Defaults to false."
                        ),
                        "default": False,
                    },
                },
            },
        },
    }


def get_personal_memory_tools() -> dict[str, dict[str, Any]]:
    """Tool definitions for personal cross-session memory (capture/recall/topics/forget)."""
    return {
        "personal_memory_capture": {
            "description": (
                "Save a decision, pattern, troubleshooting finding, or reference to personal "
                "cross-session memory. Content is polished and stored under ~/.attune/memory/ "
                "(global) or .attune/memory/ (project-local)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic slug (letters, digits, hyphens; max 50 chars)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Raw content to capture and store",
                    },
                    "kind": {
                        "type": "string",
                        "enum": ["decision", "pattern", "troubleshooting", "reference"],
                        "description": "Memory kind (default: decision)",
                        "default": "decision",
                    },
                    "project_local": {
                        "type": "boolean",
                        "description": "Store in project .attune/memory/ instead of global (default: false)",
                        "default": False,
                    },
                },
                "required": ["topic", "content"],
            },
        },
        "personal_memory_recall": {
            "description": "Search personal cross-session memory with a natural language query.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 3)",
                        "default": 3,
                    },
                    "kind_filter": {
                        "type": "string",
                        "enum": ["decision", "pattern", "troubleshooting", "reference"],
                        "description": "Filter results by kind (optional)",
                    },
                },
                "required": ["query"],
            },
        },
        "personal_memory_topics": {
            "description": "List all topics stored in personal cross-session memory.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        "personal_memory_forget": {
            "description": "Delete a topic (or specific kind within a topic) from personal memory.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic slug to delete",
                    },
                    "kind": {
                        "type": "string",
                        "enum": ["decision", "pattern", "troubleshooting", "reference"],
                        "description": "Delete only this kind (omit to delete all kinds for the topic)",
                    },
                },
                "required": ["topic"],
            },
        },
    }


def get_memory_tools() -> dict[str, dict[str, Any]]:
    """Tool definitions for memory store/retrieve/search/forget."""
    return {
        "memory_store": {
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
            "description": "Retrieve data from attune-ai memory by key or pattern ID.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key or pattern_id to retrieve"},
                },
                "required": ["key"],
            },
        },
        "memory_search": {
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
            "description": "Remove data from attune-ai memory.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key or pattern_id to remove"},
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
    }


def get_resources() -> dict[str, dict[str, Any]]:
    """MCP resource definitions."""
    return {
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


def get_prompts() -> dict[str, dict[str, Any]]:
    """MCP prompt definitions."""
    return {
        "security-scan": {
            "name": "security-scan",
            "description": "Run a comprehensive security scan on a directory. Checks for eval/exec usage, path traversal, hardcoded secrets, and broad exception handling.",
            "arguments": [
                {
                    "name": "path",
                    "description": "Directory or file to scan",
                    "required": True,
                },
            ],
        },
        "test-gen": {
            "name": "test-gen",
            "description": "Generate behavioral tests for a Python module. Creates pytest test files with Given/When/Then structure.",
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
            "description": "Generate a cost optimization report. Shows LLM spend by workflow, cache hit rates, and savings from tier routing.",
            "arguments": [
                {
                    "name": "days",
                    "description": "Number of days to analyze (default: 30)",
                    "required": False,
                },
            ],
        },
    }
