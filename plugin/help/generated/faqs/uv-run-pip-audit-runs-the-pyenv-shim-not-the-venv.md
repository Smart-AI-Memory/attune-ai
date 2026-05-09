---
type: faq
name: uv-run-pip-audit-runs-the-pyenv-shim-not-the-venv
tags: [security, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about uv run pip-audit runs the pyenv shim, not the venv?

## Answer

The pyenv `pip-audit` shim takes precedence on PATH, so `uv run pip-audit` audits whatever Python pyenv points at — not `.venv/`. Symptom: bumping a dep in the venv (verified with `uv pip show`) doesn't change the pip-audit output.

**How to fix:**
- install pip-audit *into* the venv with `.venv/bin/python -m pip install pip-audit` and run `.venv/bin/python -m pip_audit`

```
 shim takes precedence on PATH, so
```

## Related Topics
- **Error**: Detailed error: `uv run pip-audit` runs the pyenv shim, not the venv
