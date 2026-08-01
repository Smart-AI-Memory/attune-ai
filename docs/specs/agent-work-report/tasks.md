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

**Scope:** `src/attune/reports/{narrative,verify}.py`.
**Delivers:** closed-book CHEAP-tier narrative; the mechanical
gate; keyless and gate-fail degradation to tables-only.
**Receipts:** suite — seeded-fabrication test (invented `#9999`
dropped with notice) + keyless run exit 0; live-fire — one real
CHEAP-tier render over a real window with the narrative surviving
the gate, cost reported from telemetry; drift test — `narrative.py`
import surface pinned (closed-book by construction).
**Risks:** number-extraction false positives dropping good
narratives (medium — the ≥ 10 floor and pattern exclusions exist
for this; tune with table-driven cases before loosening anything).

## Task 4 — Copy-ready prompts (US-4)

**Scope:** `render.py` prompt section + validation helper.
**Delivers:** open items from stubs/briefs rendered as paste-ready
commands, each validated against the reader's entry point
(installed CLI registered-command check; version-precondition note
on mismatch — the pre-11.2.0 `attune fix` trap made this a
requirement).
**Receipts:** suite; behavioral — every emitted command in a
sample render passes the validation it claims.
**Risks:** low; smallest task, depends on Tasks 1–2.

## Sequencing

1 → 2 → 3, with 4 after 2 (3 and 4 are independent). Tasks 1+2
deliver a complete, useful, zero-cost product (tables-only);
Task 3 adds the narrative Patrick chose in D1; Task 4 completes
US-4. If evidence at any gate argues for stopping at tables-only,
that is a chair call, not a failure.
