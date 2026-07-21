"""Ambiguity Evaluator for Attune AI.

Evaluates user prompt clarity and parameter completeness to assign an
Intent Clarity score from 1 (highly ambiguous) to 5 (highly explicit).
"""

import re


class AmbiguityEvaluator:
    """Evaluates prompt specificity and parameter completeness."""

    GENERIC_PROMPT_KEYWORDS: frozenset[str] = frozenset(
        {
            "fix this",
            "clean up",
            "make it work",
            "do it",
            "refactor",
            "update code",
            "improve performance",
        }
    )

    # Matched on word boundaries so "line" does not fire on "pipeline"
    # and "test" does not fire on "latest".
    _SPECIFIC_INDICATORS = re.compile(r"\b(file|line|class|function|module|test|return|type)\b")

    def evaluate_prompt(self, user_prompt: str, target_path: str | None = None) -> int:
        """Evaluates user prompt clarity.

        Args:
            user_prompt: Raw prompt text provided by the user.
            target_path: Target path if explicitly specified.

        Returns:
            Clarity score integer between 1 (ambiguous) and 5 (explicit).
        """
        if not user_prompt or not user_prompt.strip():
            return 1

        prompt_clean = user_prompt.strip().lower()
        score = 3  # Neutral default

        # Explicit target path boosts clarity
        if target_path and target_path.strip():
            score += 1

        # Short prompts built around a generic phrase are ambiguous
        if len(prompt_clean) < 30 and any(
            generic in prompt_clean for generic in self.GENERIC_PROMPT_KEYWORDS
        ):
            score -= 2

        # Structured prompts naming files/lines/functions boost clarity
        if len(set(self._SPECIFIC_INDICATORS.findall(prompt_clean))) >= 3:
            score += 1

        return min(5, max(1, score))
