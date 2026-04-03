---
type: error
name: linkedin-paste-use-ascii-markers-not-unicode-arrows
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: LinkedIn paste: use ASCII markers, not Unicode arrows

## Signature

LinkedIn paste: use ASCII markers, not Unicode arrows

## Root Cause

Unicode characters like `▶`/`◀` used as code-block delimiters get misinterpreted by LinkedIn's editor, causing content duplication and markers leaking into code blocks. Use plain ASCII like `--- CODE START ---` / `--- CODE END ---` instead.

## Resolution

1. Use plain ASCII like `--- CODE START ---` / `--- CODE END ---` instead

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: LinkedIn paste: use ASCII markers, not Unicode arrows
