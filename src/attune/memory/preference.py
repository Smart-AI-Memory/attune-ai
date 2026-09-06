"""User preference for the memory backend (redis-config-truth D5).

Redis stays bundled and zero-config: a plain install runs on the local
file tier and upgrades to the Redis Agent Memory Server automatically when
one is reachable. This module records the user's stated choice so the
resolver can honor it and the first-run notice can stop asking:

- ``auto``  — today's behavior: a reachable upgrade wins, else the file tier.
- ``file``  — the local tier only; the upgrade is never probed, never warned.
- ``redis`` — prefer the Agent Memory Server; degrade to files when it is
  unreachable, but say so loudly.

The preference lives in the user config (``~/.attune/config.json``, or
``$ATTUNE_HOME/config.json``), never in a project-local file, under the
``memory`` key beside the telemetry consent. ``ATTUNE_MEMORY_BACKEND``
overrides it for one process (CI, tests, one-off runs).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

VALUES: tuple[str, ...] = ("auto", "file", "redis")
ENV_VAR = "ATTUNE_MEMORY_BACKEND"
#: Set to 0/false to silence the first-run notice (hook and terminal).
NOTICE_ENV_VAR = "ATTUNE_MEMORY_NOTICE"
_FALSEY = {"", "0", "false", "no", "off"}

#: The chair's words for what Redis is FOR here (redis-config-truth D5).
REDIS_ROLE = (
    "Redis's role in attune-ai is to provide enhanced memory features using "
    "Redis's open-source options: semantic recall across sessions through the "
    "Agent Memory Server."
)


def config_path() -> Path:
    """The user config file; honors ``ATTUNE_HOME`` so tests never touch ``~``."""
    home = os.environ.get("ATTUNE_HOME")
    base = Path(home).expanduser() if home else Path("~/.attune").expanduser()
    return base / "config.json"


def _read() -> dict[str, Any]:
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _memory_section(data: dict[str, Any]) -> dict[str, Any]:
    section = data.get("memory")
    return dict(section) if isinstance(section, dict) else {}


def notice_enabled() -> bool:
    """False when ``ATTUNE_MEMORY_NOTICE`` is set to a falsy value."""
    return os.environ.get(NOTICE_ENV_VAR, "1").strip().lower() not in _FALSEY


def get_backend_preference() -> str:
    """``auto`` unless the user recorded a choice or the env var overrides it."""
    env = os.environ.get(ENV_VAR, "").strip().lower()
    if env in VALUES:
        return env
    value = _memory_section(_read()).get("backend")
    return value if value in VALUES else "auto"


def preference_recorded() -> bool:
    """True once the user has chosen (the notices stop asking)."""
    return _memory_section(_read()).get("backend") in VALUES


def set_backend_preference(value: str) -> Path:
    """Record ``value`` in the user config; returns the file written."""
    if value not in VALUES:
        raise ValueError(f"memory backend must be one of {', '.join(VALUES)}, got {value!r}")
    return _write_memory_key("backend", value)


def notice_shown() -> bool:
    """True once the terminal first-run notice has been printed."""
    return bool(_memory_section(_read()).get("notice_shown"))


def mark_notice_shown() -> Path:
    return _write_memory_key("notice_shown", True)


def _write_memory_key(key: str, value: Any) -> Path:
    from attune.security.path_validation import _validate_file_path

    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    target = _validate_file_path(str(path), allowed_dir=str(path.parent))
    data = _read()
    section = _memory_section(data)
    section[key] = value
    data["memory"] = section
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return target


__all__ = [
    "ENV_VAR",
    "NOTICE_ENV_VAR",
    "REDIS_ROLE",
    "VALUES",
    "config_path",
    "get_backend_preference",
    "mark_notice_shown",
    "notice_enabled",
    "notice_shown",
    "preference_recorded",
    "set_backend_preference",
]
