# Teaching Your AI to Learn From Its Own Mistakes

**A practical intro to Attune's FeedbackLoop — no Redis required**

---

This tutorial builds on an idea championed by Boris Dayma and the
team at Anthropic: that a well-designed AI system should close the
loop on its own outputs — rating quality, tracking trends, and
adjusting behavior over time without human intervention. Attune
makes that idea concrete and installable.

---

Most AI integrations treat every LLM call the same way: fire a prompt,
get a response, move on. There's no memory of whether that response was
actually good, no signal to improve routing next time, and no way to
know which model tier is actually worth the cost for a given task.

Attune's `FeedbackLoop` changes that. It lets you rate the quality of
LLM responses and use that history to drive smarter model selection
over time. And as of this week, it works entirely out of the box — no
Redis, no infrastructure setup, zero configuration.

---

## Install

```bash
pip install "attune-ai[developer]"
```

That's it. No database. No Docker. No `.env` file for this part.

---

## The core idea in 30 seconds

Attune routes LLM calls across three tiers:

- **cheap** — fast, low cost (Haiku-class models)
- **capable** — balanced (Sonnet-class)
- **premium** — highest quality (Opus-class)

`FeedbackLoop` collects quality scores (0.0–1.0) for each
workflow stage, tracks trends over time, and tells you when to
upgrade or downgrade the tier you're using. The more you rate,
the smarter the recommendations get.

---

## Step 1: Record your first piece of feedback

```python
from attune.telemetry.feedback_loop import FeedbackLoop, ModelTier

# No arguments needed — uses in-memory storage automatically
feedback = FeedbackLoop()

# You ran a "code-review" workflow, "analysis" stage, on the
# cheap tier. You rated the response 0.85 out of 1.0.
feedback_id = feedback.record_feedback(
    workflow_name="code-review",
    stage_name="analysis",
    tier=ModelTier.CHEAP,
    quality_score=0.85,
    metadata={"tokens": 312, "latency_ms": 980},
)

print(f"Recorded: {feedback_id}")
# Recorded: feedback_a3f21b9c
```

The `metadata` dict is freeform — stash whatever is useful for
your debugging later (token counts, latency, model version, etc.).

---

## Step 2: Build up history and read statistics

Quality recommendations require at least 10 samples before
they become actionable. Here's how to simulate building that
history and then reading the stats:

```python
import random

# Simulate 15 runs of the same stage — scores cluster around 0.82
for _ in range(15):
    feedback.record_feedback(
        workflow_name="code-review",
        stage_name="analysis",
        tier=ModelTier.CHEAP,
        quality_score=round(random.uniform(0.75, 0.90), 2),
    )

# Read aggregated stats
stats = feedback.get_quality_stats(
    workflow_name="code-review",
    stage_name="analysis",
    tier=ModelTier.CHEAP,
)

print(f"Average quality : {stats.avg_quality:.2f}")
print(f"Sample count    : {stats.sample_count}")
print(f"Trend           : {stats.recent_trend:+.2f}")
# Average quality : 0.82
# Sample count    : 16
# Trend           : +0.03
```

`recent_trend` compares the second half of your history to the
first half. Positive means things are improving; negative means
quality is slipping.

---

## Step 3: Get a tier recommendation

Once you have enough history, ask the feedback loop what to do:

```python
rec = feedback.recommend_tier(
    workflow_name="code-review",
    stage_name="analysis",
    current_tier=ModelTier.CHEAP,
)

print(f"Current tier    : {rec.current_tier}")
print(f"Recommended     : {rec.recommended_tier}")
print(f"Confidence      : {rec.confidence:.0%}")
print(f"Reason          : {rec.reason}")
# Current tier    : cheap
# Recommended     : cheap
# Confidence      : 80%
# Reason          : Acceptable quality (0.82) - maintain current tier
```

Now simulate a stage that's clearly struggling — quality drops
below the 0.70 threshold:

```python
for _ in range(12):
    feedback.record_feedback(
        workflow_name="code-review",
        stage_name="summary",
        tier=ModelTier.CHEAP,
        quality_score=round(random.uniform(0.50, 0.65), 2),
    )

rec = feedback.recommend_tier("code-review", "summary", ModelTier.CHEAP)
print(f"Recommended: {rec.recommended_tier}")
print(f"Reason     : {rec.reason}")
# Recommended: capable
# Reason     : Low quality (0.58) - upgrade for better results
```

The loop automatically recommends an upgrade. If you're already
on `capable` and quality is still poor, it recommends `premium`.
If you're on `premium` with excellent quality, it suggests
downgrading to `capable` to save cost.

---

## Step 4: Find underperforming stages at a glance

For workflows with many stages, you don't want to check each one
manually. Use `get_underperforming_stages()`:

```python
# Seed a few more stages with varying quality
for stage, score in [("lint", 0.91), ("diff", 0.62), ("comment", 0.48)]:
    for _ in range(12):
        feedback.record_feedback("code-review", stage, "cheap", score)

problems = feedback.get_underperforming_stages(
    workflow_name="code-review",
    quality_threshold=0.70,
)

for label, stats in problems:
    print(f"{label:25s}  avg={stats.avg_quality:.2f}  n={stats.sample_count}")
# comment/cheap              avg=0.48  n=12
# diff/cheap                 avg=0.62  n=12
# summary/cheap              avg=0.58  n=12
```

Results are sorted worst-first, so you know exactly where to
focus your attention first.

---

## How the in-memory fallback works

When you create `FeedbackLoop()` without any arguments:

1. It looks for a running `UsageTracker` with a Redis backend.
2. If found, it uses that — your feedback survives process restarts.
3. If not found, it falls back to `_InMemoryStore`: a lightweight,
   thread-safe, TTL-aware dict that lives in your process.

The in-memory store is perfect for development and one-off scripts.
When you're ready to persist feedback across runs, point it at
your Redis instance:

```python
from attune.memory import get_redis_memory

memory = get_redis_memory()  # Reads REDIS_URL from env
feedback = FeedbackLoop(memory=memory)
```

Everything else in the API stays identical.

---

## Putting it into a real workflow

Here's the pattern you'd follow in production:

```python
from attune.telemetry.feedback_loop import FeedbackLoop, ModelTier

feedback = FeedbackLoop()

def run_analysis(code: str, tier: ModelTier = ModelTier.CHEAP) -> str:
    """Run code analysis and record quality feedback."""
    # ... call your LLM here ...
    response = call_llm(code, tier=tier.value)

    # Rate the response (your logic — could be automated or human)
    score = rate_response(response)

    feedback.record_feedback(
        workflow_name="code-review",
        stage_name="analysis",
        tier=tier,
        quality_score=score,
    )

    return response


def get_best_tier() -> ModelTier:
    """Ask the feedback loop which tier to use."""
    rec = feedback.recommend_tier("code-review", "analysis")
    return ModelTier(rec.recommended_tier)


# Route dynamically based on accumulated feedback
result = run_analysis(my_code, tier=get_best_tier())
```

Over time, `get_best_tier()` returns cheaper tiers when they're
delivering high quality, and escalates automatically when they're
not — without you having to hard-code any thresholds.

---

## What's next

- Pair `FeedbackLoop` with `UsageTracker` for a full cost and
  quality dashboard in your terminal.
- Add the React dashboard (`dashboard/`) for a live visual view
  of model routing and system health — it reads from the same APIs.
- Swap in a Redis backend when you're ready to persist feedback
  across deployments.

The full source is in `src/attune/telemetry/feedback_loop.py`
and the test suite is in `tests/unit/telemetry/test_feedback_loop.py`.

---

---

## Acknowledgments

The concept of automating quality feedback as a first-class part of
an AI system's architecture — rather than bolting it on after the
fact — comes from ideas Boris Dayma has championed in the open-source
AI community, and from the Anthropic team's thinking on how capable
AI systems should self-evaluate and self-correct. `FeedbackLoop` is
Attune's attempt to make that principle practical for everyday Python
developers. Thank you both for pointing in this direction.

---

*Attune AI is open source under the Apache 2.0 license.*
*GitHub: github.com/Smart-AI-Memory/attune-ai*
