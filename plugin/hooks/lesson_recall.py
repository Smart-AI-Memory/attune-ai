#!/usr/bin/env python
"""UserPromptSubmit lesson recall — surface matching lessons with the
prompt that needs them.

The lessons corpus (``attune.lessons``) holds hundreds of trap-moment
lessons; this hook retrieves the top few that score against the user's
prompt and injects their titles + truncated bodies as
``additionalContext`` (lessons-corpus-rag design D5 surface 2).

Noise controls (all from the design):

- Score floor (``ATTUNE_LESSON_RECALL_FLOOR``, default 8.0) — most
  prompts inject nothing.
- Minimum prompt length (short acks like ``y`` / ``go`` never query).
- Slash-command prompts are skipped (``/recall`` IS the manual surface).
- Surface-once per ``(session, lesson)`` sentinel.
- ``ATTUNE_LESSON_RECALL=0`` off-switch; fail-safe exit 0 always.

Test/ops knob: ``ATTUNE_LESSONS_FILE`` pins the corpus file (default:
walk up from the payload cwd via ``attune.lessons.find_lessons_file``).

Each fire is logged to ``~/.attune/telemetry/memory_events.jsonl``
(lesson ids, scores, injected size, a ``surfacing_id`` join key; see
``_memory_telemetry``) so a later verdict pass can label each
surfacing acted-on / ignored / wrong (memory-recall-eval spec).

Exit 0 always — a crash, missing attune install, or missing corpus
degrades to silent no-op.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
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
    from _state import _sentinel_dir, resolve_session_key  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001 — hook must never crash a prompt
    _sentinel_dir = None  # type: ignore[assignment]
    resolve_session_key = None  # type: ignore[assignment]

try:
    from _memory_telemetry import log_memory_event
except Exception:  # noqa: BLE001 — telemetry is optional, never load-bearing

    def log_memory_event(event: str, session_id: str | None = None, **fields: object) -> None:
        return


_SENTINEL_PREFIX = ".lesson-recalled-"
_SENTINEL_TTL_SECONDS = 7 * 24 * 3600  # match the jit-recall TTL
_MIN_PROMPT_CHARS = 20
_BODY_EXCERPT_CHARS = 400
_TOP_K = 3


def _enabled() -> bool:
    return os.environ.get("ATTUNE_LESSON_RECALL", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _floor() -> float:
    try:
        return float(os.environ.get("ATTUNE_LESSON_RECALL_FLOOR", "8.0"))
    except ValueError:
        return 8.0


def _safe(fragment: str | None, fallback: str) -> str:
    if not fragment:
        return fallback
    return re.sub(r"[^A-Za-z0-9_-]", "_", fragment)[:64] or fallback


def _sentinel_path(session_key: str | None, lesson_id: str) -> Path | None:
    # No session identity -> no sentinel: fail OPEN (surface again)
    # rather than share an "unknown" bucket across sessions, where the
    # first fire suppresses the lesson machine-wide for the TTL.
    if _sentinel_dir is None or not session_key:
        return None
    name = f"{_SENTINEL_PREFIX}{_safe(session_key, 'unknown')}-{_safe(lesson_id, 'lesson')}"
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


def _lessons_index(cwd: str | None):
    """Build a LessonsIndex, honoring the ATTUNE_LESSONS_FILE override."""
    from attune.lessons import LessonsIndex, find_lessons_file

    override = os.environ.get("ATTUNE_LESSONS_FILE")
    if override:
        return LessonsIndex(override)
    start = Path(cwd) if cwd else None
    return LessonsIndex(find_lessons_file(start))


def main() -> int:
    """Surface top-scoring lessons for this prompt, once per session each."""
    try:
        if not _enabled():
            return 0
        payload = json.load(sys.stdin)
        prompt = str(payload.get("prompt") or "").strip()
        if len(prompt) < _MIN_PROMPT_CHARS or prompt.startswith("/"):
            return 0

        index = _lessons_index(payload.get("cwd"))
        floor = _floor()
        hits = [h for h in index.retrieve(prompt, k=_TOP_K) if h.score >= floor]
        if not hits:
            return 0

        session_key = (
            resolve_session_key(payload)
            if resolve_session_key is not None
            else payload.get("session_id")
        )
        fresh = []
        for hit in hits:
            lesson_id = Path(hit.entry.metadata.get("parent_path", hit.entry.path)).stem
            sentinel = _sentinel_path(session_key, lesson_id)
            if sentinel is not None and sentinel.exists():
                continue
            fresh.append((hit, lesson_id))
        if not fresh:
            return 0

        lines = ["Lessons that may apply to this prompt:"]
        for hit, _lesson_id in fresh:
            body = " ".join(hit.entry.content.split())
            # The doc body opens with its own "- **title**:" line —
            # drop it so the excerpt doesn't repeat the summary.
            body = re.sub(r"^- \*\*.+?\*\*[ :—-]*", "", body)
            if len(body) > _BODY_EXCERPT_CHARS:
                body = body[:_BODY_EXCERPT_CHARS] + "…"
            lines.append(f"- **{hit.entry.summary}**: {body}")
        context = "\n".join(lines)
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": context,
                    }
                }
            )
        )
        sys.stdout.flush()

        # Telemetry: which lessons surfaced, at what score, and how much
        # context they cost. The surfacing_id is the join key a later
        # verdict pass (acted-on / ignored / wrong) references — without
        # this record, prompt-time recall is invisible to the noise
        # denominator (memory-recall-eval spec, 2026-07-14).
        log_memory_event(
            "lesson_recall",
            session_id=session_key,
            surfacing_id=uuid.uuid4().hex[:12],
            lessons=[lesson_id for _hit, lesson_id in fresh],
            scores=[round(hit.score, 1) for hit, _lesson_id in fresh],
            injected_chars=len(context),
        )

        # Sentinels AFTER the emit so a mid-work crash retries next fire.
        for _hit, lesson_id in fresh:
            sentinel = _sentinel_path(session_key, lesson_id)
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
        # INTENTIONAL: lesson recall is best-effort guidance; never block
        # or break the prompt (missing attune install, missing corpus,
        # malformed payload all land here).
        return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
