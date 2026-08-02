"""Tests for ``_emit_run_meta_for_daemon`` in workflow_commands.

The CLI helper emits ATTUNE_RUN_META stdout lines when:
1. The ``ATTUNE_RUN_META_EMIT=1`` env var is set (daemon opted in)
2. The workflow result carries ``sdk_stderr`` / ``sdk_error_kind`` in its
   metadata (only set by BaseWorkflow._error_result during SDK failure)

Both conditions must be true. Either alone is a silent no-op so users
who pipe ``attune workflow run X > out.md`` outside the daemon don't
see marker pollution in their output file.

Spec: docs/specs/sdk-error-message-fidelity/ Phase 3b
"""

from __future__ import annotations

import base64
import io
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Any

from attune.cli_commands.workflow_commands import _emit_run_meta_for_daemon


@dataclass
class _FakeResult:
    """Minimal WorkflowResult stand-in carrying ``metadata`` dict."""

    metadata: dict[str, Any]


def _capture(callback) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        callback()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Env-var gate: nothing emits without ATTUNE_RUN_META_EMIT
# ---------------------------------------------------------------------------


class TestEnvGate:
    def test_env_unset_emits_nothing(self, monkeypatch):
        monkeypatch.delenv("ATTUNE_RUN_META_EMIT", raising=False)
        result = _FakeResult(metadata={"sdk_error_kind": "api_quota", "sdk_stderr": "oops"})
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        assert out == ""

    def test_env_empty_emits_nothing(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "")
        result = _FakeResult(metadata={"sdk_error_kind": "api_quota", "sdk_stderr": "oops"})
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        assert out == ""


# ---------------------------------------------------------------------------
# Metadata presence gate: nothing emits when neither field is set
# ---------------------------------------------------------------------------


class TestMetadataGate:
    def test_no_metadata_attr_emits_nothing(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        # Object without a ``metadata`` attribute — common for old WorkflowResult shapes.
        out = _capture(lambda: _emit_run_meta_for_daemon(object()))
        assert out == ""

    def test_non_dict_metadata_emits_nothing(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        result = _FakeResult(metadata="not a dict")  # type: ignore[arg-type]
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        assert out == ""

    def test_empty_metadata_emits_nothing(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        result = _FakeResult(metadata={})
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        assert out == ""

    def test_metadata_without_sdk_keys_emits_nothing(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        result = _FakeResult(metadata={"some_other_field": "value"})
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        assert out == ""


# ---------------------------------------------------------------------------
# Happy path: env set + metadata present -> emits version + field lines
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_emits_version_and_kind_only(self, monkeypatch):
        """Only ``sdk_error_kind`` present -> version line + that field."""
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        result = _FakeResult(metadata={"sdk_error_kind": "auth"})
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        lines = out.strip().split("\n")
        assert lines[0].startswith("ATTUNE_RUN_META_VERSION ")
        assert "ATTUNE_RUN_META sdk_error_kind=auth" in lines
        # No stderr_b64 line because stderr wasn't in metadata
        assert not any("sdk_stderr_b64" in line for line in lines)

    def test_emits_version_and_stderr_only(self, monkeypatch):
        """Only ``sdk_stderr`` present -> version line + base64 stderr line."""
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        stderr = "Error: connection refused\nat tcp/127.0.0.1:5000\n"
        result = _FakeResult(metadata={"sdk_stderr": stderr})
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        lines = out.strip().split("\n")
        assert lines[0].startswith("ATTUNE_RUN_META_VERSION ")
        # Find the b64 line and verify it decodes back to the original
        b64_lines = [line for line in lines if line.startswith("ATTUNE_RUN_META sdk_stderr_b64=")]
        assert len(b64_lines) == 1
        encoded = b64_lines[0].split("=", 1)[1]
        assert base64.b64decode(encoded).decode("utf-8") == stderr

    def test_emits_both_when_both_present(self, monkeypatch):
        """Both fields present -> version + kind + stderr_b64."""
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        stderr = "anthropic.RateLimitError: 429"
        result = _FakeResult(metadata={"sdk_error_kind": "rate_limit", "sdk_stderr": stderr})
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        lines = out.strip().split("\n")
        assert len(lines) == 3  # version + kind + stderr
        assert lines[0].startswith("ATTUNE_RUN_META_VERSION ")
        assert any("sdk_error_kind=rate_limit" in line for line in lines)
        b64_lines = [line for line in lines if "sdk_stderr_b64=" in line]
        assert len(b64_lines) == 1
        encoded = b64_lines[0].split("=", 1)[1]
        assert base64.b64decode(encoded).decode("utf-8") == stderr

    def test_round_trip_via_runner_parser(self, monkeypatch):
        """End-to-end: emitter output parses cleanly via the runner-side
        parse_line — this guards against any wire-format drift between the
        CLI emitter and the runner consumer."""
        from attune.ops import run_meta_stdout

        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        stderr = "complex multi-line stderr\nwith unicode: ⚠️\n"
        result = _FakeResult(metadata={"sdk_error_kind": "schema_rejected", "sdk_stderr": stderr})
        out = _capture(lambda: _emit_run_meta_for_daemon(result))

        decoded_kind = None
        decoded_stderr = None
        for line in out.strip().split("\n"):
            parsed = run_meta_stdout.parse_line(line)
            if parsed is None:
                continue
            if parsed["event"] == "field":
                if parsed["key"] == "sdk_error_kind":
                    decoded_kind = parsed["value"]
                elif parsed["key"] == "sdk_stderr_b64":
                    decoded_stderr = run_meta_stdout.decode_stderr(parsed["value"])
        assert decoded_kind == "schema_rejected"
        assert decoded_stderr == stderr


class TestEmissionFailureIsNonFatal:
    """Regression: a pipe error during meta emission (EPIPE, non-blocking
    EAGAIN edge) must not turn a succeeded run into exit 1 — the report
    already exists; emission is daemon-side plumbing."""

    def test_oserror_during_emission_is_swallowed(self, monkeypatch, capsys):
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")

        from attune.ops import run_meta_stdout

        def boom() -> None:
            raise BlockingIOError(35, "write could not complete without blocking")

        monkeypatch.setattr(run_meta_stdout, "emit_version_line", boom)
        result = _FakeResult(metadata={"sdk_error_kind": "auth"})

        _emit_run_meta_for_daemon(result)  # must not raise

        err = capsys.readouterr().err
        assert "run-meta emission failed" in err
