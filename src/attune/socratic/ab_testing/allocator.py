"""Traffic Allocation for A/B Testing

Allocates traffic to experiment variants using various strategies
including fixed splits, epsilon-greedy, Thompson sampling, and UCB.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import math
import random  # Security Note: For A/B test simulation data, not cryptographic use

from .models import AllocationStrategy, Experiment, Variant


class TrafficAllocator:
    """Allocates traffic to experiment variants."""

    def __init__(self, experiment: Experiment):
        """Initialize allocator.

        Args:
            experiment: The experiment to allocate for

        """
        self.experiment = experiment
        self._random = random.Random()

    def allocate(self, user_id: str) -> Variant:
        """Allocate a user to a variant.

        Args:
            user_id: Unique user/session identifier

        Returns:
            Allocated variant

        """
        strategy = self.experiment.allocation_strategy

        if strategy == AllocationStrategy.FIXED:
            return self._fixed_allocation(user_id)
        if strategy == AllocationStrategy.EPSILON_GREEDY:
            return self._epsilon_greedy(epsilon=0.1)
        if strategy == AllocationStrategy.THOMPSON_SAMPLING:
            return self._thompson_sampling()
        if strategy == AllocationStrategy.UCB:
            return self._ucb_allocation()
        return self._fixed_allocation(user_id)

    def _fixed_allocation(self, user_id: str) -> Variant:
        """Deterministic allocation based on user ID hash."""
        # Deterministic bucket assignment using CRC32 (not cryptographic/not for security)
        import zlib

        bucket_key = f"{self.experiment.experiment_id}:{user_id}"
        bucket = zlib.crc32(bucket_key.encode()) % 100

        cumulative = 0.0
        for variant in self.experiment.variants:
            cumulative += variant.traffic_percentage
            if bucket < cumulative:
                return variant

        return self.experiment.variants[-1]

    def _epsilon_greedy(self, epsilon: float = 0.1) -> Variant:
        """Epsilon-greedy: explore with probability epsilon."""
        if self._random.random() < epsilon:
            # Explore: random variant
            return self._random.choice(self.experiment.variants)
        # Exploit: best performing variant
        return max(
            self.experiment.variants,
            key=lambda v: v.avg_success_score,
        )

    def _thompson_sampling(self) -> Variant:
        """Thompson sampling: Bayesian multi-armed bandit."""
        samples = []

        for variant in self.experiment.variants:
            # Beta distribution parameters
            alpha = variant.conversions + 1
            beta = (variant.impressions - variant.conversions) + 1

            # Sample from beta distribution
            sample = self._random.betavariate(alpha, beta)
            samples.append((sample, variant))

        # Select variant with highest sample
        return max(samples, key=lambda x: x[0])[1]

    def _ucb_allocation(self) -> Variant:
        """Upper Confidence Bound selection."""
        total_impressions = self.experiment.total_impressions or 1

        ucb_scores = []
        for variant in self.experiment.variants:
            if variant.impressions == 0:
                # Give unvisited variants high priority
                ucb_scores.append((float("inf"), variant))
            else:
                mean = variant.avg_success_score
                exploration = math.sqrt(2 * math.log(total_impressions) / variant.impressions)
                ucb = mean + exploration
                ucb_scores.append((ucb, variant))

        return max(ucb_scores, key=lambda x: x[0])[1]
