---
name: feedback-loop
source: src/attune/help/engine.py
summary: This template covers a feedback loop system that collects user ratings on
  template helpfulness, calculates confidence scores based on those ratings, and uses
  those scores to rank and surface templates accordingly.
tags:
- help-system
- telemetry
type: concept
---

# Concept: Template Feedback Loop

## Overview

Users can rate templates as helpful or unhelpful. These ratings accumulate into a confidence score that influences how templates are ranked and surfaced over time.

## Why It Matters

Template quality can only be measured by whether a template actually helps the person using it. The feedback loop closes the gap between template generation and real-world usefulness — templates that consistently help users rise in ranking, while underperforming templates fall.

## How It Works

Three components work together to collect, store, and apply feedback:

- **`record_template_feedback()`** — Persists a user's rating to `feedback.json`.
- **`get_template_confidence()`** — Calculates and returns a confidence score using the formula `good / (good + bad)`, expressed as a value between `0.0` and `1.0`.
- **CLI** — Users submit feedback directly from the command line:

  ```bash
  attune help-docs <id> --feedback good|bad
  ```

A higher confidence score causes a template to rank more prominently. A lower score suppresses it.

## Related Topics

*No related topics yet.*
