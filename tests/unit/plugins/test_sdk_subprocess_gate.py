"""Hook gating for SDK-spawned subprocess sessions (sdk-subprocess-isolation Phase 1).

Spec R1/R2 + AC1–AC3: every registered hook script exits 0 with zero
output when either detection signal is present (the explicit
``ATTUNE_SDK_SUBPROCESS=1`` marker or the SDK's own
``CLAUDE_CODE_ENTRYPOINT=sdk-*`` stamp), and behaves normally in
interactive sessions (AC3 = the existing hook test suites). The R6a
drift guard pins the gate call into every script the plugin's
hooks.json (and the repo's settings.json) registers.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_HOOKS = REPO_ROOT / "plugin" / "hooks"


def _plugin_hook_scripts() -> list[Path]:
    """Every script plugin/hooks/hooks.json registers (deduped)."""
    config = json.loads((PLUGIN_HOOKS / "hooks.json").read_text(encoding="utf-8"))
    scripts: set[str] = set()
    for groups in config["hooks"].values():
        for group in groups:
            for hook in group.get("hooks", []):
                match = re.search(r"hooks/(\w+\.py)", hook.get("command", ""))
                if match:
                    scripts.add(match.group(1))
    return sorted(PLUGIN_HOOKS / name for name in scripts)


def _repo_hook_scripts() -> list[Path]:
    """Every script .claude/settings.json registers (deduped)."""
    config = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    scripts: set[str] = set()
    for groups in config.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                match = re.search(r"src/attune/hooks/scripts/(\w+\.py)", hook.get("command", ""))
                if match:
                    scripts.add(match.group(1))
    return sorted(REPO_ROOT / "src" / "attune" / "hooks" / "scripts" / name for name in scripts)


def _load_gate():
    """Import plugin/hooks/_sdk_gate.py (not a package) by path."""
    spec = importlib.util.spec_from_file_location("_plugin_sdk_gate", PLUGIN_HOOKS / "_sdk_gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestIsSdkSubprocess:
    """The detection predicate (spec D3)."""

    def test_explicit_marker_detected(self, monkeypatch):
        """ATTUNE_SDK_SUBPROCESS=1 is the attune-set signal."""
        gate = _load_gate()
        monkeypatch.setenv("ATTUNE_SDK_SUBPROCESS", "1")
        monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
        assert gate.is_sdk_subprocess() is True

    @pytest.mark.parametrize("entrypoint", ["sdk-py", "sdk-ts", "sdk-go"])
    def test_sdk_entrypoint_detected(self, monkeypatch, entrypoint):
        """sdk-py/sdk-ts (and unknown future sdk-*) cover third-party
        SDK scripts — unknown values stay gated (D9 fail-safe)."""
        gate = _load_gate()
        monkeypatch.delenv("ATTUNE_SDK_SUBPROCESS", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", entrypoint)
        assert gate.is_sdk_subprocess() is True

    def test_headless_cli_entrypoint_not_detected(self, monkeypatch):
        """D9: sdk-cli marks plain headless ``claude -p`` (stamped into
        every such session since at least CC 2.1.144) — NOT an SDK
        subprocess. Gating it silenced all attune hooks headless."""
        gate = _load_gate()
        monkeypatch.delenv("ATTUNE_SDK_SUBPROCESS", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "sdk-cli")
        assert gate.is_sdk_subprocess() is False

    def test_marker_still_gates_headless_entrypoint(self, monkeypatch):
        """The explicit marker wins over the sdk-cli exemption: an
        attune adapter subprocess is gated whatever the CLI stamps."""
        gate = _load_gate()
        monkeypatch.setenv("ATTUNE_SDK_SUBPROCESS", "1")
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "sdk-cli")
        assert gate.is_sdk_subprocess() is True

    def test_override_force_disables_gate(self, monkeypatch):
        """ATTUNE_SDK_GATE_OVERRIDE=1 (benchmark-only) beats both
        signals — harnesses that parse stream-json defensively use it
        to keep hooks live in SDK-driven sessions."""
        gate = _load_gate()
        monkeypatch.setenv("ATTUNE_SDK_GATE_OVERRIDE", "1")
        monkeypatch.setenv("ATTUNE_SDK_SUBPROCESS", "1")
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "sdk-py")
        assert gate.is_sdk_subprocess() is False

    @pytest.mark.parametrize("entrypoint", ["claude-desktop", "cli", ""])
    def test_interactive_sessions_not_detected(self, monkeypatch, entrypoint):
        """Interactive entrypoints never match (AC3 precondition)."""
        gate = _load_gate()
        monkeypatch.delenv("ATTUNE_SDK_SUBPROCESS", raising=False)
        monkeypatch.delenv("ATTUNE_SDK_GATE_OVERRIDE", raising=False)
        if entrypoint:
            monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", entrypoint)
        else:
            monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
        assert gate.is_sdk_subprocess() is False

    def test_marker_other_values_not_detected(self, monkeypatch):
        """Only the literal '1' arms the explicit marker."""
        gate = _load_gate()
        monkeypatch.setenv("ATTUNE_SDK_SUBPROCESS", "0")
        monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
        assert gate.is_sdk_subprocess() is False


class TestGateDriftGuards:
    """R6a: every registered hook script calls the gate."""

    def test_every_plugin_hook_gated(self):
        """All hooks.json scripts call exit_if_sdk_subprocess."""
        scripts = _plugin_hook_scripts()
        assert scripts, "hooks.json parsed to zero scripts — parser drift?"
        offenders = [
            str(p) for p in scripts if "exit_if_sdk_subprocess" not in p.read_text(encoding="utf-8")
        ]
        assert not offenders, (
            f"Plugin hooks without the SDK-subprocess gate will fire inside "
            f"SDK workflow subprocesses and poison the stream-json channel "
            f"for subscription users: {offenders}"
        )

    def test_every_repo_hook_gated(self):
        """All .claude/settings.json scripts call exit_if_sdk_subprocess."""
        scripts = _repo_hook_scripts()
        assert scripts, "settings.json parsed to zero scripts — parser drift?"
        offenders = [
            str(p) for p in scripts if "exit_if_sdk_subprocess" not in p.read_text(encoding="utf-8")
        ]
        assert not offenders, f"Repo hook scripts missing the gate: {offenders}"

    def test_gate_twins_have_identical_logic(self):
        """The two _sdk_gate copies must not drift (docstrings may differ)."""

        def logic(path: Path) -> str:
            text = path.read_text(encoding="utf-8")
            # Strip the module docstring; compare executable content only.
            return re.sub(r'^"""[\s\S]*?"""', "", text, count=1).strip()

        plugin_gate = logic(PLUGIN_HOOKS / "_sdk_gate.py")
        repo_gate = logic(REPO_ROOT / "src" / "attune" / "hooks" / "scripts" / "_sdk_gate.py")
        assert plugin_gate == repo_gate


class TestHooksSilentInSdkSubprocess:
    """AC1/AC2: each registered hook exits 0 with zero output."""

    @staticmethod
    def _gated_env(**overrides: str) -> dict[str, str]:
        """os.environ minus the benchmark override, plus the signal."""
        env = {**os.environ, **overrides}
        env.pop("ATTUNE_SDK_GATE_OVERRIDE", None)
        return env

    @pytest.mark.parametrize("script", _plugin_hook_scripts(), ids=lambda p: p.name)
    def test_plugin_hook_silent_with_marker(self, script):
        """AC1: the explicit marker silences every plugin hook."""
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(script)],
            env=self._gated_env(ATTUNE_SDK_SUBPROCESS="1"),
            input="",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert result.returncode == 0, f"{script.name}: exit {result.returncode}"
        assert result.stdout == "" and result.stderr == "", (
            f"{script.name} emitted output despite the SDK marker: "
            f"stdout={result.stdout[:120]!r} stderr={result.stderr[:120]!r}"
        )

    def test_plugin_hook_silent_with_sdk_entrypoint(self):
        """AC2: the SDK's own entrypoint stamp silences hooks too."""
        env = self._gated_env(CLAUDE_CODE_ENTRYPOINT="sdk-py")
        env.pop("ATTUNE_SDK_SUBPROCESS", None)
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(PLUGIN_HOOKS / "welcome.py")],
            env=env,
            input="",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert result.returncode == 0
        assert result.stdout == "" and result.stderr == ""

    def test_repo_hook_silent_with_marker(self):
        """The repo-level scripts honor the same gate."""
        script = REPO_ROOT / "src" / "attune" / "hooks" / "scripts" / "lessons_reminder.py"
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(script)],
            env=self._gated_env(ATTUNE_SDK_SUBPROCESS="1"),
            input="",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert result.returncode == 0
        assert result.stdout == "" and result.stderr == ""


class TestRepoGateTwin:
    """Direct coverage of attune.hooks.scripts._sdk_gate (the repo twin).

    The subprocess-based tests above exercise the plugin twin invisibly
    to coverage; this class imports the packaged twin and exercises the
    same contract in-process.
    """

    def test_marker_detected(self, monkeypatch):
        """ATTUNE_SDK_SUBPROCESS=1 arms the repo twin too."""
        from attune.hooks.scripts import _sdk_gate

        monkeypatch.setenv("ATTUNE_SDK_SUBPROCESS", "1")
        monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
        assert _sdk_gate.is_sdk_subprocess() is True

    def test_sdk_entrypoint_detected(self, monkeypatch):
        """The sdk- entrypoint prefix arms the repo twin too."""
        from attune.hooks.scripts import _sdk_gate

        monkeypatch.delenv("ATTUNE_SDK_SUBPROCESS", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "sdk-ts")
        assert _sdk_gate.is_sdk_subprocess() is True

    def test_headless_cli_entrypoint_not_detected(self, monkeypatch):
        """D9 in the repo twin: sdk-cli = plain headless, hooks live."""
        from attune.hooks.scripts import _sdk_gate

        monkeypatch.delenv("ATTUNE_SDK_SUBPROCESS", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "sdk-cli")
        assert _sdk_gate.is_sdk_subprocess() is False

    def test_override_force_disables_gate(self, monkeypatch):
        """The benchmark override disarms the repo twin too."""
        from attune.hooks.scripts import _sdk_gate

        monkeypatch.setenv("ATTUNE_SDK_GATE_OVERRIDE", "1")
        monkeypatch.setenv("ATTUNE_SDK_SUBPROCESS", "1")
        assert _sdk_gate.is_sdk_subprocess() is False

    def test_interactive_not_detected(self, monkeypatch):
        """No signal → not an SDK subprocess."""
        from attune.hooks.scripts import _sdk_gate

        monkeypatch.delenv("ATTUNE_SDK_SUBPROCESS", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "claude-desktop")
        assert _sdk_gate.is_sdk_subprocess() is False

    def test_exit_helper_exits_zero_when_armed(self, monkeypatch):
        """exit_if_sdk_subprocess raises SystemExit(0) under the marker."""
        from attune.hooks.scripts import _sdk_gate

        monkeypatch.setenv("ATTUNE_SDK_SUBPROCESS", "1")
        with pytest.raises(SystemExit) as excinfo:
            _sdk_gate.exit_if_sdk_subprocess()
        assert excinfo.value.code == 0

    def test_exit_helper_noop_when_interactive(self, monkeypatch):
        """No signal → the helper returns without exiting."""
        from attune.hooks.scripts import _sdk_gate

        monkeypatch.delenv("ATTUNE_SDK_SUBPROCESS", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
        assert _sdk_gate.exit_if_sdk_subprocess() is None
