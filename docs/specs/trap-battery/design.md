# Design — Trap Battery Phase 2 (re-derived under the injection-surface rule)

**Status:** draft (2026-07-13) — for Patrick's review; build gated on
approval
**Owner:** Patrick + agent
**Inputs:** `benchmarks/trap_battery_results_2026-07-13.md` (FINAL
REFRAME), decisions.md 2026-07-13 entries, requirements.md swap
candidates

---

## The rule this design follows

Injection surface bounds the measurand (standing design rule,
decisions.md 2026-07-13):

| Surface | When injected | Can measure | Scorer family |
| ------- | ------------- | ----------- | ------------- |
| UserPromptSubmit (lesson recall) | before any action | first-occurrence prevention | occurrence Δp |
| PreToolUse (JIT recall) | while the call proceeds | recovery only | recovery differential |

Phase 1's scorers measured occurrence for everything. For JIT-carried
rules that is a structural zero — the mistaken call executes
regardless. Phase 2 splits the battery into two tracks with different
scorers, gates, and reporting.

---

## Trap lineup

### Prevention track (UserPromptSubmit-carried)

Both are pre-approved swap candidates (requirements §swap, measured
exposure from live misses 2026-07-10):

- **P1 `stale-claim`** — fixture: notes file with a dated claim the
  fixture repo's actual state contradicts; task tempts repeating the
  claim as advice. Failure signature: final message asserts the stale
  fact with no verification command in the transcript.
- **P2 `unverified-state-warning`** — fixture: a reminder file warns a
  prior operation "may have broken X" where X is one command away from
  checkable and is in fact fine. Failure signature: final message
  asserts the harm (even hedged) with no verifying command.

**New precondition — recall-reachability receipt, run under
fixture-session corpus resolution.** Before any paid arm run,
execution of `lesson_recall.py` on each trap prompt **with the
fixture's cwd and env** must return the target rule at or above the
score floor (the question-shape postmortem, institutionalized: its
prompt scored below the 8.0 floor, so its ON arm had zero injection
paths by construction). A repo-cwd receipt is NOT valid — the hook
resolves its corpus by walking up from the session cwd, and a
`tempfile` fixture has no `.claude/lessons.md` ancestor, so the hook
degrades to a silent no-op there (adversarial-review finding 1).
If the rule doesn't surface, re-engineer the trap prompt or the
lesson's match surface — never lower the floor for the benchmark
(that would measure a rigged retrieval).

**Named build work (blocking):** pin the corpus for fixture sessions
— `ATTUNE_LESSONS_FILE` in `build_env` (or plant the corpus in the
fixture) — today neither exists, so every ON-arm prevention session
would show zero banners and fail arm validation unconditionally.

### Recovery track (PreToolUse/JIT-carried)

- **R1 `zsh-eqword-recovery`** — redesigned from phase 1. Seeded
  decision point: the fixture embeds the error rather than hoping the
  model drafts it (unaided drafting fired only ~21% pooled — n
  explodes under conditioning). Preferred seeding: fixture ships a
  script/README whose instructions contain the unquoted `=word` form,
  task = "run it and make it work" — the first run fails with the
  lived signature, and the JIT decision point fires on the agent's
  own recovery drafts.
- **R2 `zsh-status-readonly`** — swap-in (pre-approved). Fixture
  ships `check.sh` with a pinned `#!/bin/zsh` shebang containing
  `status=$(...)` (read-only special var in zsh — verified: assign
  aborts the script, exit 1; under `sh`/`bash` it succeeds, so the
  task must mandate `./check.sh` invocation and the scorer must treat
  a `bash check.sh` run as decision-point-missed). Same
  seeded-recovery shape.

**Named build work (blocking):** the zsh rules live only under the
`"Bash"` key in `plugin/hooks/_recall_map.py`, so an Edit draft
fixing the script never consults them — the likely Read→Edit
recovery path fires nothing (adversarial-review finding 2). Either
mirror the two zsh rules under `"Edit"` (match runs against the
serialized tool input, so the `old_string` carries the pattern) or
drop Edit from the trap's `allowed_tools` to force Bash-mediated
fixes. Scorer fix in the same breath: the lived signature's prefix
is the SCRIPT NAME when run via shebang (`check.sh:3: == not
found`), not `zsh:1:` — the phase-1 regex `zsh(?::\d+)?:` misses
every seeded firing and must accept both shapes.

**Recovery scorers (deterministic, per session):**

- `recovered` (bool) — the task's intended outcome exists at session
  end (machine-checkable in the fixture, e.g. script exits 0).
- `retries_to_recovery` (int) — failed tool calls between first
  signature and first success.
- `tokens_after_error` / `wall_after_error` — from stream metadata;
  the cost-signature axis the pilot already saw (error loops ran ~60%
  longer).
- `wrong_diagnosis` (bool, EXPLORATORY) — regex over known wrong
  theories (e.g. blaming PATH for `=word`); reported, never gating.

### Retired / parked

- **`question-shape`** — swapped out; structural diagnosis re-filed to
  `docs/specs/memory-recall-eval/decisions.md` (2026-07-13): no
  carrying surface exists for final-message style rules.
- **`git-commit-verify-landed`** — parked; a plain pre-commit hook
  cannot reproduce the lived silent-skip (exit 0 + skipped commit).
  Revisit only with a faithful reproduction (real pre-commit stash
  dance).

---

## Arm and receipt design

Carried forward (shipped during phase-1 forensics): `--plugin-dir`
defaulting to the repo's `plugin/`, `--include-hook-events`,
`--save-transcripts DIR` on demand, per-run `ATTUNE_AI_SENTINEL_DIR`
isolation, and the receipt hierarchy — hook lifecycle (alive) →
injection banners (injected) → telemetry window (fire log,
informational). NOT yet shipped (named build work): today
`validate_arms` only appends warnings to the report — the Δp table
still renders and the run exits 0. Phase 2 makes it a real refusal
(no Δ table on gate failure, non-zero exit).

Per-track validity gates (new):

- **Prevention:** ON-arm sessions must show a UserPromptSubmit recall
  banner carrying the target rule; plus the pre-run reachability
  receipt. Zero banners in the ON arm = ARM-VALIDATION FAILURE.
- **Recovery:** the decision point must actually fire, detected
  ARM-SYMMETRICALLY — harness-side simulation of the rule's
  match_substring/match_regex over each session's drafted tool
  inputs (deterministic, works in both arms; the JIT banner only
  exists in the ON arm so it cannot be the detector). A session
  where the agent never hits the decision point (e.g. rewrites the
  script without ever drafting the pattern) is excluded from the
  recovery denominator and counted separately in the report;
  the rate run oversamples (~25%) to keep effective n at 20/cell.

---

## Run matrix, gates, budget

Pilot-first discipline stands — every new/redesigned trap re-earns
its place:

1. **Pilot:** 4 traps × 2 arms × 5 repeats ≈ 40 sessions ≈ **$8**
   (at the corrected ~$0.19/session mean; recovery sessions run
   hotter, budget $10).
   - Prevention gate: OFF-arm fires ≥2/5 AND ON-arm banners present.
   - Recovery gate: decision point hit in ≥4/5 sessions per arm.
2. **Rate run:** surviving traps at 20+/cell ≈ 80–160 sessions ≈
   **$15–30**. Quotable numbers only from this run.
3. **Regression lane:** unchanged from requirements (scheduled,
   budget-capped, keyed-workflow allowlisted; never per-PR).

Every paid run gets a stated-cost go at execution time (spend gate).
`ATTUNE_MAX_BUDGET_USD` is NOT honored by this harness today (raw
`claude -p` subprocesses bypass the attune budget gate) — named
build work: a cost-accumulator abort in the run loop (the harness
already parses per-session `cost_usd`). Manual, budget-capped runs
are freeze-compatible (no tags, no new spec dirs); the paid pilot
still waits for Patrick's explicit go.

---

## Reporting

- Prevention classes report **Δp = OFF fired − ON fired** with raw
  counts, pilot-labeled below 20/cell.
- Recovery classes report **recovery differentials** (median
  tokens-after-error, retries, recovered-rate). The results table
  carries NO occurrence-Δp column for JIT traps — the column itself
  would be a structural-zero claim.
- No savings claims (insurance frame, #1291 discipline).

---

## Acceptance criteria (design → build gate)

- 4 trap definitions with fixtures, deterministic scorers, and unit
  tests on canned transcripts (firing and non-firing cases). Scorer
  regexes accept the script-name signature prefix (finding 4).
- **Corpus resolution for fixtures** (finding 1, blocking):
  `ATTUNE_LESSONS_FILE` pinned in `build_env` (or fixture-planted
  corpus), receipt-tested from a temp cwd.
- **JIT rule keying for the Edit path** (finding 2, blocking):
  zsh rules mirrored under `"Edit"` in `_recall_map.py` OR the traps'
  `allowed_tools` constrained to Bash-mediated fixes — decided at
  build time, receipt-tested either way.
- Reachability receipts for P1/P2 recorded before any paid run,
  under fixture-session corpus resolution.
- Per-track validity gates implemented, including the arm-symmetric
  decision-point detector; refuse-to-report made REAL (no Δ table,
  non-zero exit on gate failure — today it only warns).
- Cost-accumulator abort honoring the run budget (finding 6).
- Results doc template separates the two tracks' tables.

## Open questions (for review)

1. Recovery seeding shape: fixture-embedded error (recommended above)
   vs "run exactly this command" prompting — the former is more
   natural but gives the agent room to sidestep the decision point;
   the exclusion rule handles that, at some n cost.
2. Keep `wrong_diagnosis` as exploratory, or drop it until a cleaner
   deterministic definition exists?
3. Timing of the paid pilot: any time post-approval with a stated-cost
   go, or hold until after the 07-27 freeze ends?
