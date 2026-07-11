"""Tests for no-signal stderr rendering (setup-friction F1).

When ``capture_subprocess_failure()`` recovers nothing real, the
"unknown" rendering used to point the user at "raw stderr below" that
was just a synthetic placeholder. It now says what the placeholder
means and names the most likely fixes (auth), keyed on whether
``ANTHROPIC_API_KEY`` is present.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.workflows.agent_sdk_adapter import (
    SdkSubprocessError,
    _stderr_carries_no_signal,
)


class TestStderrCarriesNoSignal:
    def test_empty_is_no_signal(self):
        assert _stderr_carries_no_signal("") is True
        assert _stderr_carries_no_signal("   \n ") is True

    def test_synthetic_placeholder_is_no_signal(self):
        assert (
            _stderr_carries_no_signal(
                "(the SDK reported a subprocess failure but exposed no "
                "command or stderr to capture)"
            )
            is True
        )

    def test_exit_marker_is_no_signal(self):
        assert _stderr_carries_no_signal("(claude exited 1 with no stderr/stdout)") is True

    def test_probe_note_plus_marker_is_no_signal(self):
        text = (
            "(could not recover the exact failing command from the SDK; "
            "ran a minimal `claude` health probe instead)\n"
            "(capture-call timed out after 10s)"
        )
        assert _stderr_carries_no_signal(text) is True

    def test_real_stderr_is_signal(self):
        assert _stderr_carries_no_signal("Error: invalid api key (401)") is False

    def test_probe_note_plus_real_output_is_signal(self):
        text = (
            "(could not recover the exact failing command from the SDK; "
            "ran a minimal `claude` health probe instead)\n"
            "Error: not logged in"
        )
        assert _stderr_carries_no_signal(text) is False


class TestFormatUserMessageNoSignal:
    def _err(self) -> SdkSubprocessError:
        return SdkSubprocessError(
            message="The claude CLI subprocess failed; see raw stderr below.",
            stderr=(
                "(the SDK reported a subprocess failure but exposed no "
                "command or stderr to capture)"
            ),
            kind="unknown",
        )

    def test_keyless_names_auth_and_next_steps(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        rendered = self._err().format_user_message()
        assert "ANTHROPIC_API_KEY is not set" in rendered
        assert "attune auth setup" in rendered
        # The dead-end pointer is gone:
        assert "see raw stderr below" not in rendered

    def test_with_key_suggests_invalid(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-something")  # pragma: allowlist secret
        rendered = self._err().format_user_message()
        assert "may be invalid" in rendered

    def test_real_stderr_still_rendered_inline(self):
        err = SdkSubprocessError(
            message="The claude CLI subprocess failed; see raw stderr below.",
            stderr="weird error nobody recognized",
            kind="unknown",
        )
        rendered = err.format_user_message()
        assert "weird error nobody recognized" in rendered


@pytest.mark.parametrize("kind", ["api_quota", "auth", "rate_limit"])
def test_classified_kinds_unchanged(kind):
    err = SdkSubprocessError(message="summary", stderr="blob", kind=kind)  # type: ignore[arg-type]
    assert "/runs/<id>/view" in err.format_user_message()
