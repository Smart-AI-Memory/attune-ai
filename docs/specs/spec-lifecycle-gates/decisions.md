# Spec-Lifecycle Gates — Decisions

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
