---
type: faq
name: full-coverage-runs-on-15k-test-suites-timeout-easily
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: Why does full coverage runs on 15k+ test suites timeout easily?

## Answer

`pytest --cov=src/attune` with the full test suite takes 10+ minutes. For development feedback, use targeted coverage: `pytest tests/unit/module/ --cov=attune.module --no-cov-on-fail` to measure specific modules in seconds.

```
pytest --cov=src/attune
```

## Related Topics
- **Error**: Detailed error: Full coverage runs on 15k+ test suites timeout easily
