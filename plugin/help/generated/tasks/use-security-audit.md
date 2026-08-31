---
type: task
name: use-security-audit
tags: [skill, task]
source: plugin/skills/security-audit/SKILL.md
---

# Task: Use the security-audit skill

Scan code for security vulnerabilities including eval/exec usage, path traversal, hardcoded secrets, and injection risks. Triggers on: security, vulnerability, audit, scan, CVE, CWE, secrets, injection, eval, exec, OWASP.

Invoke with: `/security-audit <path or directory to scan>`

## Steps

1. **Define scope**
   "Which path should I scan?" Default to the project root if the user says "everything."

2. **Define focus**
   "Any specific concern — secrets, injection, dependencies, or a full sweep?"

3. **Run the tool**
   ### Shared command workspace (preferred)

   Open adapter `security-audit` with the validated path and focus. The invocation
   authorizes this read-only scan, so the running workspace has no confirmation
   action. Call `security_audit` and publish its exact outcome as `scan_result`,
   including health score, files scanned, and categorized path/line/severity/CWE
   findings. An incomplete scan must say “did not complete,” never “clean.”

   Critical/high findings render one per page with bound Previous/Next actions,
   avoiding a tall unscrollable form. `finish_security_audit` records the report;
   `handoff_to_fix` prepares an explicit Fix input containing all critical/high
   receipts but performs no mutation. Fix retains its own exact-command approval.
   Present the terminal widget or Markdown and preserve the same pagination,
   failure, and handoff semantics in text fallback.

   Call the `security_audit` MCP tool with the scoped path:

   ```
   security_audit(path="<user-specified path>")
   ```

4. **Choose follow-up action**
   Want me to fix the critical issues?; Should I generate security tests for the flagged files?; Want a deeper scan of a specific directory?


## Related Topics
- **Reference**: Skill: security-audit — full reference
