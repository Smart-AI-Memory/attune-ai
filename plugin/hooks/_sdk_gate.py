"""Detect SDK-spawned subprocess sessions so hooks can self-gate.

sdk-subprocess-isolation spec (R1/R2, decision D1: gate everything):
an SDK-spawned ``claude`` subprocess is not an interactive session —
no attune hook applies there, and SessionStart hook stdout poisons
the SDK's stream-json channel (the failure that broke every SDK
workflow for subscription users). Every hook script calls
:func:`exit_if_sdk_subprocess` as its first ``__main__`` statement.

Two detection signals (spec D3, amended by D9):

- ``ATTUNE_SDK_SUBPROCESS=1`` — attune's explicit marker, set by
  ``agent_sdk_adapter.sdk_isolation_kwargs()`` (Phase 2).
- ``CLAUDE_CODE_ENTRYPOINT`` starting with ``sdk-`` — stamped by the
  Agent SDK itself into every subprocess env (``sdk-py``/``sdk-ts``),
  so the gate also covers third-party SDK scripts that never touch
  attune's adapter. Interactive sessions carry other values
  (``claude-desktop``, etc.).

EXCEPT ``sdk-cli`` (spec D9): current Claude Code stamps
``CLAUDE_CODE_ENTRYPOINT=sdk-cli`` into EVERY plain headless
``claude -p`` session (verified live 2026-07-13 on 2.1.144), which is
not an SDK subprocess — its hooks must work. Gating on the bare
``sdk-`` prefix silenced every attune hook for all headless users
(trap-battery decisions, 2026-07-13 "SDK-gate discovery").

``ATTUNE_SDK_GATE_OVERRIDE=1`` force-disables the gate entirely —
a benchmark-only escape hatch for harnesses that drive sessions
through the SDK but parse stream-json defensively and need the
hooks live. Nothing else should set it.

Twin copy: ``src/attune/hooks/scripts/_sdk_gate.py`` (repo-level
hooks). Keep both in sync — each is imported from its own script dir.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os
import sys


def is_sdk_subprocess() -> bool:
    """True when running inside an SDK-spawned ``claude`` subprocess.

    ``sdk-cli`` is exempt: it marks plain headless ``claude -p``, not
    an SDK subprocess (spec D9). Unknown future ``sdk-*`` values stay
    gated — over-gating is a silent hook, under-gating poisons the
    SDK stream-json channel.
    """
    if os.environ.get("ATTUNE_SDK_GATE_OVERRIDE") == "1":
        return False
    if os.environ.get("ATTUNE_SDK_SUBPROCESS") == "1":
        return True
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")
    return entrypoint.startswith("sdk-") and entrypoint != "sdk-cli"


def exit_if_sdk_subprocess() -> None:
    """Exit 0 with no output when inside an SDK subprocess session."""
    if is_sdk_subprocess():
        sys.exit(0)
