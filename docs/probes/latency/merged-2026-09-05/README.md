# Merged-build timing receipt — 2026-09-05

Four complete ABBA runs used a fresh observable in-app browser and fresh public
MCP stdio process. The seven synthetic candidates and all-decline choices are
identical to the original fixture. Baseline submits seven individual declines;
batched submits 3+3+1 rulings. All terminal Markdown is byte-identical.

## Measurements

Milliseconds, rounded to whole milliseconds because browser and server clocks
were not offset-calibrated. Raw precision is retained for audit, not accuracy.

| Run | Condition | Submissions | Request → first visible | Median submit → canonical acceptance | Sum submit → canonical acceptance | Sum submit → acknowledgment | Median submit → next paint |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | baseline | 7 | 523 | 8 | 56 | 77 | 43 |
| 2 | batched | 3 | 87 | 8 | 25 | 36 | 58 |
| 3 | batched | 3 | 90 | 6 | 23 | 33 | 59 |
| 4 | baseline | 7 | 68 | 6 | 42 | 89 | 57 |

Batching reduced cumulative acceptance and acknowledgment waits in this fixture.
Per-submission canonical acceptance was similar. Subsequent paint times were
broadly similar; the warm baseline first paint was faster than either batched
run. The first baseline was the first request to the fresh process, so its
523 ms value includes cold-start effects and cannot establish a batching gain.
Two repetitions per condition are not a population estimate.

These results do not justify renderer optimization yet. The baseline uses the
single-candidate fallback on the same batch-capable rendered workspace: this
tests interaction strategies, not two renderer implementations. Native chat-host
delivery, model generation and human task-completion speed remain unmeasured.
Automation dwell varied, including an accessibility-locator recovery during run
1; do not compare total elapsed task durations as human-speed measurements.

## Provenance and boundaries

- GitHub `gh pr view 2421 --json state,mergeCommit,mergedAt` confirmed MERGED at
  `c2138be2d6be10dfd252495dfae05cc861776375`.
- Measured checkout: `e0d88bc50ab22b5d49dccc28a4fb34ee8242c660`, a descendant.
  `git diff c2138be2d HEAD --stat -- src pyproject.toml uv.lock
  docs/probes/latency/browser_host.py docs/probes/latency/browser_host.html`
  returned empty. The fixture and relevant code match the integration merge.
- Fresh server used this checkout's `src` through explicit `PYTHONPATH`, with
  `/Users/patrickroebuck/attune-ai/.venv/bin/python`. Import probes resolved
  `attune` and its MCP server there; Forms resolved from that venv's installed
  package and `importlib.metadata.version('attune-forms')` returned `0.12.3`.
  This is a merged-source runtime receipt, not an AI published-wheel receipt.
- Initial sandboxed launch failed at localhost bind, before any scenario ran.
  The approved localhost launch created a fresh private telemetry directory.
  No existing Claude/Codex MCP session was restarted or claimed reloaded.
- No model calls, external board writes, or persistent promotions occurred.

## Timing and verification

Visibility is iframe first-contentful-paint, from a browser PerformanceObserver.
All 24 page records report visible document state; a screenshot also confirmed
the first form. Visibility does not imply every control fits without scrolling.

Browser submission and acknowledgment use `performance.timeOrigin +
performance.now()`. Canonical acceptance uses the server's UTC event emitted
after `self._records[workspace_id] = successor` in command_workspace.py.
They share a machine epoch but not a monotonic clock, and no offset calibration
was performed. Every canonical timestamp fell inside its browser submit/ack
interval. Acknowledgment remains a separate same-browser-clock measurement.

Verification parsed the append-only logs and asserted four complete, error-free
runs in ABBA order, submission counts 7/3/3/7, identical terminal Markdown, and
20 canonical acceptances. Every acceptance matches exactly one render event by
workspace ID, consumed revision and instance ID. Each browser submission pairs
uniquely by revision and its submit/ack interval, with one workspace per run.
The browser fixture does not store instance IDs directly; that pairing method
is recorded explicitly rather than presented as a browser-token join.

Files: `browser-receipts.jsonl` retains every browser observation;
`workspace-events.jsonl` retains server events; `joined-receipts.json` contains
the final four runs, paired events and summary; `manifest.json` records source,
runtime, clock limitations and SHA-256 hashes. Original 2026-09-04 receipts are
unchanged.
