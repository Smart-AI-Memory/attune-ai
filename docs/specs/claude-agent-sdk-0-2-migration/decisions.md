# claude-agent-sdk 0.2.x Migration — Decisions & Findings

## Decisions

- **d1 (2026-06-16, approved):** Adopt the 0.2.x line with a new
  deliberate cap `>=0.2.101,<0.3.0`. `uv lock` resolves to the actual
  latest in range, **0.2.102** (0.2.101 was an estimate; 0.2.102 is
  latest and within the cap).

## T0 — empirical breakage scan (2026-06-16)

Run in worktree `sdk-0-2-migration` off `origin/main`, fresh
`uv sync --all-extras`, SDK resolved `0.1.63 -> 0.2.102`.

### API compatibility — PASS

Every symbol and `ClaudeAgentOptions` field the adapter
(`agent_sdk_adapter.py`) and workflows use still exists in 0.2.102:
`query`, `ClaudeAgentOptions`, `AssistantMessage`, `ResultMessage`,
`SystemMessage`, `types.TextBlock`; options fields `system_prompt`,
`task_budget`, `mcp_servers`, `setting_sources`, `allowed_tools`,
`permission_mode`. No symbol renames/removals affect attune. attune
already uses the `claude_agent_sdk` package name; `TodoWrite` is
unused in `src/`.

### Unit suite (keyless) — PASS

`ANTHROPIC_API_KEY="" pytest tests/unit`:
**17857 passed, 72 skipped, 7 xfailed, 0 failed** (40m).
Trailing "Event loop is closed" is asyncio teardown noise after the
green summary, not a failure.

### Scope implication for T1 / T2

The two behavioral risks (system-prompt default, MCP
background-connection) produced **zero unit-test failures**. BUT the
keyless unit suite mocks/skips the real SDK subprocess, so it does
not exercise those behavioral defaults end-to-end. Per the
"registered != working / dogfood the live loop" discipline, T0 is
not complete until at least one real-SDK round-trip confirms the
live loop under 0.2.102. T1/T2 may collapse to "no change needed"
if that round-trip is clean.

### Open item

- Run one budget-capped real-SDK workflow (live-loop dogfood) to
  validate behavioral defaults. Pending cost go-ahead.

## T1 / T2 — static audit (2026-06-16): NO CODE CHANGE NEEDED

- **T1 (system-prompt default):** 16 `ClaudeAgentOptions` sites; all
  16 splat `sdk_isolation_kwargs()` which sets `setting_sources=[]`,
  already suppressing the Claude Code system prompt regardless of the
  SDK default. 15/16 also set explicit `system_prompt`; the 1
  exception (`rag_code_gen.py:392`) carries context in the prompt +
  isolation — behavior unchanged 0.1.63 -> 0.2.102. The 0.2.x
  default change does not reach attune.
- **T2 (MCP background-connection):** no workflow passes
  `mcp_servers` into `ClaudeAgentOptions`, so the background-connect
  default does not affect workflow runs.
- A drift-guard test already asserts every site uses
  `sdk_isolation_kwargs()`; it passed in the green unit run.

## T4 — verification status

- Unit (keyless): PASS (17857). Live-loop (real SDK) validation:
  run `integration-auth` in CI's clean env (NOT a local nested-Bash
  run, which the SDK-nested-failure trap would corrupt). Budget-capped.

## T4 — live-loop validation FAILED (2026-06-16)

`integration-auth` on the branch (run 27591684930, budget-capped)
**failed systemically** against 0.2.102. Every real-API workflow
(perf-audit, bug-predict, …) raised, deep in the SDK:

```
Exception: Claude Code returned an error result: success
  claude_agent_sdk/_internal/query.py:852  receive_messages
```

Workflows returned `source-failure` markers instead of analysis. So
0.2.102 has a real behavioral incompatibility in the result-message
path that the mocked unit suite (17857 green) and the static T1/T2
audit could NOT surface — vindicating the decision to run the paid
dogfood. **T1/T2 are reopened.**

### Next (focused follow-up)

- Reproduce ONE workflow with 0.2.102 + a real key in a CLEAN env
  (not nested Bash), capture the raw `ResultMessage` envelope —
  the SDK raises inside `receive_messages`, before attune's
  `collect_agent_output` sees it, so the result contract changed.
- Bisect which 0.2.x introduced the break (0.2.0 .. 0.2.102) to
  isolate the change.
- Decide: adapter/result-handling fix, or pin to the last good 0.2.x.

**PR #917 is DRAFT — do not merge.**
