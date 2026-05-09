"""Transcript-size proxy for context utilization.

Stop-hook payloads from Claude Code do NOT expose a context-
utilization or token-count field (verified 2026-05-09). The
transcript JSONL on disk grows monotonically as the session
accumulates turns, so we use it as a crude-but-monotonic proxy:

    chars   = sum of user/assistant message-body characters
    tokens  ≈ chars / chars-per-token
    util    = tokens / context window

The absolute number can drift ±10–15% from real utilization;
that's fine. The hook needs a single threshold-crossing event
to fire the compact warning, not exact accounting.

Both factors are tunable via env vars so V4 calibration (after
observing real sessions) can adjust without a code change.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Defaults — V4 calibration may revise these.
_DEFAULT_CHARS_PER_TOKEN = 4.0
_DEFAULT_CONTEXT_WINDOW_TOKENS = 200_000  # Sonnet 4.6 / Opus 4.7 window


def _chars_per_token() -> float:
    raw = os.environ.get("ATTUNE_AI_CHARS_PER_TOKEN")
    if not raw:
        return _DEFAULT_CHARS_PER_TOKEN
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_CHARS_PER_TOKEN
    return value if value > 0 else _DEFAULT_CHARS_PER_TOKEN


def _context_window_tokens() -> int:
    raw = os.environ.get("ATTUNE_AI_CONTEXT_WINDOW_TOKENS")
    if not raw:
        return _DEFAULT_CONTEXT_WINDOW_TOKENS
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_CONTEXT_WINDOW_TOKENS
    return value if value > 0 else _DEFAULT_CONTEXT_WINDOW_TOKENS


def _content_chars(content: object) -> int:
    """Recursively count characters in a transcript message body.

    Anthropic transcripts can encode message ``content`` as a
    plain string OR a list of typed parts (text, tool_use,
    tool_result, image, …). Walk the structure and sum the
    string-valued ``text`` / ``content`` fields. Anything else
    (binary blobs, image refs) is ignored — those don't drive
    context-window pressure proportionally.
    """
    if content is None:
        return 0
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(_content_chars(part) for part in content)
    if isinstance(content, dict):
        total = 0
        text = content.get("text")
        if isinstance(text, str):
            total += len(text)
        nested = content.get("content")
        if nested is not None and not isinstance(nested, str):
            total += _content_chars(nested)
        elif isinstance(nested, str):
            total += len(nested)
        return total
    return 0


def _sum_message_chars(transcript_path: Path) -> int:
    """Sum content characters across user/assistant turns in the JSONL.

    Tolerates malformed lines and missing files: returns whatever
    has been counted so far. Never raises.
    """
    if not transcript_path.is_file():
        return 0
    total = 0
    try:
        with transcript_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # Claude Code transcript records vary in shape;
                # handle both the legacy ``{type, message}`` and
                # newer flat ``{role, content}`` envelopes.
                message = record.get("message") if isinstance(record, dict) else None
                if isinstance(message, dict):
                    total += _content_chars(message.get("content"))
                elif isinstance(record, dict):
                    role = record.get("role") or record.get("type")
                    if role in {"user", "assistant", "human"}:
                        total += _content_chars(record.get("content"))
    except OSError:
        return total
    return total


def estimate_utilization(transcript_path: str | Path) -> float:
    """Return estimated context utilization in ``[0.0, 1.0]``.

    Args:
        transcript_path: Path to the session transcript JSONL.
            Missing or unreadable transcripts return ``0.0``.

    Returns:
        Utilization fraction. Clamped to ``[0.0, 1.0]``.
    """
    if not transcript_path:
        return 0.0
    path = Path(transcript_path)
    chars = _sum_message_chars(path)
    if chars <= 0:
        return 0.0
    est_tokens = chars / _chars_per_token()
    util = est_tokens / _context_window_tokens()
    if util < 0.0:
        return 0.0
    if util > 1.0:
        return 1.0
    return util
