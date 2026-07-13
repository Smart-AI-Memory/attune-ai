"""Detect SDK-spawned subprocess sessions so hooks can self-gate.

sdk-subprocess-isolation spec (R1/R2, decision D1: gate everything):
an SDK-spawned ``claude`` subprocess is not an interactive session —
no attune hook applies there, and SessionStart hook stdout poisons
the SDK's stream-json channel (the failure that broke every SDK
workflow for subscription users). Every hook script calls
:func:`exit_if_sdk_subprocess` as its first ``__main__`` statement.

Two detection signals (spec D3):

- ``ATTUNE_SDK_SUBPROCESS=1`` — attune's explicit marker, set by
  ``agent_sdk_adapter.sdk_isolation_kwargs()`` (Phase 2).
- ``CLAUDE_CODE_ENTRYPOINT`` starting with ``sdk-`` — stamped by the
  Agent SDK itself into every subprocess env, so the gate also covers
  third-party SDK scripts that never touch attune's adapter.
  Interactive sessions carry other values (``claude-desktop``, etc.).

Twin copy: ``plugin/hooks/_sdk_gate.py`` (shipped plugin hooks).
Keep both in sync — each is imported from its own script dir.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os
import sys


def is_sdk_subprocess() -> bool:
    """True when running inside an SDK-spawned ``claude`` subprocess.

    ``ATTUNE_SDK_GATE_OVERRIDE=1`` force-disables the gate: headless
    ``claude -p`` stamps ``CLAUDE_CODE_ENTRYPOINT=sdk-cli`` into EVERY
    such session (verified live 2026-07-13 on 2.1.144), so the gate
    silences all attune hooks in headless mode even for deliberate
    consumers. The trap-battery benchmark (which parses stream-json
    defensively and NEEDS the recall hooks live) sets the override for
    its child sessions; nothing else should.
    """
    if os.environ.get("ATTUNE_SDK_GATE_OVERRIDE") == "1":
        return False
    if os.environ.get("ATTUNE_SDK_SUBPROCESS") == "1":
        return True
    return os.environ.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("sdk-")


def exit_if_sdk_subprocess() -> None:
    """Exit 0 with no output when inside an SDK subprocess session."""
    if is_sdk_subprocess():
        sys.exit(0)
