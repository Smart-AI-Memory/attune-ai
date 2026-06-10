# Spec: SDK Subprocess Isolation — Decisions

> Pre-committed per the "decision matrices survive contact with
> data" lesson. D1/D2 were ratified by Patrick in-session 2026-06-10
> before drafting; the rest are design decisions recorded with
> rationale so later sessions don't re-litigate.

---

## Decision matrix

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Hook gating scope | **Gate ALL 12 plugin hooks**, not a selective subset | Ratified 2026-06-10 (overrode the selective recommendation). Simplest mental model: an SDK subprocess is not an interactive session, so no hook applies. **Recorded tradeoff:** `security_guard` (eval/exec Bash blocking) and `format_on_save` are also inactive inside SDK workflow subprocesses. Revisit if a workflow agent demonstrably needs either; the gate helper makes re-enabling per-hook a one-line change. |
| D2 | Filesystem settings in SDK subprocesses | **Exclude via `setting_sources=[]`** once the empty flag value is live-verified; keep the hook gate as belt-and-suspenders | Ratified 2026-06-10. No hooks, no CLAUDE.md injection, faster + cheaper + deterministic startup; workflows carry their own system prompts. The hook gate stays for older SDKs and spawn paths that bypass the adapter. |
| D3 | Detection signal | **Dual**: `CLAUDE_CODE_ENTRYPOINT` prefix `sdk-` OR `ATTUNE_SDK_SUBPROCESS=1` | The SDK stamps `CLAUDE_CODE_ENTRYPOINT=sdk-py` into every subprocess env (findings F2) — free coverage for end users running their own SDK scripts with the plugin installed. The explicit marker survives SDK renames and covers non-SDK spawn paths attune controls. Interactive values observed: `claude-desktop` (desktop), so prefix-match `sdk-` cannot false-positive there. |
| D4 | Marker env var name | `ATTUNE_SDK_SUBPROCESS=1` | Named for what it marks (an SDK-spawned subprocess session), per the "name the env var after what it does, not who flips it" lesson. NOT `CLAUDE_CODE_SDK_SUBPROCESS` (the 2026-06-06 lesson's sketch) — that prefix implies Claude Code owns it; it's ours. |
| D5 | Where the marker is set | `agent_sdk_adapter.sdk_isolation_kwargs()` helper, splatted into EVERY `ClaudeAgentOptions` construction (15 workflow sites), drift-guarded | REVISED during Phase 2 (2026-06-10): the original "adapter only, one site" premise was wrong — each workflow constructs its own `ClaudeAgentOptions`; there is no single construction site. The helper + `TestSdkWorkflowsUseIsolationKwargs` drift guard (the `resolve_cwd_for_path` pattern) is the equivalent single source. Runner `proc_env` unchanged. |
| D6 | Gate helper location | One shared `plugin/hooks/_sdk_gate.py` (or extend the existing `_state.py`-style shared module), imported by every hook script | 12 copies of a two-line check WILL drift. The R6a drift guard asserts every hooks.json script references the gate. |
| D7 | Repo's own `.claude/settings.json` hooks | Out of scope for the product fix; MAY adopt the same gate opportunistically | The shipped plugin is the user-facing surface. The dev repo's hooks polluting Patrick's own dogfooding is real but fixable the same way at any time. |

## Calibration record

- 2026-06-10 — Phase 2: live probe confirmed the CLI accepts an empty
  `--setting-sources=` (exit 0, keyless/subscription) — R3's gate passed.
  D5's "one adapter site" premise corrected on contact with code (see
  revised D5).

- 2026-06-10 — Phase 0 ran via direct venv introspection instead of a
  committed probe script first; `scripts/probe_sdk_subprocess_env.py`
  captures the same checks reproducibly (re-run it when bumping
  claude-agent-sdk).

## Live receipts (Phase 3)

- _pending_
