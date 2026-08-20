---
type: warning
name: hooks-warning
feature: hooks
depth: warning
generated_at: 2026-08-20T12:28:08.536306+00:00
source_hash: 6a74897099089de928581379ad010c61f7449b270204090c659e122d08d62c1c
status: generated
---

# The hook system — shipped scripts that Claude Code runs on session and tool lifecycle events

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| Hook blocks a real tool on odd input | script raised / exited non-zero on malformed stdin | parse defensively and exit `0` on any non-dict / non-JSON payload | high |
| Tool not blocked when it should be | wrong exit code (only `2` blocks a `PreToolUse`) | `sys.exit(2)` to block | high |
| Banner or side effect missing | script exceeded its `hooks.json` timeout and was killed | keep the script fast; move slow work off the critical path | medium |
| Hook never fires | event not wired in `hooks.json`, or wrong event name | check the mapping and the Claude Code event name | medium |

### Risk areas

- **Fail open.** A `PreToolUse` guard must exit `0` on malformed input,
  never crash — a crashing guard silently stops blocking.
- **Only `2` blocks.** Any other exit code from a `PreToolUse` hook
  lets the tool through.
- **Timeouts are real.** A script slower than its `hooks.json` timeout
  is killed and its effect is lost.

### Diagnosis order

1. Is the event wired to the script in `hooks.json`?
2. What exit code does the script return for this payload?
3. Does it fail open on malformed stdin?
4. Is it finishing inside its timeout?
