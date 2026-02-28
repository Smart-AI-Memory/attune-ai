"""Real-time tier recommendation system for cascading workflows.

This module provides intelligent tier selection based on historical patterns,
bug types, and file analysis. It can be used programmatically or via CLI.

Usage:
    from attune import TierRecommender

    recommender = TierRecommender()
    tier = recommender.recommend(
        bug_description="integration test failure with import error",
        files_affected=["tests/integration/test_foo.py"]
    )

    print(f"Recommended tier: {tier.tier}")
    print(f"Confidence: {tier.confidence}")
    print(f"Expected cost: ${tier.expected_cost}")
"""

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from attune.security.path_validation import _validate_file_path


@dataclass
class TierRecommendationResult:
    """Result of tier recommendation."""

    tier: str  # CHEAP, CAPABLE, or PREMIUM
    confidence: float  # 0.0-1.0
    reasoning: str
    expected_cost: float
    expected_attempts: float
    similar_patterns_count: int
    fallback_used: bool = False


class TierRecommender:
    """Intelligent tier recommendation system.

    Learns from historical patterns to recommend optimal starting tier
    for new bugs based on:
    - Bug type/description
    - Files affected
    - Historical success rates
    - Cost optimization
    """

    def __init__(self, patterns_dir: Path | None = None, confidence_threshold: float = 0.7):
        """Initialize tier recommender.

        Args:
            patterns_dir: Directory containing pattern JSON files.
                         Defaults to patterns/debugging/
            confidence_threshold: Minimum confidence for non-default recommendations

        Raises:
            ValueError: If confidence_threshold is out of valid range

        """
        # Pattern 4: Range validation
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be between 0.0 and 1.0, got {confidence_threshold}",
            )

        if patterns_dir is None:
            patterns_dir = Path(__file__).parent.parent.parent / "patterns" / "debugging"

        self.patterns_dir = Path(patterns_dir)
        self.confidence_threshold = confidence_threshold
        self.patterns = self._load_patterns()

        # Build indexes for fast lookup
        self._build_indexes()

    def _load_patterns(self) -> list[dict]:
        """Load all enhanced patterns with tier_progression data."""
        patterns: list[dict] = []

        if not self.patterns_dir.exists():
            return patterns

        for file_path in self.patterns_dir.glob("*.json"):
            try:
                validated_path = _validate_file_path(str(file_path))
                with open(validated_path) as f:
                    data = json.load(f)

                    # Check if this is an enhanced pattern
                    if isinstance(data, dict) and "tier_progression" in data:
                        patterns.append(data)
                    # Or if it's a patterns array
                    elif isinstance(data, dict) and "patterns" in data:
                        for pattern in data["patterns"]:
                            if "tier_progression" in pattern:
                                patterns.append(pattern)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return patterns

    def _build_indexes(self):
        """Build indexes for fast pattern lookup."""
        self.bug_type_index: dict[str, list[dict]] = defaultdict(list)
        self.file_pattern_index: dict[str, list[dict]] = defaultdict(list)

        for pattern in self.patterns:
            # Index by bug type
            bug_type = pattern.get("bug_type", "unknown")
            self.bug_type_index[bug_type].append(pattern)

            # Index by file patterns
            files = pattern.get("files_affected", [])
            for file in files:
                # Extract file pattern (e.g., "tests/" from "tests/test_foo.py")
                parts = Path(file).parts
                if parts:
                    self.file_pattern_index[parts[0]].append(pattern)

    def recommend(
        self,
        bug_description: str,
        files_affected: list[str] | None = None,
        complexity_hint: int | None = None,
    ) -> TierRecommendationResult:
        """Recommend optimal starting tier for a new bug.

        Args:
            bug_description: Description of the bug/task
            files_affected: List of files involved (optional)
            complexity_hint: Manual complexity score 1-10 (optional)

        Returns:
            TierRecommendationResult with tier, confidence, and reasoning

        Raises:
            ValueError: If bug_description is empty or complexity_hint out of range
            TypeError: If files_affected is not a list

        """
        # Pattern 1: String ID validation
        if not bug_description or not bug_description.strip():
            raise ValueError("bug_description cannot be empty")

        # Pattern 5: Type validation
        if files_affected is not None and not isinstance(files_affected, list):
            raise TypeError(f"files_affected must be list, got {type(files_affected).__name__}")

        # Pattern 4: Range validation for complexity_hint
        if complexity_hint is not None and not (1 <= complexity_hint <= 10):
            raise ValueError(f"complexity_hint must be between 1 and 10, got {complexity_hint}")

        # Step 1: Match bug type from description
        bug_type = self._classify_bug_type(bug_description)

        # Step 2: Find similar patterns
        similar_patterns = self._find_similar_patterns(
            bug_type=bug_type,
            files_affected=files_affected or [],
        )

        # Step 3: If no similar patterns, use fallback logic
        if not similar_patterns:
            return self._fallback_recommendation(
                bug_description=bug_description,
                complexity_hint=complexity_hint,
            )

        # Step 4: Analyze tier distribution in similar patterns
        tier_analysis = self._analyze_tier_distribution(similar_patterns)

        # Step 5: Select tier with highest success rate
        recommended_tier, confidence = self._select_tier(tier_analysis)

        # Step 6: Calculate expected cost and attempts
        cost_estimate = self._estimate_cost(similar_patterns, recommended_tier)

        return TierRecommendationResult(
            tier=recommended_tier,
            confidence=confidence,
            reasoning=self._generate_reasoning(
                bug_type=bug_type,
                tier=recommended_tier,
                confidence=confidence,
                similar_count=len(similar_patterns),
            ),
            expected_cost=cost_estimate["avg_cost"],
            expected_attempts=cost_estimate["avg_attempts"],
            similar_patterns_count=len(similar_patterns),
            fallback_used=False,
        )

    def _classify_bug_type(self, description: str) -> str:
        """Classify bug type from description using keyword matching."""
        desc_lower = description.lower()

        # Define bug type keywords
        bug_type_keywords = {
            "integration_error": ["integration", "import", "module", "package"],
            "type_mismatch": ["type", "annotation", "mypy", "typing"],
            "import_error": ["import", "module", "cannot import", "no module"],
            "syntax_error": ["syntax", "invalid syntax", "parse error"],
            "runtime_error": ["runtime", "exception", "traceback"],
            "test_failure": ["test fail", "assertion", "pytest"],
        }

        for bug_type, keywords in bug_type_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                return bug_type

        return "unknown"

    def _find_similar_patterns(self, bug_type: str, files_affected: list[str]) -> list[dict]:
        """Find patterns similar to current bug.

        Raises:
            TypeError: If files_affected is not a list

        """
        # Pattern 5: Type validation
        if not isinstance(files_affected, list):
            raise TypeError(f"files_affected must be list, got {type(files_affected).__name__}")

        similar = []

        # Match by bug type
        similar.extend(self.bug_type_index.get(bug_type, []))

        # Match by file patterns
        if files_affected:
            for file in files_affected:
                parts = Path(file).parts
                if parts:
                    file_matches = self.file_pattern_index.get(parts[0], [])
                    # Add only if not already in similar list
                    for pattern in file_matches:
                        if pattern not in similar:
                            similar.append(pattern)

        return similar

    def _analyze_tier_distribution(self, patterns: list[dict]) -> dict[str, dict]:
        """Analyze tier success rates from similar patterns."""
        tier_stats: dict[str, dict] = defaultdict(
            lambda: {"count": 0, "total_cost": 0.0, "total_attempts": 0},
        )

        for pattern in patterns:
            tp = pattern["tier_progression"]
            successful_tier = tp["successful_tier"]

            stats = tier_stats[successful_tier]
            stats["count"] += 1
            stats["total_cost"] += tp["cost_breakdown"]["total_cost"]
            stats["total_attempts"] += tp["total_attempts"]

        # Calculate averages
        for _tier, stats in tier_stats.items():
            count = stats["count"]
            stats["success_rate"] = count / len(patterns)
            stats["avg_cost"] = stats["total_cost"] / count
            stats["avg_attempts"] = stats["total_attempts"] / count

        return dict(tier_stats)

    def _select_tier(self, tier_analysis: dict[str, dict]) -> tuple[str, float]:
        """Select best tier based on success rate and cost."""
        if not tier_analysis:
            return "CHEAP", 0.5

        # Sort by success rate
        sorted_tiers = sorted(
            tier_analysis.items(),
            key=lambda x: x[1]["success_rate"],
            reverse=True,
        )

        best_tier, stats = sorted_tiers[0]
        confidence = stats["success_rate"]

        return best_tier, confidence

    def _estimate_cost(self, patterns: list[dict], tier: str) -> dict[str, float]:
        """Estimate cost and attempts for recommended tier."""
        matching = [p for p in patterns if p["tier_progression"]["successful_tier"] == tier]

        if not matching:
            # Default estimates by tier
            defaults = {
                "CHEAP": {"avg_cost": 0.030, "avg_attempts": 1.5},
                "CAPABLE": {"avg_cost": 0.150, "avg_attempts": 2.5},
                "PREMIUM": {"avg_cost": 0.450, "avg_attempts": 1.0},
            }
            return defaults.get(tier, defaults["CHEAP"])

        total_cost = sum(p["tier_progression"]["cost_breakdown"]["total_cost"] for p in matching)
        total_attempts = sum(p["tier_progression"]["total_attempts"] for p in matching)

        return {
            "avg_cost": total_cost / len(matching),
            "avg_attempts": total_attempts / len(matching),
        }

    def _fallback_recommendation(
        self,
        bug_description: str,
        complexity_hint: int | None,
    ) -> TierRecommendationResult:
        """Provide fallback recommendation when no historical data available."""
        # Use complexity hint if provided
        if complexity_hint is not None:
            if complexity_hint <= 3:
                tier = "CHEAP"
                cost = 0.030
            elif complexity_hint <= 7:
                tier = "CAPABLE"
                cost = 0.150
            else:
                tier = "PREMIUM"
                cost = 0.450

            return TierRecommendationResult(
                tier=tier,
                confidence=0.6,
                reasoning=f"Based on complexity score {complexity_hint}/10",
                expected_cost=cost,
                expected_attempts=2.0,
                similar_patterns_count=0,
                fallback_used=True,
            )

        # Default: start with CHEAP tier (conservative)
        return TierRecommendationResult(
            tier="CHEAP",
            confidence=0.5,
            reasoning="No historical data - defaulting to CHEAP tier (conservative approach)",
            expected_cost=0.030,
            expected_attempts=1.5,
            similar_patterns_count=0,
            fallback_used=True,
        )

    def _generate_reasoning(
        self,
        bug_type: str,
        tier: str,
        confidence: float,
        similar_count: int,
    ) -> str:
        """Generate human-readable reasoning for recommendation."""
        percent = int(confidence * 100)

        if similar_count == 0:
            return "No historical data - defaulting to CHEAP tier"
        if similar_count == 1:
            return f"1 similar bug ({bug_type}) resolved at {tier} tier"
        return f"{percent}% of {similar_count} similar bugs ({bug_type}) resolved at {tier} tier"

    def get_stats(self) -> dict:
        """Get overall statistics about pattern learning."""
        if not self.patterns:
            return {"total_patterns": 0, "message": "No patterns loaded"}

        # Calculate tier distribution
        tier_dist: dict[str, int] = defaultdict(int)
        bug_type_dist: dict[str, int] = defaultdict(int)
        total_savings = 0.0

        for pattern in self.patterns:
            tp = pattern["tier_progression"]
            tier_dist[tp["successful_tier"]] += 1
            bug_type_dist[pattern["bug_type"]] += 1
            total_savings += tp["cost_breakdown"]["savings_percent"]

        return {
            "total_patterns": len(self.patterns),
            "tier_distribution": dict(tier_dist),
            "bug_type_distribution": dict(bug_type_dist),
            "avg_savings_percent": round(total_savings / len(self.patterns), 1),
            "patterns_by_tier": {
                "CHEAP": tier_dist.get("CHEAP", 0),
                "CAPABLE": tier_dist.get("CAPABLE", 0),
                "PREMIUM": tier_dist.get("PREMIUM", 0),
            },
        }
