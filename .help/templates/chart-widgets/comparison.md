---
type: comparison
name: chart-widgets-comparison
feature: chart-widgets
depth: comparison
generated_at: 2026-08-06T09:22:53.642618+00:00
source_hash: 71c54fb463f2d49528c971020259edcdfb7d6586f3b95cc9affc5243c6c4e0bb
status: generated
---

# Declarative chart widgets — a ~100-token JSON spec in, sealed-kernel SVG out

## Comparison

A number or two is prose; a handful of labelled rows is a markdown
table; shape across many points — a trend, a distribution, a
magnitude ranking — is a chart. And a chart that implies a decision
is a chart *plus* a decision form: the display member reports the
shape, the interactive member collects the answer. Versus writing
SVG or matplotlib code directly: the spec costs ~100 tokens, cannot
execute anything, and stays patchable for the rest of the session.
