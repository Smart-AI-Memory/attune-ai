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
| D8 | The Bash security guard inside SDK subprocesses | **Re-inject programmatically** via `ClaudeAgentOptions.hooks` (an in-process `HookMatcher(matcher="Bash")` PreToolUse callback inside `sdk_isolation_kwargs()`), reusing the hook script's own `validate_bash_command` and denying with a reason | Ratified 2026-06-10 after pushback on D1's tradeoff: isolation strips ALL filesystem hooks, so ungating the script (selective D1) would be symbolic — the guard must travel WITH the adapter. D1 stays gate-everything; protection becomes something the workflow carries, not something the environment provides. Bash/eval-exec scope only; extend if workflows gain broader write surfaces. |

## Calibration record

- 2026-06-10 — Phase 4 added on Patrick's review: "are we going to have
  some monster refactor?" — no; the helper + drift-guard architecture
  made the guard re-injection a one-function change with zero edits to
  the 15 workflow files.
- 2026-06-10 — Phase 2: live probe confirmed the CLI accepts an empty
  `--setting-sources=` (exit 0, keyless/subscription) — R3's gate passed.
  D5's "one adapter site" premise corrected on contact with code (see
  revised D5).

- 2026-06-10 — Phase 0 ran via direct venv introspection instead of a
  committed probe script first; `scripts/probe_sdk_subprocess_env.py`
  captures the same checks reproducibly (re-run it when bumping
  claude-agent-sdk).

## Live receipts (Phase 3)

- **2026-06-10 — PASS.** `ANTHROPIC_API_KEY=""` (strict keyless) +
  `attune workflow run bug-predict --path src/attune/gates --depth
  quick` from inside a Claude Code session, on the P2+P4 stack:
  exit 0, 249.5 s, real multi-subagent run via subscription, genuine
  structured findings (risk score 32/100; the envelope-persistence
  TOCTOU race independently re-confirmed the 2026-06-06 API-mode
  finding). **Before the fix this exact invocation died in seconds
  with the opaque `Command failed with exit code 1`** from
  SessionStart-hook stdout poisoning the stream-json channel.
  Residual nit observed: the voice cost line (`$1.8394 | 249.5s`)
  still shows for unmigrated workflows on subscription — resolved
  per-workflow by the wrf T8 migrations (rendered reports already
  suppress it).

## D9 — 2026-07-13 amendment: exempt `sdk-cli` from the entrypoint
## prefix check (headless `claude -p` is not an SDK subprocess)

D3's premise drifted: current Claude Code stamps
`CLAUDE_CODE_ENTRYPOINT=sdk-cli` into EVERY plain headless
`claude -p` session (verified live 2026-07-13 on 2.1.144), so the
bare `sdk-` prefix check silenced every gated attune hook for ALL
headless users — not just SDK subprocesses. Discovered by the
trap-battery benchmark (docs/specs/trap-battery/decisions.md,
"SDK-gate discovery" entry): phase-1 "hooks alive" receipts were
lifecycle-only; gated hooks started and exited 0 with no output.

**Decision:** keep both D3 signals, exempt the single entrypoint
value verified to mean "plain headless CLI":
`ATTUNE_SDK_SUBPROCESS=1` OR (`sdk-` prefix AND != `sdk-cli`).

Alternatives rejected:

- *Drop the prefix check, keep only `ATTUNE_SDK_SUBPROCESS=1`* —
  regresses D3's third-party coverage: the Agent SDK still stamps
  `sdk-py` (re-verified 2026-07-13, claude-agent-sdk 0.2.116 via
  `scripts/probe_sdk_subprocess_env.py`), and those subprocesses
  never touch attune's adapter.
- *Allow-list (`sdk-py`, `sdk-ts` only)* — fails open: a future
  SDK language stamp would un-gate and re-poison the stream-json
  channel. The deny-list fails closed: unknown `sdk-*` values stay
  gated (worst case a silent hook, the soft failure).
- *`CLAUDECODE` nesting depth* — does not discriminate: an SDK
  script run from a terminal is not nested; a plain headless run
  inside a Claude Code session is.

Also codified here: `ATTUNE_SDK_GATE_OVERRIDE=1` force-disables the
gate — benchmark-only escape hatch (shipped for the trap-battery
harness, whose children parse stream-json defensively). Nothing
else should set it.

Receipt (same-day A/B, one `zsh-eqword` trap session per arm,
scrubbed env, worktree plugin force-loaded, per-run sentinel
isolation): pre-fix ON-arm = hook lifecycle present, ZERO
injections, trap fired; post-fix ON-arm = recall injection present
with no override set. Unit contract: sdk-cli → not gated;
sdk-py/sdk-ts/unknown sdk-* → gated; marker beats the exemption
(`tests/unit/plugins/test_sdk_subprocess_gate.py`).

Interaction note: un-gating headless hooks makes the jit_recall
surface-once sentinel collapse (headless payloads carry no
session_id → shared "unknown" bucket, 7-day machine-wide
suppression) USER-VISIBLE for headless sessions. That bug has its
own task; the two fixes compose but this one lands first.
