# Round table — spec-lifecycle quality gates (q-spec-gates-001)

**Thread:** `q-spec-gates-001` · **Date:** 2026-07-19 ·
**Roster:** claude, antigravity, codex · **Rounds:** 1 (halted on
convergence, D3) · **Promoted items:** #2 #3 #4 #5 (chair-approved).

## #5 — synthesis (moderator)

SYNTHESIS (moderator, round 1 — halting on convergence, D3):
AGREEMENT (strong, all three seats):
- Gate placement: all seats put gates at the same five lifecycle boundaries (brainstorm->requirements, requirements->design, design->tasks, tasks->execution, execution->verification), plus continuous/drift monitoring (claude #6, codex #5).
- The autonomy split is unanimous and crisp: autonomous gates may BLOCK/REPORT/FLAG with evidence and exact shortfalls, but only the chair may APPROVE scope, irreversible choices, waivers, and promotion. Never-auto-promote generalizes to never-auto-advance-on-judgment.
- Receipt-first verification: all three make "every acceptance claim names its receipt type + a probe that would fail if false" a mechanical lint (claude gate 2, antigravity gate 2, codex gate 4), with mock-vs-real-boundary distinction enforced at execution exit (all three).
- Reality-grounding: all three want spec text validated against the live tree (claude premise-validation + symbol-reality; antigravity symbol-existence scan; codex parallel-mechanism detection).
- The named RISK is the same word in two seats: ceremony inflation (codex, claude "ceremony creep"), decision fatigue (antigravity) — and the mitigation converges on RISK-TIERED ACTIVATION: a small mandatory baseline for all work, the full ladder only for spec-tier/irreversible work.
DISTINCT CONTRIBUTIONS:
- codex: the SHARED GATE PROTOCOL — one machine-readable finding format with four states (PASS / REVISE / CHAIR_REQUIRED / BLOCKED) so every phase shares approval semantics. Strongest single structural idea on the table.
- claude: gates mapped 1:1 onto SHIPPED attune mechanisms (compiler-lint seam, corpus-readiness shape, doc-import-gate port, producing caps, central receipt re-run, curator self-truthing sweep) — the cheapest build path.
- antigravity: blast-radius classification (additive/isolated auto-passes; public API/schema/security always chair) — the cleanest autonomous-vs-chair decision rule.
MODERATOR READ: the three positions compose rather than conflict — codex's protocol as the container, claude's mechanism mapping as the implementation path, antigravity's blast-radius rule as the escalation policy, risk-tiering as the guard against the shared failure mode.
OPEN FOLLOW-UPS FOR THE CHAIR (R9): (a) gate verdicts in decisions.md vs a separate machine ledger [claude]; (b) chair override of flaky live-fire receipt failures directly vs via spec revision [antigravity]; (c) fixed per-stage gate policy vs risk-profile-dynamic with mandatory baseline [codex].

---

*Curated stub (local-first reports, `docs/specs/local-first-reports/`): the sections above are the
chair-promoted content. The full deliberation transcript is
machine-local at `~/.attune/reports/roundtable/q-spec-gates-001.md` and is
not distributed with the repository.*
