---
name: security-audit
source: content/features/security-audit.md
tags:
- security
- audit
- owasp
- scanning
- cve
type: reference
---

# Audit code for vulnerabilities with four Agent SDK subagents

## Reference

Security-audit's public surface is the `SecurityAuditWorkflow`
class, re-exported from `attune.workflows`. `WorkflowResult` comes
from `attune.workflows` as well.

### `SecurityAuditWorkflow` — `attune.workflows.security_audit`

| Symbol | Purpose |
|--------|---------|
| `SecurityAuditWorkflow(*, system_prompt_suffix="", **kwargs)` | Construct the workflow. `system_prompt_suffix` (keyword-only) is appended to the orchestrator's system prompt; the empty default preserves stock behavior. Other kwargs pass to `BaseWorkflow`. |
| `SecurityAuditWorkflow.execute(**kwargs)` | **Async.** Run the audit. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`); other kwargs are ignored. Returns a `WorkflowResult`. |
| `SecurityAuditWorkflow.name` | The registered slug, `"security-audit"`. |
| `SecurityAuditWorkflow.stages` | `["agent-audit"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → budget

| Depth | Max turns | Behavior |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | Thorough; additionally engages a token-aware budget and extended thinking. |

### The four subagents

| Subagent | Domain |
|----------|--------|
| `vuln-scanner` | Injection, `eval`/`exec`, XSS, path traversal, command injection, insecure deserialization. |
| `secret-detector` | Hardcoded credentials, API keys, tokens, private keys, sensitive env vars in source. |
| `auth-reviewer` | Missing auth, broken access control, session weaknesses, privilege escalation. |
| `remediation-planner` | Prioritized fix plan grouped by effort, with time estimates and dependencies. |

### `WorkflowResult` fields read after an audit

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the audit completed. |
| `final_output` | `Any` | The synthesized report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short posture summary. |
| `suggestions` | `list[NextAction]` | Prioritized remediation actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run. |
| `metadata` | `dict` | Echoes `path`, `depth`, `max_turns`, and `subagent_transcripts`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/security-audit` in a Claude Code conversation. |
| CLI | `attune workflow run security-audit --path <p> [--depth quick\|standard\|deep] [--json] [--cheap]`. |
| MCP tool | `security_audit` — one required `path` argument; runs at standard depth (the handler does not pass `depth`). |
| Python | `await SecurityAuditWorkflow().execute(path=<p>, depth=<d>)`. |
