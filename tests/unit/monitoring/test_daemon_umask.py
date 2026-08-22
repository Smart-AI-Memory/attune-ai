"""The alert daemon must not run with a permissive umask.

``os.umask(0)`` is the textbook daemonize idiom, but it only makes sense
when every later creation passes an explicit mode. Nothing downstream
here does, so the alert database, its SQLite journal/WAL siblings, and
any directory created after the fork land wide open.

Measured under ``umask(0)``: a created directory is 0o777 (world
WRITABLE) and the SQLite database 0o644 (world readable). Under
``umask(0o077)`` they are 0o700 and 0o600.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import ast
import os
import sqlite3
import stat
from pathlib import Path

import pytest

_SOURCE = Path(__file__).resolve().parents[3] / "src" / "attune" / "monitoring" / "alerts_cli.py"

# POSIX-only: umask is meaningless on Windows, and os.fork does not exist
# there either, so _daemonize is unreachable. Computed with a safe
# accessor because a skipif CONDITION is evaluated at collection time —
# a bare os.geteuid() would AttributeError the whole module on Windows.
_NOT_POSIX = os.name != "posix"


def _daemonize_umask_args() -> list[int]:
    """Every literal passed to os.umask inside _daemonize."""
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    found: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "_daemonize":
            continue
        for call in ast.walk(node):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "umask"
                and call.args
                and isinstance(call.args[0], ast.Constant)
            ):
                found.append(call.args[0].value)
    return found


def test_daemonize_sets_a_restrictive_umask():
    """Static guard — reads the source, so it needs no fork."""
    masks = _daemonize_umask_args()

    assert masks, "no os.umask(...) literal found in _daemonize"
    for mask in masks:
        assert mask != 0, (
            "os.umask(0) lets the daemon create world-writable files and "
            "directories; nothing downstream passes an explicit mode."
        )
        # Owner-only: group and other bits must all be masked off.
        assert mask & 0o077 == 0o077, f"umask {oct(mask)} leaves group/other bits open"


@pytest.mark.skipif(_NOT_POSIX, reason="umask is POSIX-only")
def test_the_chosen_umask_actually_yields_owner_only_artifacts(tmp_path):
    """Behavioural counterpart: the literal produces the modes we claim."""
    (mask,) = set(_daemonize_umask_args())

    previous = os.umask(mask)
    try:
        created_dir = tmp_path / "alerts"
        created_dir.mkdir()
        db = created_dir / "alerts.db"
        sqlite3.connect(db).close()

        dir_mode = stat.S_IMODE(created_dir.stat().st_mode)
        db_mode = stat.S_IMODE(db.stat().st_mode)
    finally:
        os.umask(previous)

    assert dir_mode & 0o077 == 0, f"directory {oct(dir_mode)} is group/world accessible"
    assert db_mode & 0o077 == 0, f"database {oct(db_mode)} is group/world accessible"
