---
type: faq
name: sdk-native-workflows-validate-in-execute-not-input-schema
tags: [testing, security]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about sDK-native workflows validate in execute(), not input_schema?

## Answer

After merging to SDK-native, workflows no longer declare `input_schema` as a class attribute — path validation happens inside `execute()`. Tests asserting `Workflow.input_schema is not None` must be removed or updated.

```
input_schema
```

## Related Topics
- **Error**: Detailed error: SDK-native workflows validate in `execute()`, not `input_schema`
