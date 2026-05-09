---
type: faq
name: noqa-f401-re-exports-break-silently-on-satellite-file-deletion
tags: [security, imports, python]
source: .claude/CLAUDE.md
---

# FAQ: Why does # noqa: F401 re-exports break silently on satellite file deletion?

## Answer

SDK-native workflows re-export constants from legacy satellite files (e.g. `from .security_audit_patterns import SECURITY_PATTERNS  # noqa: F401`).

```
from .security_audit_patterns import SECURITY_PATTERNS  # noqa: F401
```

## Related Topics
- **Error**: Detailed error: `# noqa: F401` re-exports break silently on satellite file
  deletion
