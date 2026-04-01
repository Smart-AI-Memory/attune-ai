---
type: faq
name: ruff-parses-pytest-ini-as-python
tags: [testing, git, claude-code, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about ruff parses pytest.ini as Python?

## Answer

When committing `pytest.ini` alongside `.py` files, ruff's pre-commit hook tries to parse it as Python and produces syntax errors. Commit `pytest.ini` in a separate commit from Python files so the ruff hook only sees valid Python.

```
pytest.ini
```

## Related Topics
- **Error**: Detailed error: ruff parses pytest.ini as Python
