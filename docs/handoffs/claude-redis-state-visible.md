# Agent work handoff

## Goal

Rework PR #2446 to the chair's corrected goal (redis-config-truth D5,
assumption review 2026-09-06): Redis stays bundled and zero-config; the
backend STATE is visible; **a first-run notice lets users choose**; the
choice is a **persisted preference the resolver honors** (`auto|file|redis`);
Redis's role is stated in the chair's words ("enhanced memory features
using Redis's open-source options").

## Acceptance criteria

- `~/.attune/config.json` (or `$ATTUNE_HOME/config.json`) `memory.backend`
  ∈ {auto, file, redis}; `ATTUNE_MEMORY_BACKEND` overrides per process.
- `resolve_backend()`: `file` never probes the upgrade; `redis` prefers it
  and degrades loudly; `auto` unchanged. `backend_status()` carries
  `preference`; a chosen `file` tier never reports a dark upgrade.
- Surfaces: SessionStart hook notice (consent-notice pattern: once, anti-nag,
  "ACTION FOR CLAUDE: ask once, then `attune memory use`"); one-time
  terminal notice on the first interactive `attune` run (informs, never
  blocks); interactive prompt in `attune setup`; `attune memory use
  <auto|file|redis>`; `attune memory status` shows the preference.
- Changed code ≥ 90%; whole tree green; D5 rewritten in the chair's words;
  producer_baseline regenerated for the new hook (coordination: #2444 embeds
  the baseline — whichever of #2444/#2446 lands second regenerates).

## Current state

- Branch `claude/redis-state-visible` (PR #2446). Landed earlier: `attune
  memory status`, doctor line, pyproject comment, D5 v1, tests (66042b2e8).
- This WIP commit: `src/attune/memory/preference.py` (new), resolver +
  `backend_status` honoring the preference, `cmd_memory_use`,
  `first_run_memory_notice` + `main()` call, `_memory_backend_setup_prompt`,
  `memory use` parser/dispatch. All import cleanly. **Not yet:** the hook
  (`plugin/hooks/memory_backend_notice.py` + `hooks.json` registration),
  tests for all of the above, baseline regen, D5 rewrite, README/CHANGELOG,
  suite runs.

## Verification

| Claim | Probe | Result |
| --- | --- | --- |
| Edited modules import | `python -c "import …"` under the worktree src | ok |
| Everything else | not yet run | pending |

## Next action

Write the hook + registration, the tests (preference, resolver, CLI use/status,
setup prompt, first-run notice, hook), regenerate `producer_baseline.json`,
rewrite D5 in the chair's words, README + CHANGELOG, run gates + whole tree,
push, update the #2446 body. Chair reads D5, then merge word. Not armed.
