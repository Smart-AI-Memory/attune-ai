#!/usr/bin/env python3
"""SessionStart hook — surface recent cross-session findings at startup.

SessionStart has no query, so recall is recency-driven: the newest
stashed findings for the current project (cwd), via
``attune.memory.session_stash.recent_entries``. Emits a compact
``## Recalled memories`` block to stdout, which Claude Code splices into
the model's initial context.

Quiet by design: no backend, no findings, or the ``compact`` source all
produce no output. Bounded to a small char budget so it never crowds the
opening context. Never raises — a crash must not break the session.

Tunables (env): ``ATTUNE_MEMORY_RECALL`` (set ``0`` to disable),
``ATTUNE_MEMORY_RECALL_TOPK`` (default 5).

Each emission is logged to ``~/.attune/telemetry/memory_events.jsonl``
(size + entry count; see ``_memory_telemetry``) so the layer's token
cost is measured, not modeled.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

try:
    from _memory_telemetry import log_memory_event
except Exception:  # noqa: BLE001 — telemetry is optional, never load-bearing

    def log_memory_event(event: str, session_id: str | None = None, **fields: object) -> None:
        return


_DEFAULT_TOPK = 5
_CONTENT_BUDGET = 1_400  # ~350 tokens of finding text


def _enabled() -> bool:
    return os.environ.get("ATTUNE_MEMORY_RECALL", "1").strip() not in {"0", "false", "no"}


def _type_of(topics: object) -> str:
    """Pull the ``type:X`` marker out of a record's topics (default note)."""
    if isinstance(topics, list):
        for t in topics:
            if isinstance(t, str) and t.startswith("type:"):
                return t[len("type:") :] or "note"
    return "note"


def _format(entries: list[dict]) -> str:
    """Render the recalled findings as a compact markdown block."""
    lines = [
        "## Recalled memories",
        "",
        "Recent findings from this project (most recent first):",
        "",
    ]
    used = 0
    for e in entries:
        if not isinstance(e, dict):
            continue
        content = e.get("text") or e.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        content = content.strip()
        used += len(content)
        if used > _CONTENT_BUDGET:
            break
        lines.append(f"- [{_type_of(e.get('topics'))}] {content}")
    lines.append("")
    lines.append("_Pull more with `/recall <topic>`._")
    return "\n".join(lines)


def main() -> int:
    try:
        if not _enabled():
            return 0
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        source = (payload.get("source") or "startup").lower()
        if source == "compact":
            return 0  # post-compact context is handled elsewhere; don't pile on
        cwd = str(payload.get("cwd") or Path.cwd())

        try:
            from attune.memory.session_stash import recent_entries
        except Exception:  # noqa: BLE001 — attune not importable -> silent
            return 0

        try:
            topk = int(os.environ.get("ATTUNE_MEMORY_RECALL_TOPK", _DEFAULT_TOPK))
        except ValueError:
            topk = _DEFAULT_TOPK

        # Health line: a registered upgrade backend (e.g. Redis AMS) that is
        # unreachable means recall is silently degraded and findings stored
        # in that tier are dark. Surfacing this at session start is the fix
        # for the 2026-06-11 incident where AMS was down for a week unnoticed.
        health = ""
        try:
            from attune.memory.session_stash import backend_status

            status = backend_status()
            dark = status.get("unreachable_upgrade")
            if dark:
                health = (
                    f"⚠ cross-session recall degraded: memory backend '{dark}' is "
                    "unreachable — findings stored there are dark until it's back "
                    "(e.g. restart the Agent Memory Server)."
                )
        except Exception:  # noqa: BLE001 — health line is best-effort
            pass

        entries = recent_entries(top_k=topk, cwd=cwd)
        if not entries:
            if health:
                print(health)
            return 0
        block = _format(entries)
        # Only print if we actually rendered at least one finding line.
        rendered = sum(1 for line in block.splitlines() if line.startswith("- ["))
        if rendered:
            print(block)
            log_memory_event(
                "session_recall",
                session_id=payload.get("session_id"),
                entries=rendered,
                injected_chars=len(block),
            )
        if health:
            print(health)
        return 0
    except Exception:  # noqa: BLE001 — SessionStart hook must never crash a session
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
