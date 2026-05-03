---
name: run-security-audit
source: src/attune/cli_minimal.py
summary: This template guides developers through running an automated security audit
  on their codebase to identify and categorize vulnerabilities by severity using CWE
  identifiers.
tags:
- workflow
- security
type: quickstart
---

# Quickstart: Run a Security Audit

Scan your codebase for vulnerabilities and review severity-grouped findings.

```bash
attune workflow run security-audit --path "src/"
```

**Output:** Findings grouped by severity, each labeled with a [CWE identifier](https://cwe.mitre.org/).

**Next step:** Resolve all critical issues, then generate tests with:

```bash
attune workflow run test-gen
```

## Related Topics

- [Interpreting Security Findings](#)
- [Fixing Common Vulnerabilities](#)
- [Running the Test Generation Workflow](#)
