---
type: faq
name: patch-the-source-module-for-from-x-import-y-in-function-bodies
tags: [testing, security, imports]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about patch the source module for from ..X import Y in function bodies?

## Answer

When a function does `from ..real_tools import RealSecurityAuditor`, patching `_strategies.base.RealSecurityAuditor` fails (not at module scope). Instead patch `real_tools.RealSecurityAuditor` — the source module where the name IS at module scope.

```
from ..real_tools import RealSecurityAuditor
```

## Related Topics
- **Error**: Detailed error: Patch the source module for `from ..X import Y` in function
  bodies
