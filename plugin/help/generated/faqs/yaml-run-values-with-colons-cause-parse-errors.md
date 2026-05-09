---
type: faq
name: yaml-run-values-with-colons-cause-parse-errors
tags: [ci]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about YAML run: values with colons cause parse errors?

## Answer

A GitHub Actions `run:` like `run: gh pr review --body "Auto-approved: update"` fails YAML parsing because the colon after "Auto-approved" is interpreted as a mapping. Remove the colon or quote the entire value.

```
run: gh pr review --body "Auto-approved: update"
```

## Related Topics
- **Error**: Detailed error: YAML `run:` values with colons cause parse errors
