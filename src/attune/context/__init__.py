"""Context Management for Attune AI

Strategic compaction to preserve critical state through context window resets.
Ensures trust levels, detected patterns, and session continuity survive compaction events.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune.context.allocator import TokenBudgetAllocator
from attune.context.compaction import CompactionStateManager, CompactState, WorkHandoff
from attune.context.inflater import ContextInflater
from attune.context.manager import ContextManager
from attune.context.skeleton import ASTSkeletonGenerator

__all__ = [
    "ASTSkeletonGenerator",
    "CompactState",
    "CompactionStateManager",
    "ContextInflater",
    "ContextManager",
    "TokenBudgetAllocator",
    "WorkHandoff",
]
