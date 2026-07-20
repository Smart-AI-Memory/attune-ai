# Advanced Debugging Plugin — Decisions

## 2026-07-19 — Origin and pre-spec rulings (chair: Patrick)

Born from a live brainstorm the same day the run-record corpus
closed (RC-2 #1483, RC-3 rec-click attribution #1485): the
self-healing loop's "diagnose" stage is the gap this plugin
fills. Chair-ratified leans, folded into the treatment and the
producing run's grounding pack as hard constraints:

- **First target:** attune's own failed runs (dogfood-first).
- **Propose-only v1:** the chair rules on every fix; auto-apply is
  a later rung behind its own gate.
- **On-demand trigger first:** the run-view button; auto-diagnosis
  only as a later opt-in threshold.
- **Self-records stamped:** diagnostic runs carry `attune-heal`,
  enter the corpus, excluded from mining.

Artifacts: `treatment.md` (chair-approved one-pager),
`grounding-pack.md` (producing-run input).

## 2026-07-19 — Requirements chair-ruled per item (thread `producing-advanced-debugging-plugin-001`)

Producing run staged 8 candidates (RR-1..RR-8); the chair approved
**all eight**. RR-7 approved WITH the panel's 2-1 binding
(manual-command-only triage in v1; scheduler deferred). RR-8
approved despite `deferred_over_cap` (TR-6 cap 7) — read-only
curator source, unanimously agreed by seats.

**Run degradations (receipts, per failure-honesty):**

- `SEAT_ABSENT` round 2: claude critic seat failed
  `401 OAuth access token has been revoked` after retry — critique
  round ran on antigravity + codex only. Operational follow-up:
  re-auth the `claude` CLI before the next table run.
- `LINT_DIRTY` round 3: symbol-reality gate blocked one bare
  `producing.py` citation; staged texts carry full paths.

**Dissent register (stands until ruled):**

- Lesson-corpus ownership unresolved — graduated diagnostic
  lessons to `.claude/lessons.md` directly vs. a dedicated
  projected source. Implementation keeps lesson publication behind
  an interface until this is ruled.
- Confidence scale and the hypothesis-vs-fix-eligible threshold
  are configuration decisions; every `DiagnosisRecord` exposes the
  values used rather than hard-coding policy.

Board thread promoted with item ids 6–13; requirements compiled
deterministically by `attune.roundtable.compiler`
(`compile_requirements`, approved-only).
