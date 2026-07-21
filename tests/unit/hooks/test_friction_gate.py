"""Tests for the friction_gate PreToolUse hook (non-mocked stdin round trips)."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "plugin" / "hooks" / "friction_gate.py"
SRC = REPO_ROOT / "src"


def _run_hook(payload: object, extra_env: dict[str, str] | None = None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    env.pop("ATTUNE_FRICTION_ENFORCE", None)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=30,
    )


class TestFrictionGateHook:
    """stdin → exit-code round trips through the real hook script."""

    def test_low_risk_command_allowed_silently(self) -> None:
        proc = _run_hook({"tool_name": "Bash", "tool_input": {"command": "git status"}})
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""

    def test_destructive_command_gets_advisory_by_default(self) -> None:
        proc = _run_hook({"tool_name": "Bash", "tool_input": {"command": "rm -rf build/"}})
        assert proc.returncode == 0
        assert "[friction-gate]" in proc.stdout

    def test_destructive_command_blocked_in_enforce_mode(self) -> None:
        proc = _run_hook(
            {"tool_name": "Bash", "tool_input": {"command": "rm -rf build/"}},
            extra_env={"ATTUNE_FRICTION_ENFORCE": "1"},
        )
        assert proc.returncode == 2
        assert "BLOCKED" in proc.stderr

    def test_chained_destructive_command_blocked_in_enforce_mode(self) -> None:
        proc = _run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls && git reset --hard HEAD~3"},
            },
            extra_env={"ATTUNE_FRICTION_ENFORCE": "1"},
        )
        assert proc.returncode == 2

    def test_non_bash_tool_ignored(self) -> None:
        proc = _run_hook(
            {"tool_name": "Edit", "tool_input": {"file_path": "x.py"}},
            extra_env={"ATTUNE_FRICTION_ENFORCE": "1"},
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""

    def test_malformed_payload_degrades_open(self) -> None:
        proc = _run_hook("{not json", extra_env={"ATTUNE_FRICTION_ENFORCE": "1"})
        assert proc.returncode == 0
