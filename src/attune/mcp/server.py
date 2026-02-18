"""Attune AI MCP Server Implementation.

Exposes Empathy workflows as MCP tools for Claude Code integration.
"""

import asyncio
import json
import logging
import sys
from typing import Any

from .tool_definitions import (
    PROMPT_DEFINITIONS,
    RESOURCE_DEFINITIONS,
    TOOL_DEFINITIONS,
    TOOL_HANDLERS,
)

# MCP server will be implemented using stdio transport
logger = logging.getLogger(__name__)


class EmpathyMCPServer:
    """MCP server for Attune AI workflows.

    Exposes workflows, agent dashboard, and telemetry as MCP tools
    that can be invoked from Claude Code.
    """

    def __init__(self):
        """Initialize the MCP server."""
        self.tools = dict(TOOL_DEFINITIONS)
        self.resources = dict(RESOURCE_DEFINITIONS)
        self.prompts = dict(PROMPT_DEFINITIONS)
        self._memory = None
        self._attune_level = 3  # Default: Level3Proactive
        self._context: dict[str, str] = {}

        # Check for updates (non-blocking, cached per session)
        try:
            from .version_check import check_for_updates

            check_for_updates()
        except Exception:  # noqa: BLE001
            pass  # INTENTIONAL: Version check is best-effort

    def get_prompt_list(self) -> list[dict[str, Any]]:
        """Get list of available prompts.

        Returns:
            List of prompt definitions
        """
        return list(self.prompts.values())

    def get_prompt_messages(
        self, prompt_name: str, arguments: dict[str, str]
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
                }
            ]
        elif prompt_name == "test-gen":
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
                    }
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
                }
            ]
        elif prompt_name == "cost-report":
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
                }
            ]
        else:
            raise ValueError(f"Unknown prompt: {prompt_name}")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        handler_name = TOOL_HANDLERS.get(tool_name)
        if not handler_name:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            handler = getattr(self, handler_name)
            # Handlers with no args (attune_get_level, dashboard_status, auth_status)
            if tool_name in ("attune_get_level", "dashboard_status", "auth_status"):
                return await handler()
            return await handler(arguments)
        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_name}")
            return {"success": False, "error": str(e)}

    async def _run_security_audit(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run security audit workflow."""
        from attune.workflows.security_audit import SecurityAuditWorkflow

        workflow = SecurityAuditWorkflow()
        result = await workflow.execute(path=args["path"])

        return {
            "success": result.success,
            "score": result.final_output.get("health_score"),
            "findings": result.final_output.get("findings", []),
            "cost": result.cost_report.total_cost,
            "provider": result.provider,
        }

    async def _run_bug_predict(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run bug prediction workflow."""
        from attune.workflows.bug_predict import BugPredictWorkflow

        workflow = BugPredictWorkflow()
        result = await workflow.execute(path=args["path"])

        return {
            "success": result.success,
            "predictions": result.final_output.get("predictions", []),
            "cost": result.cost_report.total_cost,
        }

    async def _run_code_review(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run code review workflow."""
        from attune.workflows.code_review import CodeReviewWorkflow

        workflow = CodeReviewWorkflow()
        result = await workflow.execute(target_path=args["path"])

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
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        workflow = PerformanceAuditWorkflow()
        result = await workflow.execute(path=args["path"])

        return {
            "success": result.success,
            "findings": result.final_output.get("findings", []),
            "score": result.final_output.get("score"),
            "cost": result.cost_report.total_cost,
        }

    async def _run_release_prep(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run release preparation workflow."""
        from attune.workflows.release_prep import ReleasePreparationWorkflow

        workflow = ReleasePreparationWorkflow(skip_approve_if_clean=True)
        result = await workflow.execute(path=args.get("path", "."))

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
        from pathlib import Path

        from attune.models import (
            count_lines_of_code,
            get_auth_strategy,
            get_module_size_category,
        )

        file_path = Path(args["file_path"])
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
        """Get telemetry statistics."""
        # Placeholder - would integrate with actual telemetry system
        return {
            "success": True,
            "days": args.get("days", 30),
            "total_cost": 0.0,
            "savings": 0.0,
            "cache_hit_rate": 0.0,
        }

    async def _get_dashboard_status(self) -> dict[str, Any]:
        """Get dashboard status."""
        # Placeholder - would integrate with actual dashboard
        return {"success": True, "active_agents": 0, "pending_approvals": 0, "recent_signals": 0}

    def _get_memory(self) -> Any:
        """Lazily initialize and return UnifiedMemory instance.

        Returns:
            UnifiedMemory instance

        Raises:
            ImportError: If attune memory module is not available
        """
        if self._memory is None:
            from attune.memory import UnifiedMemory

            self._memory = UnifiedMemory(
                user_id="mcp-session",
                environment="development",
            )
        return self._memory

    async def _handle_memory_store(self, args: dict[str, Any]) -> dict[str, Any]:
        """Store data in attune-ai memory.

        Args:
            args: Must contain key and value; optional classification and pattern_type
        """
        try:
            memory = self._get_memory()
            key = args["key"]
            value = args["value"]
            classification = args.get("classification", "PUBLIC")
            pattern_type = args.get("pattern_type")

            # Use short-term stash for simple key-value storage
            memory.stash(
                key,
                {
                    "value": value,
                    "classification": classification,
                    "pattern_type": pattern_type,
                },
            )

            # If pattern_type is specified, also persist as a long-term pattern
            result: dict[str, Any] = {"success": True, "key": key, "classification": classification}
            if pattern_type:
                try:
                    persist_result = memory.persist_pattern(
                        content=value,
                        pattern_type=pattern_type,
                    )
                    result["pattern_id"] = persist_result.get("pattern_id")
                except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Pattern persistence is best-effort
                    logger.warning(f"Pattern persistence failed: {e}")

            return result

        except ImportError as e:
            logger.error(f"Memory module not available: {e}")
            return {
                "success": False,
                "error": "attune-ai memory module not installed. Run: pip install attune-ai",
            }
        except Exception as e:
            logger.exception("memory_store failed")
            return {"success": False, "error": str(e)}

    async def _handle_memory_retrieve(self, args: dict[str, Any]) -> dict[str, Any]:
        """Retrieve data from attune-ai memory.

        Args:
            args: Must contain key (key or pattern_id)
        """
        try:
            memory = self._get_memory()
            key = args["key"]

            # Try short-term first
            data = memory.retrieve(key)
            if data is not None:
                return {"success": True, "key": key, "data": data, "source": "short_term"}

            # Try long-term pattern recall
            try:
                pattern = memory.recall_pattern(key)
                if pattern:
                    return {"success": True, "key": key, "data": pattern, "source": "long_term"}
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Pattern recall may fail for non-pattern keys
                pass

            return {"success": True, "key": key, "data": None, "message": "Key not found"}

        except ImportError as e:
            logger.error(f"Memory module not available: {e}")
            return {
                "success": False,
                "error": "attune-ai memory module not installed. Run: pip install attune-ai",
            }
        except Exception as e:
            logger.exception("memory_retrieve failed")
            return {"success": False, "error": str(e)}

    async def _handle_memory_search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search attune-ai memory for patterns.

        Args:
            args: Must contain query; optional pattern_type filter
        """
        try:
            memory = self._get_memory()
            query = args["query"]
            pattern_type = args.get("pattern_type")

            # Search through available patterns
            results = []
            if hasattr(memory, "search_patterns"):
                results = memory.search_patterns(query, pattern_type=pattern_type)
            elif hasattr(memory, "list_patterns"):
                all_patterns = memory.list_patterns()
                results = [
                    p
                    for p in all_patterns
                    if query.lower() in str(p).lower()
                    and (pattern_type is None or p.get("pattern_type") == pattern_type)
                ]

            return {"success": True, "query": query, "results": results, "count": len(results)}

        except ImportError as e:
            logger.error(f"Memory module not available: {e}")
            return {
                "success": False,
                "error": "attune-ai memory module not installed. Run: pip install attune-ai",
            }
        except Exception as e:
            logger.exception("memory_search failed")
            return {"success": False, "error": str(e)}

    async def _handle_memory_forget(self, args: dict[str, Any]) -> dict[str, Any]:
        """Remove data from attune-ai memory.

        Args:
            args: Must contain key; optional scope (session/persistent/all)
        """
        try:
            memory = self._get_memory()
            key = args["key"]
            scope = args.get("scope", "all")

            removed_from = []

            if scope in ("session", "all"):
                try:
                    memory.stash(key, None)  # Clear short-term
                    removed_from.append("session")
                except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Short-term removal is best-effort
                    logger.debug(f"Short-term removal failed for {key}: {e}")

            if scope in ("persistent", "all"):
                try:
                    if hasattr(memory, "delete_pattern"):
                        memory.delete_pattern(key)
                        removed_from.append("persistent")
                except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Long-term removal is best-effort
                    logger.debug(f"Long-term removal failed for {key}: {e}")

            return {"success": True, "key": key, "removed_from": removed_from}

        except ImportError as e:
            logger.error(f"Memory module not available: {e}")
            return {
                "success": False,
                "error": "attune-ai memory module not installed. Run: pip install attune-ai",
            }
        except Exception as e:
            logger.exception("memory_forget failed")
            return {"success": False, "error": str(e)}

    async def _handle_attune_get_level(self) -> dict[str, Any]:
        """Get current interaction level."""
        level_names = {
            1: "Reactive",
            2: "Guided",
            3: "Proactive",
            4: "Anticipatory",
            5: "Systems",
        }
        return {
            "success": True,
            "level": self._attune_level,
            "name": level_names.get(self._attune_level, "Unknown"),
            "description": {
                1: "Respond when asked. Minimal proactive guidance.",
                2: "Collaborative exploration with clarifying questions.",
                3: "Act before being asked. Suggest improvements.",
                4: "Predict future needs. Prepare for likely next steps.",
                5: "Build structures that help at scale.",
            }.get(self._attune_level, ""),
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

        level_names = {
            1: "Reactive",
            2: "Guided",
            3: "Proactive",
            4: "Anticipatory",
            5: "Systems",
        }

        return {
            "success": True,
            "previous_level": previous,
            "current_level": level,
            "name": level_names[level],
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
        return list(self.tools.values())

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
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = await server.call_tool(tool_name, arguments)
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    elif method == "resources/list":
        return {"resources": server.get_resource_list()}
    elif method == "prompts/list":
        return {"prompts": server.get_prompt_list()}
    elif method == "prompts/get":
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

    logger.info("Empathy MCP Server started")
    logger.info(f"Registered {len(server.tools)} tools")

    while True:
        try:
            # Read request from stdin (JSON-RPC format)
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
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
        except Exception as e:
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("/tmp/attune-mcp.log")],  # nosec B108
    )

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("Empathy MCP Server stopped")


if __name__ == "__main__":
    main()
