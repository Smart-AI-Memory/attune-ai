# Spec: SDK Subprocess Isolation — Requirements

**Status:** approved (2026-06-10, "GO") — Phase 0 done
([findings.md](findings.md)); Phase 2 (adapter isolation) implemented
first (it directly unblocks the subscription receipt), Phase 1 next.

---

## Problem

SDK-native workflows (code-review, bug-predict, security-audit,
test-gen, …) spawn a `claude` CLI subprocess in stream-json mode via
`claude_agent_sdk.query()`. That subprocess starts a full Claude Code
session: SessionStart hooks fire, project/user settings load, and
CLAUDE.md is injected. Two failure modes follow:

1. **Subscription users (no `ANTHROPIC_API_KEY`) get a hard failure.**
   SessionStart hook output poisons the stream-json channel — the CLI
   responds with conversational prose ("I see the session
   orientation…") instead of stream-json, the SDK reader raises, and
   the workflow dies with an opaque `Command failed with exit code 1`
   (observed live 2026-06-10; see CLAUDE.md lesson "Subscription
   `claude` CLI is structurally broken for `claude_agent_sdk.query()`").
   The shipped plugin registers 4 SessionStart hooks, so **every
   plugin user on a Claude subscription hits this** — the plugin's
   primary audience cannot run its flagship feature set.
2. **All users pay an avoidable tax.** Stop hooks run at every
   subprocess turn end (`session_stash` can block ~40 s on a cold
   Ollama), and the injected session context (CLAUDE.md, orientation
   output) inflates tokens and startup latency for workflows that
   already carry their own system prompts.

The auth itself is fine: the sibling-subscription-auth spec's Phase 0
proved `claude_agent_sdk.query()` succeeds without an API key inside
Claude Code. The breakage is session-content pollution, not auth.

## Requirements

- **R1 — Hooks are silent in SDK subprocesses.** ALL attune plugin
  hooks (SessionStart ×4, Stop ×2, PreToolUse ×3, PostToolUse ×3)
  exit immediately, with no output, when running inside an
  SDK-spawned subprocess session. (Ratified 2026-06-10: gate
  everything, not a selective subset — see decisions.md D1.)
- **R2 — Dual detection, no false positives in interactive
  sessions.** A hook detects "SDK subprocess" via EITHER signal:
  (a) `CLAUDE_CODE_ENTRYPOINT` starts with `sdk-` (stamped by the
  Agent SDK itself — covers third-party SDK scripts run with the
  plugin installed); (b) `ATTUNE_SDK_SUBPROCESS=1` (explicit marker
  set by attune's adapter — survives SDK renames). Interactive
  sessions (`claude-desktop`, `cli`) must never match.
- **R3 — Adapter excludes filesystem settings.** The SDK adapter
  passes `setting_sources=[]` so user/project/local settings (and
  their hooks + CLAUDE.md injection) never load in workflow
  subprocesses — gated on the Phase-1 live check that the CLI
  accepts an empty `--setting-sources=` value. The hook gate (R1/R2)
  stays regardless, as the fallback for older SDKs and non-adapter
  spawn paths. (Ratified 2026-06-10 — decisions.md D2.)
- **R4 — Subscription end-to-end works.** A subscription-only
  environment (`ANTHROPIC_API_KEY` empty) inside Claude Code can run
  an SDK workflow to a successful `WorkflowResult`. Acceptance is a
  live receipt, not a unit test (the "registered ≠ working" lesson).
- **R5 — Failures stay diagnosable.** The `ATTUNE_SDK_ERROR_PROBE`
  capture path is preserved; if isolation regresses, the run record
  still shows the real subprocess error.
- **R6 — Drift guards.** (a) A test asserts every hook script in
  `plugin/hooks/hooks.json` calls the shared SDK-subprocess gate;
  (b) a test asserts the adapter never sets `options.skills` without
  an explicit `setting_sources` (the SDK silently forces
  `["user","project"]` back on when skills are set — findings.md F4).

## Acceptance criteria

- AC1: With `CLAUDE_CODE_ENTRYPOINT=sdk-py` in the env, every plugin
  hook exits 0 with empty stdout/stderr in <100 ms (unit-testable per
  hook via subprocess).
- AC2: With `ATTUNE_SDK_SUBPROCESS=1`, same as AC1.
- AC3: In a normal interactive env (neither signal), hooks behave
  exactly as today (existing hook tests stay green).
- AC4: The adapter's `ClaudeAgentOptions` carries
  `env={"ATTUNE_SDK_SUBPROCESS": "1", ...}` and (post live check)
  `setting_sources=[]` — asserted by adapter unit tests.
- AC5: Live receipt recorded in decisions.md: one SDK workflow run
  with `ANTHROPIC_API_KEY=""` completing successfully via
  subscription, before/after.

## Out of scope

- Sibling packages' auth routing (attune-author / attune-rag) — owned
  by the `sibling-subscription-auth` spec.
- Plain `claude -p` invocations not going through the Agent SDK.
- The repo's own `.claude/settings.json` hooks (dev-environment
  concern; the same gate helper is available to them, but the product
  surface is the shipped plugin).

## Phasing

- **Phase 0 — SDK introspection.** DONE; [findings.md](findings.md).
- **Phase 1 — Hook gate (plugin).** Shared `is_sdk_subprocess()`
  helper + gate call at the top of all 12 hook scripts + drift guard
  R6a + per-hook AC1–AC3 tests. Ships in a plugin release.
- **Phase 2 — Adapter isolation.** Live-verify empty
  `--setting-sources=` parse; set `env` marker +
  `setting_sources=[]` in `agent_sdk_adapter`; drift guard R6b.
- **Phase 3 — Live receipt.** Subscription-mode run of one SDK
  workflow (bug-predict on a small leaf module) recorded in
  decisions.md; flip spec to complete.
- **Phase 4 — Programmatic guard (D8).** `sdk_isolation_kwargs()`
  carries an in-process PreToolUse `HookMatcher(matcher="Bash")`
  reusing `validate_bash_command` (deny-with-reason) — re-injects the
  protection that settings exclusion removes. No workflow-file edits.
