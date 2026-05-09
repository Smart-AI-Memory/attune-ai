---
type: faq
name: sdk-native-security-audit-workflow-swallows-subagent-findings
tags: [security, packaging, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about sDK-native security-audit workflow swallows subagent findings?

## Answer

`attune workflow run security-audit` returns successfully but `metadata.findings` is `{}` and `final_output` only contains the orchestrator's planning message ("I'll launch four subagents..."). The SDK adapter doesn't aggregate `AssistantMessage` content from the spawned subagents back into the parent result.

```
attune workflow run security-audit
```

## Related Topics
- **Error**: Detailed error: SDK-native `security-audit` workflow swallows subagent
  findings
