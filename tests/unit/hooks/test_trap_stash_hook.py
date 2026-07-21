"""Tests for the trap_stash PostToolUse hook (non-mocked stdin round trips).

HOME is redirected to a tmp dir so the subprocess's backend resolution
(FileStashBackend under ~/.attune/session_stash) and the dedupe
sentinel (~/.attune/trap_stash) write into the test sandbox, never the
real user home.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "plugin" / "hooks" / "trap_stash.py"
SRC = REPO_ROOT / "src"

PYTEST_FAILURE = """\
=========================== short test summary info ============================
FAILED tests/unit/test_x.py::test_boom - AssertionError: nope
============================== 1 failed in 0.10s ===============================
"""


def _run_hook(payload: object, home: Path, extra_env: dict[str, str] | None = None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)  # Windows Path.home()
    env.pop("ATTUNE_TRAP_STASH", None)
    # Force the file fallback: an unreachable AMS keeps the subprocess's
    # backend resolution out of any live Redis/AMS instance.
    env["AMS_BASE_URL"] = "http://127.0.0.1:9"
    env.pop("REDIS_URL", None)
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


def _payload(command: str, output: str, session: str = "sess-hook") -> dict:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_result": output,
        "session_id": session,
    }


class TestTrapStashHook:
    """stdin → exit-code/side-effect round trips through the real script."""

    def test_failure_captured_and_stashed(self, tmp_path: Path) -> None:
        proc = _run_hook(_payload("pytest -q", PYTEST_FAILURE), home=tmp_path)
        assert proc.returncode == 0
        assert "[trap-stash] captured pytest_failure" in proc.stdout
        # Real side effects under the sandboxed HOME:
        assert (tmp_path / ".attune" / "session_stash" / "findings.jsonl").exists()
        dedupe = list((tmp_path / ".attune" / "trap_stash").glob("*.json"))
        assert len(dedupe) == 1

    def test_same_failure_deduped_within_session(self, tmp_path: Path) -> None:
        first = _run_hook(_payload("pytest -q", PYTEST_FAILURE), home=tmp_path)
        second = _run_hook(_payload("pytest -q", PYTEST_FAILURE), home=tmp_path)
        assert "[trap-stash]" in first.stdout
        assert "[trap-stash]" not in second.stdout  # deduped, no second stash
        findings = (
            (tmp_path / ".attune" / "session_stash" / "findings.jsonl")
            .read_text(encoding="utf-8")
            .strip()
            .splitlines()
        )
        assert len(findings) == 1

    def test_green_output_no_capture(self, tmp_path: Path) -> None:
        proc = _run_hook(_payload("pytest -q", "3 passed in 0.1s\n"), home=tmp_path)
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""

    def test_disabled_by_env(self, tmp_path: Path) -> None:
        proc = _run_hook(
            _payload("pytest -q", PYTEST_FAILURE),
            home=tmp_path,
            extra_env={"ATTUNE_TRAP_STASH": "0"},
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""

    def test_non_bash_and_malformed_degrade_open(self, tmp_path: Path) -> None:
        ok = _run_hook({"tool_name": "Edit", "tool_input": {}}, home=tmp_path)
        assert ok.returncode == 0
        bad = _run_hook("{not json", home=tmp_path)
        assert bad.returncode == 0
