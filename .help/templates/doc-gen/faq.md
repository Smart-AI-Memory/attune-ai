---
type: faq
name: doc-gen-faq
feature: doc-gen
depth: faq
generated_at: 2026-07-14T15:58:51.277022+00:00
source_hash: bcc987b14e370273da9042e975c82dcf5af466e245d407e9ce45d5250d354384
status: generated
---

# Doc Gen FAQ

## Does doc-gen write documentation files for me?

No. Its subagents are read-only; the generated
documentation comes back in `final_output` for you to review and
place.

## What's the difference between doc-gen, doc-audit, and doc-orchestrator?

Doc-gen creates new docs; doc-audit finds stale or missing
docs; doc-orchestrator runs the full maintenance pipeline. The
`/doc-gen` skill routes among them.

## How do I run doc-gen reliably from code?

Use the CLI (`attune workflow run doc-gen --path <p>`) or
Python (`DocumentGenerationWorkflow().execute(path=<p>)`) — both
pass the `path` the workflow expects.

## Which calls are async?

`execute` is a coroutine — `await` it or use
`asyncio.run`.

## How do I keep a run cheap?

Narrow the `path` and use a shallower `depth` (`quick`
uses the smallest agent-turn budget).
