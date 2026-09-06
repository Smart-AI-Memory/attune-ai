"""``attune doctor`` names the live memory backend (redis-config-truth D5).

Redis is optional: a zero-config install runs on the local file tier and
upgrades to the Redis Agent Memory Server automatically when one is
reachable. Before D5 the doctor reported raw Redis reachability but never
which memory backend recall actually resolves to, so a dark upgrade
(AMS registered but down) was invisible from the CLI. These tests pin the
three states a user can be in, driven through the real command with
``backend_status`` intercepted — no server, no network.
"""

from __future__ import annotations

from argparse import Namespace

import pytest

from attune.cli_commands.utility_commands import cmd_doctor
from attune.memory import session_stash


def _doctor_line(monkeypatch: pytest.MonkeyPatch, status: dict, capsys) -> str:
    monkeypatch.setattr(session_stash, "backend_status", lambda: status)
    cmd_doctor(Namespace())
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if "Memory backend" in line]
    assert len(lines) == 1, f"doctor printed {len(lines)} memory-backend lines:\n{out}"
    return lines[0]


def test_live_upgrade_backend_is_ok(monkeypatch, capsys) -> None:
    line = _doctor_line(
        monkeypatch,
        {
            "backend": "AMSMemoryBackend",
            "fallback": False,
            "unreachable_upgrade": None,
            "ok": True,
            "transport": "direct",
        },
        capsys,
    )
    assert line.startswith("  [OK]") and "AMSMemoryBackend" in line and "direct" in line


def test_zero_config_file_tier_is_ok_and_says_redis_is_optional(monkeypatch, capsys) -> None:
    line = _doctor_line(
        monkeypatch,
        {
            "backend": "FileStashBackend",
            "fallback": True,
            "unreachable_upgrade": None,
            "ok": True,
            "transport": "file",
        },
        capsys,
    )
    assert line.startswith("  [OK]") and "file tier" in line and "optional" in line


def test_dark_upgrade_is_a_warning_naming_the_upgrade(monkeypatch, capsys) -> None:
    line = _doctor_line(
        monkeypatch,
        {
            "backend": "FileStashBackend",
            "fallback": True,
            "unreachable_upgrade": "redis",
            "ok": True,
            "transport": "file",
        },
        capsys,
    )
    assert line.startswith("  [--]") and "'redis' unreachable" in line and "dark" in line


def test_no_usable_backend_is_a_warning_with_the_reason(monkeypatch, capsys) -> None:
    line = _doctor_line(
        monkeypatch,
        {
            "backend": None,
            "fallback": False,
            "unreachable_upgrade": None,
            "ok": False,
            "reason": "file_write_denied",
        },
        capsys,
    )
    assert line.startswith("  [--]") and "none usable" in line and "file_write_denied" in line


def test_memory_line_never_fails_the_doctor(monkeypatch, capsys) -> None:
    """Memory is optional; the doctor's exit code must not depend on it."""
    monkeypatch.setattr(
        session_stash,
        "backend_status",
        lambda: {
            "backend": None,
            "fallback": False,
            "unreachable_upgrade": None,
            "ok": False,
            "reason": "no_backend",
        },
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-not-a-key")
    code = cmd_doctor(Namespace())
    out = capsys.readouterr().out
    assert "[FAIL] Memory" not in out
    assert code in (0, 1)  # other checks decide; this one never contributes a FAIL
