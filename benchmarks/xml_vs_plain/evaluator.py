"""Quality evaluator for benchmark results.

Scores benchmark results on 5 automated metrics by comparing against
known expected findings in each sample.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from collections import defaultdict

from benchmarks.xml_vs_plain.config import (
    BenchmarkResult,
    BenchmarkSample,
    QualityScore,
)

logger = logging.getLogger(__name__)


class QualityEvaluator:
    """Evaluates benchmark results against ground truth.

    Computes 5 quality metrics:
    1. Parsing score — did response parse into structured format?
    2. Completeness — did it find the expected findings?
    3. Precision — what fraction of reported findings are real?
    4. Actionability — do findings include location AND fix?
    5. Consistency — how similar are results across repeated runs?
    """

    def evaluate_single(
        self,
        result: BenchmarkResult,
        sample: BenchmarkSample,
    ) -> QualityScore:
        """Score a single benchmark result.

        Args:
            result: The benchmark result to evaluate.
            sample: The original sample with expected findings.

        Returns:
            QualityScore with all metrics except consistency.
        """
        # 1. Parsing score
        parsing_score = 1.0 if result.xml_parse_success else 0.0

        # 2. Completeness: expected findings detected / total expected
        completeness_score = self._score_completeness(result, sample)

        # 3. Precision: matched findings / total reported
        precision_score = self._score_precision(result, sample)

        # 4. Actionability: findings with location AND fix / total
        actionability_score = self._score_actionability(result)

        return QualityScore(
            parsing_score=parsing_score,
            completeness_score=completeness_score,
            precision_score=precision_score,
            actionability_score=actionability_score,
            consistency_score=0.0,  # Set later via evaluate_consistency
        )

    def evaluate_consistency(
        self,
        results: list[BenchmarkResult],
    ) -> float:
        """Score consistency across repeated runs of the same sample.

        Uses Jaccard similarity of finding categories across runs.

        Args:
            results: Multiple runs of the same sample (same sample_id,
                     same xml_enabled, same model).

        Returns:
            Consistency score 0.0-1.0.
        """
        if len(results) < 2:
            return 1.0  # Single run is perfectly consistent with itself

        # Extract finding categories from each run
        category_sets: list[set[str]] = []
        for result in results:
            categories = set()
            for sev, count in result.findings_by_severity.items():
                categories.add(sev)
            # Also use findings_count as a signal
            categories.add(f"count:{result.findings_count}")
            category_sets.append(categories)

        # Pairwise Jaccard similarity
        similarities: list[float] = []
        for i in range(len(category_sets)):
            for j in range(i + 1, len(category_sets)):
                a, b = category_sets[i], category_sets[j]
                if not a and not b:
                    similarities.append(1.0)
                elif not a or not b:
                    similarities.append(0.0)
                else:
                    intersection = len(a & b)
                    union = len(a | b)
                    similarities.append(intersection / union if union > 0 else 0.0)

        return sum(similarities) / len(similarities) if similarities else 1.0

    def evaluate_all(
        self,
        results: list[BenchmarkResult],
        samples: dict[str, BenchmarkSample],
    ) -> list[BenchmarkResult]:
        """Evaluate all results and attach quality scores.

        Args:
            results: All benchmark results.
            samples: Mapping of sample_id to BenchmarkSample.

        Returns:
            Same results list with quality_score populated.
        """
        # First pass: individual scoring
        for result in results:
            sample = samples.get(result.sample_id)
            if sample:
                result.quality_score = self.evaluate_single(result, sample)

        # Second pass: consistency scoring (group by sample + xml_enabled + model)
        groups: dict[str, list[BenchmarkResult]] = defaultdict(list)
        for result in results:
            key = f"{result.sample_id}:{result.xml_enabled}:{result.model}"
            groups[key].append(result)

        for group_results in groups.values():
            if len(group_results) > 1:
                consistency = self.evaluate_consistency(group_results)
                for result in group_results:
                    if result.quality_score:
                        result.quality_score.consistency_score = consistency

        return results

    def _score_completeness(
        self,
        result: BenchmarkResult,
        sample: BenchmarkSample,
    ) -> float:
        """Score completeness: how many expected findings were detected.

        For "hard" samples (clean code with no expected findings),
        returns 1.0 if no findings reported, 0.0 if any reported.
        """
        expected = [f for f in sample.expected_findings if f.required]
        if not expected:
            # Clean code sample — score based on false positive rate
            return 1.0 if result.findings_count == 0 else 0.0

        # Check if response contains evidence of each expected finding
        response_lower = result.raw_response.lower()
        found = 0
        for exp in expected:
            # Check if the category or a close variant appears in the response
            category_terms = exp.category.replace("_", " ").split()
            if any(term in response_lower for term in category_terms):
                found += 1
            elif exp.location_hint.lower() in response_lower:
                found += 1

        return found / len(expected) if expected else 1.0

    def _score_precision(
        self,
        result: BenchmarkResult,
        sample: BenchmarkSample,
    ) -> float:
        """Score precision: fraction of reported findings that match expected.

        For clean code samples, any finding is a false positive (score 0).
        """
        if result.findings_count == 0:
            return 1.0 if not sample.expected_findings else 0.0

        if not sample.expected_findings:
            # Clean code — all findings are false positives
            return 0.0

        # Generous matching: if we have N expected and M reported,
        # precision = min(N, M) / M (assumes reported findings are real
        # up to the expected count)
        n_expected = len(sample.expected_findings)
        n_reported = result.findings_count
        return min(n_expected, n_reported) / n_reported

    def _score_actionability(self, result: BenchmarkResult) -> float:
        """Score actionability based on parsed findings.

        Checks if findings have location AND fix information.
        Falls back to text analysis if parsing failed.
        """
        if result.findings_count == 0:
            return 1.0  # No findings to evaluate

        # Heuristic: check if response contains location and fix patterns
        response = result.raw_response.lower()
        has_locations = any(
            term in response for term in ["line ", "function ", "method ", "class "]
        )
        has_fixes = any(
            term in response for term in ["fix:", "replace", "instead", "use ", "should "]
        )

        if has_locations and has_fixes:
            return 1.0
        elif has_locations or has_fixes:
            return 0.5
        return 0.0
