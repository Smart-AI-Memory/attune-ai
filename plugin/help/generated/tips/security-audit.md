---
name: security-audit
source: content/features/security-audit.md
tags:
- security
- audit
- owasp
- scanning
- cve
type: tip
---

# Audit code for vulnerabilities with four Agent SDK subagents

## Notes & tips

- **Depend on the documented public surface.** The supported API
  is `SecurityAuditWorkflow` (its constructor and async `execute`)
  plus the `WorkflowResult` it returns. Names with a leading
  underscore — `_run_agent_audit`, `_SUBAGENT_NAMES` — are
  internal and may change.
- **Use `metadata["subagent_transcripts"]` to attribute findings.**
  The synthesized report is the headline; the recovered transcripts
  show which of the four subagents raised each finding, which helps
  when triaging.
- **Start shallow, then go deep on the hot spots.** Run `standard`
  broadly, and spend a `deep` (extended-thinking) audit only on the
  modules that came back risky.
- **Use `--cheap` for routine CLI runs.** It forces unpinned
  subagents onto Haiku, trading some depth for cost.
- **Monitoring is a separate subsystem.** Alerting and telemetry
  storage live in `attune.monitoring`, not here — this feature is
  the audit workflow only.
