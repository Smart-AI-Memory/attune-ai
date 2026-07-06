#!/usr/bin/env python3
"""PreToolUse just-in-time recall — surface the governing rule at the
decision point.

Cross-session memory recalls findings at the session DOOR; this hook
recalls durable RULES at the moment of the action they govern (the
*not-applying* failure mode — the rule existed, stored twice, and still
slipped mid-session; see docs/specs/just-in-time-recall/).

Flow (all best-effort, never blocks a tool call):

1. Read the PreToolUse payload; look the tool name up in the curated
   ``_recall_map.RECALL_MAP``. No entry -> silent no-op (R3).
2. Surface-once gate: a per-``(session, rule)`` sentinel so a repeated
   action in one session isn't nagged repeatedly (decision D5).
3. Emit the rule one-liner(s) as PreToolUse ``additionalContext``
   (verified channel, decision D2 — empirically smoke-tested
   2026-06-09: the injected text reaches the model while the call
   proceeds). The sentinel is written AFTER the emit so a crash
   retries on the next fire.

Tunables (env): ``ATTUNE_JIT_RECALL`` (set ``0`` to disable),
``ATTUNE_AI_SENTINEL_DIR`` (sentinel dir override, for tests).

Each fire is logged to ``~/.attune/telemetry/memory_events.jsonl``
(tool, rule ids, injected size; see ``_memory_telemetry``) so fire
rate and context cost are measurable per session.

Exit 0 always — a crash or missing corpus degrades to silent no-op (R4).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# Force utf-8 on stdout/stderr (Windows cp1252 would crash on em-dash,
# caught by the outer try/except -> silent breakage).
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

try:
    from _recall_map import RECALL_MAP
    from _state import _sentinel_dir  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001 — hook must never crash a tool call
    RECALL_MAP = {}  # type: ignore[assignment]
    _sentinel_dir = None  # type: ignore[assignment]

try:
    from _memory_telemetry import log_memory_event
except Exception:  # noqa: BLE001 — telemetry is optional, never load-bearing

    def log_memory_event(event: str, session_id: str | None = None, **fields: object) -> None:
        return


_SENTINEL_PREFIX = ".jit-recalled-"
_SENTINEL_TTL_SECONDS = 7 * 24 * 3600  # match _state's compact-warned TTL
_LESSON_EXCERPT_CHARS = 600  # keep the injected context bounded


def _resolve_lesson(ref: str) -> str | None:
    """Resolve a lessons-corpus slug to ``title: excerpt`` at fire time.

    Best-effort by design: returns None when ``attune.lessons`` is
    unavailable (older install, stale main checkout) or the slug no
    longer exists — the caller falls back to the inline one-liner.
    """
    try:
        from attune.lessons import LessonsIndex

        entry = LessonsIndex().get(ref)
        if entry is None or not entry.content:
            return None
        body = " ".join(entry.content.split())
        if len(body) > _LESSON_EXCERPT_CHARS:
            body = body[:_LESSON_EXCERPT_CHARS].rstrip() + "…"
        title = (entry.summary or "").strip()
        return f"{title}: {body}" if title else body
    except Exception:  # noqa: BLE001
        # INTENTIONAL: lesson enrichment is optional; the inline
        # one-liner still surfaces (R4: never block the tool call).
        return None


def _enabled() -> bool:
    return os.environ.get("ATTUNE_JIT_RECALL", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _safe(fragment: str | None, fallback: str) -> str:
    if not fragment:
        return fallback
    return re.sub(r"[^A-Za-z0-9_-]", "_", fragment)[:64] or fallback


def _sentinel_path(session_id: str | None, rule_id: str) -> Path | None:
    if _sentinel_dir is None:
        return None
    name = f"{_SENTINEL_PREFIX}{_safe(session_id, 'unknown')}-{_safe(rule_id, 'rule')}"
    return _sentinel_dir() / name


def _prune_stale(now: float | None = None) -> None:
    """Best-effort TTL prune of this hook's own sentinels."""
    if _sentinel_dir is None:
        return
    base = _sentinel_dir()
    if not base.is_dir():
        return
    cutoff = (now if now is not None else time.time()) - _SENTINEL_TTL_SECONDS
    try:
        entries = list(base.iterdir())
    except OSError:
        return
    for entry in entries:
        if not entry.name.startswith(_SENTINEL_PREFIX):
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
        except OSError:
            continue


def main() -> int:
    """Entry point — surface matching rules once per session, never raise."""
    try:
        if not _enabled():
            return 0
        payload = json.load(sys.stdin)
        tool_name = str(payload.get("tool_name") or "")
        rules = RECALL_MAP.get(tool_name) or []
        if not rules:
            return 0

        session_id = payload.get("session_id")
        tool_input = payload.get("tool_input") or {}
        tool_input_text = json.dumps(tool_input)
        # Raw (un-JSON-escaped) string fields, for regex shapes that
        # contain backslashes — `\<` becomes `\\<` in the JSON dump.
        raw_input_text = " ".join(v for v in tool_input.values() if isinstance(v, str))
        fresh = []
        for rule in rules:
            # Optional content filters (e.g. a Bash rule scoped to one
            # command shape) — without one a Bash-keyed rule would fire
            # on the first bash call of every session (R3: low noise).
            needle = rule.get("match_substring")
            if needle and needle not in tool_input_text:
                continue
            pattern = rule.get("match_regex")
            if pattern:
                try:
                    if not re.search(pattern, raw_input_text):
                        continue
                except re.error:
                    continue  # bad pattern never blocks the call (R4)
            sentinel = _sentinel_path(session_id, rule["rule_id"])
            if sentinel is not None and sentinel.exists():
                continue
            fresh.append(rule)
        if not fresh:
            return 0

        lines = [f"Just-in-time recall — rule(s) governing {tool_name}:"]
        for rule in fresh:
            lines.append(f"- {rule['text']}")
            ref = rule.get("lesson_ref")
            if ref:
                resolved = _resolve_lesson(ref)
                if resolved:
                    lines.append(f"  Full lesson — {resolved}")
        context = "\n".join(lines)
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": context,
                    }
                }
            )
        )
        sys.stdout.flush()

        # Telemetry: which rules surfaced, for which tool, and how much
        # context they cost — the (tool, rules, ts) triple also lets a
        # later analysis estimate prevented-failure rate by checking
        # whether the matching failure still occurred after the fire.
        log_memory_event(
            "jit_recall",
            session_id=session_id,
            tool=tool_name,
            rules=[rule["rule_id"] for rule in fresh],
            injected_chars=len(context),
        )

        # Sentinels AFTER the emit so a mid-work crash retries next fire.
        for rule in fresh:
            sentinel = _sentinel_path(session_id, rule["rule_id"])
            if sentinel is None:
                continue
            try:
                sentinel.parent.mkdir(parents=True, exist_ok=True)
                sentinel.write_text("", encoding="utf-8")
            except OSError:
                continue
        _prune_stale()
        return 0
    except Exception:  # noqa: BLE001
        # INTENTIONAL: recall is best-effort guidance; never block or
        # break the governed tool call (R4).
        return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
