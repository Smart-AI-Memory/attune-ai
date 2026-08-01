# Agent Work Report — Requirements

**Status:** approved (2026-07-31 ~20:18 ET — chair: "approved - go
ahead with design and tasks"). Implementation waits for a fresh
branch after the 11.2.0 cut. (Timestamp correction: first authored
~20:15 ET 07-31, not "00:30 ET 08-01" as the draft said — a
UTC-to-ET conversion error the chair caught live.)
**Slug:** `agent-work-report`
**Provenance:** chair ask 2026-07-31 late evening, verbatim: "create
a report that summarize actions taken by agents or llms during a
selectable time period. The purpose of the report is to let
developers track and manage multiple LLMs or agents using
attune-ai." Framed through the spec intake form (#1826) the same
night; grounding stance settled by explicit chair overrule plus a
three-constraint adoption (see decisions.md D1). The interview was
the conversation.

## Position against the existing stack

This spec is a CONSUMER of
[local-first-reports](../local-first-reports/requirements.md)
(placement: generated reports live machine-local, the repo keeps
curated stubs) and of the existing model-routing tiers (the
narrative layer calls the CHEAP tier, never a hardcoded model id).
It is a SIBLING of the roundtable report corpus
(`docs/reports/roundtable/`): it reads those stubs as a data
source and never writes into that directory. It adds no elicitation
controls, no dashboard surface, and no new telemetry system —
`--explain`-style projection over existing data only.

## Problem

Developers running multiple agents/LLMs through attune-ai have no
single surface answering "who did what, over which window, with
what disposition." The evidence exists — PRs, commits, telemetry
rows, roundtable stubs — but assembling it is a hand job: the
2026-07-31 daily report
(`docs/reports/daily-agent-work-2026-07-31.md`) took a session's
attention to build and is frozen to one day.

## Grounded evidence (why grounding is the core requirement)

The first live API-billed `attune fix --run` (2026-07-31 ~23:50)
was given exactly this report goal with scope
`docs/reports/roundtable` — and satisfied its contract by
FABRICATING a plausible digest: invented per-agent counts, invented
RATIFIED/DEFERRED dispositions, and a provenance pointer to a
machine-local transcript that does not exist. The execution receipt
was truthful about actions (file created, probe passed) and silent
about content truth — receipts prove actions, not content.
Specimen: `~/.attune/scratch/fabricated-digest-specimen-2026-07-31.md`.
Lessons batch: #1841. This spec's architecture exists to make that
failure class impossible by construction, not caught by review.

## Architecture stance (binding, from D1)

Mechanical fetch → closed-book narration → mechanical verify.

1. A mechanical layer queries real sources (`gh`, `git`, telemetry
   JSONL, tracked roundtable stubs) into a typed dataset. No LLM.
2. A narrative layer (CHEAP tier) receives ONLY the dataset —
   closed-book: no tools, no repo access, no fetching — and writes
   the arcs-style summary over it.
3. A mechanical verify gate extracts every number, PR reference,
   and thread name from the narrative and matches it against the
   dataset; any miss drops the narrative and the report renders
   tables-only with a visible notice. The gate is deterministic
   and keyless — never an LLM judging an LLM.

## User stories

**US-1 — Selectable-window report from one command.** As a
developer, I run `attune report agents --since <date> --until
<date>` (window defaults to the current day) and get the report on
stdout plus a machine-local file. Done when: both boundary flags
work, an empty window renders a truthful "no activity in window"
report, and the command is registered with an `input_schema`.

**US-2 — Grounded activity metrics.** The report's metric tables
(PRs merged, commits, diff volume, per-type breakdown, telemetry
cost rows when present) are queried, never generated. Done when:
a run over 2026-07-31 reproduces the hand-built report's numbers
exactly (34 PRs merged, 45 commits, +67,340/−7,225 lines), and a
grounding test walks every rendered figure back to a query.

**US-3 — Roundtable actions in window.** Roundtable threads whose
records fall in the window appear with their actions, dispositions,
and open chair decisions, parsed from the tracked curated stubs.
Done when: a window covering 2026-07-31 lists
`q-outcome-first-attune-ux-001` with its ruling, cautions, and the
open canonical-scenario decision; a window with no roundtable
activity says so — sections are never invented to fill space.

**US-4 — Copy-ready improvement prompts.** Open items found in the
sources (open chair decisions in stubs, standing generator briefs)
render as paste-ready terminal commands. Done when: every emitted
command is validated against the READER's entry point (the
installed CLI's registered commands, not the authoring repo's
source tree — the pre-11.2.0 `attune fix` trap, lessons #1841),
with a version-precondition note when they differ.

**US-5 — Closed-book narrative behind the verify gate.** The
narrative section is produced per the architecture stance. Done
when: TWO seeded-fabrication tests pass — an invented PR number is
dropped, AND a real thread id paired with a wrong disposition is
dropped (the disposition-vocabulary ban, D7); a keyless run (empty
`ANTHROPIC_API_KEY`, no subscription) renders tables-only, exit 0,
zero spend; a passing narrative contains **no unknown protected
tokens and no disposition vocabulary**. (Honest-wording note, D7:
this is deliberately narrower than "names only dataset facts" —
relationship-level fabrication composed from valid tokens remains
possible in v1, is a recorded limit, and the typed-claims design
is the named upgrade path.)

**US-6 — Local-first placement.** The full report writes to
`~/.attune/reports/agent-work/<window>.md`; nothing is written
into the repository unless the developer passes an explicit
`--stub` flag, which emits a curated stub suitable for
`docs/reports/`. Done when: default runs leave `git status`
untouched, and the stub path carries the standard local-first
footer.

## Non-functional requirements

- **Fail-open on source outages:** an unreachable `gh` or absent
  telemetry file marks that section "unavailable" — degraded
  sections are named, never silently omitted, never invented.
- **Cost:** narrative renders route the CHEAP tier; a render's
  spend is on the order of cents and respects the standing budget
  configuration. Mechanical-only renders are free.
- **Windows-safe:** path handling and subprocess calls follow the
  repo's POSIX-normalization conventions; Windows lanes gate the
  merge.
- **Coverage:** ≥80% on changed code; the verify gate and the
  fail-open branches carry dedicated tests.

## Out of scope (v1)

- Scheduling/cron and the ops dashboard surface (chair picked CLI
  for v1; both are natural later phases).
- Cross-repo aggregation.
- Agentic fetch by the narrative LLM — permanently out, not just
  v1-deferred (architecture stance).
- Writing into `docs/reports/roundtable/` (that directory belongs
  to the roundtable corpus).

## Open questions (for design)

- Dataset schema: one typed dict vs per-source dataclasses.
- Verify-gate extraction rules: numbers and `#\d+` refs are easy;
  thread names and person/agent names need a defined token class.
- Whether US-4's prompt validation can reuse
  `VerificationProbe.missing_paths` (#1837) or needs a
  command-registry check.
