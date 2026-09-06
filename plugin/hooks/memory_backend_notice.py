#!/usr/bin/env python3
"""SessionStart hook — surface the memory-backend choice once (redis-config-truth D5).

Redis stays bundled and zero-config: a plain install runs on the local file
tier and upgrades to the Redis Agent Memory Server automatically when one
is reachable. Until the user records a preference, this notice explains
what Redis is FOR here and asks the assistant to collect the choice once at
a natural break; the answer is recorded with ``attune memory use``.

Mirrors ``usage_consent_notice.py``: shows at most ``_MAX_SHOWS`` times, never
on the post-compact SessionStart, never when a preference exists, silenced by
``ATTUNE_MEMORY_NOTICE=0``, and never crashes the session.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

_FALSEY = {"", "0", "false", "no", "off"}
_VALUES = ("auto", "file", "redis")
_MAX_SHOWS = 3

_NOTICE = """\
## Memory backend (one-time choice)

attune-ai memory is running on the **local file tier** — zero-config,
nothing to set up. Redis is optional. Redis's role in attune-ai is to
provide **enhanced memory features using Redis's open-source options**:
semantic recall across sessions through the Agent Memory Server.

Choices (recorded in `~/.attune/config.json`, change any time):
- `auto`  — a reachable Agent Memory Server wins, otherwise the file tier (default)
- `file`  — the local tier only; the upgrade is never probed or warned about
- `redis` — prefer the Agent Memory Server; degrade to files when unreachable, loudly

ACTION FOR CLAUDE: At a natural break in this session, ask the user ONCE
which memory backend they want (a decision card: auto / file / redis, with
`auto` recommended for a plain install and `redis` when they run an Agent
Memory Server). Then run `attune memory use <choice>`. Do not ask again
this session; `attune memory status` shows the live state. Silence this
notice with ATTUNE_MEMORY_NOTICE=0.
"""


def _attune_home() -> Path:
    home = os.environ.get("ATTUNE_HOME")
    return Path(home).expanduser() if home else Path("~/.attune").expanduser()


def _config_path() -> Path:
    return _attune_home() / "config.json"


def _count_path() -> Path:
    return _attune_home() / "telemetry" / ".memory_notice_count"


def _enabled() -> bool:
    return os.environ.get("ATTUNE_MEMORY_NOTICE", "1").strip().lower() not in _FALSEY


def _preference_recorded() -> bool:
    """True when the user (or the env override) already chose a backend."""
    if os.environ.get("ATTUNE_MEMORY_BACKEND", "").strip().lower() in _VALUES:
        return True
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    memory = data.get("memory") if isinstance(data, dict) else None
    return bool(isinstance(memory, dict) and memory.get("backend") in _VALUES)


def _show_count() -> int:
    try:
        return int(_count_path().read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return 0


def _bump_count(current: int) -> None:
    try:
        path = _count_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(current + 1), encoding="utf-8")
    except OSError:
        pass  # anti-nag is best-effort; a missed bump just shows once more


def main() -> int:
    try:
        if not _enabled():
            return 0
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        if str(payload.get("source") or "startup").lower() == "compact":
            return 0  # don't pile onto post-compact context
        if _preference_recorded():
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
