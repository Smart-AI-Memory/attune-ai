# Agent Work Report — Tasks

**Status:** active (gated ladder — each task executes only behind
its own chair go; implementation additionally waits for the
post-cut fresh branch per D5)

Receipt discipline: every task names its receipt types at
execution time and the receipts are re-run centrally before the
chair reads the result (contract: receipt-declared delegation).

## Task 1 — Dataset + collectors (the mechanical layer)

**Scope:** `src/attune/reports/{__init__,dataset,collectors}.py`
+ `tests/unit/reports/`.
**Delivers:** typed records, `AgentWorkDataset.facts()`, the four
collectors with named-unavailable degradation.
**Receipts:** suite (new tests, serial tail); behavioral — the
recorded 2026-07-31 fixture reproduces the hand-built report's
numbers exactly (34 PRs, 45 commits, +67,340/−7,225).
**Risks:** `gh` stub-on-PATH pattern is new to the suite (medium);
roundtable stub parsing must tolerate format drift (low — parser
tested against a copied real stub).

## Task 2 — Render + CLI entry

**Scope:** `src/attune/reports/render.py`,
`src/attune/cli_commands/report_commands.py`, CLI registration +
`input_schema`.
**Delivers:** `attune report agents` end to end in tables-only
mode; local-first write; `--stub` flag.
**Receipts:** suite; live-fire — the command runs over the current
day from a terminal and writes `~/.attune/reports/agent-work/`;
behavioral — default run leaves `git status` untouched.
**Risks:** registration trips the count/claim drift-guard cascade
(HIGH known class — run `scripts/project_capabilities.py --write`
+ the root-level guard suites before push, per the #1824 lesson).

## Task 3 — Narrative + verify gate + degradation

**Scope:** `src/attune/reports/{narrative,verify}.py` PLUS the
narrative slot in `render.py` (roundtable amendment: Task 3
necessarily integrates through render — the boundary is an
explicit extension point Task 2 leaves behind, so Tasks 3 and 4
compose without touching each other's sections).
**Delivers:** closed-book CHEAP-tier narrative; the mechanical
gate; keyless, empty-dataset, and gate-fail degradation to
tables-only.
**Receipts:** suite — TWO seeded-fabrication tests (invented
`#9999` dropped; real thread id + wrong disposition dropped) +
keyless exit 0 + empty-dataset no-completion; live-fire — CHEAP
renders over **N ≥ 5 real windows with the narrative DROP RATE
reported** (the drop-rate receipt: a fail-safe gate that drops
most real narratives is a dead feature masked green — measure it
before calling Task 3 done); drift tests — `narrative.py` import
surface AND request-configuration pinned.
**Risks:** number-extraction false positives dropping good
narratives (medium — comma/float-aware tokenizer + derived values
in `facts()` exist for this; the drop-rate receipt is the
detector).

## Task 4 — Copy-ready prompts (US-4)

**Scope:** `render.py` prompt section + validation helper, plus
the briefs SOURCE Task 1 must define (roundtable amendment: Task 4
consumed "standing generator briefs" that no collector produced —
Task 1's dataset gains an open-items field fed by the stub parser
and, when present, `docs/reports/modules-needing-work.md`).
**Delivers:** open items from stubs/briefs rendered as paste-ready
commands — **mechanical templates only, never LLM-generated**
(roundtable amendment closing the provenance gap: a generated
prompt is ungated narrative by another name) — each validated
against the reader's entry point (installed CLI registered-command
check; version-precondition note on mismatch — the pre-11.2.0
`attune fix` trap made this a requirement).
**Receipts:** suite; behavioral — every emitted command in a
sample render passes the validation it claims.
**Risks:** low; smallest task, depends on Tasks 1–2.

## Sequencing

1 → 2 → 3, with 4 after 2 (3 and 4 are independent). Tasks 1+2
deliver a complete, useful, zero-cost product (tables-only);
Task 3 adds the narrative Patrick chose in D1; Task 4 completes
US-4. If evidence at any gate argues for stopping at tables-only,
that is a chair call, not a failure.
