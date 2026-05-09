---
type: error
name: sdk-native-security-audit-workflow-swallows-subagent-findings
confidence: Verified
tags: [security, packaging, python]
source: .claude/CLAUDE.md
---

# Error: SDK-native `security-audit` workflow swallows subagent
  findings

## Signature

SDK-native `security-audit` workflow swallows subagent
  findings

## Root Cause

`attune workflow run security-audit` returns successfully but `metadata.findings` is `{}` and `final_output` only contains the orchestrator's planning message ("I'll launch four subagents..."). The SDK adapter doesn't aggregate `AssistantMessage` content from the spawned subagents back into the parent result. For real pre-release security checks, run bandit, detect-secrets, and pip-audit directly against the venv until the SDK adapter is fixed.

## Resolution

1. `attune workflow run security-audit` returns successfully but `metadata.findings` is `{}` and `final_output` only contains the orchestrator's planning message ("I'll launch four subagents...")

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
