"""Context Management for Attune AI

Token-budget fitting for LLM prompts: AST skeletons that preserve
every signature and docstring when full source exceeds a budget
(see ``TokenBudgetAllocator.fit_source``).

The former compaction-state stack (ContextManager,
CompactionStateManager, CompactState, WorkHandoff, ContextInflater)
was retired by docs/specs/context-compaction-retirement (D1/D2,
2026-08-18); recover it from git history if ever needed.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune.context.allocator import TokenBudgetAllocator
from attune.context.skeleton import ASTSkeletonGenerator

__all__ = [
    "ASTSkeletonGenerator",
    "TokenBudgetAllocator",
]
