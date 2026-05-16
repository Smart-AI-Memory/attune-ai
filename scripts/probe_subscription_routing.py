#!/usr/bin/env python3
"""Phase 0 probe for the sibling-subscription-auth spec.

Probes how `claude_agent_sdk` authenticates across three contexts:

1. **In-shell, no env key**: Run from a plain terminal with no
   ``ANTHROPIC_API_KEY``. Does the SDK find any auth context on
   its own (e.g., from `~/.claude/`)?
2. **In-shell, with env key**: Same shell, env key set. Confirms
   the API-key fallback path works.
3. **Subprocess of a Claude Code session, no env key**: Spawned
   from inside Claude Code. Does session auth inherit?

This script also surveys the local environment for signals that
advertise Claude Code's presence: env vars, config files, and
running processes.

Writes a JSON-shaped report to stdout so the caller can pipe
into `tee findings.md` or jq.

Usage::

    python scripts/probe_subscription_routing.py
    python scripts/probe_subscription_routing.py --probe minimal

The script makes ONE tiny LLM call when probing — a "say hi"
prompt with 8-token max. Cost is negligible (~$0.00001 on
Haiku); designed so the probe can run repeatedly during
investigation without spend concerns.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Environment-variable names commonly set by Claude Code / Anthropic SDKs.
# Presence is informational only; we don't decide routing from this.
_ENV_VARS_OF_INTEREST = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_SESSION_ID",
    "CLAUDECODE",
    "CLAUDE_CODE",
    "VSCODE_PID",
)


# Filesystem paths commonly used by Claude Code for auth/state.
_PATHS_OF_INTEREST = (
    "~/.claude",
    "~/.claude/auth.json",
    "~/.claude/credentials.json",
    "~/.claude/projects",
    "~/.anthropic",
)


def _env_snapshot() -> dict[str, str]:
    """Return a dict of relevant env vars (values redacted by default)."""
    snapshot: dict[str, str] = {}
    for name in _ENV_VARS_OF_INTEREST:
        value = os.environ.get(name)
        if value is None:
            continue
        if "KEY" in name or "TOKEN" in name:
            snapshot[name] = "<redacted, len=%d>" % len(value)
        else:
            snapshot[name] = value
    return snapshot


def _path_snapshot() -> dict[str, dict[str, Any]]:
    """Check which interest paths exist and their type."""
    snapshot: dict[str, dict[str, Any]] = {}
    for raw in _PATHS_OF_INTEREST:
        path = Path(os.path.expanduser(raw))
        if not path.exists():
            continue
        snapshot[raw] = {
            "exists": True,
            "type": "dir" if path.is_dir() else "file",
            "size_bytes": path.stat().st_size if path.is_file() else None,
        }
    return snapshot


def _claude_code_tooling() -> dict[str, Any]:
    """Check whether `claude` CLI is on PATH; capture version."""
    out: dict[str, Any] = {}
    claude_path = shutil.which("claude")
    out["on_path"] = bool(claude_path)
    if not claude_path:
        return out
    out["path"] = claude_path
    try:
        result = subprocess.run(
            [claude_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        out["version_stdout"] = result.stdout.strip()[:200]
        out["returncode"] = result.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        out["error"] = str(exc)[:200]
    return out


def _agent_sdk_signature() -> dict[str, Any]:
    """Inspect claude_agent_sdk's public surface without calling it."""
    out: dict[str, Any] = {"importable": False}
    try:
        import claude_agent_sdk  # type: ignore[import-not-found]
    except ImportError as exc:
        out["import_error"] = str(exc)[:200]
        return out
    out["importable"] = True
    out["version"] = getattr(claude_agent_sdk, "__version__", "unknown")
    out["module_file"] = getattr(claude_agent_sdk, "__file__", "unknown")
    out["has_query"] = hasattr(claude_agent_sdk, "query")
    return out


def _anthropic_sdk_signature() -> dict[str, Any]:
    """Same, for the vanilla `anthropic` Python SDK."""
    out: dict[str, Any] = {"importable": False}
    try:
        import anthropic
    except ImportError as exc:
        out["import_error"] = str(exc)[:200]
        return out
    out["importable"] = True
    out["version"] = getattr(anthropic, "__version__", "unknown")
    out["has_async_client"] = hasattr(anthropic, "AsyncAnthropic")
    return out


async def _probe_agent_sdk_call() -> dict[str, Any]:
    """Tiny `claude_agent_sdk.query()` call.

    Returns shape:
        {"attempted": bool, "ok": bool, "error": str | None,
         "response_text": str | None}
    """
    out: dict[str, Any] = {"attempted": False}
    try:
        import claude_agent_sdk  # type: ignore[import-not-found]
    except ImportError:
        out["error"] = "claude_agent_sdk not installed"
        return out

    out["attempted"] = True

    query_fn = getattr(claude_agent_sdk, "query", None)
    if query_fn is None:
        out["ok"] = False
        out["error"] = "claude_agent_sdk.query not exposed"
        return out

    options = None
    try:
        from claude_agent_sdk import ClaudeAgentOptions  # type: ignore[import-not-found]

        options = ClaudeAgentOptions(max_turns=1)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: options is optional; missing class is informational.
        out["options_error"] = str(exc)[:200]

    response_text: list[str] = []
    try:
        kwargs: dict[str, Any] = {"prompt": "say hi"}
        if options is not None:
            kwargs["options"] = options
        async for message in query_fn(**kwargs):
            for block in getattr(message, "content", []) or []:
                text = getattr(block, "text", None)
                if text:
                    response_text.append(text)
            if len("".join(response_text)) > 80:
                break
        out["ok"] = True
        out["response_text"] = "".join(response_text)[:200]
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: probe — surface every failure mode in the report.
        out["ok"] = False
        out["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    return out


async def _probe_anthropic_sdk_call() -> dict[str, Any]:
    """Tiny direct-SDK call. Requires ANTHROPIC_API_KEY."""
    out: dict[str, Any] = {"attempted": False}
    if not os.environ.get("ANTHROPIC_API_KEY"):
        out["error"] = "ANTHROPIC_API_KEY not set"
        return out
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        out["error"] = "anthropic SDK not installed"
        return out

    out["attempted"] = True
    try:
        client = AsyncAnthropic(timeout=10.0)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8,
            messages=[{"role": "user", "content": "say hi"}],
        )
        text_parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                text_parts.append(text)
        out["ok"] = True
        out["response_text"] = "".join(text_parts)[:200]
        out["stop_reason"] = response.stop_reason
    except Exception as exc:  # noqa: BLE001
        out["ok"] = False
        out["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    return out


def _build_report(args: argparse.Namespace) -> dict[str, Any]:
    """Synchronously collect everything except the async LLM probes."""
    import asyncio

    report: dict[str, Any] = {
        "schema_version": 1,
        "platform": {
            "system": platform.system(),
            "python": sys.version.split()[0],
        },
        "cwd": str(Path.cwd()),
        "env": _env_snapshot(),
        "paths": _path_snapshot(),
        "claude_cli": _claude_code_tooling(),
        "agent_sdk": _agent_sdk_signature(),
        "anthropic_sdk": _anthropic_sdk_signature(),
    }

    if args.probe == "minimal":
        report["llm_calls"] = {"skipped": True, "reason": "--probe minimal"}
        return report

    report["llm_calls"] = {
        "agent_sdk_query": asyncio.run(_probe_agent_sdk_call()),
        "anthropic_sdk_messages": asyncio.run(_probe_anthropic_sdk_call()),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe",
        choices=("full", "minimal"),
        default="full",
        help="full: also makes 2 tiny LLM calls (~$0.00002 total). "
        "minimal: skips the live calls; signature-only.",
    )
    args = parser.parse_args()

    report = _build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
