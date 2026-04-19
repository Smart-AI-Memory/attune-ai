---
type: tip
feature: security-audit
depth: tip
generated_at: 2026-04-19T18:44:50.200296+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Start with directory scans, not individual files

When running security audits, scan entire directories rather than cherry-picking files. The `SecurityAuditWorkflow` uses four specialized subagents that work best when they can see the full context of your codebase.

Use `/security-audit src/` instead of `/security-audit src/auth.py` — vulnerabilities often span multiple files, and path traversal issues in particular require seeing how files interact across directory boundaries.

**Tags:** `security`, `audit`, `owasp`, `scanning`
