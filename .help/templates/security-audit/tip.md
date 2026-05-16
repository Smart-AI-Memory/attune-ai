---
type: tip
name: security-audit-tip
feature: security-audit
depth: tip
generated_at: 2026-05-16T06:19:45.817598+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Tip: Run the security audit before you review, not after

After a code review, findings feel like criticism. Before one, they feel like preparation — and you can fix issues before anyone else sees them.

Run the audit against the path you changed, not the entire repository:

```
attune workflow run security-audit --path "src/your_changed_module/"
```

This keeps the output focused. A full-repo scan on a large codebase produces noise that buries the findings you actually need to act on.

**Why:** The four subagents (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) each report independently, then the orchestrator synthesizes findings by severity. Scoping to your changed path means the synthesis stays signal-rich.

**Tradeoff:** Scanning a subdirectory can miss vulnerabilities that cross module boundaries — for example, a secret introduced in `src/utils/` that is consumed by `src/api/`. Run a full scan at release time even if you scope daily scans narrowly.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
