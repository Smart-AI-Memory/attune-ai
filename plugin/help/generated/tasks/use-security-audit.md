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

1. **Scope the security-audit request**
   The skill asks scoping questions before running.

2. **Execute the security-audit workflow**
   Run the MCP tool with your scoped parameters.

   ```
   security_audit(path="<user-specified path>")
   ```

3. **Review results and choose follow-up**
   The skill offers contextual next actions after presenting results.


## Related Topics
- **Reference**: Skill: security-audit — full reference
