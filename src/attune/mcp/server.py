"""Attune AI MCP Server Implementation.

Exposes Empathy workflows as MCP tools for Claude Code integration.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from attune.mcp.memory_handlers import MemoryHandlersMixin
from attune.mcp.workflow_handlers import WorkflowHandlersMixin

# MCP server will be implemented using stdio transport
logger = logging.getLogger(__name__)

ATTUNE_LEVEL_NAMES: dict[int, str] = {
    1: "Reactive",
    2: "Guided",
    3: "Proactive",
    4: "Anticipatory",
    5: "Systems",
}

ATTUNE_LEVEL_DESCRIPTIONS: dict[int, str] = {
    1: "Responds to explicit requests only",
    2: "Asks clarifying questions before acting",
    3: "Suggests next steps and improvements",
    4: "Predicts needs based on context and history",
    5: "Considers systemic impacts and cross-cutting concerns",
}


class EmpathyMCPServer(MemoryHandlersMixin, WorkflowHandlersMixin):
    """MCP server for Attune AI workflows.

    Exposes workflows and telemetry as MCP tools
    that can be invoked from Claude Code.
    """

    def __init__(self, workspace_root: str | None = None):
        """Initialize the MCP server.

        Args:
            workspace_root: Root directory for workspace path
                containment. Defaults to current working directory.

        """
        self._workspace_root = workspace_root or os.getcwd()
        self.tools = self._register_tools()
        self.resources = self._register_resources()
        self.prompts = self._register_prompts()
        self._memory = None
        self._attune_level = 3  # Default: Level3Proactive
        self._context: dict[str, str] = {}
        self._plugin_handlers: dict[str, Any] = {}
        self._tool_handlers = self._build_dispatch_table()

        # Check for updates in background to avoid blocking init
        try:
            import threading

            from .version_check import check_for_updates

            threading.Thread(target=check_for_updates, daemon=True).start()
        except Exception:  # noqa: BLE001
            pass  # INTENTIONAL: Version check is best-effort

        # Register MCP tools from plugins
        self._register_plugin_tools()

    def _register_plugin_tools(self) -> None:
        """Discover and register MCP tools from plugins.

        Iterates over installed plugins and calls
        ``register_mcp_tools()`` on each, allowing plugins
        to add tool definitions and handler functions.
        """
        try:
            from attune.plugins.registry import get_global_registry

            registry = get_global_registry()
            for name in registry.list_plugins():
                plugin = registry.get_plugin(name)
                if plugin and hasattr(plugin, "register_mcp_tools"):
                    try:
                        plugin.register_mcp_tools(self)
                    except Exception as e:  # noqa: BLE001
                        # INTENTIONAL: Plugin MCP registration is best-effort
                        logger.warning(
                            "Plugin '%s' MCP registration failed: %s",
                            name,
                            e,
                        )
        except ImportError:
            pass  # Plugin registry not available
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Plugin discovery is best-effort
            logger.debug("Plugin tool registration skipped: %s", e)

    @staticmethod
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

    def _register_workflow_tools(self) -> dict[str, dict[str, Any]]:
        """Register workflow-related MCP tools.

        Returns:
            Tool definitions for workflow execution tools

        """
        _pt = self._path_tool
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
            "release_prep": _pt(
                "Run release preparation workflow. Checks health, security, changelog, and provides release recommendation.",
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
                "description": "Synthesize insights from multiple documents. Summarizes, analyzes patterns, and produces a unified answer.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of document texts to synthesize (minimum 2)",
                        },
                        "question": {
                            "type": "string",
                            "description": "Research question to answer",
                        },
                    },
                    "required": ["sources", "question"],
                },
            },
        }

    def _register_utility_tools(self) -> dict[str, dict[str, Any]]:
        """Register auth, telemetry, and session management tools.

        Returns:
            Tool definitions for utility tools

        """
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
        }

    def _register_memory_tools(self) -> dict[str, dict[str, Any]]:
        """Register memory operation tools.

        Returns:
            Tool definitions for memory store/retrieve/search/forget

        """
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

    def _register_tools(self) -> dict[str, dict[str, Any]]:
        """Register available MCP tools.

        Returns:
            Dictionary of tool definitions

        """
        tools: dict[str, dict[str, Any]] = {}
        tools.update(self._register_workflow_tools())
        tools.update(self._register_memory_tools())
        tools.update(self._register_utility_tools())
        return tools

    def _register_resources(self) -> dict[str, dict[str, Any]]:
        """Register available MCP resources.

        Returns:
            Dictionary of resource definitions

        """
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

    def _register_prompts(self) -> dict[str, dict[str, Any]]:
        """Register available MCP prompts.

        Prompts are pre-built templates that appear as auto-discovered
        commands in Claude Code, providing guided workflows.

        Returns:
            Dictionary of prompt definitions

        """
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

    def get_prompt_list(self) -> list[dict[str, Any]]:
        """Get list of available prompts.

        Returns:
            List of prompt definitions

        """
        return list(self.prompts.values())

    def get_prompt_messages(
        self,
        prompt_name: str,
        arguments: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Get messages for a specific prompt.

        Args:
            prompt_name: Name of the prompt to retrieve
            arguments: Prompt arguments provided by the caller

        Returns:
            List of messages for the prompt

        Raises:
            ValueError: If prompt_name is not found

        """
        if prompt_name not in self.prompts:
            raise ValueError(f"Unknown prompt: {prompt_name}")

        if prompt_name == "security-scan":
            path = arguments.get("path", "src/")
            return [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Run a comprehensive security audit on `{path}`. "
                            "Check for: eval/exec usage (CWE-95), path traversal (CWE-22), "
                            "hardcoded secrets, broad exception handling (BLE001), "
                            "and shell injection risks (B602). "
                            "Report findings in a severity-sorted table with file:line, CWE, "
                            "and recommended fix."
                        ),
                    },
                },
            ]
        if prompt_name == "test-gen":
            module = arguments.get("module", "")
            batch = arguments.get("batch", "false").lower() == "true"
            if batch:
                return [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                "Generate behavioral tests in batch mode for all untested modules. "
                                "Use Given/When/Then structure, pytest fixtures, and target 80%+ coverage. "
                                "Run: `uv run attune workflow run test-gen-behavioral --batch`"
                            ),
                        },
                    },
                ]
            return [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Generate behavioral tests for `{module}`. "
                            "Use Given/When/Then structure, pytest fixtures, and test naming convention "
                            "`test_{{function}}_{{scenario}}_{{expected}}()`. "
                            f"Run: `uv run attune workflow run test-gen-behavioral --path {module}`"
                        ),
                    },
                },
            ]
        if prompt_name == "cost-report":
            days = arguments.get("days", "30")
            return [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Generate a cost optimization report for the last {days} days. "
                            "Show: total LLM spend by workflow, cache hit rates, "
                            "savings from tier routing (cheap vs capable vs premium), "
                            "and recommendations for further optimization. "
                            "Run: `uv run attune telemetry report`"
                        ),
                    },
                },
            ]
        raise ValueError(f"Unknown prompt: {prompt_name}")

    def _build_dispatch_table(self) -> dict[str, Any]:
        """Build tool name -> handler mapping.

        Returns:
            Dict mapping tool names to async handler callables.
            All handlers accept (args: dict) and return dict.

        """
        return {
            "security_audit": self._run_security_audit,
            "bug_predict": self._run_bug_predict,
            "code_review": self._run_code_review,
            "test_generation": self._run_test_generation,
            "performance_audit": self._run_performance_audit,
            "release_prep": self._run_release_prep,
            "doc_audit": self._run_doc_audit,
            "doc_gen": self._run_doc_gen,
            "doc_orchestrator": self._run_doc_orchestrator,
            "test_audit": self._run_test_audit,
            "test_gen_parallel": self._run_test_gen_parallel,
            "refactor_plan": self._run_refactor_plan,
            "dependency_check": self._run_dependency_check,
            "simplify_code": self._run_simplify_code,
            "secure_release": self._run_secure_release,
            "health_check": self._run_health_check,
            "research_synthesis": self._run_research_synthesis,
            "auth_status": lambda _args: self._get_auth_status(),
            "auth_recommend": self._get_auth_recommend,
            "telemetry_stats": self._get_telemetry_stats,
            "memory_store": self._handle_memory_store,
            "memory_retrieve": self._handle_memory_retrieve,
            "memory_search": self._handle_memory_search,
            "memory_forget": self._handle_memory_forget,
            "attune_get_level": lambda _args: self._handle_attune_get_level(),
            "attune_set_level": self._handle_attune_set_level,
            "context_get": self._handle_context_get,
            "context_set": self._handle_context_set,
        }

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result

        """
        try:
            if tool_name == "security_audit":
                return await self._run_security_audit(arguments)
            if tool_name == "bug_predict":
                return await self._run_bug_predict(arguments)
            if tool_name == "code_review":
                return await self._run_code_review(arguments)
            if tool_name == "test_generation":
                return await self._run_test_generation(arguments)
            if tool_name == "performance_audit":
                return await self._run_performance_audit(arguments)
            if tool_name == "release_prep":
                return await self._run_release_prep(arguments)
            if tool_name == "doc_audit":
                return await self._run_doc_audit(arguments)
            if tool_name == "doc_gen":
                return await self._run_doc_gen(arguments)
            if tool_name == "doc_orchestrator":
                return await self._run_doc_orchestrator(arguments)
            if tool_name == "test_audit":
                return await self._run_test_audit(arguments)
            if tool_name == "test_gen_parallel":
                return await self._run_test_gen_parallel(arguments)
            if tool_name == "refactor_plan":
                return await self._run_refactor_plan(arguments)
            if tool_name == "dependency_check":
                return await self._run_dependency_check(arguments)
            if tool_name == "simplify_code":
                return await self._run_simplify_code(arguments)
            if tool_name == "secure_release":
                return await self._run_secure_release(arguments)
            if tool_name == "health_check":
                return await self._run_health_check(arguments)
            if tool_name == "research_synthesis":
                return await self._run_research_synthesis(arguments)
            if tool_name == "auth_status":
                return await self._get_auth_status()
            if tool_name == "auth_recommend":
                return await self._get_auth_recommend(arguments)
            if tool_name == "telemetry_stats":
                return await self._get_telemetry_stats(arguments)
            if tool_name == "memory_store":
                return await self._handle_memory_store(arguments)
            if tool_name == "memory_retrieve":
                return await self._handle_memory_retrieve(arguments)
            if tool_name == "memory_search":
                return await self._handle_memory_search(arguments)
            if tool_name == "memory_forget":
                return await self._handle_memory_forget(arguments)
            if tool_name == "attune_get_level":
                return await self._handle_attune_get_level()
            if tool_name == "attune_set_level":
                return await self._handle_attune_set_level(arguments)
            if tool_name == "context_get":
                return await self._handle_context_get(arguments)
            if tool_name == "context_set":
                return await self._handle_context_set(arguments)
            if tool_name in self._plugin_handlers:
                handler = self._plugin_handlers[tool_name]
                return await handler(self, arguments)
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Tool execution failed: {tool_name}")
            return {"success": False, "error": f"Tool execution failed: {type(e).__name__}"}

    async def _run_security_audit(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run security audit workflow."""
        from attune.security.path_validation import _validate_file_path
        from attune.workflows.security_audit import SecurityAuditWorkflow

        validated_path = str(_validate_file_path(args["path"], allowed_dir=self._workspace_root))
        workflow = SecurityAuditWorkflow()
        result = await workflow.execute(path=validated_path)

        return {
            "success": result.success,
            "score": result.final_output.get("health_score"),
            "findings": result.final_output.get("findings", []),
            "cost": result.cost_report.total_cost,
            "provider": result.provider,
        }

    async def _run_bug_predict(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run bug prediction workflow."""
        from attune.security.path_validation import _validate_file_path

        validated_path = str(_validate_file_path(args["path"], allowed_dir=self._workspace_root))

        from attune.workflows.bug_predict import BugPredictionWorkflow

        workflow = BugPredictionWorkflow()
        result = await workflow.execute(path=validated_path)

        return {
            "success": result.success,
            "predictions": result.final_output.get("predictions", []),
            "cost": result.cost_report.total_cost,
        }

    async def _run_code_review(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run code review workflow."""
        from attune.security.path_validation import _validate_file_path
        from attune.workflows.code_review import CodeReviewWorkflow

        validated_path = str(_validate_file_path(args["path"], allowed_dir=self._workspace_root))
        workflow = CodeReviewWorkflow()
        result = await workflow.execute(target_path=validated_path)

        return {
            "success": result.success,
            "feedback": result.final_output.get("feedback"),
            "score": result.final_output.get("quality_score"),
            "cost": result.cost_report.total_cost,
        }

    async def _run_test_generation(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run test generation workflow."""
        from attune.workflows.test_gen import TestGenerationWorkflow

        workflow = TestGenerationWorkflow()
        result = await workflow.execute(module_path=args["module"])

        return {
            "success": result.success,
            "tests_generated": result.final_output.get("tests_generated", 0),
            "output_path": result.final_output.get("output_path"),
            "cost": result.cost_report.total_cost,
        }

    async def _run_performance_audit(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run performance audit workflow."""
        from attune.security.path_validation import _validate_file_path
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        validated_path = str(_validate_file_path(args["path"], allowed_dir=self._workspace_root))
        workflow = PerformanceAuditWorkflow()
        result = await workflow.execute(path=validated_path)

        return {
            "success": result.success,
            "findings": result.final_output.get("findings", []),
            "score": result.final_output.get("score"),
            "cost": result.cost_report.total_cost,
        }

    async def _run_release_prep(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run release preparation workflow."""
        from attune.security.path_validation import _validate_file_path
        from attune.workflows.release_prep import ReleasePreparationWorkflow

        validated_path = str(
            _validate_file_path(args.get("path", "."), allowed_dir=self._workspace_root)
        )
        workflow = ReleasePreparationWorkflow(skip_approve_if_clean=True)
        result = await workflow.execute(path=validated_path)

        return {
            "success": result.success,
            "approved": result.final_output.get("approved"),
            "health_score": result.final_output.get("health_score"),
            "recommendation": result.final_output.get("recommendation"),
            "cost": result.cost_report.total_cost,
        }

    async def _get_auth_status(self) -> dict[str, Any]:
        """Get authentication strategy status."""
        from attune.models import AuthStrategy

        strategy = AuthStrategy.load()

        return {
            "success": True,
            "subscription_tier": strategy.subscription_tier.value,
            "default_mode": strategy.default_mode.value,
            "setup_completed": strategy.setup_completed,
        }

    async def _get_auth_recommend(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get authentication recommendation."""
        from attune.models import (
            count_lines_of_code,
            get_auth_strategy,
            get_module_size_category,
        )
        from attune.security.path_validation import _validate_file_path

        file_path = _validate_file_path(args["file_path"], allowed_dir=self._workspace_root)
        lines = count_lines_of_code(file_path)
        category = get_module_size_category(lines)

        strategy = get_auth_strategy()
        recommended = strategy.get_recommended_mode(lines)

        return {
            "success": True,
            "file_path": str(file_path),
            "lines_of_code": lines,
            "category": category,
            "recommended_mode": recommended.value,
        }

    async def _get_telemetry_stats(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get telemetry statistics from UsageTracker."""
        try:
            from attune.telemetry.usage_tracker import UsageTracker

            tracker = UsageTracker()
            stats = tracker.get_stats(days=args.get("days", 30))
            return {"success": True, **stats}
        except ImportError as e:
            logger.warning("Telemetry module not available: %s", e)
            return {"success": False, "error": "Telemetry module not installed"}

    async def _handle_attune_get_level(self) -> dict[str, Any]:
        """Get current interaction level."""
        return {
            "success": True,
            "level": self._attune_level,
            "name": ATTUNE_LEVEL_NAMES.get(self._attune_level, "Unknown"),
            "description": ATTUNE_LEVEL_DESCRIPTIONS.get(self._attune_level, ""),
        }

    async def _handle_attune_set_level(self, args: dict[str, Any]) -> dict[str, Any]:
        """Set interaction level for this session.

        Args:
            args: Must contain level (integer 1-5)

        """
        level = args.get("level")
        if not isinstance(level, int) or level < 1 or level > 5:
            return {
                "success": False,
                "error": "Level must be an integer between 1 and 5",
            }

        previous = self._attune_level
        self._attune_level = level

        return {
            "success": True,
            "previous_level": previous,
            "current_level": level,
            "name": ATTUNE_LEVEL_NAMES[level],
        }

    async def _handle_context_get(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get session context value.

        Args:
            args: Must contain key

        """
        key = args["key"]
        value = self._context.get(key)
        return {
            "success": True,
            "key": key,
            "value": value,
            "found": value is not None,
        }

    async def _handle_context_set(self, args: dict[str, Any]) -> dict[str, Any]:
        """Set session context value.

        Args:
            args: Must contain key and value

        """
        key = args["key"]
        value = args["value"]
        self._context[key] = value
        return {
            "success": True,
            "key": key,
            "value": value,
        }

    def get_tool_list(self) -> list[dict[str, Any]]:
        """Get list of available tools.

        Returns:
            List of tool definitions

        """
        return [{"name": name, **defn} for name, defn in self.tools.items()]

    def get_resource_list(self) -> list[dict[str, Any]]:
        """Get list of available resources.

        Returns:
            List of resource definitions

        """
        return list(self.resources.values())


async def handle_request(server: EmpathyMCPServer, request: dict[str, Any]) -> dict[str, Any]:
    """Handle an MCP request.

    Args:
        server: MCP server instance
        request: MCP request

    Returns:
        MCP response

    """
    method = request.get("method")
    params = request.get("params", {})

    if method == "tools/list":
        return {"tools": server.get_tool_list()}
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = await server.call_tool(tool_name, arguments)
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    if method == "resources/list":
        return {"resources": server.get_resource_list()}
    if method == "prompts/list":
        return {"prompts": server.get_prompt_list()}
    if method == "prompts/get":
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            messages = server.get_prompt_messages(prompt_name, arguments)
            return {"messages": messages}
        except ValueError as e:
            return {"error": {"code": -32602, "message": str(e)}}
    else:
        return {"error": {"code": -32601, "message": f"Method not found: {method}"}}


async def main_loop():
    """Main MCP server loop using stdio transport."""
    server = EmpathyMCPServer()
    loop = asyncio.get_running_loop()

    logger.info("Empathy MCP Server started")
    logger.info(f"Registered {len(server.tools)} tools")

    while True:
        try:
            # Read request from stdin (JSON-RPC format)
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            request = json.loads(line)
            response = await handle_request(server, request)

            # Write response to stdout
            print(json.dumps(response), flush=True)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            error_response = {"error": {"code": -32700, "message": "Parse error"}}
            print(json.dumps(error_response), flush=True)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Server loop must not crash
            logger.exception("Error handling request")
            error_response = {"error": {"code": -32603, "message": str(e)}}
            print(json.dumps(error_response), flush=True)


def create_server() -> EmpathyMCPServer:
    """Create and return an Empathy MCP server instance.

    Returns:
        Configured MCP server

    """
    return EmpathyMCPServer()


def main():
    """Entry point for MCP server."""
    import tempfile

    log_dir = Path(tempfile.gettempdir()) / "attune"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(str(log_dir / "attune-mcp.log"))],
    )

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("Empathy MCP Server stopped")


if __name__ == "__main__":
    main()
