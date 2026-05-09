---
type: warning
name: structlog-default-output-pollutes-stdout-captured-cli-tests
confidence: Verified
tags: [testing, packaging]
source: .claude/CLAUDE.md
---

# Warning: structlog default output pollutes stdout-captured CLI
  tests

## Condition

structlog's default `ConsoleRenderer` writes log lines to `sys.stdout`, not stderr

## Risk

`capsys.readouterr().out` in a pytest CLI test that emits JSON ends up with log lines like `2026-04-17 [info     ] rag.run ...` prepended to the JSON payload, breaking `json.loads()`

## Mitigation

1. parse from the first `{` (`json.loads(text[text.find("{"):])`) or configure structlog to stderr in the CLI's `main()` before running the pipeline
2. Don't just silence logs — they're useful in prod

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: structlog default output pollutes stdout-captured CLI
  tests
