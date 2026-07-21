"""Behavioral tests for the enterprise standard-path branch.

Closes the last uncovered branch in ``attune.memory.claude_memory``
(test-quality-program #1569): ``_load_enterprise_memory`` falling
through env var and config to the Unix standard location
``/etc/claude/CLAUDE.md``. The path is mocked at the module boundary —
tests must never depend on the host's real ``/etc/claude`` state.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.memory.claude_memory import (
    ClaudeMemoryConfig,
    ClaudeMemoryLoader,
    MemoryFile,
)


@pytest.fixture
def loader(monkeypatch: pytest.MonkeyPatch) -> ClaudeMemoryLoader:
    """Loader with no env-var and no config enterprise path set."""
    monkeypatch.delenv("CLAUDE_ENTERPRISE_MEMORY", raising=False)
    return ClaudeMemoryLoader(ClaudeMemoryConfig(enabled=True, enterprise_memory_path=None))


def _fake_standard_path(exists: bool) -> MagicMock:
    fake = MagicMock()
    fake.exists.return_value = exists
    fake.__str__ = MagicMock(return_value="/etc/claude/CLAUDE.md")
    return fake


class TestEnterpriseStandardPath:
    def test_standard_path_loads_when_present(self, loader: ClaudeMemoryLoader) -> None:
        """With no env var and no config path, an existing
        /etc/claude/CLAUDE.md is loaded at enterprise level."""
        sentinel = MemoryFile(
            level="enterprise",
            path="/etc/claude/CLAUDE.md",
            content="org-wide rules",
        )
        with patch(
            "attune.memory.claude_memory.Path",
            return_value=_fake_standard_path(exists=True),
        ):
            with patch.object(loader, "_load_memory_file", return_value=sentinel) as load:
                result = loader._load_enterprise_memory()

        assert result is sentinel
        load.assert_called_once_with("/etc/claude/CLAUDE.md", "enterprise")

    def test_absent_standard_path_returns_none(self, loader: ClaudeMemoryLoader) -> None:
        """No env var, no config path, no standard file → None, and the
        file loader is never invoked."""
        with patch(
            "attune.memory.claude_memory.Path",
            return_value=_fake_standard_path(exists=False),
        ):
            with patch.object(loader, "_load_memory_file") as load:
                result = loader._load_enterprise_memory()

        assert result is None
        load.assert_not_called()

    def test_env_var_wins_over_standard_path(
        self, loader: ClaudeMemoryLoader, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Precedence: CLAUDE_ENTERPRISE_MEMORY short-circuits before
        the standard location is even consulted."""
        monkeypatch.setenv("CLAUDE_ENTERPRISE_MEMORY", "/custom/CLAUDE.md")
        sentinel = MemoryFile(
            level="enterprise",
            path="/custom/CLAUDE.md",
            content="custom",
        )
        with patch.object(loader, "_load_memory_file", return_value=sentinel) as load:
            result = loader._load_enterprise_memory()

        assert result is sentinel
        load.assert_called_once_with("/custom/CLAUDE.md", "enterprise")
