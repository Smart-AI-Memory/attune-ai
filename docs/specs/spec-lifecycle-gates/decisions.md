# Spec-Lifecycle Gates — Decisions

**Status:** shipped (2026-07-19; header added 2026-07-21 status-truth) —
gates executed (chair go, tasks.md); the triage consumption surface is
homed in `roundtable-triage`, ordered after the P3 skeptic (#1559).

## 2026-07-19 — Charter (chair; round-table thread q-spec-gates-001)

The chair convened the table on where to insert intelligent
progress/quality gates into the spec lifecycle, runnable
autonomously or chair-gated. One round; strong convergence; the
deliberation is preserved at
`docs/reports/roundtable/q-spec-gates-001.md` (board items #2–#5
promoted per-item). The chair chartered this spec and queued it as
the next producing-run subject: **claude drafts** (owed per the
rotation ledger), per-spec arming, grounding pack at
`grounding-pack.md` in this directory. Requirements are NOT yet
authored — the producing run writes them; the pack's seed frame
(shared gate protocol, mechanism mapping, blast-radius escalation,
risk-tiered activation) is input, not contract.

## 2026-07-19 — G1: gate verdicts live in a machine ledger, not decisions.md (chair)

Autonomous gate verdicts (PASS / REVISE / CHAIR_REQUIRED / BLOCKED
+ evidence) persist to a machine ledger (working name
`~/.attune/ops/gates/verdicts.jsonl`), NOT to any decisions.md.
Verdicts are high-volume and re-derivable; decisions.md remains the
human-judgment record everywhere in this repo. Chair rulings may
CITE verdict ids — the same ledger-to-ruling relationship the
pipeline-learner decisions ledger has to its spec. (Resolves
round-table follow-up (a), claude seat.)

## 2026-07-19 — G2: flaky live-fire failures are chair-overridable as explicit waivers (chair)

When a live-fire or metric receipt fails on a transient/flaky
environment result, the chair may override directly in the owning
spec's decisions.md as an EXPLICIT WAIVER carrying the retry
evidence — matching the existing chair-waiver pattern (lesson-lane
waivers; usage-signals US-5). A spec revision is required only when
the receipt TYPE was wrong for the claim, not when the environment
flaked. Waivers are per-item and never self-granted by any
autonomous component. (Resolves follow-up (b), antigravity seat.)

## 2026-07-19 — G3: risk-profile-dynamic gate policy over a small mandatory baseline (chair)

Gate activation is selected from the work's risk profile, not fixed
per lifecycle stage — with a small MANDATORY baseline that always
runs: the fully-mechanical gates (symbol-reality resolution,
falsifiability lint on acceptance claims). The full ladder
activates by blast radius (public API, shared schema, security
primitives, migrations → always chair). Sub-spec-tier work (the
xml-enhanced-prompts "Do NOT use" list) sees only the baseline —
the ceremony-inflation guard all three seats demanded. (Resolves
follow-up (c), codex seat.)

## 2026-07-19 — Requirements authored by producing run; ruled per item (chair: "as recommended")

Slot history: `20260719-1` failed honestly (LINT_DIRTY — uncited
codex critique; fixed by the CITATION_EXAMPLE worked-example brief,
PR #1478); `20260719-2` failed pre-invocation (INPUT_INVALID —
moderator-side stale pack path; zero spend); `20260719-3` produced
(drafter: antigravity per rotation; 4 invocations; 9 items; 7
staged + 2 deferred over the TR-6 cap; dissent empty-attested).

Rulings: RR-1..RR-6, RR-8, RR-9 APPROVED (RR-8/RR-9 restaged from
deferred_over_cap per the TR-6 recourse); RR-1/RR-3/RR-4/RR-5/RR-6
carry in-place chair edits — every specific module path the drafter
cited was verified MISSING against the tree (text-only seat
confabulation), corrected and marked `[chair edit]`, and the
verdict-ledger destination corrected to G1's machine ledger. RR-7
DECLINED as written: its "measured ~3.2 rulings/week" baseline was
invented; re-admit once the chair-interaction count is actually
measured. The confabulation episode is itself the live evidence for
this spec's symbol-reality gate — recorded here so the design phase
treats seat-cited paths as claims to verify, never facts.

Compiled deterministically (`compiler.compile_requirements`,
approved items only, declined RR-7 in the header) into
`requirements.md`; thread `producing-spec-lifecycle-gates-20260719-3`
promoted per-item.

## 2026-07-19 — Design chair-approved as written; G4/G5 ruled (chair)

The chair approved `design.md` as written, adopting the moderator's
recommendations on both open questions:

**G4 — RR-7 re-admitted amended, effective now.** The declined
batching requirement returns with the MEASURED baseline (~26.5
decisions.md commits/week; 159 commits / 6 weeks on main — an
upper-bound proxy, re-measured at implementation) replacing the
drafter's invented figure. Threshold: gate-generated
`CHAIR_REQUIRED` volume > 20% of baseline → weekly batch summary;
security-surface and `BLOCKED` escalations never batch.
requirements.md amended in place.

**G5 — Block semantics at /spec boundaries.** Hard-block on
`BLOCKED` (the skill cannot proceed); soft-block on
`CHAIR_REQUIRED` (proceed only with the receipt rendered and an
explicit chair acknowledgment recorded).

Next: Phase 3 (tasks.md decomposition) then implementation, gated
on #1475's merge for the corpus-readiness seam. Sequencing per
design.md's dependency section.

## 2026-07-19 — Implementation executed (T1–T7); closure receipts (chair go)

All seven tasks landed on `feat/spec-lifecycle-gates-v1` in one PR.

**Deviation recorded:** the design's `src/attune/gates/` destination
was already taken by the collaboration-gates package (spend gate) —
a collision the design's seam probes missed because they verified
sources, not the destination namespace. Resolved as the
`attune.gates.lifecycle` subpackage; the parent's dependency-light
`__init__` is untouched. (Filed as evidence that the symbol-reality
discipline must also cover DESTINATION paths in future designs.)

**Receipts:**
- Suite: 85 gates tests serial (protocol closure, ledger isolation
  drift guard, activation surface-map cases, waiver expiry,
  full-seam event→ledger→ruling linkage); 35 producing serial (the
  post-compile gate degrades a confabulated final non-terminally,
  LINT_DIRTY-coded, candidates still staged); 137 curator (the
  spec_drift SourceReader surfaces stale / approved-not-shipped
  buckets; registered in `core._SOURCE_MODULES`).
- Behavioral: the slot-3 confabulated draft is a permanent
  regression fixture — symbol-reality yields BLOCKED with all seven
  missing paths named.
- Live-fire: `attune gates check requirements --spec
  run-record-corpus` → PASS/exit 0 after the resolver learned
  spec-relative, repo-idiomatic (`src/attune` prefix), and
  `~`-runtime path classes (three false-positive classes found and
  fixed BY the live fire); the dogfood run `attune gates check
  tasks --spec spec-lifecycle-gates` → PASS/exit 0 — the gates
  gate their own spec.
- G5 semantics verified: BLOCKED → exit 2 (hard), CHAIR_REQUIRED →
  exit 1 (soft), receipts always ledgered, spec tree never mutated.

**Trigger wiring:** `/spec` skill Stage 2 + Stage 4 boundary gates
(G5 binding; `.agents` mirror re-projected via
`sync_agents_skills.py`); producing runs gate the compiled
requirements post-compile (closed taxonomy honored — gate findings
ride LINT_DIRTY, never a new code).

**G4 note:** the batching threshold's baseline re-measure hook
lives with the ledger config; activation exposes
`BATCH_THRESHOLD_FRACTION = 0.20`. Batch-mode surfacing itself is
deferred to first real CHAIR_REQUIRED volume (nothing to batch on
day one — honest sequencing, not scope cut).

## 2026-07-20 — UI surface phase: the Specs page Stage column (chair-ruled)

Chair asked for the Phases column to become tracked, managed phase
state; pushback accepted (option 1): NO separate tracking store —
stage is DERIVED at render time from the phase files' own status
lines (`derive_stage`, `attune.ops.spec_lifecycle`), the same
single-source discipline the status-line gate enforces. The column
shows pipeline position (requirements → design → tasks → executing
→ shipped) + a next-transition hint; the chip reuses the existing
chair-gated status editor targeting the next-action phase (RR-2:
advancement stays a chair action). A gate-verdict badge reads the
RR-1 machine ledger (`~/.attune/ops/gates/verdicts.jsonl`,
`read_gate_verdicts`) and degrades to nothing until gates emit —
this column is the spec's render surface from day one. Old
per-phase pills live on in the chip tooltip. Receipts: 139
lifecycle/routes/rewrite tests serial-green incl. 8 new
derive_stage + 3 ledger-reader tests; live render verified against
a worktree-code server (31 specs, honest stages, editable chips).

## 2026-07-21 — P2 gate-triage inbox ruled (thread q-roundtable-extensions-001; chair: Patrick)

The round table adopted (modified) the gate-triage inbox as the
consumption surface for this spec's RR-1 ledger, to be built AFTER
the P3 skeptic (order ruled on the moderator's fact-check:
`verdicts.jsonl` not yet emitting). V1 shape: a READ-ONLY routine
that groups unresolved CHAIR_REQUIRED receipts by spec+gate,
convenes ONE D3-capped mini-table only past a threshold (N≥3
pending OR oldest >48h), emits one disposition per shortfall from a
closed enum, appends a single chair digest, and marks receipts
triaged (dedup mandatory — never re-deliberate the same shortfall).
Never alters gate state; RR-4 risk tiers govern eligibility from
day one. P3 skeptic dissents route into this digest (one chair
inbox). Failure mode on record: inbox ceremony — a meeting queue
noisier than the raw ledger.

## 2026-08-02 — Feature name RATIFIED: "Spec Ladders" (chair)

The chair ratified **"Spec Ladders"** as the public name for the
goal-driven spec-development surface (`/spec` + the spec engine):
state a goal, be interviewed into requirements and design, then
climb a **gated task ladder** — every rung behind an explicit go,
every quality gate scored, every ruling recorded. "Goal-driven"
is the describing adjective, mirroring outcome-first-fix D9's
artifact-over-process pattern (Fix Receipts). Homed here because
the spec engine has no owning spec directory and this spec governs
the ladder's gate machinery; "gated ladder" was already internal
vocabulary (agent-work-report tasks.md).

Candidates considered: Living Specs (vague), Governed Specs
(bureaucratic), Guided Specs (undersells post-intake). Scope:
prose surfaces only (READMEs, spec-engine feature master + full
projection, spec skill description); slugs, CLI, and code
identifiers unchanged. Family framing with Fix Receipts: "State
an outcome, get a receipt. State a goal, climb a ladder."
