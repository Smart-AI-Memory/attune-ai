---
type: faq
name: pip-audit-fails-on-unpublished-versions
tags: [ci, packaging]
source: .claude/CLAUDE.md
---

# FAQ: Why does pip-audit fails on unpublished versions?

## Answer

`pip-audit --strict` with a local editable install (`pip install -e .`) fails if the version in `pyproject.toml` doesn't exist on PyPI yet. The error is `Dependency not found on PyPI and could not be audited: attune-ai (5.0.0)`.

```
pip-audit --strict
```

## Related Topics
- **Error**: Detailed error: `pip-audit` fails on unpublished versions
