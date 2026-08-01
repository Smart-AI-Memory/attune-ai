# Agent Work Report — Design

**Status:** active (2026-07-31 ~20:25 ET, authored on the chair's
"approved - go ahead with design and tasks"; execution stays gated
per tasks.md and D5)
**Slug:** `agent-work-report`

## Shape

One new module, one thin CLI entry, three layers with a one-way
data flow:

```text
collectors (mechanical)  →  AgentWorkDataset  →  render tables
                                   │
                                   ├→ narrative (CHEAP tier,
                                   │   closed-book over dataset)
                                   └→ verify gate (mechanical)
                                        │ pass → narrative section
                                        │ fail → tables-only + notice
```

```text
src/attune/reports/
├── __init__.py        # public: generate_report(window, options)
├── dataset.py         # typed records + AgentWorkDataset + facts()
├── collectors.py      # gh / git / telemetry / roundtable-stub
├── narrative.py       # closed-book prompt + CHEAP-tier call
├── verify.py          # mechanical gate over narrative vs facts
└── render.py          # markdown tables + assembly + local write
src/attune/cli_commands/report_commands.py  # `attune report agents`
```

The narrative layer imports nothing from `collectors` — it can
only see the dataset it is handed. That import boundary IS the
closed-book constraint, and a drift test pins it (no
`import` of collectors/subprocess/requests inside `narrative.py`).

## Dataset (resolves open question 1)

Per-source dataclasses, composed:

- `PRRecord` — number, title, merged_at, type-prefix.
- `CommitStats` — count, files_changed, insertions, deletions.
- `TelemetryRow` — workflow, cost_usd, timestamp (absent file → []).
- `RoundtableThread` — thread id, date, dispositions
  (`label → status`), open decisions (parsed from tracked stubs).
- `AgentWorkDataset` — window + the lists above, plus
  `facts() -> Facts`: the derived flat index the verify gate
  matches against — `pr_numbers: set[int]`,
  `thread_ids: set[str]`, `numbers: set[int]` (every integer the
  dataset can vouch for: counts, line totals, costs rounded),
  `names: set[str]` (agent roster + workflow names).

Per-source dataclasses keep collectors independently testable; the
single `facts()` derivation keeps the verify gate one function
over one structure.

## Collectors

All mechanical, all degrade to a named-unavailable marker (never
an empty section pretending to be a zero day):

- **PRs:** `gh pr list --state merged --search "merged:<window>"
  --json number,title,mergedAt` via fixed-argv subprocess, with
  pagination handled (`--limit` high-watermark asserted in tests).
  Non-zero exit or missing `gh` → section unavailable.
- **Commits:** `git log --since/--until` + `git diff --numstat`
  (NOT `--stat` — roundtable amendment: `--numstat` is the
  machine-readable form) over the window boundary commits.
- **Window semantics (pinned):** boundaries are LOCAL time,
  inclusive on both ends; PR membership by MERGE time; commit
  membership by COMMITTER time; `--since > --until` is a CLI
  error, not an empty report.
- **Telemetry:** read `~/.attune/telemetry/usage.jsonl`, filter to
  window; absent file → empty (telemetry absence is normal, not an
  outage — rendered as "no tracked spend").
- **Roundtable:** parse tracked stubs in
  `docs/reports/roundtable/` — thread id from the header, date,
  disposition tables, open-decision headings. Machine-local
  transcripts are NOT read in v1 (the tracked stub is the curated
  record; the transcript is chair-private context).

## Verify gate (resolves open question 2)

Deterministic extraction over the narrative, matched against
`facts()`:

- `#\d+` tokens → must be in `pr_numbers`.
- `q-[a-z0-9-]+-\d{3}` tokens → must be in `thread_ids`.
- Numeric tokens, tokenized COMMA/SIGN/FLOAT-AWARE (roundtable
  amendment): `+67,340` is ONE token (67340), never `67` + `340`;
  currency (`$0.62`) and percentages (`98.5%`) are their own
  classes matched against `facts()` cost/derived sets — they never
  silently bypass as non-integers. Bare integers ≥ 10
  (word-boundary, excluding version strings and dates by pattern)
  → must be in `numbers`; `facts()` includes defined DERIVED
  values (collection counts, totals) so truthful sums don't
  false-drop.
- **Disposition vocabulary is a FORBIDDEN class** (RATIFIED /
  APPROVED / DECLINED / DEFERRED / OPEN and kin): the narrative
  may not use these words at all — dispositions render only in
  the mechanical tables. This is the cheap patch for the
  motivating incident's exact shape (real thread id + invented
  disposition).
- Roster names (from `names`) are allowed; UNKNOWN capitalized
  agent-like tokens are not blocked in v1 — a documented
  limitation, NOT a verified token class (codex amendment).

Any miss → narrative dropped, tables-only render, visible notice
naming the offending token AND the collector that failed to vouch
(per-fact provenance is retained through `facts()`, not flattened
away). The gate never edits the narrative — drop is the only
action (an edited narrative is a new unverified narrative).

**Recorded v1 limit (D7, honest wording):** the gate checks
protected-token membership, not claim truth — a false relationship
composed entirely of valid tokens passes. The named upgrade path
is codex's typed-claims design (model emits claim objects
referencing dataset record ids → mechanical validation →
deterministic prose render), to be re-ruled when the drop-rate
receipt (Task 3) provides evidence.

## Narrative

- Input: `AgentWorkDataset` serialized to JSON + a fixed
  instruction block ("write the arcs; use only these facts; no
  rounding or derived arithmetic; no disposition vocabulary").
  Dataset TEXT fields (PR titles, stub excerpts) are untrusted
  data — delimited/fenced in the prompt against injection
  (roundtable amendment).
- Call: one completion through the existing model-routing CHEAP
  tier — no hardcoded model id, no tools, no streaming needs.
  Closed-book is asserted at BOTH layers: the import-boundary
  drift test AND a request-configuration test (the built request
  carries no tool definitions, no external context).
- Budget: input is the dataset (~5–10k tokens for a heavy day),
  output capped ~1.5k tokens; cents per render.
- Auth absent (empty key, no subscription) → skip the call
  entirely; render tables-only, exit 0, zero spend.
- **Empty dataset → skip the call the same way** (roundtable
  amendment): a closed-book model on empty input is the
  highest-hallucination case for zero value; US-1's "no activity"
  report renders mechanically, no completion issued.

## CLI

`attune report agents [--since D] [--until D] [--stub] [--no-narrative]`

- Window defaults to the current local day.
- Registered with an `input_schema` (intake-forms Task 1
  convention) — trips the ~7 registration drift guards; budget a
  `python scripts/project_capabilities.py --write` pass.
- Output: stdout + `~/.attune/reports/agent-work/<window>.md`.
  `--stub <PATH>` (takes an explicit path argument — roundtable
  amendment resolving the boolean-vs-path ambiguity) additionally
  writes a curated stub with the local-first footer: path
  validated via the standard helper, atomic write, no silent
  overwrite (`--force` required if the file exists). Never a
  default repo write.

## Testing strategy

- Collectors: real tmp git repos (house style — no mocks for git);
  `gh` faked as a stub executable on PATH returning recorded JSON
  (a real subprocess round trip through the real parse path);
  telemetry from fixture JSONL; roundtable parser against a copy
  of a real stub.
- Verify gate: table-driven token cases + the US-5
  seeded-fabrication test (narrative with an invented `#9999` →
  dropped, notice rendered).
- Degradation: keyless run renders tables-only exit 0; `gh`
  unavailable renders the unavailable marker.
- Reproduction anchor (US-2): a recorded 2026-07-31 fixture
  dataset must render the hand-built report's numbers (34 PRs,
  45 commits, +67,340/−7,225).
- Closed-book drift test: `narrative.py` import surface pinned.

## Explicitly not in this design

- No agentic fetch by the LLM (D1 — permanent).
- No writes to `docs/reports/roundtable/`.
- No scheduler, no dashboard tab, no cross-repo aggregation (v1
  scope; later phases re-enter through the spec).
- No second telemetry/state system — every source already exists.
