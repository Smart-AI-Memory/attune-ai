---
type: note
name: chart-widgets-note
feature: chart-widgets
depth: note
generated_at: 2026-08-06T09:22:53.642618+00:00
source_hash: 71c54fb463f2d49528c971020259edcdfb7d6586f3b95cc9affc5243c6c4e0bb
status: generated
---

# Declarative chart widgets — a ~100-token JSON spec in, sealed-kernel SVG out

## Overview

Chart widgets (the `chart_render_widget` MCP tool) let an agent show
quantitative shape — a trend, a distribution, a comparison — as inline
SVG instead of prose or a markdown table. The split that makes this
cheap: the model authors a small declarative JSON spec (measured:
260–395 bytes for the tutorial's nine-type examples, roughly 65–100
tokens), and a sealed ~10 KB JavaScript kernel shipped inside the
package turns the spec into themable SVG. The model never writes
renderer code.

Updates are cheaper still. The current spec persists per `chart_id`
in session memory, so changing a chart is an RFC 7386 JSON Merge
Patch against the stored spec — a title change measures 42 bytes.
When persistence is unreachable, the tool says so and asks for a full
spec; degradation is legible, never silent.

Nine chart types ship in 11.3.0: `bar` (stacked, grouped, or
horizontal), `line`, `scatter`, `area`, `heatmap`, and — new in
11.3.0 — `donut`, `box`, `waterfall`, and `treemap`. This is the
first *display* member of attune's communication grammar: unlike an
elicitation form it collects no answer — it reports.

## Concepts

### The spec is the artifact

A chart is one JSON object: `{v: 1, type, data, encodings, options}`.
`data` is a list of plain row dicts; `encodings` maps row fields to
channels (`x`, `y`, optional `color`) with a field type
(`quantitative`, `nominal`, `temporal`); `options` carries
presentation (`title`, `legend`, `stacked`, `horizontal`, `total`).
The contract is `src/attune/widgets/chartkit/spec.schema.json` on the
JS side, mirrored by `attune.widgets.chart_spec` on the Python side;
sync tests keep the two aligned.

### Type-specific row shapes

- `box` — each row carries pre-computed numeric `min`, `q1`,
  `median`, `q3`, `max`; the kernel never aggregates raw samples.
- `donut` / `treemap` — `encodings.y` is the positive slice/tile
  value; non-positive rows are dropped, and all-non-positive is an
  error.
- `waterfall` — `encodings.y` is a signed delta; bars run at a
  cumulative offset, colored by sign, and `options.total` appends a
  computed total bar with the given label.
- `heatmap` — `encodings.color` is required; it carries the cell
  value.

### Patch, don't re-send

To update a chart, send the same `chart_id` with a `patch` instead of
a `spec`. Semantics are RFC 7386: objects merge, `null` deletes a
key, arrays and scalars replace wholesale. Specs persist with an
8-hour TTL; a patch against an expired or unknown `chart_id` is
rejected with an instruction to re-send the full spec.

### The seal

The kernel lives in `src/attune/widgets/chartkit/` and is sealed:
kernel source imports nothing outside itself, nothing in attune
imports kernel internals, and the built artifact stays at or under
20,480 bytes — all three enforced in CI by
`scripts/check_widget_kernel_boundaries.py`. Renderers build SVG via
`createElementNS` and `textContent` only, so spec strings can never
execute as markup or script. Colors and text read host CSS variables
(`--chartkit-c1..c6`, `--text-primary`, `--border`) with hex
fallbacks, adapting to light and dark themes automatically.

### Errors are field-level at author time

A display member has no answer to validate, so its rigor lives at
authoring: `validate_chart_spec` reports one field-level problem per
mistake (`encodings.y: Field required`;
`options.total: only valid for type 'waterfall'`), phrased so the
emitting model can fix its own spec and retry. This is the display
analogue of the form substrate's re-ask-only-the-offending-field
rule.

## Notes & tips

- Reuse a stable, meaningful `chart_id` (`coverage-trend`, not
  `chart1`) — it is the handle every later patch needs.
- Arrays replace wholesale under RFC 7386, so a data update re-sends
  the full `data` array. Still far smaller than re-emitting the
  widget.
- For recurring shapes, prefer a named component
  (`expand_component`) over hand-authoring the same spec — expansion
  is server-side and validated.
- The images in the tutorial are static-SVG exports of live renders
  (1.9–2.6 KB each) — the same trick works for READMEs and PyPI
  pages.
