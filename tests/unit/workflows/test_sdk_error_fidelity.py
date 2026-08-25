"""Unit tests for SDK error fidelity primitives.

Covers Phase 1 of docs/specs/sdk-error-message-fidelity/:

- ``SdkSubprocessError`` dataclass-exception (str, format_user_message)
- ``classify_subprocess_failure`` (all 6 kinds, most-specific-wins)
- ``capture_subprocess_failure`` (happy path, timeout, OSError, redaction)
- ``_last_subprocess_argv`` extractor (3 shapes + fallback + drift guard)
"""

from __future__ import annotations

import subprocess

from attune.models.sdk_errors import (
    SdkSubprocessError,
    _last_subprocess_argv,
    capture_subprocess_failure,
    classify_subprocess_failure,
)

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

    def test_empty_argv_default_no_probe(self, monkeypatch):
        """Default (probe disabled): empty argv returns a deterministic
        'no stderr' note — no crash, no real subprocess — so the failure
        classifies as 'unknown' (what every workflow test expects)."""
        monkeypatch.delenv("ATTUNE_SDK_ERROR_PROBE", raising=False)
        out = capture_subprocess_failure([])
        assert "no" in out.lower() and "capture" in out.lower()
        assert "IndexError" not in out  # the old bug must not recur
        kind, _ = classify_subprocess_failure(out)
        assert kind == "unknown"

    def test_empty_argv_runs_claude_health_probe(self, monkeypatch):
        """With ATTUNE_SDK_ERROR_PROBE on, empty argv falls back to the
        `claude` health probe and surfaces its real output — NOT a crash.
        The probe is monkeypatched to a deterministic 401 so no real
        `claude` runs."""
        monkeypatch.setenv("ATTUNE_SDK_ERROR_PROBE", "1")
        monkeypatch.setattr(
            "attune.models.sdk_errors._claude_health_probe_argv",
            lambda: ["sh", "-c", "echo '401 Invalid authentication credentials' 1>&2; exit 1"],
        )
        out = capture_subprocess_failure([])
        assert "health probe" in out  # the explanatory probe note
        assert "401 Invalid authentication credentials" in out  # real error surfaced
        assert "IndexError" not in out  # the old bug must not recur

    def test_probe_with_no_output_reports_exit_code(self, monkeypatch):
        """When the health probe exits with no stdout/stderr, report its
        exit code instead of an empty string (covers the `if not text`
        branch)."""
        monkeypatch.setenv("ATTUNE_SDK_ERROR_PROBE", "1")
        monkeypatch.setattr(
            "attune.models.sdk_errors._claude_health_probe_argv",
            lambda: ["sh", "-c", "exit 7"],
        )
        out = capture_subprocess_failure([])
        assert "claude exited 7 with no stderr/stdout" in out

    def test_health_probe_argv_invokes_claude(self):
        """The fallback probe is a minimal `claude -p` invocation."""
        from attune.models.sdk_errors import _claude_health_probe_argv

        argv = _claude_health_probe_argv()
        assert argv[0] == "claude" or argv[0].endswith("/claude")
        assert "-p" in argv


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
        return []. Downstream capture_subprocess_failure([]) hits the
        OSError path and surfaces a synthetic message."""
        exc = Exception("plain string message, no argv anywhere")
        assert _last_subprocess_argv(exc) == []

    def test_handles_cause_cmd_as_string(self):
        """Some subprocess errors store .cmd as a single string instead
        of a list — shlex-split into argv, so subprocess.run doesn't
        treat the whole command line as one executable path."""
        called = subprocess.CalledProcessError(
            returncode=1,
            cmd="claude -p test",
        )
        wrapper = Exception("Command failed")
        wrapper.__cause__ = called
        assert _last_subprocess_argv(wrapper) == ["claude", "-p", "test"]

    def test_direct_cmd_string_is_shlex_split(self, monkeypatch):
        """Shape 3 with a string .cmd is split into argv, quotes honored.

        POSIX pinned: single-quote grouping is a POSIX lexing rule, so
        this must not float with the CI platform's real os.name.
        """
        from attune.models import sdk_errors

        monkeypatch.setattr(sdk_errors.os, "name", "posix")
        exc = Exception("Command failed")
        exc.cmd = "claude -p 'hello world'"
        assert _last_subprocess_argv(exc) == ["claude", "-p", "hello world"]

    def test_string_cmd_unbalanced_quote_falls_back_to_whitespace_split(self):
        """Unbalanced quotes must not crash extraction; whitespace-split."""
        exc = Exception("Command failed")
        exc.cmd = 'claude -p "unterminated'
        assert _last_subprocess_argv(exc) == ["claude", "-p", '"unterminated']

    def test_string_cmd_windows_backslash_paths_survive(self, monkeypatch):
        """On Windows, non-POSIX lexing keeps backslash paths intact."""
        from attune.models import sdk_errors

        monkeypatch.setattr(sdk_errors.os, "name", "nt")
        exc = Exception("Command failed")
        exc.cmd = r'"C:\Users\dev\claude.exe" -p test'
        assert _last_subprocess_argv(exc) == [
            r"C:\Users\dev\claude.exe",
            "-p",
            "test",
        ]

    def test_ignores_args_zero_when_not_list_of_str(self):
        """Don't false-positive on non-string args[0]."""
        exc = Exception({"not": "a list"})
        assert _last_subprocess_argv(exc) == []
