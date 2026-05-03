---
name: check-health
source: src/attune/cli_minimal.py
summary: This template covers how to use the `attune doctor` command to run a diagnostic
  health check that identifies configuration and dependency issues in your environment.
tags:
- cli
- setup
type: quickstart
---

# Quickstart: Run an Environment Health Check

Diagnose configuration and dependency issues before they affect your workflow.

```bash
attune doctor
```

**Result:** A health report listing each check with a **PASS**, **WARN**, or **ERROR** status.

**Next steps:**
- Review the output and address any **WARN** or **ERROR** items before proceeding.
- Re-run `attune doctor` after making changes to confirm the issues are resolved.

## Related Topics

- [Troubleshooting Common Errors](#)
- [Configuration Reference](#)
