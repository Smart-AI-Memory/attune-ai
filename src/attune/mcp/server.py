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
    get_elicitation_tools,
    get_help_tools,
    get_memory_tools,
    get_personal_memory_tools,
    get_prompts,
    get_resources,
    get_utility_tools,
    get_workflow_tools,
)
from attune.mcp.workflow_handlers import WorkflowHandlersMixin, _workflow_response

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
        "personal_memory_capture",
        "personal_memory_recall",
        "personal_memory_topics",
        "personal_memory_forget",
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
                containment. Resolution order: explicit argument >
                ``ATTUNE_MCP_WORKSPACE_ROOT`` env var >
                ``CLAUDE_PROJECT_DIR`` env var > current working
                directory. Setting ``ATTUNE_MCP_WORKSPACE_ROOT`` lets
                users broaden the sandbox to a parent directory (e.g.
                the main checkout when the MCP launches in a worktree)
                without code changes. ``CLAUDE_PROJECT_DIR`` is set by
                Claude Code in the spawned MCP server's environment to
                the project root, so the sandbox tracks the project
                even when the server's cwd differs (it is a no-op in
                environments that don't export the variable).
            user_id: Identity for memory operations. Defaults
                to the OS login name or "mcp-session".

        """
        self._workspace_root = (
            workspace_root
            or os.environ.get("ATTUNE_MCP_WORKSPACE_ROOT")
            or os.environ.get("CLAUDE_PROJECT_DIR")
            or os.getcwd()
        )
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
        tools.update(get_personal_memory_tools())
        tools.update(get_utility_tools())
        tools.update(get_elicitation_tools())
        tools.update(get_help_tools())
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

        Delegates to prompts.get_prompt_messages() which owns
        the prompt templates and input sanitization.

        Args:
            prompt_name: Name of the prompt to retrieve
            arguments: Prompt arguments provided by the caller

        Returns:
            List of messages for the prompt

        Raises:
            ValueError: If prompt_name is not found

        """
        from attune.mcp.prompts import get_prompt_messages

        return get_prompt_messages(self.prompts, prompt_name, arguments)

    def _build_dispatch_table(self) -> dict[str, Any]:
        """Build tool name -> handler mapping.

        Tool namespace across the attune suite (avoid collisions
        and duplicated UX when a user enables multiple MCP servers):

        - ``help_*`` (here): attune-ai's own help engine
          (``attune.help.engine``, ``attune.workflows.help_maintenance``).
          Overlaps in intent with the two below; kept for now because
          attune-ai still ships its internal help system. Consolidation
          with ``attune-help``/``attune-author`` is a backlog item —
          see CHANGELOG / audit punch list.
        - ``lookup_*`` (attune-help MCP server): read-side lookup over
          the rendered content (``attune_help.HelpEngine``).
        - ``author_*`` (attune-author MCP server): write-side authoring
          of the source-of-truth templates that attune-help renders.

        Returns:
            Dict mapping tool names to async handler callables.
            All handlers accept (args: dict) and return dict.

        """
        return {
            "security_audit": self._run_security_audit,
            "bug_predict": self._run_bug_predict,
            "discovery_sweep": self._run_discovery_sweep,
            "code_review": self._run_code_review,
            "test_generation": self._run_test_generation,
            "performance_audit": self._run_performance_audit,
            "release_notes": self._run_release_notes,
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
            "rag_knowledge_query": self._run_rag_knowledge_query,
            "auth_status": lambda _args: self._get_auth_status(),
            "auth_recommend": self._get_auth_recommend,
            "telemetry_stats": self._get_telemetry_stats,
            "memory_store": self._handle_memory_store,
            "memory_retrieve": self._handle_memory_retrieve,
            "memory_search": self._handle_memory_search,
            "memory_forget": self._handle_memory_forget,
            "personal_memory_capture": self._handle_personal_memory_capture,
            "personal_memory_recall": self._handle_personal_memory_recall,
            "personal_memory_topics": lambda _args: self._handle_personal_memory_topics(_args),
            "personal_memory_forget": self._handle_personal_memory_forget,
            "attune_get_level": lambda _args: self._handle_attune_get_level(),
            "attune_set_level": self._handle_attune_set_level,
            "context_get": self._handle_context_get,
            "context_set": self._handle_context_set,
            "list_capabilities": lambda _args: self._handle_list_capabilities(),
            "elicitation_render_form": self._handle_elicitation_render_form,
            "elicitation_collect_response": self._handle_elicitation_collect_response,
            "elicitation_ask": self._handle_elicitation_ask,
            "elicitation_render_widget": self._handle_elicitation_render_widget,
            "help_lookup": self._handle_help_lookup,
            "help_maintain": self._handle_help_maintain,
            "help_init": self._handle_help_init,
            "help_status": self._handle_help_status,
            "help_update": self._handle_help_update,
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
            detail = str(e)
            msg = f"Tool execution failed: {type(e).__name__}"
            if detail:
                msg = f"{msg}: {detail}"
            return {"success": False, "error": msg}

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

        # security-audit's findings are category-bullets, not the
        # structured Finding shape — so it uses the UNIVERSAL panel_html
        # added by _workflow_response (spec D4), NOT a bespoke severity
        # dashboard (retired: the dashboard assumed file/line/severity the
        # real output doesn't carry). The skill renders response["panel_html"].
        return _workflow_response(
            result,
            include_provider=True,
            score="health_score",
            findings=("findings", []),
        )

    async def _run_bug_predict(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run bug prediction workflow."""
        from attune.security.path_validation import _validate_file_path

        validated_path = str(_validate_file_path(args["path"], allowed_dir=self._workspace_root))

        from attune.workflows.bug_predict import BugPredictionWorkflow

        workflow = BugPredictionWorkflow()
        result = await workflow.execute(path=validated_path)

        return _workflow_response(result, predictions=("predictions", []))

    async def _run_discovery_sweep(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run the discovery-sweep triage meta-workflow.

        Unlike the single-audit handlers, discovery-sweep renders its
        three buckets into ``final_output`` as a JSON *string*
        (``output_format="json"``), so ``_workflow_response`` would see a
        non-dict and yield empty buckets. The structured ``SweepResult``
        lives on ``result.metadata["sweep"]`` instead — extract the
        buckets from there.
        """
        from dataclasses import asdict

        from attune.security.path_validation import _validate_file_path
        from attune.workflows.discovery_sweep import DiscoverySweepWorkflow

        validated_path = str(_validate_file_path(args["path"], allowed_dir=self._workspace_root))
        workflow = DiscoverySweepWorkflow()
        result = await workflow.execute(
            path=validated_path,
            budget_usd=float(args.get("budget_usd", 10.0)),
            no_llm=bool(args.get("no_llm", False)),
            output_format="json",
        )

        cost_report = getattr(result, "cost_report", None)
        cost = cost_report.total_cost if cost_report is not None else 0.0

        sweep = (getattr(result, "metadata", None) or {}).get("sweep")
        if sweep is None:
            # execute() returned an error result (e.g. empty path) — no
            # sweep was built. Surface the message, keep buckets empty.
            return {
                "success": result.success,
                "error": None if result.success else result.final_output,
                "queue": [],
                "questions": [],
                "rejected": [],
                "cost": cost,
            }

        from attune.workflows.discovery_sweep.board import sweep_to_board_html

        buckets = {
            "queue": [asdict(f) for f in sweep.queue],
            "questions": [asdict(q) for q in sweep.questions],
            "rejected": [asdict(r) for r in sweep.rejected],
            "metadata": asdict(sweep.metadata),
        }
        return {
            "success": result.success,
            **buckets,
            # Rich triage board for mcp__visualize__show_widget (spec:
            # docs/specs/discovery-sweep-rich-surface/). Display-only,
            # injection-safe; the skill's Output step renders it.
            "board_html": sweep_to_board_html(buckets),
            "cost": cost,
        }

    async def _run_code_review(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run code review workflow."""
        from attune.security.path_validation import _validate_file_path
        from attune.workflows.code_review import CodeReviewWorkflow

        validated_path = str(_validate_file_path(args["path"], allowed_dir=self._workspace_root))
        workflow = CodeReviewWorkflow()
        result = await workflow.execute(path=validated_path)

        return _workflow_response(result, feedback="feedback", score="quality_score")

    async def _run_test_generation(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run test generation workflow."""
        from attune.security.path_validation import _validate_file_path
        from attune.workflows.test_gen import TestGenerationWorkflow

        validated_path = str(_validate_file_path(args["module"], allowed_dir=self._workspace_root))
        workflow = TestGenerationWorkflow()
        # execute reads `path` — the legacy `module_path` kwarg was dropped
        # in the v4.2.0 SDK migration, so passing it left `path` empty and
        # every call failed with "path argument is required".
        result = await workflow.execute(path=validated_path)

        return _workflow_response(
            result,
            tests_generated=("tests_generated", 0),
            output_path="output_path",
        )

    async def _run_performance_audit(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run performance audit workflow."""
        from attune.security.path_validation import _validate_file_path
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        validated_path = str(_validate_file_path(args["path"], allowed_dir=self._workspace_root))
        workflow = PerformanceAuditWorkflow()
        result = await workflow.execute(path=validated_path)

        return _workflow_response(result, findings=("findings", []), score="score")

    async def _run_release_notes(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run the release-notes advisory workflow (changelog draft + go/no-go)."""
        from attune.security.path_validation import _validate_file_path
        from attune.workflows.release_prep import ReleasePreparationWorkflow

        validated_path = str(
            _validate_file_path(args.get("path", "."), allowed_dir=self._workspace_root)
        )
        workflow = ReleasePreparationWorkflow()
        result = await workflow.execute(path=validated_path)

        response = _workflow_response(
            result,
            approved="approved",
            health_score="health_score",
            recommendation="recommendation",
        )
        if not isinstance(result.final_output, dict):
            # Short-circuited workflows degrade ``final_output`` to a
            # plain string (e.g. an error message) — surface it.
            response["recommendation"] = str(result.final_output)
        elif not response["recommendation"]:
            # Report payloads carry no "recommendation" key — fall back
            # to the result summary so the field stays populated.
            response["recommendation"] = result.summary
        return response

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
            result: dict[str, Any] = {"success": True, **stats}

            # Additive: short-term memory injection cost, read from the
            # local memory_events.jsonl the memory hooks write. Guarded so
            # a missing [ops] surface degrades to no memory section rather
            # than failing the whole telemetry call.
            try:
                from attune.ops.data import (
                    estimate_feedback_signal,
                    estimate_intervention_signal,
                    read_memory_summary,
                )

                result["memory"] = read_memory_summary()
                # Labeled benefit estimate — see the caption in the payload;
                # this is an upper bound on interventions, not savings.
                result["memory_intervention_signal"] = estimate_intervention_signal()
                # Noise side: findings surfaced then dropped as noise.
                result["memory_feedback"] = estimate_feedback_signal()
            except Exception:  # noqa: BLE001
                # INTENTIONAL: memory telemetry is a bonus section; never
                # let it break the core usage stats.
                logger.debug("memory summary unavailable", exc_info=True)

            return result
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

    async def _handle_list_capabilities(self) -> dict[str, Any]:
        """Enumerate workflows, wizards, and tools from the live registries.

        Read-only. Reads ``list_workflows()`` / ``list_wizards()`` and this
        server's own dispatch keys so a catalog renders from code, never a
        hand-maintained list.

        Returns:
            Dict with ``workflows``, ``wizards``, ``tools`` (each a list of
            ``{name, description}``) plus a ``counts`` summary.

        """
        from attune.workflows import list_workflows

        workflows = [
            {"name": w.get("name", ""), "description": w.get("description", "")}
            for w in list_workflows()
        ]

        wizards: list[dict[str, str]] = []
        try:
            from attune.wizards.registry import list_wizards

            wizards = [
                {"name": wz.wizard_id, "description": wz.description} for wz in list_wizards()
            ]
        except Exception:  # noqa: BLE001
            # INTENTIONAL: wizards are optional; an empty list still yields a
            # valid catalog rather than failing the whole call.
            logger.exception("list_wizards failed; returning empty wizard list")

        tools = [
            {"name": name, "description": defn.get("description", "")}
            for name, defn in sorted(self.tools.items())
        ]

        return {
            "success": True,
            "workflows": sorted(workflows, key=lambda c: c["name"]),
            "wizards": sorted(wizards, key=lambda c: c["name"]),
            "tools": tools,
            "counts": {
                "workflows": len(workflows),
                "wizards": len(wizards),
                "tools": len(tools),
            },
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

    async def _handle_elicitation_render_form(self, args: dict[str, Any]) -> dict[str, Any]:
        """Validate a declarative form and return batched question payloads.

        Live wiring of :func:`attune.elicitation.form_from_dict` and
        :func:`attune.elicitation.form_to_askuserquestion`. A malformed
        form definition returns ``{"success": False, "problems": [...]}``
        rather than raising, so the agent can re-fix the definition.

        Args:
            args: Must contain ``form`` (the declarative form dict).

        Returns:
            ``{"success": True, "title", "description", "batches"}`` or
            ``{"success": False, "problems": [...]}``.

        """
        from attune.elicitation import (
            FormValidationError,
            form_from_dict,
            form_to_askuserquestion,
        )

        try:
            form = form_from_dict(args.get("form", {}))
        except FormValidationError as e:
            return {"success": False, "problems": e.problems}

        recommended = self._record_surface_choice(form, chosen="ask")
        result = {
            "success": True,
            "title": form.title,
            "description": form.description,
            "batches": form_to_askuserquestion(form),
        }
        if recommended == "widget":
            result["surface_note"] = (
                "The router recommends the widget for this form (D21 — the "
                "rich surface is the default). AskUserQuestion will flatten "
                "it. Use elicitation_render_widget unless the client cannot "
                "render widgets or the user is in keyboard mode."
            )
        return result

    async def _handle_elicitation_render_widget(self, args: dict[str, Any]) -> dict[str, Any]:
        """Render a declarative form as inline HTML for ``show_widget`` (S1).

        Live wiring of :func:`attune.elicitation.form_to_widget_html` — the
        v2 escape-hatch surface (D8). Returns the self-contained HTML for
        ``mcp__visualize__show_widget``; on submit the widget posts a
        sentinel-marked JSON block via ``sendPrompt`` which the agent
        validates through ``elicitation_collect_response`` (R4). A malformed
        form definition returns ``{"success": False, "problems": [...]}``.

        Args:
            args: ``form`` (the declarative form dict) and optional
                ``message`` (prompt shown above the form).

        Returns:
            ``{"success": True, "html", "title", "field_ids"}`` or
            ``{"success": False, "problems": [...]}``.

        """
        from attune.elicitation import (
            FormValidationError,
            form_from_dict,
            form_to_widget_html,
        )

        try:
            form = form_from_dict(args.get("form", {}))
        except FormValidationError as e:
            return {"success": False, "problems": e.problems}

        self._record_surface_choice(form, chosen="widget")
        return {
            "success": True,
            "html": form_to_widget_html(form, args.get("message") or ""),
            "title": form.title,
            "field_ids": [q.id for q in form.questions],
        }

    @staticmethod
    def _record_surface_choice(form: Any, *, chosen: str) -> str | None:
        """Run the D21 router for telemetry and return its recommendation.

        The elicitation tools are the only place the live system can observe
        a surface decision: the tool the agent invoked *is* its choice.
        Running the router here records both the recommendation and whether
        the agent agreed, which is what makes the decay receipt real rather
        than a counter nothing increments.

        Best-effort in every direction — a telemetry or config problem must
        never break form rendering, so failures return ``None`` and the
        caller proceeds.

        Args:
            form: The validated ``FormSchema``.
            chosen: The surface this handler represents (``"ask"`` for the
                AskUserQuestion batches, ``"widget"`` for the HTML form).

        Returns:
            The router's recommendation, or ``None`` if it could not run.
        """
        try:
            from attune.elicitation import keyboard_mode_enabled, select_form_surface

            return select_form_surface(
                form,
                keyboard_mode=keyboard_mode_enabled(),
                chosen=chosen,
            )
        except (OSError, ValueError, ImportError) as exc:
            logger.debug("surface-choice telemetry skipped: %s", exc)
            return None

    async def _handle_elicitation_collect_response(self, args: dict[str, Any]) -> dict[str, Any]:
        """Validate user answers against a declarative form (R4).

        Live wiring of :func:`attune.elicitation.collect_form_response`.
        Missing-required or out-of-option answers return
        ``{"success": False, "problems": [...]}`` naming exactly which
        fields to re-ask — never silently accepts malformed input.

        Args:
            args: Must contain ``form`` (the form dict) and ``answers``
                (``{field_id: value}``).

        Returns:
            ``{"success": True, "responses", "response_id"}`` or
            ``{"success": False, "problems": [...]}``.

        """
        from attune.elicitation import (
            FormValidationError,
            collect_form_response,
            form_from_dict,
        )

        try:
            form = form_from_dict(args.get("form", {}))
            response = collect_form_response(form, args.get("answers", {}))
        except FormValidationError as e:
            return {"success": False, "problems": e.problems}

        return {
            "success": True,
            "responses": response.responses,
            "response_id": response.response_id,
        }

    @staticmethod
    def _elicitation_session() -> tuple[Any, Any]:
        """Return ``(session, request_id)`` for the in-flight request.

        The live MCP request context (set by the SDK during a tool call)
        carries the session that can send an ``elicitation/create``
        request. Returns ``(None, None)`` outside a request — the handler
        treats that as "client can't elicit" and signals a fallback.
        """
        try:
            ctx = _mcp_server.request_context
        except (LookupError, RuntimeError, NameError):
            return None, None
        return getattr(ctx, "session", None), getattr(ctx, "request_id", None)

    async def _handle_elicitation_ask(self, args: dict[str, Any]) -> dict[str, Any]:
        """Render a form as a native MCP elicitation and return answers.

        The v2 rich surface (decision D8): builds an elicitation
        ``requestedSchema`` from the declarative artifact, sends
        ``elicitation/create`` via the live session, and on ``accept``
        validates the structured response through
        :func:`attune.elicitation.collect_form_response` (R4). On
        ``decline``/``cancel`` returns that status; if the client cannot
        elicit, returns ``action: "unsupported"`` so the caller can fall
        back to ``elicitation_render_form`` (AskUserQuestion).

        Args:
            args: ``form`` (the declarative form dict) and optional
                ``message`` (prompt shown above the form).

        Returns:
            ``{"success": True, "action": "accept", "responses", ...}`` or
            ``{"success": False, "action"|"problems": ...}``.

        """
        from attune.elicitation import (
            FormValidationError,
            collect_form_response,
            form_from_dict,
            form_to_elicitation_schema,
        )

        try:
            form = form_from_dict(args.get("form", {}))
        except FormValidationError as e:
            return {"success": False, "problems": e.problems}

        schema = form_to_elicitation_schema(form)
        message = args.get("message") or form.title or "Please complete this form."

        session, request_id = self._elicitation_session()
        if session is None:
            return {
                "success": False,
                "action": "unsupported",
                "error": "No MCP elicitation session available (client cannot elicit).",
            }

        try:
            result = await session.elicit_form(message, schema, request_id)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: any elicit failure (unsupported capability,
            # transport) degrades to a fallback signal, never crashes.
            logger.exception("Elicitation request failed")
            return {
                "success": False,
                "action": "error",
                "error": f"Elicitation failed: {type(e).__name__}",
            }

        action = getattr(result, "action", None)
        if action != "accept":
            return {"success": False, "action": action or "cancel", "responses": {}}

        try:
            response = collect_form_response(form, getattr(result, "content", None) or {})
        except FormValidationError as e:
            return {"success": False, "action": "accept", "problems": e.problems}

        return {
            "success": True,
            "action": "accept",
            "responses": response.responses,
            "response_id": response.response_id,
        }

    async def _handle_help_lookup(self, args: dict[str, Any]) -> dict[str, Any]:
        """Look up contextual help with type-driven progression.

        Emits a help-query telemetry event to
        ``~/.attune/telemetry/help_queries.jsonl`` on every call so
        usage of the help system can be measured against drift
        maintenance cost. Queries that resolve no topic are also
        appended to ``~/.attune/telemetry/help_unmatched.jsonl``
        (FAQ-Generator channel 1). Disable both with
        ``ATTUNE_HELP_TELEMETRY=0``.

        Supports four modes:
        - progressive: escalates across template types
          (concept -> procedural -> reference)
        - workflow_help: tips relevant after a workflow completes
        - precursor: warnings relevant to a file being edited
        - search_tag: find templates matching a tag

        Args:
            args: Must contain topic; optional mode, file_path,
                last_workflow, reset.

        Returns:
            Dict with templates, depth level, and metadata.

        """
        import time

        from attune.telemetry.help_tracker import get_tracker

        topic = args["topic"]
        mode = args.get("mode", "progressive")
        started = time.perf_counter()
        result: dict[str, Any] = {}
        try:
            result = await self._handle_help_lookup_impl(args, topic, mode)
            return result
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            tracker = get_tracker()
            tracker.log(
                source="help_lookup",
                mode=mode,
                topic=topic,
                success=bool(result.get("success")),
                found=bool(result.get("success")) and "error" not in result,
                duration_ms=duration_ms,
            )
            if self._help_lookup_unmatched(mode, result):
                tracker.log_unmatched(query=topic, mode=mode)

    @staticmethod
    def _help_lookup_unmatched(mode: str, result: dict[str, Any]) -> bool:
        """True when a lookup completed but resolved no help topic.

        This is FAQ-Generator channel 1 (real user questions with no
        matching topic — see help-docs-single-source follow-ups FG1).
        Exceptions (empty result) and unknown modes don't count. The
        error prefixes are the not-found returns produced by
        ``_handle_help_lookup_impl`` below.
        """
        if not result:
            return False
        if result.get("success"):
            return mode == "search_tag" and result.get("count") == 0
        error = str(result.get("error", ""))
        return error.startswith(("Template not found", "No preamble for"))

    async def _handle_help_lookup_impl(
        self, args: dict[str, Any], topic: str, mode: str
    ) -> dict[str, Any]:
        """Dispatch help_lookup modes. Separate from the telemetry wrapper."""
        from attune.help.engine import (
            get_precursor_warnings,
            get_workflow_help,
            populate_progressive,
            reset_session,
            search_by_tag,
        )

        if mode == "preamble":
            from attune.help.engine import get_preamble

            line = get_preamble(topic)
            if line is None:
                return {"success": False, "error": f"No preamble for: {topic}"}
            return {
                "success": True,
                "topic": topic,
                "preamble": line,
            }

        if mode == "related":
            from attune.help.engine import get_related_preambles

            related = get_related_preambles(topic)
            return {
                "success": True,
                "topic": topic,
                "related": related,
            }

        if mode == "progressive":
            # Handle reset request
            if args.get("reset"):
                reset_session()

            # Context-aware starting level
            starting_level = None
            if args.get("last_workflow"):
                starting_level = 1  # skip concept, start at procedural

            result = populate_progressive(
                topic,
                starting_level=starting_level,
            )
            if result is None:
                return {"success": False, "error": f"Template not found: {topic}"}
            return {
                "success": True,
                "title": result.title,
                "body": result.body,
                "type": result.type,
                "depth_level": result.metadata.get("depth_level", 0),
                "level_label": result.metadata.get("level_label", ""),
                "topic": result.metadata.get("topic", ""),
                "tags": result.tags,
                "related": result.related,
            }

        if mode == "workflow_help":
            templates = get_workflow_help(topic)
            return {
                "success": True,
                "templates": [
                    {"title": t.title, "body": t.body, "id": t.template_id} for t in templates
                ],
            }

        if mode == "precursor":
            file_path = args.get("file_path", topic)
            warnings = get_precursor_warnings(file_path)
            return {
                "success": True,
                "warnings": [
                    {"title": w.title, "body": w.body, "id": w.template_id} for w in warnings
                ],
            }

        if mode == "search_tag":
            template_ids = search_by_tag(topic)
            return {
                "success": True,
                "template_ids": template_ids,
                "count": len(template_ids),
            }

        return {"success": False, "error": f"Unknown mode: {mode}"}

    async def _handle_help_maintain(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run help knowledge base maintenance.

        Detects stale templates and optionally regenerates them.

        Args:
            args: Optional ``dry_run`` boolean.

        Returns:
            Dict with stale count, regenerated types, and
            validation status.

        """
        from attune.workflows.help_maintenance import (
            HelpMaintenanceWorkflow,
        )

        dry_run = args.get("dry_run", False)
        batch = args.get("batch", False)
        workflow = HelpMaintenanceWorkflow()
        result = await workflow.execute(dry_run=dry_run, batch=batch)

        return {
            "success": result.success,
            "output": result.final_output,
        }

    async def _handle_help_init(self, args: dict[str, Any]) -> dict[str, Any]:
        """Bootstrap project-local help system.

        Two-phase flow:
        - action=scan: discover features, return proposals
        - action=accept: save manifest + generate templates

        Args:
            args: Must contain action; optional accepted list.

        Returns:
            Dict with proposals (scan) or generation results (accept).

        """
        from attune.help.bootstrap import (
            ProposedFeature,
            proposals_to_manifest,
            scan_project,
        )
        from attune.help.generator import generate_feature_templates
        from attune.help.manifest import save_manifest
        from attune.help.preamble import get_preamble
        from attune.security.path_validation import _validate_file_path

        action = args.get("action", "scan")
        project_root = self._workspace_root
        help_dir = Path(project_root) / ".help"
        _validate_file_path(str(help_dir), allowed_dir=self._workspace_root)

        if action == "scan":
            proposals = scan_project(project_root)
            return {
                "success": True,
                "proposals": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "files": p.files,
                        "tags": p.tags,
                        "confidence": p.confidence,
                        "reason": p.reason,
                    }
                    for p in proposals
                ],
                "count": len(proposals),
            }

        if action == "accept":
            accepted_raw = args.get("accepted", [])
            proposals = []
            for a in accepted_raw:
                name = a.get("name")
                description = a.get("description")
                if not name or not description:
                    return {
                        "success": False,
                        "error": "Each accepted proposal must have 'name' and 'description'.",
                    }
                proposals.append(
                    ProposedFeature(
                        name=name,
                        description=description,
                        files=a.get("files", []),
                        tags=a.get("tags", []),
                    )
                )
            manifest = proposals_to_manifest(proposals)
            save_manifest(manifest, help_dir)

            generated = []
            failed = []
            for feat in manifest.features.values():
                try:
                    result = generate_feature_templates(feat, help_dir, project_root)
                except OSError as exc:
                    logger.warning("Template generation failed for %s: %s", feat.name, exc)
                    failed.append(feat.name)
                    continue

                preamble = get_preamble(result.feature, help_dir) or ""
                generated.append(
                    {
                        "feature": result.feature,
                        "preamble": preamble,
                        "templates": len(result.templates),
                        "files": len(result.matched_files),
                    }
                )

            return {
                "success": True,
                "manifest_path": str(help_dir / "features.yaml"),
                "features": len(manifest.features),
                "generated": generated,
                "failed": failed,
            }

        return {"success": False, "error": f"Unknown action: {action}"}

    async def _handle_help_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Show staleness report for project-local help.

        Args:
            args: Optional features list to filter.

        Returns:
            Dict with staleness report and formatted output.

        """
        from attune.help.maintenance import format_status_report
        from attune.help.manifest import load_manifest
        from attune.help.staleness import check_staleness
        from attune.security.path_validation import _validate_file_path

        project_root = self._workspace_root
        help_dir = Path(project_root) / ".help"
        _validate_file_path(str(help_dir), allowed_dir=self._workspace_root)

        try:
            manifest = load_manifest(help_dir)
        except FileNotFoundError:
            return {
                "success": False,
                "error": ("No .help/features.yaml found. " "Run help_init(action='scan') first."),
            }

        features = args.get("features")
        report = check_staleness(manifest, help_dir, project_root, features)

        return {
            "success": True,
            "stale_count": report.stale_count,
            "current_count": report.current_count,
            "stale_features": report.stale_features,
            "report": format_status_report(report, help_dir),
        }

    async def _handle_help_update(self, args: dict[str, Any]) -> dict[str, Any]:
        """Regenerate help templates for features.

        Args:
            args: Optional features list and dry_run flag.

        Returns:
            Dict with regeneration results.

        """
        from attune.help.maintenance import run_maintenance
        from attune.security.path_validation import _validate_file_path

        project_root = self._workspace_root
        help_dir = Path(project_root) / ".help"
        _validate_file_path(str(help_dir), allowed_dir=self._workspace_root)

        features = args.get("features")
        dry_run = args.get("dry_run", False)

        try:
            result = run_maintenance(
                help_dir,
                project_root,
                features=features,
                dry_run=dry_run,
            )
        except FileNotFoundError:
            return {
                "success": False,
                "error": ("No .help/features.yaml found. " "Run help_init(action='scan') first."),
            }

        from attune.help.preamble import get_preamble

        return {
            "success": True,
            "stale_count": result.stale_count,
            "regenerated_count": result.regenerated_count,
            "regenerated": [
                {
                    "feature": r.feature,
                    "preamble": get_preamble(r.feature, help_dir) or "",
                    "templates": len(r.templates),
                }
                for r in result.regenerated
            ],
            "failed": result.failed,
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

    # Load .env so ANTHROPIC_API_KEY is available for
    # features like the help template polish pass
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

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
