---
type: warning
name: linkedin-paste-use-ascii-markers-not-unicode-arrows
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: LinkedIn paste: use ASCII markers, not Unicode arrows

## Condition

Unicode characters like `▶`/`◀` used as code-block delimiters get misinterpreted by LinkedIn's editor, causing content duplication and markers leaking into code blocks

## Risk

Unicode characters like `▶`/`◀` used as code-block delimiters get misinterpreted by LinkedIn's editor, causing content duplication and markers leaking into code blocks

## Mitigation

1. Use plain ASCII like `--- CODE START ---` / `--- CODE END ---` instead

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: LinkedIn paste: use ASCII markers, not Unicode arrows
