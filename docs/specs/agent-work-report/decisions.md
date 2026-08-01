# Agent Work Report — Decisions

**Status:** active (decision log; grows as the spec advances)

## D1 — Grounding stance: mechanical + closed-book LLM narrative (CHAIR OVERRULE, 2026-07-31 ~20:10 ET)

The lead recommended **mechanical-only** for v1: no LLM in the
render path, fabrication impossible by construction, zero cost —
grounded in the same-night live-fire evidence (a fix run given
this report goal fabricated a complete digest; specimen at
`~/.attune/scratch/fabricated-digest-specimen-2026-07-31.md`).

The chair overruled: "I overruled your mechanical only because I
wanted to take advantage of an LLM's ability to better summarize
and fetch. I was thinking it could be done using a cheaper
anthropic model to generate the report."

The lead's counter-case (recorded per the counter-case
discipline): the hand-built report's best section — the five arcs
— was LLM judgment mechanical code cannot write, so the chair's
direction captures real value; the line to hold is *summarize yes,
fetch no*. The chair then adopted all three proposed binding
constraints:

1. **Closed-book narration** — the LLM sees only the queried
   dataset; no tools, no repo access, no fetching.
2. **Mechanical verify gate** — every number/PR-ref/thread-name in
   the narrative must match the dataset or the narrative is
   dropped (tables-only render plus visible notice). Deterministic
   and keyless; never an LLM judging an LLM.
3. **CHEAP-tier routing + keyless degradation** — the narrative
   routes the existing CHEAP tier (no hardcoded model id); absent
   auth degrades to tables-only, exit 0.

Ruling: mechanical fetch → closed-book narration → mechanical
verify is the binding v1 architecture. Agentic fetch by the
narrative LLM is permanently out of scope.

## D2 — v1 surface: CLI command (chair, via intake form)

`attune report agents --since/--until`. Scheduling and the ops
dashboard tab are later phases, not v1.

## D3 — Code area: `src/attune/reports` (new module) (chair, via intake form)

New module rather than growing `cli_commands` or `ops`; the CLI
command is a thin entry over it.

## D4 — Placement inherits local-first reports (premise, not re-asked)

Per local-first-reports (#1823): full reports machine-local under
`~/.attune/reports/agent-work/`; repo gets a curated stub only via
an explicit `--stub` flag.

## D5 — Timing: spec now, implementation after the 11.2.0 cut (premise)

Authored the night before the first-real-user demo (2026-08-01
evening). No implementation before Saturday's cut; fresh branch off
main when picked.

## D6 — Requirements APPROVED; design + tasks authored same evening (chair, 2026-07-31 ~20:18 ET)

Chair: "approved - go ahead with design and tasks." design.md
(three-layer architecture, dataset schema, verify-gate token
classes, testing strategy) and tasks.md (four-task gated ladder,
receipts declared per task) authored on that go. Execution of any
task still requires its own chair gate, and implementation waits
for the post-cut fresh branch (D5). This entry also records the
timestamp correction: the draft's "authored ~00:30 ET 08-01" was a
UTC conversion error — actual authoring ~20:15 ET 07-31, caught by
the chair in-session.

## D7 — Roundtable review: guarantee honestly narrowed, amendment batch adopted (chair, 2026-07-31 ~20:55 ET)

Thread `q-agent-work-report-spec-001` (full transcript
machine-local at `~/.attune/reports/roundtable/`, msgs 2–5
promoted). All three seats independently found the same central
gap: **token-membership verifies existence, not truth** — a
narrative composing valid tokens into a false relationship passes
the designed gate, which conflicts with US-5's original "names
only dataset facts" claim. Seats split on remedy: claude = cheap
patches keeping free prose; codex = return for revision toward
typed validated claims deterministically rendered (while conceding
its own risk: that may reduce CHEAP prose to template value);
antigravity = middle, naming the fork.

**Chair ruling:** (1) v1 guarantee = HONEST WORDING + CHEAP
PATCHES — US-5 reworded to "no unknown protected tokens and no
disposition vocabulary"; relationship-level fabrication is a
RECORDED v1 limit; codex's typed-claims design is the NAMED
UPGRADE PATH, re-ruled when Task 3's drop-rate receipt provides
evidence. (2) The uncontested amendment batch is PROMOTED and now
lives in the spec text: comma/sign/float/currency-aware tokenizer
+ derived values in `facts()`; disposition-vocabulary ban + second
seeded test (real id + wrong disposition); empty-dataset LLM skip;
window semantics pinned (local time, inclusive bounds, merge-time
PRs, committer-time commits, `since > until` errors); `--numstat`
over `--stat`; `--stub <PATH>` with validation/atomic/no-silent-
overwrite; per-fact provenance retained through the gate's
failure notices; closed-book asserted by import test AND
request-configuration test; untrusted dataset text delimited
against injection; Task-3/4 render extension point; Task 4 prompts
are mechanical templates only; Task 3 gains the drop-rate receipt
(N ≥ 5 real windows).
