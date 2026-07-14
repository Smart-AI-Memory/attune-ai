---
name: doc-gen
source: content/features/doc-gen.md
tags:
- docs
- documentation
- generation
type: faq
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
