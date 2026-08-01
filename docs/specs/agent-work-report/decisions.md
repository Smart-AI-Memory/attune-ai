# Agent Work Report — Decisions

**Status:** active (decision log; grows as the spec advances)

## D1 — Grounding stance: mechanical + closed-book LLM narrative (CHAIR OVERRULE, 2026-08-01 ~00:20 ET)

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
