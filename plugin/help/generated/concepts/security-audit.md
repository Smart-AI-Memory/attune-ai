---
name: security-audit
source: content/features/security-audit.md
tags:
- security
- audit
- owasp
- scanning
- cve
type: concept
---

# Audit code for vulnerabilities with four Agent SDK subagents

## Overview

Security-audit scans a codebase for vulnerabilities and reports
them by severity with prioritized remediation. It is **SDK-native**:
`SecurityAuditWorkflow` delegates the analysis to four specialized
Claude Agent SDK subagents and synthesizes their findings into one
report — an overall security score, findings grouped CRITICAL /
HIGH / MEDIUM / LOW, and an effort-ranked remediation plan.

Like its sibling bug-predict, it **predicts** rather than proves:
the four subagents apply LLM judgment over the code (via Read /
Glob / Grep), so a finding is a lead to verify, not a confirmed
exploit. Treat a CRITICAL finding as "audit this first," not "this
is definitely exploitable."

You reach security-audit four ways, all of which run the same
workflow:

- the **`/security-audit`** skill, inside a Claude Code
  conversation;
- the CLI — **`attune workflow run security-audit`**;
- the **`security_audit`** MCP tool (one required `path`
  argument);
- the Python API — `await SecurityAuditWorkflow().execute(...)`,
  documented here for wiring an audit into a hook, a CI gate, or a
  custom tool.

The audit workflow is self-contained — it owns scanning and
report synthesis only. Alerting, telemetry storage, and
monitoring live in a **separate** subsystem (`attune.monitoring`)
and are not part of this feature.

## Concepts

### Four subagents, one synthesized report

`SecurityAuditWorkflow.execute` issues a single
`claude_agent_sdk.query` whose options define four subagents, each
scoped to `Read` / `Glob` / `Grep`:

| Subagent | What it looks for |
|----------|-------------------|
| `vuln-scanner` | `eval`/`exec` usage, SQL injection, XSS, path traversal, command injection, and insecure deserialization. Reports file, line, severity, and remediation advice. |
| `secret-detector` | Hardcoded API keys, passwords, tokens, private keys, database credentials, and sensitive environment variables committed to source — plus how to externalize each. |
| `auth-reviewer` | Missing auth checks, broken access control, insecure session management, weak password policies, and privilege-escalation risks. |
| `remediation-planner` | Reviews all findings and builds a prioritized fix plan, grouped by effort (quick wins / medium / major refactors), with time estimates and inter-fix dependencies. |

The orchestrator then synthesizes all four into one report with
three sections — **Summary** (an overall 0–100 security score plus
a 2–3 sentence posture summary), **Security** (consolidated
findings grouped CRITICAL / HIGH / MEDIUM / LOW), and
**Suggestions** (remediation steps ordered by priority, each with
an effort estimate).

### Depth controls the budget — and deep engages extended thinking

`execute` takes a `depth` of `"quick"`, `"standard"` (default),
or `"deep"`. Depth maps to the maximum agent turns and a per-run
cost cap:

| Depth | Max agent turns |
|-------|-----------------|
| `quick` | 10 |
| `standard` | 20 |
| `deep` | 40 |

An unrecognized depth falls back to the standard budget (20
turns). A `deep` audit additionally engages a token-aware task
budget and **extended thinking** (with high reasoning effort), so
the remediation-planner and architecture-level reasoning get more
room — at higher cost.

### Findings survive synthesis

Two mechanisms keep findings from being lost in the
orchestrator's synthesis step:

- the query runs with a structured `output_format`, so findings
  parse into categories reliably rather than depending on prose
  formatting; and
- after the run, the per-subagent transcripts are recovered from
  the session and appended to the report under a
  **"## Subagent findings"** heading — so a finding a subagent
  surfaced is preserved even if the synthesis under-reports it.
  The raw transcripts are also attached to the result's
  `metadata["subagent_transcripts"]`.

### `execute` is async, and honors only `path` and `depth`

`execute` is a coroutine — `await` it (or drive it with
`asyncio.run`). Calling it without awaiting is the most common
mistake.

It reads exactly two keyword arguments: `path` (required) and
`depth` (default `"standard"`). Any other keyword is ignored. An
empty or missing `path` returns a failed `WorkflowResult` rather
than raising.

### The result is a `WorkflowResult`

`execute` returns a `WorkflowResult` (from `attune.workflows`).
The synthesized report lands in `final_output` — a serialized
report when the findings parse, or the raw markdown otherwise —
with a short `summary`, a `suggestions` list, the `cost_report`,
the `provider`, and a `metadata` dict echoing `path`, `depth`,
`max_turns`, and the recovered `subagent_transcripts`. On failure,
`success` is `False` and `error` / `error_type` carry the reason.
