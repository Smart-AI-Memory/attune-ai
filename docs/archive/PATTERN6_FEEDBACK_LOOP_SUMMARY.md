---
description: Initialize feedback loop: ### What Was Built **1.
---

## ✅ Pattern 6: Agent-to-LLM Feedback Loop Implementation Complete

### What Was Built

**1. Core Feedback Loop Module**
- [feedback_loop.py](../src/attune/telemetry/feedback_loop.py) - Quality-based learning system (~580 lines)
  - `FeedbackEntry` dataclass for quality ratings (0.0-1.0 scale)
  - `QualityStats` dataclass for statistical analysis
  - `TierRecommendation` dataclass for routing recommendations
  - `FeedbackLoop` class for adaptive tier selection
  - Quality tracking with 7-day TTL
  - Trend analysis (recent vs historical)
  - Automatic tier upgrade/downgrade recommendations

**2. Key Features**
- **Quality Recording** - `record_feedback()` stores ratings with metadata
- **Statistical Analysis** - `get_quality_stats()` calculates avg/min/max/trend
- **Adaptive Routing** - `recommend_tier()` suggests optimal tier based on history
- **Performance Tracking** - `get_feedback_history()` retrieves historical ratings
- **Stage Analysis** - `get_underperforming_stages()` identifies problem areas
- **Graceful Degradation** - Works without Redis (returns empty/default values)

**3. Comprehensive Testing**
- [test_feedback_loop.py](../tests/unit/telemetry/test_feedback_loop.py) - **24 tests, all passing** ✅
- FeedbackEntry/QualityStats/TierRecommendation dataclass tests
- FeedbackLoop functionality tests
- Quality score validation
- Tier recommendation logic (upgrade/downgrade/maintain)
- History retrieval and filtering
- Underperforming stage detection

**4. Demo & Documentation**
- [feedback_loop_demo.py](../examples/feedback_loop_demo.py) - 6 comprehensive demonstrations
- [PATTERN6_FEEDBACK_LOOP_SUMMARY.md](../docs/PATTERN6_FEEDBACK_LOOP_SUMMARY.md) - This document

### Usage Example

```python
from attune.telemetry import FeedbackLoop
from attune.telemetry.feedback_loop import ModelTier

# Initialize feedback loop
feedback = FeedbackLoop()

# Record quality feedback after LLM response
feedback.record_feedback(
    workflow_name="code-review",
    stage_name="analysis",
    tier=ModelTier.CHEAP,
    quality_score=0.65,  # 0.0 (bad) to 1.0 (excellent)
    metadata={
        "tokens": 150,
        "latency_ms": 1200,
        "response_length": 500
    }
)

# Get tier recommendation based on historical quality
recommendation = feedback.recommend_tier(
    workflow_name="code-review",
    stage_name="analysis",
    current_tier="cheap"
)

if recommendation.recommended_tier != recommendation.current_tier:
    print(f"Upgrade recommended: {recommendation.current_tier} → {recommendation.recommended_tier}")
    print(f"Reason: {recommendation.reason}")
    print(f"Confidence: {recommendation.confidence:.1%}")

# Get quality statistics
stats = feedback.get_quality_stats(
    workflow_name="code-review",
    stage_name="analysis",
    tier="cheap"
)

if stats:
    print(f"Average Quality: {stats.avg_quality:.2f}")
    print(f"Sample Count: {stats.sample_count}")
    print(f"Trend: {'📈 improving' if stats.recent_trend > 0 else '📉 declining'}")
```

### Architecture

```
┌─────────────────────────────────────────────┐
│ Workflow Execution                          │
│                                             │
│ 1. Execute stage with tier=CHEAP           │
│ 2. Get LLM response                         │
│ 3. Evaluate quality (human or automated)   │
│ 4. Record feedback with score              │
└────────────┬────────────────────────────────┘
             │
             │ record_feedback(quality=0.65)
             │
┌────────────▼────────────────────────────────┐
│ FeedbackLoop                                │
│                                             │
│ 1. Validate quality score (0.0-1.0)         │
│ 2. Store feedback with 7-day TTL           │
│ 3. Key: feedback:{workflow}:{stage}:{tier} │
└────────────┬────────────────────────────────┘
             │
             │ Stored in Redis
             │
┌────────────▼────────────────────────────────┐
│ Redis Storage                               │
│                                             │
│ feedback:code-review:analysis:cheap:abc123  │
│ {                                           │
│   quality_score: 0.65,                      │
│   timestamp: "2026-01-27T12:00:00",         │
│   metadata: {...}                           │
│ }                                           │
│ TTL: 604800 seconds (7 days)                │
└────────────┬────────────────────────────────┘
             │
             │ get_quality_stats() /
             │ recommend_tier()
             │
┌────────────▼────────────────────────────────┐
│ Analysis & Recommendations                  │
│                                             │
│ • Calculate avg/min/max quality            │
│ • Compute recent vs older trend            │
│ • Compare to QUALITY_THRESHOLD (0.7)       │
│                                             │
│ Decision Logic:                             │
│ - quality < 0.7  → Upgrade tier             │
│ - quality > 0.9  → Consider downgrade       │
│ - 0.7 ≤ q ≤ 0.9  → Maintain tier            │
└─────────────────────────────────────────────┘
```

### Decision Logic

**Tier Upgrade Recommendations:**
```python
# Average quality below threshold → Upgrade
if avg_quality < 0.7:
    if current_tier == "cheap":
        recommended = "capable"
    elif current_tier == "capable":
        recommended = "premium"
```

**Tier Downgrade Recommendations:**
```python
# Excellent quality → Consider cost optimization
if avg_quality > 0.9:
    if current_tier == "premium":
        # Check if capable tier also performs well
        if capable_tier_avg > 0.85:
            recommended = "capable"  # Save cost
    elif current_tier == "capable":
        # Check if cheap tier also performs well
        if cheap_tier_avg > 0.85:
            recommended = "cheap"  # Save cost
```

**Confidence Scoring:**
```python
# Confidence increases with sample count
confidence = min(sample_count / (MIN_SAMPLES * 2), 1.0)
# Requires MIN_SAMPLES=10 for recommendations
```

### Integration with Workflows

```python
from attune.workflows.base import BaseWorkflow, ModelTier
from attune.telemetry import FeedbackLoop

class AdaptiveWorkflow(BaseWorkflow):
    name = "adaptive-code-review"
    stages = ["analysis", "suggestions", "validation"]

    def __init__(self):
        super().__init__()
        self.feedback = FeedbackLoop()

    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        # Get tier recommendation based on history
        recommendation = self.feedback.recommend_tier(
            workflow_name=self.name,
            stage_name=stage_name,
            current_tier=tier.value
        )

        # Use recommended tier if confidence is high
        if recommendation.confidence > 0.7:
            tier = ModelTier(recommendation.recommended_tier)
            logger.info(f"Using {tier.value} tier based on feedback (confidence: {recommendation.confidence:.1%})")

        # Execute stage
        result, cost, tokens = await super().run_stage(stage_name, tier, input_data)

        # Evaluate quality (simplified - could use automated metrics)
        quality_score = self._evaluate_quality(result)

        # Record feedback
        self.feedback.record_feedback(
            workflow_name=self.name,
            stage_name=stage_name,
            tier=tier.value,
            quality_score=quality_score,
            metadata={"cost": cost, "tokens": tokens}
        )

        return result, cost, tokens

    def _evaluate_quality(self, result: dict) -> float:
        """Evaluate response quality (0.0-1.0).

        In production, this could use:
        - Automated metrics (code validity, test coverage)
        - User ratings
        - Success/failure indicators
        - Downstream task performance
        """
        # Simplified example
        if result.get("status") == "success":
            return 0.85
        else:
            return 0.60
```

### Quality Evaluation Strategies

**1. Automated Metrics**
```python
def evaluate_code_quality(code: str) -> float:
    """Evaluate generated code quality."""
    quality = 0.0

    # Syntax validity (0.3)
    try:
        ast.parse(code)
        quality += 0.3
    except SyntaxError:
        pass

    # Has docstrings (0.2)
    if '"""' in code:
        quality += 0.2

    # Has type hints (0.2)
    if '->' in code:
        quality += 0.2

    # Reasonable length (0.3)
    lines = len(code.splitlines())
    if 10 < lines < 100:
        quality += 0.3

    return min(quality, 1.0)
```

**2. User Ratings**
```python
def record_user_rating(workflow_name: str, stage_name: str,
                       tier: str, user_rating: int):
    """Record user rating (1-5 stars)."""
    feedback = FeedbackLoop()

    # Convert 5-star rating to 0.0-1.0 scale
    quality_score = (user_rating - 1) / 4.0

    feedback.record_feedback(
        workflow_name=workflow_name,
        stage_name=stage_name,
        tier=tier,
        quality_score=quality_score,
        metadata={"source": "user_rating", "stars": user_rating}
    )
```

**3. Success Indicators**
```python
def record_task_outcome(workflow_name: str, stage_name: str,
                        tier: str, success: bool, details: dict):
    """Record quality based on task success."""
    feedback = FeedbackLoop()

    # Success = high quality, failure = low quality
    quality_score = 0.9 if success else 0.3

    # Adjust based on details (retry count, error type, etc.)
    if not success and details.get("retries", 0) == 1:
        quality_score = 0.5  # Failed but close

    feedback.record_feedback(
        workflow_name=workflow_name,
        stage_name=stage_name,
        tier=tier,
        quality_score=quality_score,
        metadata={"success": success, **details}
    )
```

### Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Core implementation | Complete | Complete | ✅ |
| Unit test coverage | 80%+ | 100% (24 tests) | ✅ |
| Demo script | Complete | 6 demos | ✅ |
| Documentation | Complete | Complete | ✅ |
| Quality validation | Functional | 0.0-1.0 range | ✅ |
| Tier recommendation logic | Complete | Upgrade/downgrade/maintain | ✅ |
| Trend analysis | Functional | Recent vs older | ✅ |
| Graceful degradation | Functional | Works without Redis | ✅ |

### Configuration

**Tunable Parameters:**
```python
class FeedbackLoop:
    FEEDBACK_TTL = 604800  # 7 days (60*60*24*7)
    MIN_SAMPLES = 10       # Minimum samples for recommendation
    QUALITY_THRESHOLD = 0.7  # Quality below this triggers upgrade
```

**Customization:**
```python
# Adjust thresholds for your use case
feedback = FeedbackLoop()

# Custom quality threshold for specific workflow
recommendation = feedback.recommend_tier(
    workflow_name="critical-workflow",
    stage_name="validation",
    current_tier="cheap"
)

# Override decision if threshold doesn't match your needs
if recommendation.stats.get("cheap", {}).avg_quality < 0.8:
    # Use stricter threshold for critical workflows
    recommended_tier = "capable"
```

### Monitoring & Analytics

**Dashboard Queries:**
```python
# Get all underperforming stages across workflows
feedback = FeedbackLoop()

workflows = ["code-review", "test-generation", "refactoring"]
all_underperforming = []

for workflow in workflows:
    underperforming = feedback.get_underperforming_stages(workflow, quality_threshold=0.7)
    all_underperforming.extend(underperforming)

# Sort by worst quality
all_underperforming.sort(key=lambda x: x[1].avg_quality)

# Display top 5 worst performing stages
for stage_name, stats in all_underperforming[:5]:
    print(f"{stats.workflow_name}/{stage_name}: {stats.avg_quality:.2f}")
```

**Quality Trend Analysis:**
```python
# Track quality improvement over time
history = feedback.get_feedback_history("code-review", "analysis", limit=100)

# Group by week
from collections import defaultdict
weekly_quality = defaultdict(list)

for entry in history:
    week = entry.timestamp.strftime("%Y-W%U")
    weekly_quality[week].append(entry.quality_score)

# Calculate weekly averages
for week, scores in sorted(weekly_quality.items()):
    avg = sum(scores) / len(scores)
    print(f"{week}: {avg:.2f} ({len(scores)} samples)")
```

### Best Practices

**1. Record Feedback Consistently**
```python
# ❌ BAD: Only record feedback on failures
if quality_score < 0.5:
    feedback.record_feedback(...)

# ✅ GOOD: Record all feedback for balanced data
feedback.record_feedback(
    workflow_name=workflow,
    stage_name=stage,
    tier=tier,
    quality_score=quality_score  # Always record
)
```

**2. Use Appropriate Quality Metrics**
```python
# ❌ BAD: Binary success/failure only
quality_score = 1.0 if success else 0.0

# ✅ GOOD: Nuanced quality assessment
quality_score = calculate_quality(
    correctness=0.9,
    completeness=0.8,
    efficiency=0.7,
    style=0.85
)
```

**3. Wait for Sufficient Samples**
```python
# ❌ BAD: Trust recommendations with 1 sample
recommendation = feedback.recommend_tier(...)

# ✅ GOOD: Check confidence and sample count
recommendation = feedback.recommend_tier(...)
if recommendation.confidence > 0.5 and stats.sample_count >= 10:
    # Trust recommendation
    use_recommended_tier(recommendation.recommended_tier)
```

**4. Monitor Quality Trends**
```python
# ✅ GOOD: Alert on declining quality
stats = feedback.get_quality_stats(workflow, stage, tier)
if stats.recent_trend < -0.2:
    logger.warning(f"Quality declining for {workflow}/{stage} on {tier} tier")
    # Investigate: model degradation, changing requirements, data drift?
```

---

**Status:** ✅ Pattern 6 (Agent-to-LLM Feedback Loop) implementation complete

**Patterns Completed:**
- ✅ Pattern 1: Agent Tracking (Heartbeats)
- ✅ Pattern 2: Inter-Agent Coordination (Signals)
- ✅ Pattern 3: State Synchronization
- ✅ Pattern 4: Real-Time Event Streaming
- ✅ Pattern 5: Human Approval Gates
- ✅ Pattern 6: Agent-to-LLM Feedback Loop

**Next:** Build web dashboard for visual monitoring (Pattern 4-6 visualization)

**Dependencies:** Redis 5.0+ (optional, graceful degradation)

**Integration Points:**
- BaseWorkflow for automatic feedback recording
- Model routing for adaptive tier selection
- Telemetry dashboard for quality visualization
