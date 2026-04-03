---
type: faq
name: registry-count-assertions-are-scattered-across-test-files
tags: [testing, security, git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about registry count assertions are scattered across test files?

## Answer

When merging SDK workflow variants (reducing `_SDK_WORKFLOW_MAP` from 12→9 entries), hardcoded count assertions like `assert len(_SDK_WORKFLOW_MAP) == 12` and expected-set assertions exist in routing behavioral tests, validation framework tests, and coverage batch tests. `SecurityAuditAgentSDKWorkflow`) across all test files when changing registry size.

**How to fix:**
- Always grep for the old count and old class names (e.g

```
_SDK_WORKFLOW_MAP
```

## Related Topics
- **Error**: Detailed error: Registry count assertions are scattered across test files
