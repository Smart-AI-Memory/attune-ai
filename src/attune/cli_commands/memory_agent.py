"""``attune memory-agent`` — a single-shot agent with a Redis-backed Memory tool.

Runs the raw ``anthropic`` SDK ``tool_runner`` with attune's Anthropic
Memory-tool bridge attached, so Claude reads/writes a ``/memories``
directory persisted on attune's backend — the local file backend by
default, the **Redis Agent Memory Server** when ``attune_redis`` is
configured. This is the concrete, runnable form of the dual-vendor claim:
Anthropic's native Memory tool (``memory_20250818``), backed by attune on
Redis.

Note: this is the **one** attune surface that requires the raw API
(``ANTHROPIC_API_KEY``). The Memory tool is not available on the
subscription / agent-SDK path (``claude_agent_sdk`` exposes a tool-name
allowlist + MCP servers, not a slot for a ``BetaAbstractMemoryTool``, and
its ``betas`` do not include ``memory_20250818``).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# CAPABLE-tier stable alias — tracks the latest Sonnet minor, never retires
# (avoids pinning a dated snapshot that EOLs).
_DEFAULT_MODEL = "claude-sonnet-5"
# Required beta header for the memory_20250818 tool + context management.
_MEMORY_BETA = "context-management-2025-06-27"
_DEFAULT_MAX_TOKENS = 4096


def cmd_memory_agent(args: Any) -> int:
    """Run a single-shot agent with attune's Redis-backed Memory tool.

    Returns a process exit code: 0 success, 1 runtime failure, 2 usage
    / precondition error (missing prompt or API key).
    """
    prompt = getattr(args, "prompt", None)
    if not prompt:
        print('Error: a prompt is required:  attune memory-agent "<prompt>"')
        return 2

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "Error: attune memory-agent requires ANTHROPIC_API_KEY.\n"
            "The Anthropic Memory tool is a raw-API capability and is not "
            "available on the\nsubscription / agent-SDK path. Set the key, e.g.:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...   "
            "(or: source ~/.attune/anthropic.env)"
        )
        return 2

    try:
        import anthropic

        from attune.memory import make_memory_tool
    except ImportError as exc:
        print(f"Error: the anthropic SDK with Memory-tool support is required: {exc}")
        return 2

    root = getattr(args, "path", None) or "/memories"
    user_id = getattr(args, "user_id", None)
    model = getattr(args, "model", None) or _DEFAULT_MODEL
    max_tokens = getattr(args, "max_tokens", None) or _DEFAULT_MAX_TOKENS

    try:
        tool = make_memory_tool(root=root, user_id=user_id)
    except RuntimeError as exc:
        print(f"Error: could not build the memory tool: {exc}")
        return 1

    client = anthropic.Anthropic()
    tool_runner = getattr(getattr(client.beta, "messages", None), "tool_runner", None)
    if tool_runner is None:
        print(
            "Error: the installed anthropic SDK has no beta.messages.tool_runner; "
            "upgrade the `anthropic` package."
        )
        return 2

    try:
        runner = tool_runner(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            tools=[tool],
            betas=[_MEMORY_BETA],
        )
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: surface auth/API/transport errors to the user without
        # a traceback; the run never started so there is nothing to clean up.
        logger.exception("memory-agent: tool_runner construction failed")
        print(f"Error: agent run failed to start: {exc}")
        return 1

    return _drive(runner)


def _drive(runner: Any) -> int:
    """Iterate the tool runner, printing assistant text + memory operations.

    The ``BetaToolRunner`` auto-executes the attached memory tool between
    turns; each iteration yields the assistant message for that turn.
    """
    try:
        for message in runner:
            for block in getattr(message, "content", None) or []:
                btype = getattr(block, "type", None)
                if btype == "text":
                    print(getattr(block, "text", ""), end="", flush=True)
                elif btype == "tool_use" and getattr(block, "name", "") == "memory":
                    data = getattr(block, "input", None) or {}
                    cmd = data.get("command", "?")
                    path = data.get("path", "")
                    print(f"\n  · memory.{cmd} {path}".rstrip(), flush=True)
        print()
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: a mid-run API/tool error should report cleanly, not
        # crash the CLI with a traceback.
        logger.exception("memory-agent: run loop failed")
        print(f"\nError during agent run: {exc}")
        return 1
    return 0
