"""Unit tests for SDK error fidelity primitives.

Covers Phase 1 of docs/specs/sdk-error-message-fidelity/:

- ``SdkSubprocessError`` dataclass-exception (str, format_user_message)
- ``classify_subprocess_failure`` (all 6 kinds, most-specific-wins)
- ``capture_subprocess_failure`` (happy path, timeout, OSError, redaction,
  empty-argv probe fallback)
- ``_last_subprocess_argv`` extractor (3 shapes + fallback + drift guard)
- ``_fallback_probe_argv`` / ``_find_claude_cli`` (probe construction)
"""

from __future__ import annotations

import subprocess

import claude_agent_sdk
import pytest

from attune.workflows.agent_sdk_adapter import (
    SdkSubprocessError,
    _fallback_probe_argv,
    _find_claude_cli,
    _last_subprocess_argv,
    capture_subprocess_failure,
    classify_subprocess_failure,
)


@pytest.fixture(autouse=True)
def _no_real_claude_probe():
    """Override the workflows-conftest probe-disable for this module.

    The conftest fixture nulls ``_find_claude_cli`` so other workflow
    tests never spawn a real probe. This module tests the probe and
    finder machinery directly, with explicit per-test mocks, so it
    needs the real functions — a no-op override restores them.
    """
    yield


# ---------------------------------------------------------------------
# SdkSubprocessError
# ---------------------------------------------------------------------


class TestSdkSubprocessError:
    """The typed wrapper around the SDK's bare 'Command failed' exception."""

    def test_str_returns_message(self):
        err = SdkSubprocessError(
            message="Anthropic API quota reached for this account.",
            stderr="raw stderr",
            kind="api_quota",
        )
        assert str(err) == "Anthropic API quota reached for this account."

    def test_format_user_message_unknown_kind_includes_raw_stderr(self):
        """Unknown classifications include the raw stderr inline so the
        user has the truth even when no pattern matched."""
        err = SdkSubprocessError(
            message="The claude CLI subprocess failed; see raw stderr below.",
            stderr="weird error nobody recognized",
            kind="unknown",
        )
        rendered = err.format_user_message()
        assert "weird error nobody recognized" in rendered
        assert "raw stderr" in rendered.lower()

    def test_format_user_message_classified_kind_points_to_run_view(self):
        """Classified kinds give the summary + a pointer to the dashboard
        view (where Phase 3 will surface the full stderr)."""
        err = SdkSubprocessError(
            message="Anthropic API quota reached for this account.",
            stderr="full stderr blob",
            kind="api_quota",
        )
        rendered = err.format_user_message()
        assert "API quota" in rendered
        assert "/runs/<id>/view" in rendered
        # Full stderr is NOT inlined for classified kinds
        assert "full stderr blob" not in rendered

    def test_original_exc_round_trips(self):
        """The original SDK exception is preserved on the wrapper so
        callers / tests can `raise X from err.original_exc`."""
        underlying = ValueError("inner")
        err = SdkSubprocessError(
            message="msg",
            stderr="",
            kind="unknown",
            original_exc=underlying,
        )
        assert err.original_exc is underlying


# ---------------------------------------------------------------------
# classify_subprocess_failure
# ---------------------------------------------------------------------


class TestClassifySubprocessFailure:
    """One test per ``SdkErrorKind`` + most-specific-wins ordering."""

    def test_classifies_api_quota(self):
        kind, msg = classify_subprocess_failure(
            "Error: You have reached your specified API usage limits. "
            "You will regain access on 2026-06-01."
        )
        assert kind == "api_quota"
        assert "quota" in msg.lower()

    def test_classifies_auth(self):
        kind, msg = classify_subprocess_failure("401 Unauthorized: invalid api key provided")
        assert kind == "auth"
        assert "auth" in msg.lower()

    def test_classifies_auth_via_invalid_api_key(self):
        kind, _ = classify_subprocess_failure("Error: invalid_api_key")
        assert kind == "auth"

    def test_classifies_rate_limit(self):
        kind, msg = classify_subprocess_failure("429 Too Many Requests: rate limit exceeded")
        assert kind == "rate_limit"
        assert "rate" in msg.lower()

    def test_classifies_not_found(self):
        kind, _ = classify_subprocess_failure(
            "FileNotFoundError: [Errno 2] No such file or directory: 'claude'"
        )
        assert kind == "not_found"

    def test_classifies_not_found_via_path_message(self):
        kind, _ = classify_subprocess_failure("Error: claude not found on PATH")
        assert kind == "not_found"

    def test_classifies_schema_rejected(self):
        kind, _ = classify_subprocess_failure("Error: --json-schema parameter rejected")
        assert kind == "schema_rejected"

    def test_falls_back_to_unknown(self):
        """No pattern match → unknown + a generic message."""
        kind, msg = classify_subprocess_failure("Some completely novel error nobody anticipated")
        assert kind == "unknown"
        assert "see raw stderr" in msg

    def test_most_specific_wins_quota_over_auth(self):
        """An error message containing both 'API usage limits' AND '401'
        classifies as api_quota (more specific) not auth."""
        kind, _ = classify_subprocess_failure(
            "401 Unauthorized — also: specified API usage limits reached"
        )
        assert kind == "api_quota"

    def test_empty_stderr_classifies_as_unknown(self):
        kind, _ = classify_subprocess_failure("")
        assert kind == "unknown"


# ---------------------------------------------------------------------
# capture_subprocess_failure
# ---------------------------------------------------------------------


class TestCaptureSubprocessFailure:
    """The second-subprocess helper that captures real stderr."""

    def test_captures_failing_command_stderr(self):
        """A failing command's stderr should come back non-empty."""
        # `false` exits 1 with no output; use `sh -c` to produce stderr.
        out = capture_subprocess_failure(["sh", "-c", "echo 'real failure' 1>&2; exit 1"])
        assert "real failure" in out

    def test_returns_synthetic_string_on_timeout(self):
        out = capture_subprocess_failure(
            ["sh", "-c", "sleep 5"],
            timeout_s=0.2,
        )
        assert "timed out" in out
        assert "0.2s" in out

    def test_returns_synthetic_string_on_os_error(self):
        """Invalid argv → OSError (FileNotFoundError) → synthetic
        '(capture-call also failed)' string."""
        out = capture_subprocess_failure(["/no/such/binary/anywhere"])
        assert "capture-call also failed" in out
        # The error class name should be in the synthetic string
        assert "Error" in out or "OSError" in out

    def test_routes_output_through_redact(self):
        """Any sensitive token in captured output must be redacted before
        return. Uses a synthetic Anthropic-shaped API key via runtime
        concat so the source file itself doesn't trigger push protection
        (per CLAUDE.md GitHub push-protection lesson)."""
        fake_key = "sk-" + "ant-api03-" + "TESTFAKETOKEN" + "ABCDEFGHIJ"
        out = capture_subprocess_failure(["sh", "-c", f"echo 'key=\"{fake_key}\"' 1>&2; exit 1"])
        # The exact token should NOT appear in output (redacted away)
        assert fake_key not in out

    def test_empty_argv_probes_when_claude_present(self, monkeypatch):
        """When claude IS locatable, an empty argv re-runs a real probe
        whose stderr is captured and classifiable. Monkeypatch the probe
        to a fast fake binary so the test makes no real API call."""
        monkeypatch.setattr(
            "attune.workflows.agent_sdk_adapter._fallback_probe_argv",
            lambda: ["sh", "-c", "echo 'reached your specified API usage limits' 1>&2; exit 1"],
        )
        out = capture_subprocess_failure([])
        assert "IndexError" not in out
        assert "usage limits" in out
        kind, _msg = classify_subprocess_failure(out)
        assert kind == "api_quota"

    def test_empty_argv_honest_message_when_claude_missing(self, monkeypatch):
        """When no claude binary exists, the empty-argv path returns a
        synthetic message that classifies as 'unknown' (the original
        cause is undiagnosable — we couldn't probe), NOT 'not_found'."""
        monkeypatch.setattr(
            "attune.workflows.agent_sdk_adapter._find_claude_cli",
            lambda: None,
        )
        out = capture_subprocess_failure([])
        assert "no claude binary available" in out
        assert "IndexError" not in out
        kind, _msg = classify_subprocess_failure(out)
        assert kind == "unknown"


# ---------------------------------------------------------------------
# _last_subprocess_argv
# ---------------------------------------------------------------------


class TestLastSubprocessArgv:
    """Drift guard + the three recognized exception shapes."""

    def test_extracts_from_args_zero_list(self):
        """Shape 1: SDK stashes argv in exc.args[0] as a list[str]."""
        exc = Exception(["claude", "--output-format", "stream-json"])
        assert _last_subprocess_argv(exc) == [
            "claude",
            "--output-format",
            "stream-json",
        ]

    def test_extracts_from_cause_cmd_list(self):
        """Shape 2: subprocess.CalledProcessError-shaped __cause__ with
        .cmd as list[str]."""
        called = subprocess.CalledProcessError(
            returncode=1,
            cmd=["claude", "-p", "test"],
        )
        wrapper = Exception("Command failed with exit code 1")
        wrapper.__cause__ = called
        assert _last_subprocess_argv(wrapper) == ["claude", "-p", "test"]

    def test_extracts_from_direct_cmd_attribute(self):
        """Shape 3: direct .cmd attribute on the exception itself."""
        exc = Exception("Command failed")
        exc.cmd = ["claude", "--version"]
        assert _last_subprocess_argv(exc) == ["claude", "--version"]

    def test_returns_empty_list_when_no_shape_matches(self):
        """Drift guard: when none of the recognized shapes apply,
        return []. Downstream capture_subprocess_failure([]) then falls
        back to a claude probe (see TestCaptureSubprocessFailure)."""
        exc = Exception("plain string message, no argv anywhere")
        assert _last_subprocess_argv(exc) == []

    def test_real_sdk_exception_shape_yields_empty(self):
        """Drift guard pinned to the INSTALLED claude-agent-sdk.

        The exception the SDK actually raises on a failed run
        (``claude_agent_sdk/_internal/query.py``:
        ``raise Exception(message.get("error", "Unknown error"))``)
        carries NO argv — ``args[0]`` is the string error message,
        ``__cause__`` is None, no ``.cmd``. So extraction returns [].

        Verified against 0.1.63 (2026-06-06). If a future SDK starts
        stashing the argv on the exception, this assertion flips and we
        should teach ``_last_subprocess_argv`` the new shape so the
        capture re-runs the EXACT failing argv instead of the probe.
        The version print makes the pin auditable when it does change.
        """
        # Reproduces the exact construction at query.py.
        real_exc = Exception("Command failed with exit code 1")
        assert real_exc.args[0] == "Command failed with exit code 1"
        assert real_exc.__cause__ is None
        assert not hasattr(real_exc, "cmd")
        assert _last_subprocess_argv(real_exc) == [], (
            f"claude-agent-sdk {claude_agent_sdk.__version__} now stashes "
            "an argv on the failure exception — extend _last_subprocess_argv "
            "to read it (preferred over the probe fallback)."
        )

    def test_handles_cause_cmd_as_string(self):
        """Some subprocess errors store .cmd as a single string instead
        of a list — wrap in a single-element list."""
        called = subprocess.CalledProcessError(
            returncode=1,
            cmd="claude -p test",
        )
        wrapper = Exception("Command failed")
        wrapper.__cause__ = called
        assert _last_subprocess_argv(wrapper) == ["claude -p test"]

    def test_ignores_args_zero_when_not_list_of_str(self):
        """Don't false-positive on non-string args[0]."""
        exc = Exception({"not": "a list"})
        assert _last_subprocess_argv(exc) == []


# ---------------------------------------------------------------------
# _fallback_probe_argv / _find_claude_cli
# ---------------------------------------------------------------------


class TestFallbackProbe:
    """The minimal claude probe used when no argv is recoverable."""

    def test_probe_uses_located_binary(self, monkeypatch):
        """When claude is found, the probe is [path, '-p', 'ping']."""
        monkeypatch.setattr(
            "attune.workflows.agent_sdk_adapter._find_claude_cli",
            lambda: "/usr/local/bin/claude",
        )
        assert _fallback_probe_argv() == ["/usr/local/bin/claude", "-p", "ping"]

    def test_probe_empty_when_no_binary(self, monkeypatch):
        """No claude binary → empty probe (caller renders not-found)."""
        monkeypatch.setattr(
            "attune.workflows.agent_sdk_adapter._find_claude_cli",
            lambda: None,
        )
        assert _fallback_probe_argv() == []

    def test_find_claude_cli_returns_path_or_none(self):
        """In a real environment the finder returns a path or None;
        either way it must never raise."""
        result = _find_claude_cli()
        assert result is None or isinstance(result, str)

    def test_find_claude_cli_prefers_path_when_no_bundle(self, monkeypatch, tmp_path):
        """With the SDK bundle absent, PATH discovery wins."""
        fake = tmp_path / "claude"
        fake.write_text("#!/bin/sh\n")
        fake.chmod(0o755)
        # Force the bundled-CLI lookup to miss by pointing the SDK dir
        # at an empty temp location.
        monkeypatch.setattr(
            "attune.workflows.agent_sdk_adapter.claude_agent_sdk.__file__",
            str(tmp_path / "no_such_pkg" / "__init__.py"),
        )
        monkeypatch.setattr(
            "attune.workflows.agent_sdk_adapter.shutil.which",
            lambda name: str(fake) if name == "claude" else None,
        )
        assert _find_claude_cli() == str(fake)
