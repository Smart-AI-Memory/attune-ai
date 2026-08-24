"""Tests for scripts/with_timeout.py (retro 2026-08-24 item 7).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parents[3] / "scripts" / "with_timeout.py")


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_fast_command_exit_code_propagates():
    ok = _run("10", "--", sys.executable, "-c", "raise SystemExit(0)")
    assert ok.returncode == 0
    fail = _run("10", "--", sys.executable, "-c", "raise SystemExit(7)")
    assert fail.returncode == 7


def test_hung_command_killed_at_bound():
    t0 = time.monotonic()
    result = _run("1", "--", sys.executable, "-c", "import time; time.sleep(60)")
    elapsed = time.monotonic() - t0
    assert result.returncode == 124
    assert elapsed < 15  # killed at the bound, not after 60s
    assert "exceeded" in result.stderr


def test_usage_errors_are_125():
    assert _run("nope", "--", "true").returncode == 125
    assert _run("5", "true").returncode == 125  # missing --
    assert _run("-3", "--", "true").returncode == 125
