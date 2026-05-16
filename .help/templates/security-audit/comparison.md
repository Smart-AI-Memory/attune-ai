---
type: comparison
name: security-audit-comparison
feature: security-audit
depth: comparison
generated_at: 2026-05-16T06:19:45.822543+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Security Audit: Workflow vs Skill

Attune exposes security auditing through two distinct entry points: the **`security-audit` workflow** (CLI / SDK) and the **`/security-audit` skill** (Claude Code conversation). Both scan for the same vulnerability classes — `eval`/`exec` usage, path traversal, hardcoded secrets, and injection risks — but they differ in depth, output format, and how you integrate them.

## Feature comparison

| Capability | `security-audit` workflow | `/security-audit` skill |
|---|---|---|
| **Entry point** | `attune workflow run security-audit --path "src/"` | `/security-audit <path>` in Claude Code |
| **Output format** | Severity-grouped findings with CWE identifiers | Structured markdown in your conversation |
| **Subagents** | Four specialized subagents: `vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner` | Single-pass pattern scan |
| **Report sections** | Summary (security score 0–100), severity-grouped findings (CRITICAL → LOW), prioritized remediation with effort estimates | Findings listed in conversation |
| **OWASP mapping** | Yes, via deep scan mode (~5 min) | No |
| **Fix suggestions** | Yes — remediation planner subagent estimates effort per fix | No |
| **CI / scripted use** | Yes — invoke from a script, pipeline, or SDK | No — requires an interactive Claude Code session |
| **Scan depth control** | Quick (~30 s), Standard (~2 min), Deep (~5 min) | Single depth |
| **Secrets detection** | `SecretDetector` / `SecretsDetector` with typed `SecretType` | Pattern-based |
| **File + line citations** | Yes — orchestrator prompt requires file paths and line numbers | Best-effort |

## Vulnerability coverage

Both entry points cover the same core categories:

| Category | Examples caught |
|---|---|
| **Code injection** | `eval()`, `exec()`, `compile()` on untrusted input |
| **Path traversal** | File operations without path validation |
| **Hardcoded secrets** | API keys, tokens, passwords committed to source |
| **SQL / command injection** | String concatenation in queries or shell commands |
| **SSRF** | HTTP requests to user-controlled URLs |
| **Weak cryptography** | MD5/SHA1 for security, hardcoded IVs |

## Tradeoffs

**The workflow is the stronger tool for most production use cases.** It runs four coordinated subagents, produces a scored report mapped to severity levels, and emits CWE identifiers that downstream tooling (tickets, dashboards) can consume. The skill trades depth for speed and convenience — useful when you want a quick sanity check without leaving your conversation.

The skill has no CI integration path and no OWASP mapping. If you need a repeatable, auditable artifact — for a release gate, a compliance review, or a PR check — the workflow is the right choice.

## Use the `security-audit` workflow when…

- You are running a pre-release security gate or CI check.
- You need a scored report (0–100) with CWE identifiers and severity tiers.
- You want OWASP-mapped findings or prioritized remediation steps with effort estimates.
- You need to scan a large directory and control scan depth (quick / standard / deep).
- You are invoking the audit from a script, SDK, or automated pipeline.

## Use the `/security-audit` skill when…

- You are already in a Claude Code session and want a fast, interactive check on a file or small directory.
- You do not need OWASP mapping, CWE identifiers, or a formal report.
- You are doing exploratory work and a full workflow run would be overkill.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
