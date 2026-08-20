"""Focused coverage for MCP workflow handlers and protocol adapters."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import attune.mcp.server as server_module


def _make_server(tmp_path):
    """Create a server without plugin discovery side effects."""
    with patch.object(server_module.EmpathyMCPServer, "_register_plugin_tools"):
        return server_module.EmpathyMCPServer(workspace_root=str(tmp_path))


def _workflow_result(final_output, *, success=True, summary="summary"):
    """Return the minimum legacy WorkflowResult shape used by handlers."""
    return SimpleNamespace(
        success=success,
        final_output=final_output,
        summary=summary,
        provider="mock-provider",
        cost_report=SimpleNamespace(total_cost=1.25),
        error=None,
        metadata={},
    )


@pytest.fixture
def reset_adapter_app():
    """Keep module-level adapter singleton tests order-independent."""
    previous = server_module._app
    server_module._app = None
    try:
        yield
    finally:
        server_module._app = previous


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler_name", "argument", "module_name", "class_name", "expected_kwargs", "field"),
    [
        (
            "_run_security_audit",
            "path",
            "attune.workflows.security_audit",
            "SecurityAuditWorkflow",
            {"path": "{path}"},
            "score",
        ),
        (
            "_run_bug_predict",
            "path",
            "attune.workflows.bug_predict",
            "BugPredictionWorkflow",
            {"path": "{path}"},
            "predictions",
        ),
        (
            "_run_code_review",
            "path",
            "attune.workflows.code_review",
            "CodeReviewWorkflow",
            {"path": "{path}"},
            "feedback",
        ),
        (
            "_run_test_generation",
            "module",
            "attune.workflows.test_gen",
            "TestGenerationWorkflow",
            {"path": "{path}"},
            "tests_generated",
        ),
        (
            "_run_performance_audit",
            "path",
            "attune.workflows.perf_audit",
            "PerformanceAuditWorkflow",
            {"path": "{path}"},
            "score",
        ),
    ],
)
async def test_workflow_handlers_execute_with_validated_path(
    tmp_path,
    handler_name,
    argument,
    module_name,
    class_name,
    expected_kwargs,
    field,
):
    target = tmp_path / "target.py"
    target.write_text("value = 1\n")
    final_output = {
        "health_score": 91,
        "findings": ["finding"],
        "predictions": ["prediction"],
        "feedback": "looks good",
        "quality_score": 88,
        "tests_generated": 4,
        "output_path": "tests/test_target.py",
        "score": 77,
    }
    workflow = MagicMock()
    workflow.execute = AsyncMock(return_value=_workflow_result(final_output))

    with patch(f"{module_name}.{class_name}", return_value=workflow):
        result = await getattr(_make_server(tmp_path), handler_name)({argument: str(target)})

    workflow.execute.assert_awaited_once_with(
        **{
            key: str(target) if value == "{path}" else value
            for key, value in expected_kwargs.items()
        }
    )
    assert result["success"] is True
    expected_field = (
        "health_score" if field == "score" and handler_name == "_run_security_audit" else field
    )
    assert result[field] == final_output[expected_field]
    assert result["cost"] == 1.25


@pytest.mark.asyncio
async def test_release_notes_uses_default_path_and_summary_fallback(tmp_path, monkeypatch):
    workflow = MagicMock()
    workflow.execute = AsyncMock(
        return_value=_workflow_result(
            {"approved": True, "health_score": 95},
            summary="Ready to release",
        )
    )
    monkeypatch.chdir(tmp_path)
    with patch(
        "attune.workflows.release_prep.ReleasePreparationWorkflow",
        return_value=workflow,
    ):
        result = await _make_server(tmp_path)._run_release_notes({})

    workflow.execute.assert_awaited_once_with(path=str(tmp_path))
    assert result["recommendation"] == "Ready to release"
    assert result["approved"] is True


@pytest.mark.asyncio
async def test_release_notes_surfaces_string_output(tmp_path):
    workflow = MagicMock()
    workflow.execute = AsyncMock(return_value=_workflow_result("release failed", success=False))
    with patch(
        "attune.workflows.release_prep.ReleasePreparationWorkflow",
        return_value=workflow,
    ):
        result = await _make_server(tmp_path)._run_release_notes({"path": str(tmp_path)})

    assert result["success"] is False
    assert result["recommendation"] == "release failed"


@pytest.mark.asyncio
async def test_discovery_sweep_forwards_options_and_handles_missing_sweep(tmp_path):
    workflow = MagicMock()
    workflow.execute = AsyncMock(return_value=_workflow_result("nothing to scan", success=False))
    with patch(
        "attune.workflows.discovery_sweep.DiscoverySweepWorkflow",
        return_value=workflow,
    ):
        result = await _make_server(tmp_path)._run_discovery_sweep(
            {"path": str(tmp_path), "budget_usd": "2.5", "no_llm": 1}
        )

    workflow.execute.assert_awaited_once_with(
        path=str(tmp_path),
        budget_usd=2.5,
        no_llm=True,
        output_format="json",
    )
    assert result == {
        "success": False,
        "error": "nothing to scan",
        "queue": [],
        "questions": [],
        "rejected": [],
        "cost": 1.25,
    }


@pytest.mark.asyncio
async def test_discovery_sweep_serializes_buckets_and_board(tmp_path):
    from attune.workflows.discovery_sweep.workflow import SweepMetadata, SweepResult

    sweep = SweepResult(
        queue=[],
        questions=[],
        rejected=[],
        metadata=SweepMetadata(spent_usd=0.5, budget_usd=3.0),
    )
    result_obj = _workflow_result("{}")
    result_obj.metadata = {"sweep": sweep}
    workflow = MagicMock()
    workflow.execute = AsyncMock(return_value=result_obj)

    with (
        patch(
            "attune.workflows.discovery_sweep.DiscoverySweepWorkflow",
            return_value=workflow,
        ),
        patch(
            "attune.workflows.discovery_sweep.board.sweep_to_board_html",
            return_value="<board />",
        ),
    ):
        result = await _make_server(tmp_path)._run_discovery_sweep({"path": str(tmp_path)})

    assert result["metadata"]["budget_usd"] == 3.0
    assert result["board_html"] == "<board />"
    assert result["cost"] == 1.25


@pytest.mark.asyncio
async def test_auth_status_returns_strategy_shape(tmp_path):
    strategy = SimpleNamespace(
        subscription_tier=SimpleNamespace(value="team"),
        default_mode=SimpleNamespace(value="api"),
        setup_completed=True,
    )
    with patch("attune.models.AuthStrategy.load", return_value=strategy):
        result = await _make_server(tmp_path)._get_auth_status()

    assert result == {
        "success": True,
        "subscription_tier": "team",
        "default_mode": "api",
        "setup_completed": True,
    }


@pytest.mark.asyncio
async def test_auth_recommend_uses_validated_file_metrics(tmp_path):
    target = tmp_path / "module.py"
    target.write_text("one\ntwo\n")
    strategy = MagicMock()
    strategy.get_recommended_mode.return_value = SimpleNamespace(value="subscription")

    with (
        patch("attune.models.count_lines_of_code", return_value=2),
        patch("attune.models.get_module_size_category", return_value="small"),
        patch("attune.models.get_auth_strategy", return_value=strategy),
    ):
        result = await _make_server(tmp_path)._get_auth_recommend({"file_path": str(target)})

    strategy.get_recommended_mode.assert_called_once_with(2)
    assert result["file_path"] == str(target)
    assert result["lines_of_code"] == 2
    assert result["category"] == "small"
    assert result["recommended_mode"] == "subscription"


@pytest.mark.asyncio
async def test_telemetry_stats_includes_optional_memory_signals(tmp_path):
    tracker = MagicMock()
    tracker.get_stats.return_value = {"calls": 9}
    with (
        patch("attune.telemetry.usage_tracker.UsageTracker", return_value=tracker),
        patch("attune.ops.data.read_memory_summary", return_value={"events": 2}),
        patch("attune.ops.data.estimate_intervention_signal", return_value={"upper": 1}),
        patch("attune.ops.data.estimate_feedback_signal", return_value={"noise": 0}),
    ):
        result = await _make_server(tmp_path)._get_telemetry_stats({"days": 7})

    tracker.get_stats.assert_called_once_with(days=7)
    assert result["calls"] == 9
    assert result["memory"] == {"events": 2}
    assert result["memory_intervention_signal"] == {"upper": 1}
    assert result["memory_feedback"] == {"noise": 0}


@pytest.mark.asyncio
async def test_telemetry_stats_survives_optional_memory_failure(tmp_path):
    tracker = MagicMock()
    tracker.get_stats.return_value = {"calls": 1}
    with (
        patch("attune.telemetry.usage_tracker.UsageTracker", return_value=tracker),
        patch("attune.ops.data.read_memory_summary", side_effect=RuntimeError("offline")),
    ):
        result = await _make_server(tmp_path)._get_telemetry_stats({})

    assert result == {"success": True, "calls": 1}


@pytest.mark.asyncio
async def test_telemetry_stats_reports_missing_module(tmp_path):
    with patch.dict(sys.modules, {"attune.telemetry.usage_tracker": None}):
        result = await _make_server(tmp_path)._get_telemetry_stats({})

    assert result == {
        "success": False,
        "error": "Telemetry module not installed",
    }


@pytest.mark.asyncio
async def test_list_capabilities_uses_live_registries(tmp_path):
    wizard = SimpleNamespace(wizard_id="setup", description="Set up")
    with (
        patch(
            "attune.workflows.list_workflows",
            return_value=[
                {"name": "zeta", "description": "Z"},
                {"name": "alpha", "description": "A"},
            ],
        ),
        patch("attune.wizards.registry.list_wizards", return_value=[wizard]),
    ):
        result = await _make_server(tmp_path)._handle_list_capabilities()

    assert [item["name"] for item in result["workflows"]] == ["alpha", "zeta"]
    assert result["wizards"] == [{"name": "setup", "description": "Set up"}]
    assert result["counts"]["tools"] == len(result["tools"])


@pytest.mark.asyncio
async def test_list_capabilities_tolerates_wizard_registry_failure(tmp_path):
    with (
        patch("attune.workflows.list_workflows", return_value=[]),
        patch(
            "attune.wizards.registry.list_wizards",
            side_effect=RuntimeError("unavailable"),
        ),
    ):
        result = await _make_server(tmp_path)._handle_list_capabilities()

    assert result["success"] is True
    assert result["wizards"] == []


@pytest.mark.asyncio
async def test_level_and_context_handlers_round_trip(tmp_path):
    app = _make_server(tmp_path)
    assert (await app._handle_attune_get_level())["level"] == 3
    assert (await app._handle_attune_set_level({"level": 4}))["current_level"] == 4
    # bool is an int subclass — `True` must be rejected, not treated as 1.
    assert (await app._handle_attune_set_level({"level": True}))["success"] is False
    set_result = await app._handle_context_set({"key": "focus", "value": "tests"})
    get_result = await app._handle_context_get({"key": "focus"})
    assert set_result["value"] == "tests"
    assert get_result["found"] is True


def test_get_app_caches_singleton(reset_adapter_app):
    instance = MagicMock()
    with patch.object(server_module, "EmpathyMCPServer", return_value=instance) as factory:
        assert server_module._get_app() is instance
        assert server_module._get_app() is instance
    factory.assert_called_once_with()


@pytest.mark.asyncio
async def test_protocol_list_tools_maps_schema_and_default(reset_adapter_app):
    server_module._app = SimpleNamespace(
        tools={
            "specified": {
                "description": "Has schema",
                "input_schema": {"type": "object", "required": ["path"]},
            },
            "defaulted": {},
        }
    )
    tools = await server_module._handle_list_tools()

    assert tools[0].name == "specified"
    assert tools[0].inputSchema["required"] == ["path"]
    assert tools[1].description == ""
    assert tools[1].inputSchema == {"type": "object", "properties": {}}


@pytest.mark.asyncio
async def test_protocol_call_tool_serializes_result_and_defaults_arguments(
    reset_adapter_app,
):
    call_tool = AsyncMock(return_value={"success": True, "value": 3})
    server_module._app = SimpleNamespace(call_tool=call_tool)

    content = await server_module._handle_call_tool("auth_status")

    call_tool.assert_awaited_once_with("auth_status", {})
    assert json.loads(content[0].text) == {"success": True, "value": 3}
    assert content[0].type == "text"


@pytest.mark.asyncio
async def test_protocol_list_resources_maps_all_fields(reset_adapter_app):
    server_module._app = SimpleNamespace(
        resources={
            "workflows": {
                "uri": "attune://workflows",
                "name": "Workflows",
                "description": "Available workflows",
                "mime_type": "application/json",
            }
        }
    )
    resources = await server_module._handle_list_resources()

    assert str(resources[0].uri) == "attune://workflows"
    assert resources[0].name == "Workflows"
    assert resources[0].mimeType == "application/json"


@pytest.mark.asyncio
async def test_protocol_list_prompts_maps_arguments(reset_adapter_app):
    server_module._app = SimpleNamespace(
        prompts={
            "scan": {
                "name": "security-scan",
                "description": "Scan code",
                "arguments": [
                    {"name": "path", "description": "Target", "required": True},
                    {"name": "depth"},
                ],
            }
        }
    )
    prompts = await server_module._handle_list_prompts()

    assert prompts[0].name == "security-scan"
    assert prompts[0].arguments[0].required is True
    assert prompts[0].arguments[1].required is False


@pytest.mark.asyncio
async def test_protocol_get_prompt_maps_messages(reset_adapter_app):
    get_messages = MagicMock(
        return_value=[
            {"role": "user", "content": {"text": "Scan src"}},
            {"role": "assistant", "content": {"text": "Starting"}},
        ]
    )
    server_module._app = SimpleNamespace(get_prompt_messages=get_messages)

    result = await server_module._handle_get_prompt("security-scan", {"path": "src"})

    get_messages.assert_called_once_with("security-scan", {"path": "src"})
    assert [message.content.text for message in result.messages] == [
        "Scan src",
        "Starting",
    ]


def test_create_server_constructs_application():
    instance = MagicMock()
    with patch.object(server_module, "EmpathyMCPServer", return_value=instance) as factory:
        assert server_module.create_server() is instance
    factory.assert_called_once_with()


def test_main_configures_logging_and_runs_stdio_without_starting_server():
    with (
        patch.object(server_module.Path, "mkdir") as mkdir,
        patch.object(server_module.logging, "FileHandler", return_value=MagicMock()),
        patch.object(server_module.logging, "basicConfig") as basic_config,
        patch.object(server_module.asyncio, "run") as asyncio_run,
        patch("structlog.configure") as configure,
    ):
        server_module.main()

    mkdir.assert_called_once_with(exist_ok=True)
    basic_config.assert_called_once()
    configure.assert_called_once()
    asyncio_run.assert_called_once()
    asyncio_run.call_args.args[0].close()


@pytest.mark.asyncio
async def test_run_stdio_delegates_streams_to_sdk_server():
    class StdioContext:
        async def __aenter__(self):
            return "read", "write"

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    sdk_server = MagicMock()
    sdk_server.run = AsyncMock()
    sdk_server.create_initialization_options.return_value = "options"
    with (
        patch.object(server_module, "stdio_server", return_value=StdioContext()),
        patch.object(server_module, "_mcp_server", sdk_server),
    ):
        await server_module._run_stdio()

    sdk_server.run.assert_awaited_once_with("read", "write", "options")


def test_main_tolerates_missing_dotenv_and_keyboard_interrupt():
    with (
        patch.dict(sys.modules, {"dotenv": None}),
        patch.object(server_module.Path, "mkdir"),
        patch.object(server_module.logging, "FileHandler", return_value=MagicMock()),
        patch.object(server_module.logging, "basicConfig"),
        patch.object(server_module.asyncio, "run", side_effect=KeyboardInterrupt),
        patch("structlog.configure"),
        patch.object(server_module.logger, "info") as log_info,
    ):
        server_module.main()

    log_info.assert_called_once_with("Attune MCP Server stopped")


def test_runtime_registered_shapes_match_protocol_contract(tmp_path):
    app = server_module.EmpathyMCPServer(workspace_root=str(tmp_path))

    assert set(app.tools) == set(app._tool_handlers) | set(app._plugin_handlers)
    assert all(set(tool) == {"name", "description", "input_schema"} for tool in app.get_tool_list())
    resources = app.get_resource_list()
    assert {resource["uri"] for resource in resources} == {
        "attune://workflows",
        "attune://auth/config",
        "attune://telemetry",
    }
    assert all(
        set(resource) == {"uri", "name", "description", "mime_type"} for resource in resources
    )
    assert {prompt["name"] for prompt in app.get_prompt_list()} == {
        "security-scan",
        "test-gen",
        "cost-report",
    }


async def test_rate_limited_dispatch_carries_success_key(tmp_path):
    """Library-review M3: the rate-limit branch of _dispatch_tool must
    return a dict with success=False, like every other error path."""
    server = _make_server(tmp_path)
    # Force the limiter to reject.
    server._rate_limiter.check = lambda tool_name: False
    result = await server._dispatch_tool("attune_get_level", {})
    assert result["success"] is False
    assert "Rate limit exceeded" in result["error"]
