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
