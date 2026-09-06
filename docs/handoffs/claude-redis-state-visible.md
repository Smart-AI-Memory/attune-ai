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

- Branch `claude/redis-state-visible` (PR #2446). Commits: 66042b2e8 (status
  + doctor line + pyproject comment + D5 v1), 76b64072b (WIP), 6c67d31b6
  (the rework: preference store, resolver, `memory use`, terminal notice,
  setup prompt, SessionStart hook + registration, baseline regen, tests,
  D5 rewritten in the chair's words, README, CHANGELOG).
- Everything in the acceptance list is implemented and unit-tested; the
  whole-tree run is the last receipt before push (see the PR body).
- Coordination: `producer_baseline.json` changed (one hook). #2444 embeds
  the baseline; whichever of #2444 / #2446 lands second regenerates it.

## Verification

| Claim | Probe | Result |
| --- | --- | --- |
| Preference store + resolver honoring it | `tests/unit/memory/test_backend_preference.py` (fake entry points; file never probes the upgrade) | 14 passed; `preference.py` 100% |
| Hook | `tests/unit/hooks/test_memory_backend_notice.py` (consent-notice harness) | 9 passed |
| CLI use / status / terminal notice / setup prompt | `tests/unit/cli/test_memory_backend_choice.py` + memory-command tests | 14 + 6 passed |
| Ratchets + gates + touched suites | `tests/unit/gates tests/unit/quality tests/unit/cli tests/unit/cli_commands tests/unit/hooks tests/unit/memory` | 4045 passed |
| Baseline regen reviewed | `git diff producer_baseline.json` | +1 registration, +1 context_stdout envelope, +1 helper edge, 0 problems |
| Pinned hooks | pre-commit on every changed file | Passed |
| Whole tree | `pytest tests -n auto`, captured (macOS, py3.11, warm caches, integration lane skipped by `--cov`) | 25579 passed, 266 skipped, 3 xfailed |

## Next action

Push; rewrite the #2446 body to the rework; chair reads D5 (lead-authored
spec text, D11 class), then merge word. Not armed. After merge: the
install/config audit chip's findings land as follow-ups under D5.
