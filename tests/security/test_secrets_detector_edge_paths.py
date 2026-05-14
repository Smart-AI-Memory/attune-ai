"""Focused fallback-paths tests for `secrets_detector.py`.

Existing tests (`tests/security/test_secrets_detector.py`, 28
tests) cover 90.96% of the module via real-content pattern
matching. This file closes the remaining ~9% gap on four
specific spots that real content rarely exercises:

| Line(s) | Method | Branch |
|---|---|---|
| 351 | `_create_context_snippet` | invalid line_number guard |
| 363-369 | `_create_context_snippet` | long-line truncation (>max_context_chars) |
| 434 | `_calculate_entropy` | empty string `return 0.0` |
| 466->462 | `_filter_overlapping_detections` | different-line continue |

Strategy: call private methods directly with hand-crafted inputs
that force each branch. Per the test-quality-program "focused
fallback-paths" pattern — leaves the 2,723-line equivalent of
existing surface alone; no rewrites.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from attune.memory.security.secrets_detector import SecretsDetector
from attune.memory.security.secrets_types import (
    SecretDetection,
    SecretType,
    Severity,
)


class TestContextSnippetEdgeCases:
    """Lines 351, 363-369 of `_create_context_snippet`."""

    def test_invalid_line_number_returns_empty(self) -> None:
        # Line 351: `if line_number < 1 or line_number > len(lines): return ""`
        detector = SecretsDetector()
        lines = ["only one line"]

        assert detector._create_context_snippet(lines, 0, 0, 5) == ""
        assert detector._create_context_snippet(lines, -1, 0, 5) == ""
        assert detector._create_context_snippet(lines, 2, 0, 5) == ""
        assert detector._create_context_snippet([], 1, 0, 5) == ""

    def test_long_line_truncation_centers_on_redaction(self) -> None:
        # Lines 363-369: when `len(redacted_line) > self.max_context_chars`,
        # truncate by centering around the redaction column, prepending "..."
        # if the truncation started past 0 and appending "..." if it ended
        # before the line ended.
        detector = SecretsDetector(max_context_chars=30)

        # Build a long line; secret is in the middle so truncation
        # should hit both sides.
        prefix = "a" * 60
        secret = "SECRET_VALUE_HERE"
        suffix = "b" * 60
        line = prefix + secret + suffix
        lines = [line]
        column_start = len(prefix)
        column_end = column_start + len(secret)

        snippet = detector._create_context_snippet(
            lines, line_number=1, column_start=column_start, column_end=column_end
        )

        assert "[REDACTED]" in snippet, "secret must be redacted"
        assert len(snippet) <= 30 + 6, "≈max_context_chars plus ellipses on both ends"
        assert snippet.startswith("..."), "left side truncated"
        assert snippet.endswith("..."), "right side truncated"
        # Ensure the actual secret never leaks.
        assert secret not in snippet

    def test_long_line_truncation_at_left_edge(self) -> None:
        # Branch where `start == 0` so the leading "..." is suppressed
        # but the trailing one fires.
        detector = SecretsDetector(max_context_chars=40)
        secret = "TOKEN_AT_START"
        suffix = "x" * 200
        line = secret + suffix
        lines = [line]

        snippet = detector._create_context_snippet(
            lines, line_number=1, column_start=0, column_end=len(secret)
        )

        assert "[REDACTED]" in snippet
        # Left edge — no leading ellipsis
        assert not snippet.startswith("...")
        assert snippet.endswith("...")

    def test_long_line_truncation_at_right_edge(self) -> None:
        # Branch 368->371: trailing ellipsis suppressed when
        # `end >= len(line)`. `end` is bounded by `len(redacted_line)`,
        # which equals `column_start + 10 + (len(line) - column_end)`.
        # When the secret is SHORTER than "[REDACTED]" (10 chars), the
        # redacted_line ends up LONGER than the original line, so `end`
        # can exceed `len(line)`. Construct a line that triggers
        # truncation and places the secret at the very end with secret
        # length < 10.
        detector = SecretsDetector(max_context_chars=30)
        prefix = "x" * 38
        secret = "abc"  # 3 chars, shorter than "[REDACTED]"
        line = prefix + secret
        lines = [line]

        snippet = detector._create_context_snippet(
            lines,
            line_number=1,
            column_start=len(prefix),
            column_end=len(line),
        )

        assert "[REDACTED]" in snippet
        # Truncation started past column 0 → leading "..." kept.
        assert snippet.startswith("...")
        # Right edge of redacted_line passes len(line) → no trailing
        # ellipsis. This is the branch 368->371 path.
        assert not snippet.endswith("...")
        # Real secret never leaks.
        assert secret not in snippet


class TestCalculateEntropyEmptyString:
    """Line 434: empty string returns 0.0."""

    def test_empty_string_entropy_is_zero(self) -> None:
        detector = SecretsDetector()
        assert detector._calculate_entropy("") == 0.0

    def test_single_char_entropy_is_zero(self) -> None:
        # Single character has zero entropy (probability = 1.0,
        # log2(1.0) = 0). Sanity-anchors the function's correctness
        # alongside the empty-string fallback.
        detector = SecretsDetector()
        assert detector._calculate_entropy("a") == 0.0
        assert detector._calculate_entropy("aaaa") == 0.0


class TestFilterOverlappingDifferentLine:
    """Branch 466->462 of `_filter_overlapping_detections`.

    The `if entropy_detection.line_number == pattern_detection.line_number`
    guard at line 464 — when lines DIFFER, the inner block at 466 is
    skipped and the loop continues to the next pattern_detection.
    Existing tests exercise the same-line branch but not this one.
    """

    @staticmethod
    def _make_detection(
        secret_type: SecretType,
        line_number: int,
        column_start: int,
        column_end: int,
    ) -> SecretDetection:
        return SecretDetection(
            secret_type=secret_type,
            severity=Severity.LOW,
            line_number=line_number,
            column_start=column_start,
            column_end=column_end,
            context_snippet="x",
            confidence=0.5,
            metadata={},
        )

    def test_different_line_does_not_filter_entropy_detection(self) -> None:
        detector = SecretsDetector()
        entropy = [
            self._make_detection(SecretType.HIGH_ENTROPY_STRING, 5, 10, 30),
        ]
        # Pattern detection on a DIFFERENT line — should NOT filter.
        patterns = [
            self._make_detection(SecretType.GENERIC_API_KEY, 1, 10, 30),
        ]

        filtered = detector._filter_overlapping_detections(entropy, patterns)
        assert len(filtered) == 1, "entropy detection on line 5 not overlapped by pattern on line 1"
        assert filtered[0] is entropy[0]

    def test_same_line_no_column_overlap_does_not_filter(self) -> None:
        # Same line but columns disjoint — entropy is kept.
        detector = SecretsDetector()
        entropy = [
            self._make_detection(SecretType.HIGH_ENTROPY_STRING, 3, 50, 70),
        ]
        patterns = [
            self._make_detection(SecretType.GENERIC_API_KEY, 3, 10, 30),
        ]

        filtered = detector._filter_overlapping_detections(entropy, patterns)
        assert len(filtered) == 1

    def test_same_line_with_column_overlap_filters(self) -> None:
        # Sanity anchor for the overlap path that the existing test
        # surface already exercises — locks down the contrast with
        # the different-line + disjoint-column cases above.
        detector = SecretsDetector()
        entropy = [
            self._make_detection(SecretType.HIGH_ENTROPY_STRING, 3, 15, 35),
        ]
        patterns = [
            self._make_detection(SecretType.GENERIC_API_KEY, 3, 10, 30),
        ]

        filtered = detector._filter_overlapping_detections(entropy, patterns)
        assert filtered == []
