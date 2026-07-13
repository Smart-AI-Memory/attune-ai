# Trap battery — phase 1 pilot results (2026-07-13)

**Run:** 3 traps × 2 arms × 5 repeats = 30 headless sessions, all ok
(0 errors). Executed by Patrick from a plain terminal on branch
`feat/trap-battery-pilot`; live terminal transcript is the source of
record for this doc. Total spend ≈ **$5.65** (vs the $30–60
estimate). **PILOT scale — nothing below is quotable externally; the
20+/cell rate run is where numbers earn quotes.**

## Fired rate by class and arm

| Trap class | OFF fired | ON fired | Δp (off − on) |
|---|--:|--:|--:|
| `zsh-eqword` | 2/5 (40%) | 0/5 (0%) | **+40%** |
| `git-commit-verify-landed` | 0/5 (0%) | 0/5 (0%) | +0% |
| `question-shape` | 5/5 (100%) | 4/5 (80%) | +20% |

Output is failure rates and Δp only — no savings claim (insurance
frame, #1291 discipline).

## Discrimination receipts

Gate: a trap earns phase 2 by firing ≥2/5 in the OFF (lesson-absent)
arm.

- **`zsh-eqword` — receipt obtained.** OFF repeats #2 and #3 fired
  with tool-result evidence `zsh:1: == not found` (the exact
  signature verified live before the regex was written). ON arm:
  0/5 — every memory-on session quoted the separator.
- **`question-shape` — receipt obtained, but see verdict.** OFF
  5/5, all with prose either/or evidence (e.g. *"Which scope do you
  want to ship — Minimal or Full?"*). The ON arm ALSO fired 4/5 —
  the surfaced rule barely changes behavior.
- **`git-commit-verify-landed` — no live receipt.** 0/5 OFF. The
  scorer itself is receipt-proven on canned transcripts (unit
  tests), but the live trap never fired: baseline sessions handled
  the hook's visible exit-1, re-staged, retried, and verified. The
  fixture's failure is louder than the lived original (`git commit
  -q` exiting 0 with the commit silently skipped), which a plain
  pre-commit hook cannot reproduce — hooks that exit 0 let the
  commit proceed.

## Class verdicts (phase-2 go/no-go)

- **`zsh-eqword`: GO.** Discriminates at exactly the gate (2/5 OFF)
  with a pilot Δp of +40% and a clean prevention story (ON 0/5).
  Graduates to the 20+/cell rate run.
- **`git-commit-verify-landed`: NO-GO as designed — redesign or
  swap.** The trap tests recovery from a *visible* failure, which
  current baseline behavior already handles. Either find a faithful
  reproduction of the silent-skip (hard: needs the real pre-commit
  framework's stash dance) or swap in `stale-claim` (pre-approved
  candidate, requirements §swap).
- **`question-shape`: SWAP, with a finding worth keeping.** It
  passes the OFF-gate trivially (5/5) but ON≈OFF means the lesson
  is either not being injected in fixture-repo sessions or is
  injected and ignored — the current harness can't distinguish
  these. Swap in `zsh-status-readonly` for phase 2 (pre-approved),
  and carry the harness follow-up below.

## Findings beyond the table

1. **First measured Δp > 0 for the memory suite.** zsh-eqword is
   the first behavioral (not cost) evidence that a surfaced lesson
   prevents a lived failure class. Pilot-labeled, n=5/cell.
2. **Failure has a visible cost signature.** The two OFF-arm
   zsh firings ran ~13s / ~$0.18 vs ~8s / ~$0.15 for clean runs —
   the error-and-recover loop costs ~60% more wall and ~20% more
   spend even on a toy task. This is the insurance premium's
   counterpart measured on the benefit side.
3. **Harness follow-up (phase 2): injection detection.** Record
   per-session whether the recall hooks actually injected content
   (visible in the stream-json system/context events), so
   "lesson ignored" and "lesson never surfaced" stop being
   confounded — question-shape's ON 4/5 is uninterpretable without
   it.
4. **Cost model correction.** ~$0.19/session mean → a 20/cell rate
   run for two classes ≈ 80 sessions ≈ **$15**, well under the
   phase-2 assumptions.

---

## CORRECTION (2026-07-13, same night) — pilot INVALID as an A/B; Δp retracted

The injection-detection diagnostic (7 further sessions + direct hook
execution + telemetry audit) established, in order:

1. **stream-json does not echo hook `additionalContext`** — the
   transcript-marker scan above is structurally blind. Detection was
   rebuilt on the authoritative channel:
   `~/.attune/telemetry/memory_events.jsonl` (every recall fire
   appends a line).
2. **The recall hooks are plugin-level and DO work from a temp dir**
   (direct execution of `jit_recall.py` with the zsh trap payload
   from a scratch dir returned the zsh-eqword rule; with
   `ATTUNE_JIT_RECALL=0` it returned nothing — the kill-switch
   receipt is good).
3. **But the telemetry log shows ZERO recall events from any of the
   37 headless fixture sessions.** Every event in the window belongs
   to interactive sessions or the direct hook tests. The plugin's
   hooks never ran inside `claude -p` sessions in temp dirs — so
   **both arms were effectively OFF for the entire pilot**, and every
   Δp above is sampling noise on identical arms.

**Retractions/re-readings:**

- `zsh-eqword` Δp "+40%" → **retracted**. With both arms unaided,
  the pooled firing rate is 3/14 (~21%); the observed 0/7-vs-3/7
  split has p≈0.19 under a common rate — consistent with chance.
- The trap DESIGNS retain their validated properties: zsh-eqword
  discriminates unaided (~21% firing with no lesson present),
  git-commit-verify-landed does not fire at all (0/14 pooled),
  question-shape fires ~100% unaided.
- `question-shape` gains a STRUCTURAL diagnosis independent of the
  arms problem: its only allowed tool is `Read`, which the JIT
  matcher (`AskUserQuestion|Bash|Edit`) does not cover, and direct
  execution of `lesson_recall.py` on the trap prompt returns nothing
  (below the 8.0 score floor). Even with hooks running, the ON arm
  had zero injection paths. SWAP verdict stands, with the finding
  re-filed to the recall-triggering axis.

**Phase-2 preconditions (blocking):**

1. Make the recall hooks actually run in harness sessions
   (candidate: run fixtures under a trusted/plugin-enabled path;
   discriminator test: one headless session cwd'd in the repo, then
   check the telemetry log for its events).
2. The harness now reads the telemetry log over the run window and
   declares ARM-VALIDATION FAILURE on zero events with an ON arm —
   re-running tonight's pilot under the fixed harness would have
   refused to report Δp.

---

## RESOLUTION (2026-07-13, later) — headless hook mechanism found

A killed probe session (rejected mid-run, but its stream survived on
disk) settled the phase-2 precondition at near-zero cost:

- `claude -p --plugin-dir <repo>/plugin` **force-loads the plugin in
  headless mode** — 10 plugin SessionStart hooks and 2
  UserPromptSubmit hooks demonstrably started/responded from a temp
  dir. (Patrick's repo-cwd probe confirmed the INSTALLED plugin's
  hooks do NOT load in `-p` mode — the flag is required.)
- `--include-hook-events` surfaces every hook as named
  `hook_started`/`hook_response` system events, with output — and
  hook outputs carry the recall banners, so transcript-marker
  detection WORKS under these flags.

The harness now always passes `--include-hook-events` and defaults
`--plugin-dir` to the repo's `plugin/` (pinning the benchmark to the
repo's current hook code). Three receipts stack: hook events
(per-session), telemetry log (run window), and the OFF-arm marker
scan. A valid pilot re-run is unblocked; Δp remains unmeasured until
it happens.

---

## AMENDMENT 2 (2026-07-13) — pilot re-run ALSO refused; receipt hierarchy revised

The re-run (30 sessions, ~$5.80) ran under the fixed harness — and the
harness correctly **refused to report Δp again** (zero recall
telemetry, zero banners). Forensics on the surviving probe stream
revised the picture:

- `--plugin-dir` DOES load the plugin in headless sessions (the
  plugin's welcome banner appears in a hook_response: "attune-ai
  loaded — 18 workflows, 31 MCP tools"). The earlier RESOLUTION
  stands on that point.
- **But 3 of the plugin's SessionStart hooks exit 1 in fixture
  sessions**, and no recall telemetry appears — the recall subsystem
  (hydrate → recall map → injection) is failing OUTSIDE a real repo
  even though the hook scripts run fine when executed directly with
  a full interactive env.
- **Telemetry is fire-only** for jit/lesson recall, so zero events
  alone cannot distinguish "hooks dead" from "hooks alive, nothing
  matched". `session_recall` (logs every session start) is the
  alive-signal: zero session_recall events across 30 sessions is
  what proves the recall path never initialized.

Receipt hierarchy (implemented): per-run **hook_summary** (lifecycle
events — hooks alive?) → **injection banners** (did recall inject?)
→ **telemetry window** (fire log). The harness now persists raw
streams on request (`--save-transcripts DIR`), so the next diagnosis
costs one $0.15 session instead of a $6 re-run. Open question for
phase 2: WHICH plugin SessionStart hooks fail in fixture dirs and
whether recall needs a repo-shaped cwd (hydrate) — answerable from
one saved transcript.

---

## ROOT CAUSE (2026-07-13, final) — surface-once sentinel collapse

The $0.15 probe with saved transcripts closed the case:

- Hooks run fine in fixture sessions (probe: SessionStart ×10,
  PreToolUse ×5, all recall-relevant hooks exit 0) — but jit_recall
  emitted nothing because of its **surface-once sentinel**: headless
  payloads carry no `session_id`, so every headless session shares
  the literal `unknown` sentinel bucket in `~/.attune`. The first
  fire anywhere (here: a direct diagnostic invocation at 03:38Z)
  suppresses the rule for ALL headless sessions for 7 days.
- Even unpolluted, a 30-session pilot would have had exactly ONE
  ON-arm injection total — the A/B was structurally broken from the
  first design, independent of plugin loading.
- **Fix (shipped):** per-run `ATTUNE_AI_SENTINEL_DIR` isolation —
  every session gets a virgin fixture-local sentinel dir, which also
  stops benchmark runs writing sentinels into the real `~/.attune`
  (the spec's isolation requirement, previously violated).
- The underlying PRODUCT bug (headless users get each JIT rule once
  per 7 days machine-wide) is flagged as its own task, out of this
  spec's scope.

Verification path: one $0.15 zsh ON probe should now show `inj j1`
and a fresh telemetry event; then the pilot re-run (~$6) measures a
real Δp for the first time.
