"""Unit tests for the ATTUNE_RUN_META stdout side-channel.

Spec: docs/specs/sdk-error-message-fidelity/ Phase 3b

Covers the pure formatter / parser surface in
:mod:`attune.ops.run_meta_stdout`. Round-trips verify emitted lines
parse back to the expected event dicts; defensive cases verify
malformed input is rejected rather than silently mis-parsed.

The CLI emit-site (``_print_workflow_result``) and runner consume-site
(``RunnerService.handle_stdout_line``) integrations are covered by
``test_runner.py`` and ``test_phase3b_integration.py``.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout

from attune.ops import run_meta_stdout

# ---------------------------------------------------------------------------
# is_emission_enabled — env-var gate
# ---------------------------------------------------------------------------


class TestEmissionGate:
    def test_unset_env_is_disabled(self, monkeypatch):
        monkeypatch.delenv(run_meta_stdout.EMIT_ENV, raising=False)
        assert run_meta_stdout.is_emission_enabled() is False

    def test_set_env_is_enabled(self, monkeypatch):
        monkeypatch.setenv(run_meta_stdout.EMIT_ENV, "1")
        assert run_meta_stdout.is_emission_enabled() is True

    def test_empty_string_env_is_disabled(self, monkeypatch):
        # Setting to empty string should NOT enable — bool("") is False
        # and the function uses os.environ.get() which preserves empty.
        monkeypatch.setenv(run_meta_stdout.EMIT_ENV, "")
        assert run_meta_stdout.is_emission_enabled() is False

    def test_arbitrary_non_empty_value_enables(self, monkeypatch):
        monkeypatch.setenv(run_meta_stdout.EMIT_ENV, "yes-please")
        assert run_meta_stdout.is_emission_enabled() is True


# ---------------------------------------------------------------------------
# Emit -> parse round-trips
# ---------------------------------------------------------------------------


def _capture_emit(callback) -> str:
    """Run ``callback`` and return whatever it wrote to stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        callback()
    return buf.getvalue()


class TestVersionLineRoundTrip:
    def test_version_line_emits_expected_format(self):
        out = _capture_emit(run_meta_stdout.emit_version_line)
        assert out == f"ATTUNE_RUN_META_VERSION {run_meta_stdout.VERSION}\n"

    def test_version_line_round_trips(self):
        out = _capture_emit(run_meta_stdout.emit_version_line)
        parsed = run_meta_stdout.parse_line(out.rstrip("\n"))
        assert parsed == {"event": "version", "version": run_meta_stdout.VERSION}


class TestFieldLineRoundTrip:
    def test_sdk_error_kind_round_trip(self):
        out = _capture_emit(lambda: run_meta_stdout.emit_field_line("sdk_error_kind", "api_quota"))
        assert out == "ATTUNE_RUN_META sdk_error_kind=api_quota\n"
        parsed = run_meta_stdout.parse_line(out.rstrip("\n"))
        assert parsed == {"event": "field", "key": "sdk_error_kind", "value": "api_quota"}

    def test_sdk_stderr_b64_round_trip(self):
        original = "anthropic.RateLimitError: Error code: 429\nrequest_id: req_abc\n"
        encoded = run_meta_stdout.encode_stderr(original)
        out = _capture_emit(lambda: run_meta_stdout.emit_field_line("sdk_stderr_b64", encoded))
        parsed = run_meta_stdout.parse_line(out.rstrip("\n"))
        assert parsed is not None
        assert parsed["event"] == "field"
        assert parsed["key"] == "sdk_stderr_b64"
        decoded = run_meta_stdout.decode_stderr(parsed["value"])
        assert decoded == original


# ---------------------------------------------------------------------------
# Emit-side defensive paths (silent skip on bad input)
# ---------------------------------------------------------------------------


class TestEmitDefensiveSkips:
    def test_unknown_key_silently_dropped(self):
        out = _capture_emit(lambda: run_meta_stdout.emit_field_line("not_in_allowlist", "value"))
        assert out == ""

    def test_empty_value_silently_dropped(self):
        out = _capture_emit(lambda: run_meta_stdout.emit_field_line("sdk_error_kind", ""))
        assert out == ""

    def test_value_with_newline_silently_dropped(self):
        # Plain-text fields with newlines would corrupt the
        # one-line-per-event grammar.
        out = _capture_emit(
            lambda: run_meta_stdout.emit_field_line("sdk_error_kind", "kind\nwith\nnewlines")
        )
        assert out == ""

    def test_value_with_carriage_return_silently_dropped(self):
        out = _capture_emit(
            lambda: run_meta_stdout.emit_field_line("sdk_error_kind", "kind\rwith\rcr")
        )
        assert out == ""


# ---------------------------------------------------------------------------
# Parse-side defensive paths (None on bad input)
# ---------------------------------------------------------------------------


class TestParseDefensivePaths:
    def test_non_marker_line_returns_none(self):
        assert run_meta_stdout.parse_line("ordinary log line") is None

    def test_empty_string_returns_none(self):
        assert run_meta_stdout.parse_line("") is None

    def test_marker_prefix_only_returns_none(self):
        # "ATTUNE_RUN_META" alone (no body) doesn't match any regex.
        assert run_meta_stdout.parse_line("ATTUNE_RUN_META") is None

    def test_field_with_unknown_key_returns_none(self):
        # The line format is syntactically valid but the key isn't
        # in _ALLOWED_KEYS — parser refuses.
        assert run_meta_stdout.parse_line("ATTUNE_RUN_META not_real_key=foo") is None

    def test_version_line_with_non_integer_returns_none(self):
        # Regex requires \d+ for the version, so a non-numeric value
        # doesn't match.
        assert run_meta_stdout.parse_line("ATTUNE_RUN_META_VERSION abc") is None

    def test_field_line_with_no_value_still_parses(self):
        # `<key>=` (empty value) is syntactically valid per the regex
        # (\S* matches zero-or-more). The consumer is expected to
        # treat empty values as "no info" and skip stashing.
        parsed = run_meta_stdout.parse_line("ATTUNE_RUN_META sdk_error_kind=")
        assert parsed == {"event": "field", "key": "sdk_error_kind", "value": ""}

    def test_handles_trailing_crlf(self):
        # Windows line endings shouldn't break the parser.
        parsed = run_meta_stdout.parse_line("ATTUNE_RUN_META sdk_error_kind=auth\r\n")
        assert parsed == {"event": "field", "key": "sdk_error_kind", "value": "auth"}


# ---------------------------------------------------------------------------
# encode_stderr / decode_stderr round-trips
# ---------------------------------------------------------------------------


class TestStderrCodec:
    def test_empty_string_codec(self):
        assert run_meta_stdout.encode_stderr("") == ""
        assert run_meta_stdout.decode_stderr("") == ""

    def test_simple_ascii_round_trip(self):
        original = "simple ascii stderr"
        encoded = run_meta_stdout.encode_stderr(original)
        assert run_meta_stdout.decode_stderr(encoded) == original

    def test_multiline_unicode_round_trip(self):
        original = "line 1\nline 2 with unicode: ⚠️ 中文\nline 3\n"
        encoded = run_meta_stdout.encode_stderr(original)
        assert run_meta_stdout.decode_stderr(encoded) == original

    def test_shell_special_chars_round_trip(self):
        original = "command failed: rm 'file with $variables' \"and\" quotes && exit 1"
        encoded = run_meta_stdout.encode_stderr(original)
        assert run_meta_stdout.decode_stderr(encoded) == original

    def test_malformed_b64_decodes_to_empty(self):
        # Invalid base64 returns empty string, not an exception —
        # the consumer logs and continues.
        assert run_meta_stdout.decode_stderr("!!! not base64 !!!") == ""

    def test_b64_with_invalid_utf8_payload_uses_replace(self):
        # Valid b64 but the decoded bytes aren't valid UTF-8.
        # The codec uses errors="replace" so we still get a string.
        import base64

        bad_utf8 = base64.b64encode(b"\xff\xfe\xfd").decode("ascii")
        result = run_meta_stdout.decode_stderr(bad_utf8)
        # Should contain replacement characters, not raise.
        assert isinstance(result, str)
        assert len(result) > 0


class TestNonBlockingPipeWrite:
    """Regression: ``report_b64`` lines routinely exceed the 64 KiB pipe
    buffer, and the daemon's pipe can be in non-blocking mode — a plain
    ``sys.stdout.write`` raised ``BlockingIOError`` mid-line and turned
    an otherwise-succeeded run into exit 1 (dashboard run 87d8438e3e8c,
    2026-08-02)."""

    def test_large_line_on_nonblocking_pipe_completes(self, monkeypatch):
        import os
        import sys
        import threading

        if sys.platform == "win32":
            import pytest

            pytest.skip("non-blocking pipes + select() are POSIX semantics")

        read_fd, write_fd = os.pipe()
        os.set_blocking(write_fd, False)
        received: list[bytes] = []

        def drain() -> None:
            while True:
                try:
                    chunk = os.read(read_fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                received.append(chunk)

        reader = threading.Thread(target=drain)
        reader.start()
        writer = os.fdopen(write_fd, "w", encoding="utf-8")
        monkeypatch.setattr(sys, "stdout", writer)
        big_value = "A" * 300_000  # ~5x the default pipe buffer
        try:
            run_meta_stdout.emit_field_line("report_b64", big_value)
        finally:
            monkeypatch.undo()
        writer.close()
        reader.join(timeout=10)
        os.close(read_fd)
        assert not reader.is_alive()
        payload = b"".join(received).decode("utf-8")
        assert payload == f"ATTUNE_RUN_META report_b64={big_value}\n"


class TestFlushRetryAndDeadline:
    """The review of #1904's own fix demanded these: the flush-retry
    BlockingIOError branch was untested (the first regression test
    writes to an empty pipe, so flush succeeds first try), and the
    retry loop needed an elapsed ceiling so a dead-but-unclosed
    reader hangs nothing."""

    @staticmethod
    def _full_nonblocking_pipe():
        import os

        read_fd, write_fd = os.pipe()
        os.set_blocking(write_fd, False)
        try:
            while True:
                os.write(write_fd, b"X" * 65536)
        except BlockingIOError:
            pass
        return read_fd, write_fd

    def test_flush_retry_branch_completes_when_reader_drains(self, monkeypatch):
        import os
        import sys
        import threading
        import time as _time

        if sys.platform == "win32":
            import pytest

            pytest.skip("non-blocking pipes + select() are POSIX semantics")

        read_fd, write_fd = self._full_nonblocking_pipe()
        writer = os.fdopen(write_fd, "w", encoding="utf-8")
        # Park text in the wrapper's buffer so _write's flush hits the
        # full pipe and takes the BlockingIOError retry branch.
        writer.write("BUFFERED|")
        received: list[bytes] = []

        def drain_later() -> None:
            _time.sleep(0.3)
            while True:
                try:
                    chunk = os.read(read_fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                received.append(chunk)

        reader = threading.Thread(target=drain_later)
        reader.start()
        monkeypatch.setattr(sys, "stdout", writer)
        try:
            run_meta_stdout.emit_field_line("sdk_error_kind", "auth")
        finally:
            monkeypatch.undo()
        writer.close()
        reader.join(timeout=10)
        os.close(read_fd)
        assert not reader.is_alive()
        payload = b"".join(received).decode("utf-8")
        assert payload.endswith("BUFFERED|ATTUNE_RUN_META sdk_error_kind=auth\n")

    def test_dead_reader_hits_deadline_not_hang(self, monkeypatch):
        import os
        import sys

        if sys.platform == "win32":
            import pytest

            pytest.skip("non-blocking pipes + select() are POSIX semantics")

        read_fd, write_fd = self._full_nonblocking_pipe()
        writer = os.fdopen(write_fd, "w", encoding="utf-8")
        monkeypatch.setattr(sys, "stdout", writer)
        monkeypatch.setattr(run_meta_stdout, "_WRITE_DEADLINE_S", 0.3)
        monkeypatch.setattr(run_meta_stdout, "_WRITE_WAIT_S", 0.05)
        import pytest

        try:
            with pytest.raises(TimeoutError, match="run-meta write stalled"):
                run_meta_stdout.emit_field_line("sdk_error_kind", "auth")
        finally:
            monkeypatch.undo()
            os.close(read_fd)
            os.close(write_fd)
            # fdopen wrapper's fd is closed above; detach to avoid a
            # double-close in its destructor.
            try:
                writer.detach()
            except (ValueError, OSError):
                pass
