"""Smoke tests for attune.context module."""


class TestContextImports:
    """Verify the context package exports are importable."""

    def test_import_package(self):
        """Test that the context package imports cleanly."""
        from attune.context import (
            CompactionStateManager,
            ContextManager,
            SBARHandoff,
        )

        assert ContextManager is not None
        assert CompactionStateManager is not None
        assert SBARHandoff is not None

    def test_sbar_handoff_dataclass(self):
        """Test SBARHandoff instantiation and to_dict."""
        from attune.context.compaction import SBARHandoff

        handoff = SBARHandoff(
            situation="Reviewing PR #42",
            background="Auth module changes",
            assessment="Looks good overall",
            recommendation="Merge after fixing typo",
        )
        assert handoff.priority == "normal"
        d = handoff.to_dict()
        assert d["situation"] == "Reviewing PR #42"

    def test_pattern_summary_roundtrip(self):
        """Test PatternSummary serialization roundtrip."""
        from attune.context.compaction import PatternSummary

        original = PatternSummary(
            pattern_type="preference",
            trigger="test",
            action="do thing",
            confidence=0.8,
            occurrences=3,
        )
        d = original.to_dict()
        restored = PatternSummary.from_dict(d)
        assert restored.confidence == 0.8
        assert restored.trigger == "test"

    def test_context_manager_instantiation(self, tmp_path):
        """Test ContextManager can be created with a temp dir."""
        from attune.context.manager import ContextManager

        mgr = ContextManager(
            storage_dir=str(tmp_path / "compact"),
            token_threshold=50,
        )
        assert mgr is not None
