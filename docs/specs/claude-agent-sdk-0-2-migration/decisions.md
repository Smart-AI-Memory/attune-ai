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

## T4 — root cause located via static analysis (2026-06-16, session 2)

Pinned the mechanism with **zero key spend** by diffing the
result-handling path between the working 0.1.63 and broken 0.2.102,
and inspecting each SDK's bundled CLI. The live-key capture (above)
is the only remaining unknown and is **parked until API access
returns** (no key available for a few days).

### The two changes that combine to break it

1. **Bundled CLI version bumped.** Both SDKs ship their own `claude`
   binary at `claude_agent_sdk/_bundled/claude` — and CI has no system
   `claude`, so the bundle IS the binary that runs.
   - SDK 0.1.63 bundles Claude Code **2.1.114**.
   - SDK 0.2.102 bundles Claude Code **2.1.178**.
2. **Result-handling got stricter in 0.2.x.**
   - 0.1.63 `_read_messages` (query.py:246-250): on a `result`
     message it just sets `_first_result_event` and forwards it —
     **never inspects `is_error`**. A trailing `ProcessError` is sent
     to the stream as `{"type":"error","error": str(e)}` (the raw
     "Command failed exit code 1" text).
   - 0.2.102 `_read_messages` (query.py:304-353): **new** — on a
     `result` with truthy `is_error` it stores
     `_last_error_result_text = "; ".join(errors) or str(subtype)`;
     then a trailing `ProcessError` is **rewritten** to
     `f"Claude Code returned an error result: {…}"`.
   - Both versions' `receive_messages` raise on a `type=="error"`
     stream message (identical) — so the injected error becomes the
     raised exception either way.

### Why the observed string is `"...error result: success"`

CLI 2.1.178 emitted a result with **`is_error: true`, empty `errors`,
`subtype: "success"`**, then exited non-zero on teardown. 0.2.x's new
code captured `subtype` → `"success"` (empty `errors` falls back to
subtype) and rewrote the teardown `ProcessError` into the literal
`"Claude Code returned an error result: success"`. 0.1.63 lacked this
path AND bundled the older 2.1.114, so it never surfaced.

### Ruled out (not the cause)

- **`--task-budget` / `--max-turns` flag rejection.** All 3
  `task_budget` sites (`rag_code_gen`, `security_audit`,
  `code_review`) use the guarded `get_task_budget()` which returns
  None when the probe sees no `--task-budget` in `--help` (the
  bundled 2.1.178 lists neither flag). No direct `task_budget=`
  assignment exists. And the failure is **systemic** — it hit
  perf-audit / bug-predict, which never set `task_budget` or
  `max_turns` at all. So per-flag rejection cannot explain a
  whole-suite break.
- **Too-old CLI (< MINIMUM_CLAUDE_CODE_VERSION = 2.0.0).** Both
  bundles are 2.1.x; the SDK version check only warns anyway.

### The one remaining unknown (needs the parked live capture)

*Why* CLI 2.1.178 sets `is_error: true` on a `subtype: "success"`
result. That single envelope decides the fix.

### Validation command (run when API access returns)

Capture the raw envelope directly from the bundled CLI — bypasses the
SDK result-handling AND is robust to the nested-Bash teardown trap
(we read stdout, not the SDK's collector):

```bash
BUNDLED=".venv/lib/python3.11/site-packages/claude_agent_sdk/_bundled/claude"
set -a && source ~/.attune/anthropic.env && set +a
echo "say hi" | "$BUNDLED" --print --output-format stream-json \
  --verbose --system-prompt "" --max-budget-usd 10 \
  --permission-mode bypassPermissions 2>&1 | tail -5
# Inspect the final {"type":"result",...} line: is_error / subtype /
# errors. Drop/add flags one at a time to see which (if any) flips
# is_error -> true. If is_error is true with NO flags, it's a CLI
# 2.1.178 bug, not an attune flag.
```

### Candidate fixes (ranked, decide after the capture)

1. **Wait + re-pin** to a newer 0.2.x whose bundled CLI no longer
   emits is_error-on-success — if the capture shows a flagless CLI
   bug (likely transient upstream). Lowest attune-side risk.
2. **Adapter tolerance** — in attune's `collect_agent_output` error
   path, treat the specific "error result: success" (subtype success
   + teardown exit) as a non-fatal teardown artifact. Targeted but
   risks masking real errors; only if the CLI behavior is permanent.
3. **Drop the triggering flag** — if the capture isolates one
   isolation flag that flips is_error, stop passing it.

**PR #917 is DRAFT — do not merge.** Resume gate: API access → run
the validation command above → pick a fix from the ranked list.
