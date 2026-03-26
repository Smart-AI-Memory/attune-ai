"""Unit tests for attune.workflows.release_prep_stages module.

Tests cover:
- ReleasePrepStagesMixin._health: lint/type/test checks, health scoring
- ReleasePrepStagesMixin._security: bandit scanning, finding parsing
- ReleasePrepStagesMixin._crew_security: fallback and merge logic
- ReleasePrepStagesMixin._changelog: commit parsing and categorization

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.release_prep_stages import ReleasePrepStagesMixin


class _FakeHost(ReleasePrepStagesMixin):
    """Minimal host class providing attributes expected by the mixin."""

    def __init__(self) -> None:
        self.enable_auth_strategy: bool = False
        self._has_blockers: bool = False
        self._auth_mode_used: str | None = None
        self.crew_config: dict = {}


# ---------------------------------------------------------------------------
# _health stage
# ---------------------------------------------------------------------------


class TestHealthStage:
    """Tests for ReleasePrepStagesMixin._health."""

    @pytest.fixture
    def host(self) -> _FakeHost:
        """Create a mixin host with auth strategy disabled."""
        return _FakeHost()

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    @patch("attune.workflows.release_prep_stages._validate_file_path")
    async def test_health_all_pass(
        self,
        mock_validate: MagicMock,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test health returns score 100 when all checks pass."""
        mock_validate.return_value = "."

        # lint, type, test all return 0
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        result, in_t, out_t = await host._health({"path": "."}, ModelTier.CHEAP)

        assert result["health"]["passed"] is True
        assert result["health"]["health_score"] == 100
        assert result["health"]["failed_checks"] == []
        assert host._has_blockers is False

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    @patch("attune.workflows.release_prep_stages._validate_file_path")
    async def test_health_lint_fails(
        self,
        mock_validate: MagicMock,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test health score decreases and blockers set when lint fails."""
        mock_validate.return_value = "."

        def side_effect(cmd, **kwargs):
            """Return different results per command."""
            if "ruff" in cmd:
                return MagicMock(returncode=1, stdout="error", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        result, _, _ = await host._health({"path": "."}, ModelTier.CHEAP)

        assert "lint" in result["health"]["failed_checks"]
        assert result["health"]["health_score"] == 80
        assert host._has_blockers is True

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    @patch("attune.workflows.release_prep_stages._validate_file_path")
    async def test_health_timeout_skips_check(
        self,
        mock_validate: MagicMock,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that subprocess timeout results in skipped check."""
        import subprocess

        mock_validate.return_value = "."
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 60)

        result, _, _ = await host._health({"path": "."}, ModelTier.CHEAP)

        # All checks should be skipped but marked as passed
        for check in result["health"]["checks"].values():
            assert check["skipped"] is True
        assert result["health"]["health_score"] == 100

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    @patch("attune.workflows.release_prep_stages._validate_file_path")
    async def test_health_default_path(
        self,
        mock_validate: MagicMock,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test health uses '.' as default path when not specified."""
        mock_validate.return_value = "."
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result, _, _ = await host._health({}, ModelTier.CHEAP)

        mock_validate.assert_called_once_with(".")


# ---------------------------------------------------------------------------
# _security stage
# ---------------------------------------------------------------------------


class TestSecurityStage:
    """Tests for ReleasePrepStagesMixin._security."""

    @pytest.fixture
    def host(self) -> _FakeHost:
        """Create a mixin host."""
        return _FakeHost()

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_security_no_issues(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test security scan with no findings."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"results": []}),
            stderr="",
        )

        result, _, _ = await host._security({"path": "."}, ModelTier.CHEAP)

        assert result["security"]["passed"] is True
        assert result["security"]["total_issues"] == 0
        assert host._has_blockers is False

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_security_high_finding_sets_blockers(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that high severity findings set _has_blockers."""
        bandit_output = {
            "results": [
                {
                    "test_id": "B101",
                    "filename": "test.py",
                    "line_number": 10,
                    "issue_severity": "HIGH",
                    "issue_text": "Use of eval()",
                    "issue_confidence": "HIGH",
                },
            ],
        }
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=json.dumps(bandit_output),
            stderr="",
        )

        result, _, _ = await host._security({"path": "."}, ModelTier.CHEAP)

        assert result["security"]["high_severity"] == 1
        assert result["security"]["passed"] is False
        assert host._has_blockers is True

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_security_medium_findings(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test medium severity findings don't set blockers."""
        bandit_output = {
            "results": [
                {
                    "test_id": "B105",
                    "filename": "cfg.py",
                    "line_number": 5,
                    "issue_severity": "MEDIUM",
                    "issue_text": "Hardcoded password",
                    "issue_confidence": "MEDIUM",
                },
            ],
        }
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=json.dumps(bandit_output),
            stderr="",
        )

        result, _, _ = await host._security({"path": "."}, ModelTier.CHEAP)

        assert result["security"]["medium_severity"] == 1
        assert result["security"]["passed"] is True  # no HIGH
        assert host._has_blockers is False

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_security_invalid_json_handled(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test handling of non-JSON bandit output."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="not json",
            stderr="",
        )

        result, _, _ = await host._security({"path": "."}, ModelTier.CHEAP)

        assert result["security"]["total_issues"] == 0

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_security_timeout_handled(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that timeout is handled gracefully."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("bandit", 120)

        result, _, _ = await host._security({"path": "."}, ModelTier.CHEAP)

        assert result["security"]["total_issues"] == 0
        assert result["security"]["passed"] is True


# ---------------------------------------------------------------------------
# _crew_security stage
# ---------------------------------------------------------------------------


class TestCrewSecurityStage:
    """Tests for ReleasePrepStagesMixin._crew_security."""

    @pytest.fixture
    def host(self) -> _FakeHost:
        """Create a mixin host."""
        return _FakeHost()

    @pytest.mark.asyncio
    async def test_crew_security_import_error_fallback(
        self,
        host: _FakeHost,
    ) -> None:
        """Test fallback when security_adapters is not importable."""
        with patch.dict(
            "sys.modules",
            {"attune.workflows.security_adapters": None},
        ):
            # Force re-import to hit ImportError
            result, in_t, out_t = await host._crew_security({"path": "."}, ModelTier.CHEAP)

            assert result["crew_security"]["available"] is False
            assert result["crew_security"]["fallback"] is True

    @pytest.mark.asyncio
    async def test_crew_security_not_available(
        self,
        host: _FakeHost,
    ) -> None:
        """Test fallback when crew is not available."""
        # The imports are lazy inside _crew_security, so we mock the
        # security_adapters module to control _check_crew_available.
        import types

        mock_adapters = types.ModuleType("attune.workflows.security_adapters")
        mock_adapters._check_crew_available = lambda: False
        mock_adapters._get_crew_audit = AsyncMock()
        mock_adapters.crew_report_to_workflow_format = MagicMock()
        mock_adapters.merge_security_results = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "attune.workflows.security_adapters": mock_adapters,
            },
        ):
            result, _, _ = await host._crew_security({"path": "."}, ModelTier.CHEAP)

        assert result["crew_security"]["available"] is False
        assert result["crew_security"]["fallback"] is True


# ---------------------------------------------------------------------------
# _changelog stage
# ---------------------------------------------------------------------------


class TestChangelogStage:
    """Tests for ReleasePrepStagesMixin._changelog."""

    @pytest.fixture
    def host(self) -> _FakeHost:
        """Create a mixin host."""
        return _FakeHost()

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_changelog_parses_commits(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that git log output is parsed into categorized commits."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123 feat: add feature\ndef456 fix: bug fix\nghi789 docs: update readme\n",
            stderr="",
        )

        result, _, _ = await host._changelog({"path": "."}, ModelTier.CHEAP)

        changelog = result["changelog"]
        assert changelog["total_commits"] == 3
        assert "features" in changelog["by_category"]
        assert "fixes" in changelog["by_category"]
        assert "docs" in changelog["by_category"]

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_changelog_categorizes_types(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test all conventional commit types are categorized."""
        lines = [
            "a1 feat: x",
            "a2 fix: y",
            "a3 docs: z",
            "a4 refactor: w",
            "a5 test: q",
            "a6 chore: r",
            "a7 unknown prefix",
        ]
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="\n".join(lines),
            stderr="",
        )

        result, _, _ = await host._changelog({"path": "."}, ModelTier.CHEAP)

        cats = result["changelog"]["by_category"]
        assert cats["features"] == 1
        assert cats["fixes"] == 1
        assert cats["docs"] == 1
        assert cats["refactor"] == 1
        assert cats["tests"] == 1
        assert cats["chores"] == 1
        assert cats["other"] == 1

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_changelog_empty_output(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test changelog with no commits."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        result, _, _ = await host._changelog({"path": "."}, ModelTier.CHEAP)

        assert result["changelog"]["total_commits"] == 0

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_changelog_uses_since_param(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that 'since' parameter is passed to git log."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        await host._changelog(
            {"path": ".", "since": "2 weeks ago"},
            ModelTier.CHEAP,
        )

        call_args = mock_run.call_args
        assert "--since=2 weeks ago" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_changelog_timeout_handled(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test graceful handling of git timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

        result, _, _ = await host._changelog({"path": "."}, ModelTier.CHEAP)

        assert result["changelog"]["total_commits"] == 0

    @pytest.mark.asyncio
    @patch("attune.workflows.release_prep_stages.subprocess.run")
    async def test_changelog_generated_at_is_iso_format(
        self,
        mock_run: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test generated_at field is ISO format timestamp."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result, _, _ = await host._changelog({"path": "."}, ModelTier.CHEAP)

        # Should not raise
        datetime.fromisoformat(result["changelog"]["generated_at"])
