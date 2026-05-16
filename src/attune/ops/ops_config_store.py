"""Persisted per-machine ops settings.

Spec: ``docs/specs/ops-specs-completion-candidates/`` (T3 in tasks).

Stores user-toggleable ops settings (currently:
``specs_candidates_enabled``) in a single JSON file at
``<attune_home>/ops/config.json`` so settings survive ``attune ops``
restarts without requiring the CLI flag every time.

Schema (v1)::

    {
      "version": 1,
      "settings": {
        "specs_candidates_enabled": true
      }
    }

Atomic writes via ``tempfile`` + ``os.replace`` so a partial write
never produces a half-readable file. Permission errors on write log
at WARN and degrade to in-memory-only — the dashboard runs fine
without persisted settings; the user just has to pass the flag
again next launch.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
SETTINGS_FILENAME = "config.json"
SETTINGS_SUBDIR = ("ops",)


def settings_path(attune_home: Path) -> Path:
    """Return the absolute path to the ops settings file."""
    return attune_home.joinpath(*SETTINGS_SUBDIR, SETTINGS_FILENAME)


def load_settings(attune_home: Path) -> dict[str, Any]:
    """Read persisted ops settings. Missing or corrupt file → ``{}``.

    Corruption handling mirrors ``dismiss_store``: any failure mode
    (missing file, unreadable, invalid JSON, wrong schema, missing
    ``settings`` key) returns an empty dict and (when meaningful)
    logs at WARN. A corrupt settings file never blocks the dashboard.
    """
    path = settings_path(attune_home)
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("ops settings unreadable at %s: %s", path, exc)
        return {}
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("ops settings has invalid JSON at %s: %s", path, exc)
        return {}
    if not isinstance(raw, dict):
        logger.warning("ops settings at %s is not a JSON object", path)
        return {}
    if raw.get("version") != SCHEMA_VERSION:
        logger.warning(
            "ops settings at %s has unsupported version %r (expected %r)",
            path,
            raw.get("version"),
            SCHEMA_VERSION,
        )
        return {}
    settings = raw.get("settings")
    if not isinstance(settings, dict):
        logger.warning("ops settings at %s missing 'settings' object", path)
        return {}
    return dict(settings)


def save_setting(attune_home: Path, key: str, value: Any) -> bool:
    """Persist a single setting; returns True on success, False on failure.

    Failure modes (PermissionError, disk full, etc.) log at WARN and
    return False — caller decides whether to surface to the user.
    The in-memory value the caller passed remains usable for the
    current session regardless.
    """
    if not key or not isinstance(key, str):
        raise ValueError("key must be a non-empty string")
    try:
        current = load_settings(attune_home)
        current[key] = value
        _write_atomic(attune_home, current)
        return True
    except OSError as exc:
        logger.warning(
            "ops settings save failed at %s: %s — using in-memory only",
            settings_path(attune_home),
            exc,
        )
        return False


def _write_atomic(attune_home: Path, settings: dict[str, Any]) -> None:
    """Serialize ``settings`` and atomically replace the settings file."""
    path = settings_path(attune_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": SCHEMA_VERSION, "settings": settings}
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{SETTINGS_FILENAME}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(serialized)
        os.replace(tmp_name, path)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Resolvers — used by cli.py to combine CLI flag + persisted state
# ---------------------------------------------------------------------------


def resolve_specs_candidates_enabled(cli_value: bool | None, attune_home: Path) -> bool:
    """Resolve the ``specs_candidates_enabled`` setting.

    Precedence:

    1. ``cli_value=True``  → persist True, return True.
    2. ``cli_value=False`` → persist False (clears prior True), return False.
    3. ``cli_value=None``  → return persisted value (default False).

    Used by ``attune ops --specs-candidates`` / ``--no-specs-candidates``
    plumbing in :mod:`attune.ops.cli`.
    """
    if cli_value is not None:
        save_setting(attune_home, "specs_candidates_enabled", cli_value)
        return cli_value
    settings = load_settings(attune_home)
    value = settings.get("specs_candidates_enabled", False)
    return bool(value)
