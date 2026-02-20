"""Statistical Analysis for A/B Tests

Provides statistical tests and confidence intervals for comparing
experiment variants including z-tests, t-tests, and Wilson score intervals.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import math


class StatisticalAnalyzer:
    """Statistical analysis for A/B tests."""

    @staticmethod
    def z_test_proportions(
        n1: int,
        c1: int,
        n2: int,
        c2: int,
    ) -> tuple[float, float]:
        """Two-proportion z-test.

        Args:
            n1: Sample size for group 1
            c1: Conversions for group 1
            n2: Sample size for group 2
            c2: Conversions for group 2

        Returns:
            (z_score, p_value)
        """
        if n1 == 0 or n2 == 0:
            return 0.0, 1.0

        p1 = c1 / n1
        p2 = c2 / n2
        p_pooled = (c1 + c2) / (n1 + n2)

        if p_pooled == 0 or p_pooled == 1:
            return 0.0, 1.0

        se = math.sqrt(p_pooled * (1 - p_pooled) * (1 / n1 + 1 / n2))
        if se == 0:
            return 0.0, 1.0

        z = (p1 - p2) / se

        # Approximate p-value using normal CDF
        p_value = 2 * (1 - StatisticalAnalyzer._normal_cdf(abs(z)))

        return z, p_value

    @staticmethod
    def t_test_means(
        n1: int,
        mean1: float,
        var1: float,
        n2: int,
        mean2: float,
        var2: float,
    ) -> tuple[float, float]:
        """Welch's t-test for means.

        Args:
            n1, mean1, var1: Stats for group 1
            n2, mean2, var2: Stats for group 2

        Returns:
            (t_score, p_value)
        """
        if n1 < 2 or n2 < 2:
            return 0.0, 1.0

        se = math.sqrt(var1 / n1 + var2 / n2)
        if se == 0:
            return 0.0, 1.0

        t = (mean1 - mean2) / se

        # Welch-Satterthwaite degrees of freedom
        num = (var1 / n1 + var2 / n2) ** 2
        denom = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
        df = num / denom if denom > 0 else 1

        # Approximate p-value using t-distribution
        p_value = 2 * StatisticalAnalyzer._t_cdf(-abs(t), df)

        return t, p_value

    @staticmethod
    def confidence_interval(
        n: int,
        successes: int,
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        """Wilson score interval for proportions.

        Args:
            n: Sample size
            successes: Number of successes
            confidence: Confidence level

        Returns:
            (lower, upper) bounds
        """
        if n == 0:
            return 0.0, 1.0

        z = StatisticalAnalyzer._z_score(confidence)
        p = successes / n

        denominator = 1 + z * z / n
        centre = p + z * z / (2 * n)
        adjustment = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)

        lower = max(0, (centre - adjustment) / denominator)
        upper = min(1, (centre + adjustment) / denominator)

        return lower, upper

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Approximate standard normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    @staticmethod
    def _t_cdf(t: float, df: float) -> float:
        """Approximate t-distribution CDF."""
        # Use normal approximation for large df
        if df > 30:
            return StatisticalAnalyzer._normal_cdf(t)

        # Beta function approximation
        x = df / (df + t * t)
        return 0.5 * StatisticalAnalyzer._incomplete_beta(df / 2, 0.5, x)

    @staticmethod
    def _incomplete_beta(a: float, b: float, x: float) -> float:
        """Approximate incomplete beta function."""
        if x == 0:
            return 0
        if x == 1:
            return 1

        # Continued fraction approximation (simplified)
        result = 0.0
        for k in range(100):
            term = (x**k) * math.gamma(a + k) / (math.gamma(k + 1) * math.gamma(a))
            result += term * ((1 - x) ** b) / (a + k)
            if abs(term) < 1e-10:
                break

        return result * math.gamma(a + b) / (math.gamma(a) * math.gamma(b))

    @staticmethod
    def _z_score(confidence: float) -> float:
        """Get z-score for confidence level."""
        # Common values
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }
        return z_scores.get(confidence, 1.96)
