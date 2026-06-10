#!/usr/bin/env python3
"""Stop-hook compact-warning — fires once per session at threshold.

Stop-hook payloads from Claude Code do NOT expose a context-
utilization field (verified 2026-05-09). We use a transcript-
size proxy via ``_transcript_size._estimate_utilization`` and
fire a single warning per session when utilization crosses
``ATTUNE_AI_COMPACT_WARNING_THRESHOLD`` (default 0.70).

The warning recommends finishing the current thought, exiting,
and pasting the resume prompt into a fresh session.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

# Force utf-8 on stdout and stderr. On Windows the default cp1252
# encoding can't emit emoji/em-dash and would crash this hook (caught
# by the outer try/except → silent breakage). errors='replace'
# substitutes '?' for any stray non-encodable byte.
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _resume_prompt import build_resume_prompt  # noqa: E402
from _state import (  # noqa: E402
    discover_specs,
    git_state,
    session_sentinel_path,
    workspace_roots,
)
from _transcript_size import estimate_utilization  # noqa: E402

_DEFAULT_THRESHOLD = 0.70


def _threshold() -> float:
    raw = os.environ.get("ATTUNE_AI_COMPACT_WARNING_THRESHOLD")
    if not raw:
        return _DEFAULT_THRESHOLD
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_THRESHOLD
    if value <= 0 or value >= 1:
        return _DEFAULT_THRESHOLD
    return value


def format_warning(util: float, threshold: float, resume_body: str) -> str:
    """Compose the user-facing warning + resume prompt."""
    util_pct = int(round(util * 100))
    threshold_pct = int(round(threshold * 100))
    return (
        f"\n⚠️  context at {util_pct}% (threshold {threshold_pct}%) — "
        "auto-compact fires near 85%\n\n"
        "Recommendation: finish your current thought, then exit. "
        "Open a fresh session and paste the prompt below to pick up "
        "cleanly:\n\n"
        f"{resume_body}\n"
    )


def main() -> int:
    """Entry point — never raises."""
    try:
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            return 0
        transcript_path = payload.get("transcript_path")
        if not transcript_path:
            return 0
        util = estimate_utilization(transcript_path)
        threshold = _threshold()
        if util < threshold:
            return 0
        sentinel = session_sentinel_path(payload.get("session_id"))
        if sentinel.exists():
            return 0  # already warned this session
        # Write the sentinel BEFORE the print so a re-fire mid-print
        # can't double-emit the warning.
        try:
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_text(f"{util:.4f}\n", encoding="utf-8")
        except OSError:
            # If we can't write the sentinel, skip the warning to
            # avoid spamming on every Stop event.
            return 0

        cwd = Path(payload.get("cwd") or Path.cwd())
        roots = workspace_roots(cwd=cwd)
        specs = discover_specs(roots)
        spec = specs[0] if specs else None
        git = git_state(cwd)
        resume_body = build_resume_prompt(spec, git)
        sys.stdout.write(format_warning(util, threshold, resume_body))
        return 0
    except Exception:  # noqa: BLE001 — hook must never crash a session
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    raise SystemExit(main())
