"""Real preference and subprocess receipts for automatic prompt refinement."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from attune.prompt_refinement import (
    HOST_INSTRUCTIONS,
    REFINEMENT_POLICY,
    handle_prompt_refinement,
    refinement_status,
    set_refinement_enabled,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def isolated_user(tmp_path, monkeypatch):
    """Keep all preference reads/writes in a disposable user home."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("ATTUNE_PROMPT_REFINEMENT", raising=False)


def test_default_on_without_writing_user_data(tmp_path):
    status = refinement_status()
    assert status["active"] and status["source"] == "default"
    assert status["instructions"] == REFINEMENT_POLICY
    assert not (tmp_path / ".attune").exists()


def test_persistent_opt_out_survives_new_process(tmp_path):
    path = set_refinement_enabled(False)
    assert json.loads(path.read_text()) == {"enabled": False}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from attune.prompt_refinement import refinement_status; "
            "import json; print(json.dumps(refinement_status()))",
        ],
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    status = json.loads(result.stdout)
    assert not status["active"] and status["source"] == "user"
    set_refinement_enabled(True)
    assert refinement_status()["active"]


def test_skip_once_does_not_change_saved_preference():
    path = set_refinement_enabled(True)
    original = path.read_bytes()
    assert not refinement_status(skip_this_prompt=True)["active"]
    assert refinement_status()["active"]
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "raw", ["null", "[]", '"false"', '{"enabled": "false"}', "{bad", '{"x":1}']
)
def test_corrupt_preference_disables_visibly_and_is_not_clobbered(tmp_path, raw):
    path = tmp_path / ".attune" / "prompt-refinement.json"
    path.parent.mkdir()
    path.write_text(raw)
    status = refinement_status()
    assert not status["active"] and not status["success"]
    assert status["warning"] and status["source"] == "unavailable"
    with pytest.raises(ValueError):
        set_refinement_enabled(True)
    assert path.read_text() == raw


def test_unreadable_settings_do_not_reenable(tmp_path):
    (tmp_path / ".attune" / "prompt-refinement.json").mkdir(parents=True)
    assert refinement_status()["source"] == "unavailable"


def test_unfamiliar_preference_fields_are_not_retained(tmp_path):
    path = set_refinement_enabled(False)
    raw = '{"enabled": false, "foreign": 1}'
    path.write_text(raw)
    assert refinement_status()["source"] == "unavailable"
    with pytest.raises(ValueError):
        set_refinement_enabled(True)
    assert path.read_text() == raw


@pytest.mark.parametrize("raw,expected", [("false", False), ("on", False), ("bad", False)])
def test_environment_override_is_reported(monkeypatch, raw, expected):
    set_refinement_enabled(False)
    monkeypatch.setenv("ATTUNE_PROMPT_REFINEMENT", raw)
    status = refinement_status()
    assert status["active"] is expected
    assert status["source"] == {"bad": "unavailable", "on": "user", "false": "environment"}[raw]


@pytest.mark.parametrize("directory_link", [True, False])
def test_preference_symlink_cannot_redirect_reads_or_writes(tmp_path, directory_link):
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "prompt-refinement.json"
    victim.write_text('{"enabled": false}')
    folder = tmp_path / ".attune"
    try:
        if directory_link:
            folder.symlink_to(outside, target_is_directory=True)
        else:
            folder.mkdir()
            (folder / victim.name).symlink_to(victim)
    except OSError as exc:
        pytest.skip(f"Host cannot create a symlink: {exc}")
    with pytest.raises(ValueError, match="symlink"):
        set_refinement_enabled(True)
    assert refinement_status()["source"] == "unavailable"
    assert victim.read_text() == '{"enabled": false}'


def test_atomic_failure_preserves_preference_and_cleans_temporary(monkeypatch):
    path = set_refinement_enabled(False)
    original = path.read_bytes()

    def reject_replace(self, target):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(Path, "replace", reject_replace)
    with pytest.raises(OSError):
        set_refinement_enabled(True)
    assert path.read_bytes() == original
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("value", ["false", 0, None])
def test_no_boolean_coercion(value):
    with pytest.raises(ValueError):
        set_refinement_enabled(value)
    with pytest.raises(ValueError):
        refinement_status(skip_this_prompt=value)


@pytest.mark.asyncio
async def test_tool_opt_out_and_skip_round_trip():
    assert (await handle_prompt_refinement({}))["active"]
    disabled = await handle_prompt_refinement({"action": "disable"})
    assert disabled["saved_enabled"] is False and not disabled["active"]
    assert not (await handle_prompt_refinement({}))["active"]
    await handle_prompt_refinement({"action": "enable"})
    assert not (await handle_prompt_refinement({"skip_this_prompt": True}))["active"]
    assert (await handle_prompt_refinement({}))["active"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args",
    [
        {"action": "unknown"},
        {"prompt": "private"},
        {"skip_this_prompt": "false"},
        {"action": "disable", "skip_this_prompt": True},
    ],
)
async def test_invalid_tool_arguments_do_not_change_preference(args, tmp_path):
    with pytest.raises(ValueError):
        await handle_prompt_refinement(args)
    assert not (tmp_path / ".attune").exists()


def _hook(prompt):
    return subprocess.run(
        [sys.executable, str(ROOT / "plugin/hooks/prompt_refinement.py")],
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        timeout=20,
        check=True,
    )


def test_real_hook_observes_changes_and_does_not_echo_prompt():
    prompt = "private request marker 73b2"
    result = _hook(prompt)
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert '"active": true' in context and prompt not in context
    set_refinement_enabled(False)
    assert '"active": false' in _hook(prompt).stdout.replace('\\"', '"')


def test_hook_skip_prefix_is_per_turn():
    assert '"skipped": true' in _hook("  [no-refine] act on this").stdout.replace('\\"', '"')
    assert '"active": true' in _hook("next prompt").stdout.replace('\\"', '"')


def test_hook_context_budget_and_compact_opt_out():
    def context():
        return json.loads(_hook("ok").stdout)["hookSpecificOutput"]["additionalContext"]

    assert len(context()) < 2200
    set_refinement_enabled(False)
    disabled = context()
    assert len(disabled) < 650
    assert "material missing information" not in disabled


def test_invalid_hook_event_continues_with_visible_degradation():
    result = _hook(None)
    assert "unavailable" in result.stderr
    assert "unavailable" in result.stdout


def test_unavailable_policy_import_fails_visibly_without_blocking(monkeypatch, capsys):
    import runpy

    # Simulate a missing import while retaining the suite's inference guard.
    monkeypatch.setitem(sys.modules, "attune.prompt_refinement", None)
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(ROOT / "plugin/hooks/prompt_refinement.py"), run_name="__main__")
    assert result.value.code == 0
    output = capsys.readouterr()
    assert "unavailable" in output.err
    assert "unavailable" in json.loads(output.out)["hookSpecificOutput"]["additionalContext"]


def test_registered_hook_is_in_plugin_user_prompt_event():
    hooks = json.loads((ROOT / "plugin/hooks/hooks.json").read_text())["hooks"]["UserPromptSubmit"]
    assert any(
        "/hooks/prompt_refinement.py" in hook["command"]
        for group in hooks
        for hook in group["hooks"]
    )


def test_cli_user_opt_out_and_status(capsys):
    from attune.cli_minimal import main

    assert main(["config", "set", "prompt_refinement", "false"]) == 0
    assert not refinement_status()["active"]
    assert main(["config", "show"]) == 0
    assert "prompt_refinement = false" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_mcp_dispatch_and_initialization(tmp_path):
    from attune.mcp.server import AttuneMCPServer, _initialization_options

    server = AttuneMCPServer(workspace_root=str(tmp_path))
    assert "prompt_refinement" in server.tools
    assert HOST_INSTRUCTIONS in _initialization_options().instructions
    assert not (await server.call_tool("prompt_refinement", {"action": "disable"}))["active"]
    assert not (await server.call_tool("prompt_refinement", {}))["active"]
    result = await server.call_tool("prompt_refinement", {"action": "oops"})
    assert not result["success"]


@pytest.mark.asyncio
async def test_public_stdio_preferences_and_information_collection(tmp_path):
    """Real MCP transport, persisted preference, and existing forms round trip.

    This proves the tools can deliver and collect; it does not simulate an
    LLM deciding what to ask or a human interacting with a rendered widget.
    """
    import asyncio

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import get_default_environment, stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "attune.mcp.server"],
        cwd=str(tmp_path),
        env={
            **get_default_environment(),
            "HOME": str(tmp_path),
            "USERPROFILE": str(tmp_path),
            "PYTHONPATH": str(ROOT / "src"),
            "ATTUNE_HOME": str(tmp_path),
            "ATTUNE_FORMS_HOME": str(tmp_path),
            "ANTHROPIC_API_KEY": "",
            "ATTUNE_PROMPT_REFINEMENT": "true",
        },
    )

    async def run():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                assert HOST_INSTRUCTIONS in init.instructions
                assert "prompt_refinement" in {
                    tool.name for tool in (await session.list_tools()).tools
                }

                async def call(name, args):
                    reply = await session.call_tool(name, args)
                    assert not reply.isError
                    return json.loads(
                        next(block.text for block in reply.content if block.type == "text")
                    )

                assert (await call("prompt_refinement", {}))["active"]
                assert not (await call("prompt_refinement", {"action": "disable"}))["active"]
                assert not (await call("prompt_refinement", {}))["active"]
                await call("prompt_refinement", {"action": "enable"})
                assert not (await call("prompt_refinement", {"skip_this_prompt": True}))["active"]
                assert (await call("prompt_refinement", {}))["active"]

                form = {
                    "title": "Festival details",
                    "fields": [
                        {"id": "venue", "type": "text_input", "text": "Venue", "required": True},
                        {
                            "id": "budget",
                            "type": "text_input",
                            "text": "Website budget",
                            "required": True,
                        },
                    ],
                }
                rendered = await call("elicitation_render_form", {"form": form})
                assert rendered["success"]
                collected = await call(
                    "elicitation_collect_response",
                    {
                        "form": form,
                        "answers": {"venue": "Peach Tree Park", "budget": "$500"},
                    },
                )
                assert collected["success"]
                assert collected["responses"] == {"venue": "Peach Tree Park", "budget": "$500"}

    await asyncio.wait_for(run(), timeout=35)
    assert json.loads((tmp_path / ".attune/prompt-refinement.json").read_text()) == {
        "enabled": True
    }
