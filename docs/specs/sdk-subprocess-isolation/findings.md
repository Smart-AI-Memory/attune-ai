# Spec: SDK Subprocess Isolation — Phase 0 Findings

**Probed:** 2026-06-10, claude-agent-sdk **0.1.63** (main venv).
Re-run `scripts/probe_sdk_subprocess_env.py` after any SDK bump.

---

## F1 — `setting_sources` exists; `None` means "CLI default", not "none"

`ClaudeAgentOptions.setting_sources: list[Literal["user","project","local"]] | None`.
The transport (`_internal/transport/subprocess_cli.py`) only emits
`--setting-sources=<csv>` when the value is **not None** — so the
adapter's current state (never sets it) leaves the CLI's own default
in charge, which loads user+project settings (observed live
2026-06-06/10: SessionStart hooks fired, CLAUDE.md injected).
Excluding settings therefore requires passing `[]`, which emits
`--setting-sources=` (empty value). **Open item for Phase 2:** verify
the CLI parses the empty value as "no sources" (one live check).

## F2 — The SDK stamps a detection signal for free

The transport builds the subprocess env as
`{**inherited, "CLAUDE_CODE_ENTRYPOINT": "sdk-py", **options.env, "CLAUDE_AGENT_SDK_VERSION": ...}`
and **filters `CLAUDECODE` out** of the inherited env (upstream #573).
Hook processes inherit the CLI's env, so a hook can detect "I'm in an
SDK-spawned session" via `CLAUDE_CODE_ENTRYPOINT.startswith("sdk-")`.
Interactive sessions carry different values (observed:
`claude-desktop`). Consequences:

- Detection works even for **third-party SDK scripts** that never
  touch attune's adapter — the broadest end-user exposure.
- `CLAUDECODE` is NOT usable as a signal (scrubbed).
- `options.env` merges over inherited → clean home for the explicit
  `ATTUNE_SDK_SUBPROCESS=1` marker (D4/D5).

## F3 — `ClaudeAgentOptions.env: dict[str, str]` is first-class

No need to mutate `os.environ` in the adapter; the marker rides the
options object and only affects the spawned subprocess.

## F4 — TRAP: `options.skills` silently re-enables settings loading

`_apply_skills_defaults()`: when `options.skills` is set and
`setting_sources` is None, the SDK forces
`setting_sources=["user","project"]` "so the CLI discovers installed
skills". The adapter does not use `skills` today, but if a future
change adds it without an explicit `setting_sources`, isolation
silently reverts. → drift guard R6b.

## F5 — Current adapter/runner state

- `agent_sdk_adapter` sets neither `env` nor `setting_sources` on
  `ClaudeAgentOptions` today.
- The dashboard runner's `proc_env` already carries
  `ATTUNE_RUN_META_EMIT`, `ATTUNE_SPEND_GATE_AUTHORIZED`,
  `ATTUNE_SDK_ERROR_PROBE` — precedent for env-marker plumbing, but
  the adapter is the single sufficient site (D5).
- Shipped plugin hook inventory (all gate targets, D1):
  SessionStart ×4 (`welcome`, `help_freshness_check`, `spec_orient`,
  `session_recall`), Stop ×2 (`compact_warning`, `session_stash`),
  PreToolUse ×3 (`jit_recall`, `security_guard` ×2), PostToolUse ×3
  (`format_on_save`, `help_on_error`, `help_post_commit`).
