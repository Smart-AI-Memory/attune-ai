"""Token Budget Allocator for Attune AI.

Manages dynamic allocation of full source code vs. AST skeletal context
based on token budget constraints and target file prioritization.
"""

import logging

from .skeleton import ASTSkeletonGenerator

logger = logging.getLogger(__name__)


class TokenBudgetAllocator:
    """Balances full source inclusion vs. AST skeletal compression."""

    def __init__(self, default_token_limit: int = 4000) -> None:
        """Initialize TokenBudgetAllocator.

        Args:
            default_token_limit: Maximum estimated token budget for context.
        """
        self.default_token_limit = default_token_limit
        self.generator = ASTSkeletonGenerator()

    def allocate_context(
        self,
        files: dict[str, str],
        primary_target: str | None = None,
        token_limit: int | None = None,
    ) -> dict[str, str]:
        """Allocates context format (full vs skeleton) across files.

        The primary target always retains full source, even when it
        alone exceeds the budget (a warning is logged in that case).
        Remaining files receive skeletons while budget lasts, then an
        omission stub.

        Args:
            files: Dictionary mapping file paths to full source code.
            primary_target: Target path that should retain full source.
            token_limit: Custom token limit override.

        Returns:
            Dictionary mapping file paths to allocated context string
            (full source, skeleton, or omission stub).
        """
        limit = token_limit or self.default_token_limit
        allocated: dict[str, str] = {}
        current_tokens = 0

        if primary_target and primary_target in files:
            full_code = files[primary_target]
            allocated[primary_target] = full_code
            current_tokens += self._estimate_tokens(full_code)
            if current_tokens > limit:
                logger.warning(
                    "allocator: primary target %s alone exceeds token limit "
                    "(%d > %d); all other files will be stubbed",
                    primary_target,
                    current_tokens,
                    limit,
                )

        for path, code in files.items():
            if path == primary_target:
                continue

            skeleton = self.generator.generate_skeleton(code)
            skel_tokens = self._estimate_tokens(skeleton)

            if current_tokens + skel_tokens <= limit:
                allocated[path] = skeleton
                current_tokens += skel_tokens
            else:
                allocated[path] = f"# AST skeleton omitted (token limit {limit} reached)\n"

        return allocated

    def fit_source(self, source: str, token_limit: int | None = None) -> str:
        """Fit a single source string into the token budget.

        The ladder: full source when it fits; the AST skeleton when
        that fits (preserving every signature and docstring while
        dropping bodies); otherwise the skeleton head-truncated to
        the budget with an omission marker. Non-Python source passes
        through the skeleton step unchanged, so it degrades to plain
        truncation.

        This is the single-string counterpart to
        :meth:`allocate_context` — use it where a prompt embeds one
        file's source under a budget, in place of a bare character
        slice that chops the tail of the module off mid-function.

        Args:
            source: Source code (or arbitrary text) to fit.
            token_limit: Custom token limit override.

        Returns:
            The source, its skeleton, or a truncated skeleton,
            whichever is the richest representation within budget.
        """
        limit = token_limit or self.default_token_limit
        if self._estimate_tokens(source) <= limit:
            return source
        skeleton = self.generator.generate_skeleton(source)
        if self._estimate_tokens(skeleton) <= limit:
            return skeleton
        return skeleton[: limit * 4] + f"\n# ... truncated at token limit {limit}\n"

    def _estimate_tokens(self, text: str) -> int:
        """Heuristic token estimation (approx 4 chars per token)."""
        return len(text) // 4
