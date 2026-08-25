#!/usr/bin/env python3
"""Tests for macos_timeout_guard — calibrated against real commands.

The TRUE cases are shapes drawn from the transcript sweep that found
`command not found: timeout` in 18 sessions. The FALSE cases are the
false-positive classes triaged out while writing the rule; each is
pinned here because the discriminator is the fragile part and the
easiest thing for a later simplification to drop.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[3] / "plugin" / "hooks" / "macos_timeout_guard.py"
sys.path.insert(0, str(GUARD.parent))
from macos_timeout_guard import uses_bare_timeout  # noqa: E402

FIRES = [
    "timeout 480 uv run --extra docs mkdocs build --strict",
    "timeout 30 pytest tests -q",
    "cd /tmp && timeout 5 ./flaky",
    "TZ=UTC timeout 5 ./probe",
    "ATTUNE_X=1 TZ=UTC timeout 10 pytest",
    "make build; timeout 60 ./deploy.sh",
    "(timeout 3 curl localhost:8765)",
    "foo | timeout 3 grep bar",
    "timeout\t5 ./x",
]

QUIET = [
    # `timeout` as an argument or flag, not a program
    "pytest --timeout 30 tests/",
    "curl --max-time 5 http://x",
    "grep -rn 'timeout' src/",
    'grep -n "timeout" README.md',
    "git config --get http.timeout",
    # env var that merely resembles it
    "TIMEOUT=5 ./run.sh",
    "export TIMEOUT_S=30",
    # inside quotes — a string, not an invocation
    'echo "timeout 5 foo"',
    "echo 'timeout 5 foo'",
    # heredoc body: a script being WRITTEN, possibly for a Linux runner
    "cat > s.sh <<'EOF'\ntimeout 5 ./job\nEOF",
    "cat > s.sh <<EOF\ntimeout 5 ./job\nEOF",
    # comment
    "# timeout 5 ./x\nls",
    # substring of another program name
    "timeoutctl status",
    "./timeout-helper --run",
    # bare mention with no argument
    "which timeout",
    "command -v timeout",
]


@pytest.mark.parametrize("cmd", FIRES)
def test_detects_command_position(cmd):
    assert uses_bare_timeout(cmd) is True, cmd


@pytest.mark.parametrize("cmd", QUIET)
def test_ignores_non_invocations(cmd):
    assert uses_bare_timeout(cmd) is False, cmd


def _run(command, tool="Bash"):
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(GUARD)], input=payload, capture_output=True, text=True
    )


@pytest.mark.skipif(sys.platform != "darwin", reason="guard is macOS-only")
def test_blocks_end_to_end_on_macos():
    r = _run("timeout 30 pytest")
    assert r.returncode == 2
    assert "not installed on this Mac" in r.stderr
    assert "timeout: 480000" in r.stderr  # names the actual alternative


@pytest.mark.skipif(sys.platform != "darwin", reason="guard is macOS-only")
def test_escape_hatch_allows():
    assert _run("ATTUNE_ALLOW_TIMEOUT=1 timeout 30 pytest").returncode == 0


def test_non_bash_tool_ignored():
    assert _run("timeout 30 pytest", tool="Write").returncode == 0


class TestRedosRegression:
    """CodeQL `py/redos` (high) on the first draft — alert 185.

    The env-assignment group offered quoted alternatives alongside
    `\\S*`, which also matches a quoted string, so `""` was matchable
    two ways inside a repetition. CodeQL named the shape exactly:
    input starting `&A=` with many repetitions of `""\\tA=`.
    """

    def test_pathological_input_returns_promptly(self):
        """The exact shape CodeQL named must not blow up.

        Bounded generously (2 s) to separate REGIMES — linear vs
        exponential — not to measure speed; the pre-fix pattern did not
        finish this input in any practical time. Measured with
        `time.monotonic` so a clock adjustment cannot end it early.
        """
        import time

        evil = "&A=" + '""\tA=' * 40
        start = time.monotonic()
        uses_bare_timeout(evil)
        assert time.monotonic() - start < 2.0

    def test_quoted_env_value_still_detected(self):
        """Dropping the quoted branches must not lose real coverage.

        `_strip_noise` blanks the quoted value before matching, so the
        assignment still parses and the invocation is still caught.
        """
        assert uses_bare_timeout('FOO="a b" timeout 5 ./x') is True

    def test_many_env_assignments_still_detected(self):
        """Within the bound, a long env prefix still matches."""
        prefix = " ".join(f"V{i}=1" for i in range(6))
        assert uses_bare_timeout(f"{prefix} timeout 5 ./x") is True


def test_malformed_payload_never_blocks():
    r = subprocess.run(
        [sys.executable, str(GUARD)], input="not json", capture_output=True, text=True
    )
    assert r.returncode == 0
