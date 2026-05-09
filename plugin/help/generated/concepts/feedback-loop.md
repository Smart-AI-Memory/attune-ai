---
type: concept
name: feedback-loop
tags: [help-system, telemetry]
source: src/attune/help/engine.py
---

# Concept: Template feedback loop

## What

Users can rate templates as good or bad. Ratings accumulate into a confidence score that influences template ranking.

## Why

Template quality is only measurable by whether it actually helps users. Feedback closes the loop between generation and usefulness.

## How

record_template_feedback() stores ratings in feedback.json. get_template_confidence() returns good/(good+bad) as a 0.0-1.0 score. CLI: `attune help-docs <id> --feedback good|bad`.

## Related Topics

_No related topics yet._
