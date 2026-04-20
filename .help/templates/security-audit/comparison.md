---
type: comparison
feature: security-audit
depth: comparison
generated_at: 2026-04-19T18:45:07.189640+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Security audit approaches: workflow vs skill vs CLI

You have three ways to run security audits in Attune AI. Each serves different use cases and integrates with different parts of your workflow.

## Feature comparison

| Approach | Best for | Speed | Output format | Integration |
|----------|----------|-------|---------------|-------------|
| **Workflow** (`attune workflow run security-audit`) | CI/CD pipelines, automated scans | Fast batch processing | Severity-grouped findings with CWE IDs | Terminal, scripts |
| **Skill** (`/security-audit`) | Interactive code review, ad-hoc scans | Interactive with follow-up | Structured results in conversation | Claude Code chat |
| **Alert system** (`attune alerts init`) | Continuous monitoring, threshold alerts | Background monitoring | Notifications when metrics exceed limits | Email, webhooks |

## Key differences

**Scope and depth:**
- The workflow runs four specialized subagents (vulnerability scanner, secret detector, authentication reviewer, remediation planner) for comprehensive coverage
- The skill focuses on immediate findings you can act on during development
- Alerts monitor ongoing telemetry patterns rather than scanning code directly

**Workflow integration:**
- Workflow fits into automated pipelines and generates machine-readable output
- Skill integrates with your coding conversation for real-time feedback
- Alerts run continuously in the background and notify you when problems emerge

**Output format:**
- Workflow provides severity scores (0-100), CWE identifiers, and structured markdown
- Skill gives clickable file links and conversational follow-up options
- Alerts send notifications with metric values and threshold breaches

## Use the workflow when...

- You're setting up CI/CD security checks
- You need comprehensive coverage with CWE mapping
- You want automated batch processing of multiple files
- You're generating reports for compliance or auditing

```bash
attune workflow run security-audit --path "src/"
```

## Use the skill when...

- You're actively coding and want immediate feedback
- You need to explore findings interactively
- You want to ask follow-up questions about vulnerabilities
- You prefer working within your Claude Code conversation

```
/security-audit src/auth.py
```

## Use alerts when...

- You want continuous monitoring of security metrics
- You need notifications when vulnerability counts spike
- You're tracking trends in code quality over time
- You want automated alerts for threshold breaches

```bash
attune alerts init --metric vulnerability_count --threshold 5
```

## Recommendation

**Start with the skill** for day-to-day development — it's the fastest way to catch issues as you code. **Add the workflow** to your CI pipeline for comprehensive pre-deployment scanning. **Set up alerts** once you have baseline metrics to monitor ongoing security health.

Most teams use all three: skills during development, workflows in CI/CD, and alerts for continuous monitoring.
