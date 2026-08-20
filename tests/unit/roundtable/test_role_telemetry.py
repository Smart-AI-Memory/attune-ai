"""Tests for the roundtable role-telemetry append surface.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from pathlib import Path

from attune.roundtable import role_telemetry


def test_record_appends_one_json_line(tmp_path: Path) -> None:
    dest = tmp_path / "roles.jsonl"
    role_telemetry.record("drafter", "claude", "t1", "served", path=dest, note="ok")
    (line,) = dest.read_text(encoding="utf-8").splitlines()
    row = json.loads(line)
    assert row["role"] == "drafter"
    assert row["seat"] == "claude"
    assert row["thread"] == "t1"
    assert row["event"] == "served"
    assert row["note"] == "ok"
    assert "at" in row


def test_unserializable_field_is_swallowed(tmp_path: Path) -> None:
    """Regression (library-review R5): the docstring promises
    logged-and-swallowed — a TypeError from an unserializable field
    must not escape any more than an OSError."""
    dest = tmp_path / "roles.jsonl"
    role_telemetry.record("drafter", "claude", "t1", "served", path=dest, extra=object())
    assert not dest.exists() or dest.read_text(encoding="utf-8") == ""
