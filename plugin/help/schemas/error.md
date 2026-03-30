---
type: error
description: >
  Error template schema for documenting known failure
  modes with root causes and verified resolutions.
required_fields:
  - name
  - signature
  - root_cause
  - resolution
optional_fields:
  - confidence
  - related_topics
  - tags
  - source
---

# Error: {name}

## Signature

{signature}

The error pattern that triggers this topic. Can be an
exact error message, a regex pattern, or a description
of the failure mode.

## Root Cause

{root_cause}

Why this error happens. Should be specific enough to
distinguish from similar errors.

## Resolution

{resolution}

Step-by-step fix. Uses ordered list for sequential
steps, unordered for independent actions. May embed
a Task template for complex procedures.

## Confidence

{confidence}

One of:

- **Verified** — fix confirmed by prior incident or
  test (source: Lessons Learned, test suite)
- **Likely** — matches a known root cause pattern
- **Speculative** — AI-inferred, not yet validated

## Related Topics

{related_topics}

Cross-links to other templates by type:

- Warning: preventive guidance
- Tip: best practice to avoid recurrence
- Task: detailed procedure if resolution is complex
- FAQ: common follow-up questions
- Reference: API or config details
