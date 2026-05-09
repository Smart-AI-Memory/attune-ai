---
type: faq
name: unused-init-py-re-exports-become-invisible-runtime-deps
tags: [testing, imports, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about unused __init__.py re-exports become invisible runtime deps?

## Answer

Adding `from sibling_pkg.foo import Bar` to a package's `__init__.py` for "backward compat" makes that package fail to import unless `sibling_pkg` is installed — even if NO consumer actually imports `Bar` from your package. The cost is paid at import time, not use time.

```
from sibling_pkg.foo import Bar
```

## Related Topics
- **Error**: Detailed error: Unused `__init__.py` re-exports become invisible
  runtime deps
