---
type: faq
name: structlog-default-output-pollutes-stdout-captured-cli-tests
tags: [testing, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about structlog default output pollutes stdout-captured CLI tests?

## Answer

structlog's default `ConsoleRenderer` writes log lines to `sys.stdout`, not stderr. `capsys.readouterr().out` in a pytest CLI test that emits JSON ends up with log lines like `2026-04-17 [info     ] rag.run ...` prepended to the JSON payload, breaking `json.loads()`.

**How to fix:**
- parse from the first `{` (`json.loads(text[text.find("{"):])`) or configure structlog to stderr in the CLI's `main()` before running the pipeline

```
ConsoleRenderer
```

## Related Topics
- **Error**: Detailed error: structlog default output pollutes stdout-captured CLI
  tests
