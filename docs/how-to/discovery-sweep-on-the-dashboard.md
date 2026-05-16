# Using discovery-sweep on the ops dashboard

The ops dashboard surfaces [`discovery-sweep`](https://github.com/Smart-AI-Memory/attune-ai/tree/main/src/attune/workflows/discovery_sweep) results in three places once you've recorded at least one sweep for a scope: per-bucket chips on the workflows page, live source-by-source progress on the run page, and a scope-keyed drill-in detail page.

This guide assumes the dashboard is running locally — `attune ops` in your project root opens it on `http://127.0.0.1:8765`.

## Enable result persistence

Set `ATTUNE_OPS_SWEEP_RESULTS=1` in the environment that launched the dashboard. The dashboard reads sweep results from `~/.attune/ops/sweep-results/<scope-hash>.json`; without the flag the runner never writes those files, so the chips stay at `0` and the drill-in returns 404.

```bash
ATTUNE_OPS_SWEEP_RESULTS=1 attune ops
```

## Trigger a sweep

Either kick off the run from the dashboard's **Run** button on the `discovery-sweep` row (after picking a scope from the dropdown), or from the CLI:

```bash
attune workflow run discovery-sweep --path src/
```

The CLI path is the same one the dashboard's runner invokes — it streams `ATTUNE_DS` events to stdout that the daemon captures and persists when the run finishes.

## Read the chips

The discovery-sweep row on `/workflows` shows three chips after the description:

| Chip | Color | What it counts |
|------|-------|---------------|
| `queue` | red | Findings the engine routed for immediate review |
| `questions` | amber | Findings that couldn't be auto-routed — needs your call |
| `rejected` | muted | Findings filtered out by deterministic rules |

Each chip links to the detail page filtered to that bucket. Pick a different scope from the dropdown and the chip counts refresh asynchronously — the chips always reflect the most recent sweep recorded for the *currently-picked* scope.

The label next to the chips reads `latest result` when a sweep has been recorded, or `no sweep recorded for this scope yet` when the persisted file is missing.

## Watch live progress

While a sweep is running, navigate to its run page (the dashboard auto-redirects when you click **Run**). The page renders a **Sources** panel above the streaming log with one row per source:

- `⌛ pattern-scan` — pending
- `⏳ bug-predict running…` — in flight
- `✓ doc-audit 3 finding(s)` — completed
- `✗ security-audit BudgetExceededError` — failed (with the exception class)

Status flips arrive as `ATTUNE_DS source_started` / `source_finished` / `source_failed` lines on the existing SSE stream. The DOM order is fixed alphabetically so the layout doesn't reflow as sources transition.

## Drill into findings

Click any chip (or any bucket-link tab on the detail page) to open `/workflows/discovery-sweep/results/<scope-hash>?bucket=<bucket>`. Each finding row shows:

- Severity chip (`critical` / `high` / `medium` / `low` / `info`)
- Source name (`bug-predict`, `security-audit`, etc.)
- Title + description
- File:line link (when present)
- Tags
- Routing metadata: the `reason` + `next_step` for questions, or the `rule` for rejected findings
- Collapsed **Evidence** snippet — the matched code or context

The detail page is read-only; it shows the *current state* of a scope (latest sweep), independent of which specific run produced it.

## Troubleshooting

- **Chips stay at `0`.** Check `ATTUNE_OPS_SWEEP_RESULTS=1` is set in the dashboard's environment, then run a sweep against the picked scope and refresh. Counts read from `~/.attune/ops/sweep-results/<scope-hash>.json`; a missing or empty file renders as zeros.
- **Detail page 404s.** Same root cause — no sweep has been persisted for that scope hash. Trigger a sweep first.
- **Progress panel doesn't appear on the run page.** Only sweeps emit `ATTUNE_DS` events; other workflows' run pages skip the panel entirely. Confirm the run is `discovery-sweep` and that the engine emitted at least one event line in the captured log.

## Related

- [Spec: discovery-sweep-ops-integration](../specs/discovery-sweep-ops-integration/) — design + tasks.
- [Spec: discovery-sweep](../specs/discovery-sweep/) — the underlying workflow.
- `attune workflow run discovery-sweep --help` — CLI flags.
