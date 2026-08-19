"""Regression guard for the attune.context public surface.

docs/specs/context-compaction-retirement R5 (D1, 2026-08-18): the
dormant compaction stack (ContextManager, CompactionStateManager,
CompactState, WorkHandoff, ContextInflater) was deleted. This guard
pins the package's public surface to the live trio's exports so the
retired half cannot silently return.
"""

import attune.context


class TestPublicSurface:
    """Pin attune.context.__all__ to the ruled surviving set."""

    def test_all_is_exactly_the_live_surface(self):
        assert sorted(attune.context.__all__) == [
            "ASTSkeletonGenerator",
            "TokenBudgetAllocator",
        ]

    def test_retired_names_are_gone(self):
        for retired in (
            "ContextManager",
            "CompactionStateManager",
            "CompactState",
            "WorkHandoff",
            "ContextInflater",
        ):
            assert not hasattr(attune.context, retired)
