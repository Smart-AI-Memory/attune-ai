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
   Call the `security_audit` MCP tool with the scoped path:

   ```
   security_audit(path="<user-specified path>")
   ```

4. **Choose follow-up action**
   Want me to fix the critical issues?; Should I generate security tests for the flagged files?; Want a deeper scan of a specific directory?


## Related Topics
- **Reference**: Skill: security-audit — full reference
