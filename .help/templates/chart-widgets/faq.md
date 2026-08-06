---
type: faq
name: chart-widgets-faq
feature: chart-widgets
depth: faq
generated_at: 2026-08-06T09:22:53.642618+00:00
source_hash: 71c54fb463f2d49528c971020259edcdfb7d6586f3b95cc9affc5243c6c4e0bb
status: generated
---

# Chart Widgets FAQ

## How much does a chart cost in tokens?

The authored spec is the whole cost — the tutorial's
measured examples run 260–395 bytes (~65–100 tokens) per chart,
and a patch update can be as small as 42 bytes. The ~10 KB kernel
ships in the package, not in the conversation.

## How do I change a chart I already rendered?

Send the same `chart_id` with a `patch` (RFC 7386: objects
merge, `null` deletes, arrays and scalars replace). The stored
spec is patched, revalidated, and re-rendered.

## Why did my patch come back with an error about re-sending the full spec?

Persistence was unavailable or the stored spec expired
(8-hour TTL). Re-send the full `spec` with the same `chart_id`.

## Why is my saved chart HTML a white page in Quick Look?

The kernel is JavaScript and Quick Look doesn't run it.
Open the file in a browser, or export a standalone SVG by
serializing `svg.outerHTML` and flattening the CSS-variable colors
to their hex fallbacks.

## Can a malicious spec inject script into my page?

Renderers build SVG via `createElementNS` and `textContent`
only — spec strings land as text nodes and attribute values, never
as markup. The spec payload is additionally `<`-escaped when
embedded.

## Does a box chart compute quartiles for me?

No — box rows carry pre-computed `min`, `q1`, `median`,
`q3`, `max`. The kernel never aggregates; summarize your samples
first.

## Do charts work in the dark theme?

Yes — colors and text read host CSS variables
(`--chartkit-c1..c6`, `--text-primary`, `--border`) and follow the
surrounding theme automatically.
