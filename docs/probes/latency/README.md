# Browser-host latency receipt — 2026-09-04

The changed attune-forms and attune-ai wheels were installed into an isolated
package directory and exercised through the public MCP stdio server and real
rendered browser controls. This is a controlled inline-widget browser host;
it is not the native Codex or Claude chat host. No model calls, network-provider
work, real board writes, or persistent promotions occurred.

## Recorded runs

Order: baseline, batched, batched, baseline. Same seven synthetic candidates,
all declined. Every run produced byte-identical terminal Markdown.

| Run | Condition | Accepted submissions | Initial request → first paint | Median submit → accepted acknowledgment | Sum of acknowledgment waits | Median submit → next paint |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | baseline | 7 | 282.4 ms | 10.4 ms | 80.5 ms | 56.0 ms |
| 2 | batched | 3 | 71.4 ms | 14.4 ms | 47.6 ms | 58.5 ms |
| 3 | batched | 3 | 83.7 ms | 12.4 ms | 35.0 ms | 57.7 ms |
| 4 | baseline | 7 | 90.1 ms | 9.5 ms | 70.1 ms | 56.6 ms |

Batching reduced the number of accepted round trips and cumulative acknowledgment
wait in these four runs. Each batch was slightly slower to acknowledge than
one single ruling. Browser paint after a submission was similar for both paths.
The first run includes process startup effects; do not interpret its initial
paint as a baseline/batch difference. Two repetitions per condition are not a
population estimate or an SLA.

Total elapsed run times are retained in the raw records but must not be used to
claim a human speedup: they include CUA tool scheduling, exploratory inspection,
scrolling and automated control operation. They are not controlled human dwell.
No model-generation latency is present. Native chat-host performance is unmeasured.

## Clock and event definitions

- Browser `PerformanceObserver` first-contentful-paint records when the iframe
  first paints content. Every recorded page reported document visibility as
  visible. A CUA screenshot additionally confirmed the real first form was visible.
  This does not assert that every control fits without scrolling.
- Parent/iframe timestamps use `performance.timeOrigin + performance.now()` (or
  the browser paint entry's start time). This avoids network clock subtraction.
- `accepted_at` is the browser's acknowledgment time after the real MCP collector
  returns. It includes HTTP/stdio transport and successor rendering.
- `workspace_accepted` is emitted separately immediately after canonical successor
  storage. It excludes rejection, replay, and adapter failures. Exact workspace,
  consumed revision and render instance join the records.
- The real log recorded 20 accepted actions and 20 joined instances. Eight setup
  views were rendered without instrumented browser submissions and remain unjoined.

## Evidence

- `browser-receipts.json`: all four complete browser runs, page timings, order,
  choices, and identical terminal receipts.
- `workspace-events.jsonl`: canonical render/accept events from the actual server.
- `wheel-manifest.json`: wheel SHA-256 values, with every packaged Python file
  compared byte-for-byte against the reviewed source before installation.
- Installed modules resolved from `/private/tmp/latency-host-site/attune` and
  `/private/tmp/latency-host-site/attune_forms`, not a source checkout.
- Final source suites: 994 attune-forms tests; 129 focused attune-ai tests.
  Changed executable Python coverage: 57/57 forms, 19/19 ai.
- Independent gpt-5.6-sol review: no blockers; verified canonical ordering,
  instance joins, old-wheel fallback and probe boundaries.

## Reproduction

Build both local wheels without dependency resolution, install them with
`pip install --no-deps --target <isolated-directory>`, and set `PYTHONPATH` to
that directory under an interpreter with the existing dependencies. Run
`browser_host.py`; it prints its ephemeral loopback URL and private receipt
directory. Open that URL visibly. Use Start baseline and decline one candidate
at a time, or Start batched and choose decline for each field then confirm the
batch. The real server rejects other actions and choices for this fixture.
Alternate condition order. Receipt JSONL is appended after each visible/accepted
observation. No global host configuration or package installation is required.
