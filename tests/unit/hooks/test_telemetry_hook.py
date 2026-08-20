"""Behavioral tests for telemetry_hook.py PostToolUse hook script.

Covers ``record_telemetry`` (tool_name pass-through + default), the stdin
reader ``_read_stdin_context`` (tty short-circuit, valid JSON, empty input,
invalid JSON), and the ``__main__`` fire-and-forget entry point.
"""

from __future__ import annotations

import importlib
import logging
import runpy
import sys
from pathlib import Path

import pytest

# The package __init__ rebinds submodule names to functions, so import the
# real module object via import_module rather than ``from ... import``.
hook = importlib.import_module("attune.hooks.scripts.telemetry_hook")

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "attune"
    / "hooks"
    / "scripts"
    / "telemetry_hook.py"
)


class FakeStdin:
    """Minimal stand-in for sys.stdin with controllable tty/read."""

    def __init__(self, data: str = "", tty: bool = False):
        self._data = data
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty

    def read(self) -> str:
        return self._data


# --------------------------------------------------------------------------- #
# record_telemetry
# --------------------------------------------------------------------------- #


def test_record_telemetry_logs_tool_name(caplog):
    with caplog.at_level(logging.INFO, logger=hook.logger.name):
        hook.record_telemetry({"tool_name": "Bash", "tool_input": {}})

    records = [r for r in caplog.records if r.message == "tool_usage"]
    assert records, "expected a tool_usage log record"
    assert records[0].tool_name == "Bash"
    assert hasattr(records[0], "timestamp")


def test_record_telemetry_defaults_to_unknown(caplog):
    with caplog.at_level(logging.INFO, logger=hook.logger.name):
        hook.record_telemetry({})

    records = [r for r in caplog.records if r.message == "tool_usage"]
    assert records[0].tool_name == "unknown"


# --------------------------------------------------------------------------- #
# _read_stdin_context
# --------------------------------------------------------------------------- #


def test_read_stdin_tty_returns_empty(monkeypatch):
    monkeypatch.setattr(sys, "stdin", FakeStdin(tty=True))

    assert hook._read_stdin_context() == {}


def test_read_stdin_parses_valid_json(monkeypatch):
    monkeypatch.setattr(sys, "stdin", FakeStdin('{"tool_name": "Edit"}'))

    assert hook._read_stdin_context() == {"tool_name": "Edit"}


def test_read_stdin_empty_input_returns_empty(monkeypatch):
    monkeypatch.setattr(sys, "stdin", FakeStdin("   \n  "))

    assert hook._read_stdin_context() == {}


def test_read_stdin_invalid_json_returns_empty(monkeypatch, caplog):
    monkeypatch.setattr(sys, "stdin", FakeStdin("{not valid"))

    with caplog.at_level(logging.DEBUG, logger=hook.logger.name):
        result = hook._read_stdin_context()

    assert result == {}
    assert any("Could not parse stdin JSON" in r.message for r in caplog.records)


# --------------------------------------------------------------------------- #
# __main__
# --------------------------------------------------------------------------- #


def test_main_block_reads_records_and_exits_zero(monkeypatch):
    monkeypatch.setattr(sys, "stdin", FakeStdin('{"tool_name": "Write"}'))

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(SCRIPT_PATH), run_name="__main__")

    assert exc.value.code == 0


def test_malformed_stdin_exits_0_telemetry():
    """Library-review L2: non-dict/wrong-typed stdin must not crash
    the exit-0 contract of telemetry_hook."""
    import subprocess
    import sys

    for payload in ("[1,2,3]", "42", "null", '"hi"', '{"tool_name":"Bash","tool_input":[1]}'):
        result = subprocess.run(
            [sys.executable, "src/attune/hooks/scripts/telemetry_hook.py"],
            input=payload,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{payload!r} -> exit {result.returncode}"
