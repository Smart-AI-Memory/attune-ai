---
type: faq
name: bandit-b108-blocks-hardcoded-tmp-paths
tags: [python]
source: .claude/CLAUDE.md
---

# FAQ: Why does bandit B108 blocks hardcoded /tmp paths?

## Answer

Using a literal `/tmp/...` string in `subprocess.run` or `open()` triggers bandit B108 (insecure temp file usage). This came up in `doc_audit/workflow.py` which used `/tmp/doc-audit-site` for mkdocs builds.

**How to fix:**
- use `tempfile.TemporaryDirectory(prefix="...")` instead

```
 string in
```

## Related Topics
- **Error**: Detailed error: Bandit B108 blocks hardcoded `/tmp` paths
