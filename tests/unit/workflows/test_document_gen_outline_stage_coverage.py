"""Coverage-completing tests for OutlineStageMixin._detect_auth_strategy.

The existing suite covers parsing, file reading, and the import-error
path; this file covers the auth-strategy happy path (module-size
detection from a target file and from inline content, both cost-logging
branches, and the zero-lines skip) plus the enabled call-site in
``_outline``.

The three ``attune.models`` helpers are imported inside the method, so
they are patched on ``attune.models`` to drive the branches
deterministically without depending on real strategy thresholds.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.document_gen.outline_stage import OutlineStageMixin


class _FakeHost(OutlineStageMixin):
    """Minimal host with auth strategy enabled."""

    def __init__(self) -> None:
        self.enable_auth_strategy: bool = True
        self._auth_mode_used: str | None = None

    async def _call_llm(self, tier, system, user_msg, max_tokens=1000):
        return "1. Introduction\n", 100, 200


def _patch_auth(mode_value, *, module_lines=120):
    """Patch the three attune.models helpers used by _detect_auth_strategy.

    Returns a context-manager stack via unittest.mock.patch as a tuple of
    patchers the caller enters.
    """
    mode = MagicMock()
    mode.value = mode_value
    strategy = MagicMock()
    strategy.get_recommended_mode.return_value = mode
    strategy.estimate_cost.return_value = {
        "quota_cost": "1 request",
        "fits_in_context": "200k",
        "monetary_cost": 0.0123,
    }
    return strategy


@pytest.fixture
def host() -> _FakeHost:
    return _FakeHost()


@pytest.mark.unit
class TestDetectAuthStrategyHappyPath:
    """The auth-detection body (lines 157-187)."""

    def test_content_only_subscription_branch(self, host: _FakeHost) -> None:
        strategy = _patch_auth("subscription")
        with (
            patch("attune.models.get_auth_strategy", return_value=strategy),
            patch("attune.models.get_module_size_category", return_value="small"),
            patch("attune.models.count_lines_of_code", return_value=0),
        ):
            # No target file -> counts non-comment, non-blank content lines.
            host._detect_auth_strategy("", "def a():\n    return 1\n# comment\n")

        assert host._auth_mode_used == "subscription"
        strategy.get_recommended_mode.assert_called_once()

    def test_target_file_api_branch(self, host: _FakeHost, tmp_path: Path) -> None:
        f = tmp_path / "big.py"
        f.write_text("x = 1\n", encoding="utf-8")
        strategy = _patch_auth("api")
        with (
            patch("attune.models.get_auth_strategy", return_value=strategy),
            patch("attune.models.get_module_size_category", return_value="huge"),
            patch("attune.models.count_lines_of_code", return_value=5000) as cloc,
        ):
            host._detect_auth_strategy(str(f), "content")

        # Existing target file -> count_lines_of_code path (lines 158-159).
        cloc.assert_called_once_with(str(f))
        assert host._auth_mode_used == "api"

    def test_zero_lines_skips_strategy(self, host: _FakeHost) -> None:
        strategy = _patch_auth("subscription")
        with (
            patch("attune.models.get_auth_strategy", return_value=strategy),
            patch("attune.models.get_module_size_category", return_value="small"),
            patch("attune.models.count_lines_of_code", return_value=0),
        ):
            # Only comments/blank lines -> module_lines == 0 -> block skipped.
            host._detect_auth_strategy("", "# only a comment\n\n")

        assert host._auth_mode_used is None
        strategy.get_recommended_mode.assert_not_called()

    def test_exception_is_swallowed(self, host: _FakeHost) -> None:
        with patch("attune.models.get_auth_strategy", side_effect=RuntimeError("boom")):
            # Non-comment content so module_lines > 0 and the strategy runs.
            host._detect_auth_strategy("", "real code line\n")

        # Error caught internally; mode left unset, no raise.
        assert host._auth_mode_used is None


@pytest.mark.unit
class TestOutlineRunsAuthDetection:
    """_outline calls _detect_auth_strategy when enabled (line 44)."""

    @pytest.mark.asyncio
    async def test_outline_triggers_auth_detection(self, host: _FakeHost) -> None:
        strategy = _patch_auth("subscription")
        with (
            patch("attune.models.get_auth_strategy", return_value=strategy),
            patch("attune.models.get_module_size_category", return_value="small"),
            patch("attune.models.count_lines_of_code", return_value=0),
        ):
            result, _, _ = await host._outline(
                {"source_code": "def f():\n    return 2\n", "doc_type": "api", "audience": "devs"},
                ModelTier.CHEAP,
            )

        assert "outline" in result
        assert host._auth_mode_used == "subscription"
