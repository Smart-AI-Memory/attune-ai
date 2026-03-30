---
type: warning
description: >
  Warning template schema for documenting preventive
  guidance — actions with consequences that users should
  be aware of before proceeding.
required_fields:
  - name
  - condition
  - risk
  - mitigation
optional_fields:
  - confidence
  - related_topics
  - tags
  - source
---

# Warning: {name}

## Condition

{condition}

When this warning applies. Describes the specific
scenario or action that triggers the warning.

## Risk

{risk}

What can go wrong if the warning is ignored. Should
be concrete and specific.

## Mitigation

{mitigation}

How to avoid or recover from the risk. Uses ordered
list for sequential steps, unordered for independent
actions.

## Confidence

{confidence}

One of:

- **Verified** — guidance confirmed by prior incident
  (source: Lessons Learned, production issue)
- **Likely** — matches a known risk pattern
- **Speculative** — AI-inferred, not yet validated

## Related Topics

{related_topics}

Cross-links to other templates by type:

- Error: diagnostic help if the risk materializes
- Tip: best practice that avoids the risk entirely
- Task: detailed procedure for complex mitigation
- Reference: config or API details relevant to the risk
