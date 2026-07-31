# Daily agent work report — 2026-07-31

One-off, hand-assembled from primary sources (`gh pr list`,
`git log`, the tracked roundtable stub). A recurring generator for
this report is a captured spec candidate, not yet built — see
Provenance at the bottom.

## Headline metrics (UTC day)

| Metric | Value |
|---|---|
| PRs merged to `main` | 34 (#1786–#1838, non-contiguous) |
| PRs opened and still in flight at write | 1 (#1839, auto-merge armed) |
| Commits landed on `main` | 45 |
| Diff volume | 396 files, +67,340 / −7,225 lines |
| Feature PRs | 7 (fix surface, intake forms, local-first reports, input schemas) |
| Bug-fix PRs | 4 (receipt honesty ×2, POSIX paths, D7 endpoint guard) |
| Lessons-corpus batches | 10 PRs appended to `.claude/lessons.md` |
| Chair rulings recorded | 2 (workflow-intake-forms approval; US-5 3/5 partial accepted) |

## The day's arcs

- **Outcome-first fix went from executable to honest.** `attune fix
  --run` landed (#1811), then three receipt-honesty holes were closed
  (#1815), untracked-scope attribution was fixed (#1822), and the D7
  correction guarded the ops run-start endpoint instead of redacting a
  shared writer (#1819). Phase 3 receipts + evidence shipped in #1818.
- **Intake forms became the front door.** The `/fix` guided intake
  (#1824) and `/spec` intake (#1826) shipped; all 21 registered
  workflows declared `input_schema` with named-field CLI errors
  (#1831); the workflow-intake-forms spec went draft → approved →
  design/tasks in one evening (#1828–#1830, amended #1832).
- **Reports went local-first.** Phase 1 (#1823): roundtable
  transcripts live machine-local under `~/.attune/reports/roundtable/`;
  the repo keeps curated stubs.
- **The receipt story went public.** Blog post live at
  smartaimemory.com/blog/the-receipt-beats-the-promise (#1825), with
  tutorial + shooting script.
- **Usage signals closed a leg.** AFTER-snapshot 3/5 committed
  (#1820); the chair ruled the partial satisfies US-5 for 11.0.0
  (#1836) — 11.1.0's window stays open through Sun 08-02 08:00 ET.
- **The evening dogfood loop ate its own output.** Three live `/fix`
  rounds produced three shipped improvements the same night:
  clean-tree fallback candidates + folder drill-down + probe-path
  warning (#1837), a probe-ranking fix excluding production modules
  with test-shaped names (#1839), and two lessons batches from the
  misses (#1835, #1838).

## Roundtable activity this period

The `q-outcome-first-attune-ux-001` roundtable (chaired 07-30) had its
curated report committed this period (#1821) and drove the day's
largest arc.

**What it ruled (pro — adopted and built the same day):**

- A thin outcome facade over existing interfaces — `attune fix
  "<request>"` — with no parallel planner, registry, executor, or
  second source of truth. Shipped as Phases 1–3.
- Contract (goal / done conditions / constraints / probes) separated
  from receipt (changes / probe provenance / results / uncertainty /
  safest next action). A successful workflow exit is never proof.
- Abstention over false confident routing. Now enforced by tests and
  visible in the live CLI (`Fix never guesses a route`).

**What it cautioned (con — constraints that held):**

- Do not begin with natural-language intent inference; do not expose
  Build/Ship as implemented concepts.
- `--explain` must project existing execution data, never create a
  second state or telemetry system.
- Keep expert surfaces (`attune workflow run`) intact.

**Still open from that roundtable (chair decision):**

- Choose the canonical repeatable Fix scenario for the live-boundary
  proof — important enough to exercise code + tests + evidence, narrow
  enough for repeated evaluation.

## Opportunities to improve Attune-AI — copy-ready

Each item below ends with a prompt you can paste into a terminal
running Claude Code (or the `attune` CLI directly).

> **Before the 11.2.0 cut (Sat 08-01 ~09:00 ET):** the `attune fix`
> surface is NOT in the installed 11.1.0 — a bare `attune fix …`
> fails with `invalid choice: 'fix'` (verified live 07-31 ~23:50).
> Until then, run fix commands repo-local:
> `cd ~/attune-ai && PYTHONPATH=~/attune-ai/src python3 -m
> attune.cli_minimal fix …` — after the cut, plain `attune fix`
> works from any install.

**1. Settle the canonical Fix scenario** (the open roundtable chair
decision) by exercising the pricing fixture end-to-end and judging it:

```bash
attune fix "make the boundary order price as bulk" --workflow fix --probe "pytest tests/fixtures/outcome_first_fix/pricing_suite.py" --scope tests/fixtures/outcome_first_fix/pricing.py --run
```

**2. Author the shared form theme** (workflow-intake-forms Task 3,
chair-authorizable now, independent of Phase 2):

```text
/spec execute workflow-intake-forms Task 3 — the shared form theme (attune/elicitation/theme.py, inline projection, 4KB budget test)
```

**3. Spec the recurring daily report generator** (this report,
automated — captured candidate from tonight):

```text
/spec daily agent-work report generator — PR metrics, roundtable actions, copy-ready improvement prompts; local-first output with curated repo stubs
```

**4. Pick the next coverage lane** (49 modules below 85% per the
standing generator):

```bash
python scripts/modules_needing_work.py --briefs 3
```

**5. Re-check the marketplace listing** (attune-ai absent from the
community catalog 25 days after submission; attune-lite is listed):

```text
Check the status of the attune-ai submission to the Anthropic community plugin directory and prepare a resubmission at 11.2.0 if it was dropped
```

## Provenance

Sources: `gh pr list --state merged --search "merged:2026-07-31"`;
`git log origin/main --since 2026-07-31T00:00:00Z`;
`docs/reports/roundtable/q-outcome-first-attune-ux-001.md` (curated
stub; full transcript is machine-local per local-first reports).
Assembled by the evening-run session on 2026-07-31; numbers are
point-in-time as of ~23:30 ET. The recurring generator is NOT built —
its spec candidate is item 3 above.
