---
type: faq
name: attune-workflow-run-code-review-and-security-audit-require-a
tags: [security, imports, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `NotADirectoryError` (attune workflow run code-review and security-audit require a DIRECTORY for --path, not a single file — passing a file raises NotADirectoryError deep inside the Claude Agent SDK call)?

## Answer

discovered while trying to deep-review two specific files (`rag_hook.py`, `rag_code_gen.py`). Direct file paths fail after a few seconds of spurious SDK spin-up (wasted API budget).

```
rag_hook.py
```

## Related Topics
- **Error**: Detailed error: `attune workflow run code-review` and
  `security-audit` require a DIRECTORY for `--path`, not
  a single file — passing a file raises
  `NotADirectoryError` deep inside the Claude Agent SDK
  call
