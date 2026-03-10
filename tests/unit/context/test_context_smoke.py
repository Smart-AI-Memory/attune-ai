"""Smoke tests for context.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestImports:
    """Verify module can be imported."""

    def test_module_imports(self) -> None:
        """Test that the module imports without error."""
        import attune.context

        assert attune.context is not None

    def test_compaction_classes_import(self) -> None:
        """Test that compaction classes import."""
        from attune.context import CompactionStateManager, CompactState, SBARHandoff

        assert CompactionStateManager is not None
        assert CompactState is not None
        assert SBARHandoff is not None

    def test_context_manager_imports(self) -> None:
        """Test that ContextManager imports."""
        from attune.context import ContextManager

        assert ContextManager is not None


@pytest.mark.unit
class TestInstantiation:
    """Verify main classes can be instantiated."""

    def test_context_manager_defaults(self, tmp_path) -> None:
        """Test ContextManager with temp dir."""
        from attune.context import ContextManager

        manager = ContextManager(storage_dir=str(tmp_path / "compact"))
        assert manager is not None
        assert manager.session_id == ""

    def test_compaction_state_manager(self, tmp_path) -> None:
        """Test CompactionStateManager with temp dir."""
        from attune.context import CompactionStateManager

        csm = CompactionStateManager(storage_dir=str(tmp_path / "states"))
        assert csm is not None

    def test_sbar_handoff_creation(self) -> None:
        """Test SBARHandoff dataclass creation."""
        from attune.context import SBARHandoff

        handoff = SBARHandoff(
            situation="Running code review",
            background="PR #42 has 15 files",
            assessment="3 security issues found",
            recommendation="Fix auth module first",
        )
        assert handoff.priority == "normal"
        d = handoff.to_dict()
        assert d["situation"] == "Running code review"

    def test_context_manager_session_property(self, tmp_path) -> None:
        """Test ContextManager session_id getter/setter."""
        from attune.context import ContextManager

        manager = ContextManager(storage_dir=str(tmp_path / "compact"))
        manager.session_id = "test-session-123"
        assert manager.session_id == "test-session-123"
