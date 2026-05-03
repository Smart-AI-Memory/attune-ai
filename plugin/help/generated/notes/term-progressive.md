---
name: term-progressive
source: CLAUDE.md
summary: This template defines "Progressive" as a multi-tier escalation workflow that
  advances actions through structured stages sequentially based on conditions, with
  each tier triggering only if the previous one doesn't resolve the issue.
tags:
- terminology
type: note
---

# Progressive

## Definition

**Progressive** — A multi-tier escalation workflow in which actions, processes, or notifications advance through a structured sequence of stages, each triggered by the outcome or condition of the previous tier.

## Context

This term is used throughout the attune-ai codebase to describe workflows that escalate incrementally rather than jumping directly to a final state. A progressive workflow ensures that each tier is evaluated in order, allowing for graduated responses before higher-level actions are invoked.

## Example Use Case

A progressive notification workflow might first attempt an in-app alert, then escalate to an email if unacknowledged, and finally trigger a push notification or on-call page at the highest tier.

## Related Topics

_No related topics yet._
