#!/usr/bin/env python
"""SessionStart hook — surface the anonymous-usage consent ask once.

The CLI consent prompt (``usage_ping.maybe_prompt_consent``) fires only
from ``cli_minimal.main()`` in an interactive terminal. Plugin / MCP
users — the dominant channel — never hit that path, yet their workflows
still write local ``usage.jsonl`` records. So they generate the data but
are never offered the choice to share it (the exact gap D11 closed for
the CLI; see ``docs/specs/usage-signals/decisions.md`` D11/D12).

Hooks run as piped subprocesses with no TTY, so this hook CANNOT prompt
interactively. Instead it emits a short ``## Anonymous usage sharing``
block to stdout (which Claude Code splices into the model's context)
asking Claude to put the choice to the user via ``AskUserQuestion`` — the
Socratic surface D9 always intended. The user's answer is persisted by
the existing ``attune telemetry enable`` / ``disable`` commands.

Quiet by design — emits nothing when:

- the user has already chosen (``telemetry.usage_ping_consented`` True),
- ``DO_NOT_TRACK`` or ``ATTUNE_USAGE_PING`` is set (an explicit signal),
- the notice has already been shown ``_MAX_SHOWS`` times (anti-nag cap),
- ``ATTUNE_CONSENT_NOTICE`` is ``0``/``false``/``no`` (hook opt-out), or
- the SessionStart source is ``compact``.

Never raises — a crash here must not break the session.

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

#: User config (opt-in state lives here, never a project-local config).
CONFIG_PATH = Path("~/.attune/config.json").expanduser()

#: Tracks how many times the notice has been surfaced, so an ignored ask
#: stops nagging after a few sessions instead of every session forever.
COUNT_PATH = Path("~/.attune/telemetry/.consent_notice_count").expanduser()

#: Stop surfacing the notice after this many sessions without a choice.
_MAX_SHOWS = 3

_FALSEY = {"", "0", "false", "no"}

_NOTICE = """\
## Anonymous usage sharing (one-time setup)

attune-ai can share **anonymous** usage to help improve it — only which
workflows you run, plus the package version, your OS, and Python version.
Never code, paths, prompts, filenames, or any personal data. It ships
**OFF** and you have not chosen yet.

ACTION FOR CLAUDE: At a natural break in this session, ask the user once
via `AskUserQuestion` whether to enable anonymous usage sharing
(recommend "No" as the safe default). Then persist their choice by
running exactly one of:

- Yes → `attune telemetry enable`
- No  → `attune telemetry disable`

Either command records the choice so this notice stops appearing. The
user can also run `attune telemetry status` to audit the exact payload
before deciding. Do not enable anything without an explicit "yes"."""


def _enabled() -> bool:
    """False when the hook is explicitly disabled via env."""
    return os.environ.get("ATTUNE_CONSENT_NOTICE", "1").strip().lower() not in _FALSEY


def _env_opt_out() -> bool:
    """True when an env signal already settles consent — never ask over it."""
    dnt = os.environ.get("DO_NOT_TRACK")
    if dnt is not None and dnt.strip().lower() not in _FALSEY:
        return True
    return os.environ.get("ATTUNE_USAGE_PING") is not None


def _already_consented() -> bool:
    """True when the user has recorded a choice (opt-in OR opt-out).

    A missing/unreadable config means no choice yet → eligible to ask.
    """
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    tele = data.get("telemetry") if isinstance(data, dict) else None
    return bool(isinstance(tele, dict) and tele.get("usage_ping_consented"))


def _show_count() -> int:
    """How many times the notice has been surfaced (0 if unknown)."""
    try:
        return int(COUNT_PATH.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return 0


def _bump_count(current: int) -> None:
    """Persist the incremented show count (best-effort)."""
    try:
        COUNT_PATH.parent.mkdir(parents=True, exist_ok=True)
        COUNT_PATH.write_text(str(current + 1), encoding="utf-8")
    except OSError:
        pass  # anti-nag is best-effort; a missed bump just shows once more


def main() -> int:
    try:
        if not _enabled() or _env_opt_out():
            return 0

        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        if str(payload.get("source") or "startup").lower() == "compact":
            return 0  # don't pile onto post-compact context

        if _already_consented():
            return 0

        count = _show_count()
        if count >= _MAX_SHOWS:
            return 0

        print(_NOTICE)
        _bump_count(count)
        return 0
    except Exception:  # noqa: BLE001 — SessionStart hook must never crash a session
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
