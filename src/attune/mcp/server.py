"""Attune AI MCP Server Implementation.

Exposes Empathy workflows as MCP tools for Claude Code integration.
Uses the official MCP Python SDK for protocol compliance.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)

from attune.mcp.memory_handlers import MemoryHandlersMixin
from attune.mcp.rate_limiter import RateLimiter
from attune.mcp.tool_schemas import (
    get_memory_tools,
    get_prompts,
    get_resources,
    get_utility_tools,
    get_workflow_tools,
)
from attune.mcp.workflow_handlers import WorkflowHandlersMixin

logger = logging.getLogger(__name__)

ATTUNE_LEVEL_NAMES: dict[int, str] = {
    1: "Reactive",
    2: "Guided",
    3: "Proactive",
    4: "Anticipatory",
    5: "Systems",
}

_VOICE_SKIP_TOOLS: frozenset[str] = frozenset(
    {
        "memory_store",
        "memory_retrieve",
        "memory_search",
        "memory_forget",
        "attune_get_level",
        "attune_set_level",
        "context_get",
        "context_set",
        "auth_status",
        "auth_recommend",
        "telemetry_stats",
    }
)

ATTUNE_LEVEL_DESCRIPTIONS: dict[int, str] = {
    1: "Responds to explicit requests only",
    2: "Asks clarifying questions before acting",
    3: "Suggests next steps and improvements",
    4: "Predicts needs based on context and history",
    5: "Considers systemic impacts and cross-cutting concerns",
}


def _get_default_user_id() -> str:
    """Return the OS login name, falling back to 'mcp-session'."""
    try:
        return os.getlogin()
    except OSError:
        return "mcp-session"


class EmpathyMCPServer(MemoryHandlersMixin, WorkflowHandlersMixin):
    """MCP server for Attune AI workflows.

    Exposes workflows and telemetry as MCP tools
    that can be invoked from Claude Code.
    """

    def __init__(
        self,
        workspace_root: str | None = None,
        user_id: str | None = None,
    ):
        """Initialize the MCP server.

        Args:
            workspace_root: Root directory for workspace path
                containment. Defaults to current working directory.
            user_id: Identity for memory operations. Defaults
                to the OS login name or "mcp-session".

        """
        self._workspace_root = workspace_root or os.getcwd()
        self._user_id = user_id or _get_default_user_id()
        self.tools = self._register_tools()
        self.resources = self._register_resources()
        self.prompts = self._register_prompts()
        self._memory = None
        self._attune_level = 3  # Default: Level3Proactive
        self._context: dict[str, str] = {}
        self._plugin_handlers: dict[str, Any] = {}
        self._rate_limiter = RateLimiter(max_calls=60, window_seconds=60.0)
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
    def _register_tools() -> dict[str, dict[str, Any]]:
        """Register available MCP tools.

        Returns:
            Dictionary of tool definitions

        """
        tools: dict[str, dict[str, Any]] = {}
        tools.update(get_workflow_tools())
        tools.update(get_memory_tools())
        tools.update(get_utility_tools())
        return tools

    @staticmethod
    def _register_resources() -> dict[str, dict[str, Any]]:
        """Register available MCP resources.

        Returns:
            Dictionary of resource definitions

        """
        return get_resources()

    @staticmethod
    def _register_prompts() -> dict[str, dict[str, Any]]:
        """Register available MCP prompts.

        Returns:
            Dictionary of prompt definitions

        """
        return get_prompts()

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
            "deep_review": self._run_deep_review,
            "secure_release": self._run_secure_release,
            "health_check": self._run_health_check,
            "research_synthesis": self._run_research_synthesis,
            "analyze_batch": self._run_analyze_batch,
            "analyze_image": self._run_analyze_image,
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

    async def _dispatch_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call to the appropriate handler.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Raw tool execution result (before voice layer)

        """
        if not self._rate_limiter.check(tool_name):
            return {
                "error": f"Rate limit exceeded for '{tool_name}'. " "Try again shortly.",
            }

        try:
            handler = self._tool_handlers.get(tool_name)
            if handler:
                return await handler(arguments)
            if tool_name in self._plugin_handlers:
                return await self._plugin_handlers[tool_name](self, arguments)
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        except Exception as e:  # noqa: BLE001
            logger.exception("Tool execution failed: %s", tool_name)
            return {"success": False, "error": f"Tool execution failed: {type(e).__name__}"}

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call with unified voice layer.

        Delegates to _dispatch_tool for handler routing, then
        wraps workflow-type results through the voice layer for
        consistent next-step suggestions and summaries.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result with voice fields

        """
        result = await self._dispatch_tool(tool_name, arguments)

        # Apply voice layer to workflow-type responses
        # (skip memory, auth, telemetry, empathy tools — they're utility)
        if tool_name not in _VOICE_SKIP_TOOLS and isinstance(result, dict):
            try:
                from attune.voice.formatter import format_mcp_response

                # Map tool_name to workflow name (underscores to hyphens)
                wf_name = tool_name.replace("_", "-")
                result = format_mcp_response(wf_name, result)
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Voice layer is optional — never break MCP
                logger.debug("Voice layer failed for %s", tool_name)

        return result

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
        from attune.security.path_validation import _validate_file_path
        from attune.workflows.test_gen import TestGenerationWorkflow

        validated_path = str(_validate_file_path(args["module"], allowed_dir=self._workspace_root))
        workflow = TestGenerationWorkflow()
        result = await workflow.execute(module_path=validated_path)

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


# -- MCP SDK wiring ------------------------------------------------
# Uses the official MCP Python SDK (mcp.server.Server) for protocol
# compliance. The EmpathyMCPServer class above holds all state and
# handlers; the SDK layer below delegates to it.

_mcp_server = Server("attune-ai")
_app: EmpathyMCPServer | None = None


def _get_app() -> EmpathyMCPServer:
    """Lazily create the application server singleton."""
    global _app  # noqa: PLW0603
    if _app is None:
        _app = EmpathyMCPServer()
    return _app


@_mcp_server.list_tools()
async def _handle_list_tools() -> list[Tool]:
    app = _get_app()
    return [
        Tool(
            name=name,
            description=defn.get("description", ""),
            inputSchema=defn.get(
                "input_schema",
                {"type": "object", "properties": {}},
            ),
        )
        for name, defn in app.tools.items()
    ]


@_mcp_server.call_tool()
async def _handle_call_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
) -> list[TextContent]:
    app = _get_app()
    result = await app.call_tool(name, arguments or {})
    return [
        TextContent(
            type="text",
            text=json.dumps(result, indent=2),
        ),
    ]


@_mcp_server.list_resources()
async def _handle_list_resources() -> list[Resource]:
    app = _get_app()
    return [
        Resource(
            uri=defn["uri"],
            name=defn["name"],
            description=defn.get("description"),
            mimeType=defn.get("mime_type"),
        )
        for defn in app.resources.values()
    ]


@_mcp_server.list_prompts()
async def _handle_list_prompts() -> list[Prompt]:
    app = _get_app()
    return [
        Prompt(
            name=defn["name"],
            description=defn.get("description"),
            arguments=[
                PromptArgument(
                    name=arg["name"],
                    description=arg.get("description"),
                    required=arg.get("required", False),
                )
                for arg in defn.get("arguments", [])
            ],
        )
        for defn in app.prompts.values()
    ]


@_mcp_server.get_prompt()
async def _handle_get_prompt(
    name: str,
    arguments: dict[str, str] | None = None,
) -> GetPromptResult:
    app = _get_app()
    messages = app.get_prompt_messages(name, arguments or {})
    return GetPromptResult(
        messages=[
            PromptMessage(
                role=m["role"],
                content=TextContent(
                    type="text",
                    text=m["content"]["text"],
                ),
            )
            for m in messages
        ],
    )


# -- Public helpers -------------------------------------------------


def create_server() -> EmpathyMCPServer:
    """Create and return an Empathy MCP server instance.

    Returns:
        Configured MCP server

    """
    return EmpathyMCPServer()


async def _run_stdio() -> None:
    """Run the MCP server over stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await _mcp_server.run(
            read_stream,
            write_stream,
            _mcp_server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for MCP server."""
    import tempfile

    log_dir = Path(tempfile.gettempdir()) / "attune"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(str(log_dir / "attune-mcp.log")),
        ],
    )

    try:
        asyncio.run(_run_stdio())
    except KeyboardInterrupt:
        logger.info("Attune MCP Server stopped")


if __name__ == "__main__":
    main()
