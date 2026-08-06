# Chart Widgets

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

## Design & extension

### Why a sealed kernel

The seal is what keeps both the bytes and the blast radius bounded:
one directory, no imports in either direction, a stated size budget
(20,480 bytes; the 11.3.0 build is ~10.4 KB minified) enforced by
`scripts/check_widget_kernel_boundaries.py` in CI. Types earn their
way in under the ceiling; the ceiling does not move. The 2026-08-06
type-expansion ruling (recorded in the chartkit reference) admitted
donut, box, waterfall, treemap, and the `horizontal` option, and
excluded gauges (infokit's territory), radar, binned histograms
(author bins in the spec), and combo charts (composition, not a
type).

### The display substrate

chartkit is the worked example of the widget-kernel-family pattern:
sealed kernel + declarative spec + RFC 7386 patch, one kernel per
widget kind, one MCP tool each. `formkit` and `infokit` are
specified as the next members. Adding a chart type is a kernel
change gated by the byte ceiling; adding a widget kind is a new
kernel, not a new grammar mechanism.

<!-- attune-generated: source_hash=71c54fb463f2d49528c971020259edcdfb7d6586f3b95cc9affc5243c6c4e0bb feature=chart-widgets kind=architecture generated_at=2026-08-06 -->
