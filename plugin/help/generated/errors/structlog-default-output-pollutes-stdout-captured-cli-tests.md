---
type: error
name: structlog-default-output-pollutes-stdout-captured-cli-tests
confidence: Verified
tags: [testing, packaging]
source: .claude/CLAUDE.md
---

# Error: structlog default output pollutes stdout-captured CLI
  tests

## Signature

structlog default output pollutes stdout-captured CLI
  tests

## Root Cause

structlog's default `ConsoleRenderer` writes log lines to `sys.stdout`, not stderr. `capsys.readouterr().out` in a pytest CLI test that emits JSON ends up with log lines like `2026-04-17 [info     ] rag.run ...` prepended to the JSON payload, breaking `json.loads()`.

## Resolution

1. parse from the first `{` (`json.loads(text[text.find("{"):])`) or configure structlog to stderr in the CLI's `main()` before running the pipeline

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: structlog default output pollutes stdout-captured CLI
  tests
- Tip: Best practice: structlog default output pollutes stdout-captured CLI
  tests
- Task: Update test mocks and assertions
