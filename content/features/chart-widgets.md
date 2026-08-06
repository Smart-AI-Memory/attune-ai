---
feature: chart-widgets
summary: Declarative chart widgets — a ~100-token JSON spec in, sealed-kernel SVG out
tags: [charts, widgets, visualization, communication]
source_globs:
  - src/attune/widgets/**
nav:
  help: chart-widgets
  mkdocs:
    how-to: how-to/chart-widgets
    architecture: architecture/chart-widgets
    reference: reference/chart-widgets
---

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

## Quickstart

Render a bar chart and hand the HTML to the widget surface:

```python
from attune.widgets.chart_widget_tool import render_chart_widget

result = render_chart_widget(
    "prs-weekly",
    spec={
        "v": 1,
        "type": "bar",
        "data": [
            {"week": "W27", "prs": 14},
            {"week": "W28", "prs": 22},
        ],
        "encodings": {
            "x": {"field": "week", "type": "nominal"},
            "y": {"field": "prs", "type": "quantitative"},
        },
        "options": {"title": "PRs merged per week"},
    },
)
result["success"]      # True
result["html"]         # kernel + spec, pass to show_widget
result["persistence"]  # "stored — next update may send a patch"
```

In a Claude Code session with the plugin, you never call this
yourself — ask for a chart and Claude drives the
`chart_render_widget` MCP tool. The hands-on narrative — ask, patch,
tour the types, export SVG — is the "Chart Widgets with Claude"
tutorial in the docs (`docs/tutorials/chart-widgets.md`).

## Tasks

### Update a chart with a merge patch

Reuse the `chart_id`; send only what changed:

```python
result = render_chart_widget(
    "prs-weekly",
    patch={"options": {"title": "Merged PRs, weekly"}},
)
```

### Validate a spec without rendering

```python
from attune.widgets.chart_spec import ChartSpecError, validate_chart_spec

try:
    validate_chart_spec({"v": 1, "type": "bar", "data": []})
except ChartSpecError as exc:
    exc.problems  # ["data: List should have at least 1 item ..."]
```

### Expand a named component

Semantic-role presets expand server-side to full validated specs:

```python
from attune.widgets.chart_components import expand_component

spec = expand_component(
    "time_series",
    {
        "data": [{"date": "2026-08-01", "value": 3}],
        "title": "Daily runs",
    },
)
```

### Apply a merge patch in your own code

```python
from attune.widgets.chart_widget_tool import merge_patch

merged = merge_patch({"a": 1, "b": {"c": 2}}, {"b": {"c": None}, "d": 3})
# {"a": 1, "b": {}, "d": 3}
```

## Reference

### Public API

| Symbol | Purpose |
|--------|---------|
| `attune.widgets.chart_widget_tool.render_chart_widget(chart_id, spec=None, patch=None, backend=None)` | Create or update a chart; returns `{success, html, chart_id, persistence}` or `{success: False, error \| problems}`. |
| `attune.widgets.chart_widget_tool.merge_patch(target, patch)` | RFC 7386 JSON Merge Patch; mirrors the kernel's `applyPatch`. |
| `attune.widgets.chart_spec.validate_chart_spec(payload)` | Validate a raw spec dict into a `ChartSpec`; raises `ChartSpecError` with field-level problems. |
| `attune.widgets.chart_spec.ChartSpec` | The pydantic spec model (`v`, `type`, `data`, `encodings`, `options`). |
| `attune.widgets.chart_spec.ChartSpecError` | Carries `problems` — one message per field-level issue. |
| `attune.widgets.chart_components.expand_component(name, args)` | Expand a named component into a validated `ChartSpec`; `KeyError` lists valid names. |
| `attune.widgets.chart_components.COMPONENTS` | The component registry: `time_series`, `comparison_bars`, `kpi_tile`, `spec_progress`. |

### Chart types and options

| Type | Row shape | Type-specific rules |
|------|-----------|---------------------|
| `bar` | label + value | `options.stacked`, `options.horizontal`; `color` splits series |
| `line` / `scatter` / `area` | x + value | `color` splits series |
| `heatmap` | x + y + cell value | `encodings.color` required |
| `donut` / `treemap` | label + positive value | non-positive rows dropped |
| `box` | label + `min`, `q1`, `median`, `q3`, `max` | stats pre-computed |
| `waterfall` | label + signed delta | `options.total` adds a computed total bar |

`options`: `title` (str), `legend` (bool, default true), `stacked`
(bar only), `horizontal` (bar only), `total` (waterfall only —
enforced). `chart_id` must match `[A-Za-z0-9_-]{1,64}`.

### MCP tool

`chart_render_widget` — `chart_id` + `spec` to create or replace,
`chart_id` + `patch` to update; pass the returned `html` straight to
the widget surface (`mcp__visualize__show_widget`).

## Comparison

A number or two is prose; a handful of labelled rows is a markdown
table; shape across many points — a trend, a distribution, a
magnitude ranking — is a chart. And a chart that implies a decision
is a chart *plus* a decision form: the display member reports the
shape, the interactive member collects the answer. Versus writing
SVG or matplotlib code directly: the spec costs ~100 tokens, cannot
execute anything, and stays patchable for the rest of the session.

## Failure modes

### Patch rejected — persistence unavailable

When no memory backend is reachable the result is `success: False`
with "Chart persistence is unavailable … Re-send the FULL chart spec
for this chart_id instead of a patch." The fix is in the message:
send a full `spec`. Same shape when the stored spec expired (8-hour
TTL) — the error names the `chart_id` and asks for a full spec.

### White page instead of a chart

The returned `html` needs JavaScript — the kernel draws at load
time. A no-JS surface (macOS Quick Look, some markdown previews)
shows a white page; that is expected, not a bug. For static
surfaces, serialize the drawn `svg.outerHTML` from a real browser
and flatten `var(--x, #hex)` to the hex fallbacks.

### Kernel artifact missing

`render_chart_widget` reads the built
`chartkit/dist/kernel.min.js`; a source checkout that never built it
gets "chartkit kernel artifact is missing … Build it with 'npm run
build' in src/attune/widgets/chartkit/". Wheels ship the built
artifact; this only bites source installs.

### Spec invalid

`{success: False, problems: [...]}` — each problem names the exact
field (`encodings.y: Field required`). Fix the named fields and
retry; nothing partial renders.

## FAQ seeds

- **Q:** How much does a chart cost in tokens?
  **A:** The authored spec is the whole cost — the tutorial's
  measured examples run 260–395 bytes (~65–100 tokens) per chart,
  and a patch update can be as small as 42 bytes. The ~10 KB kernel
  ships in the package, not in the conversation.
- **Q:** How do I change a chart I already rendered?
  **A:** Send the same `chart_id` with a `patch` (RFC 7386: objects
  merge, `null` deletes, arrays and scalars replace). The stored
  spec is patched, revalidated, and re-rendered.
- **Q:** Why did my patch come back with an error about re-sending
  the full spec?
  **A:** Persistence was unavailable or the stored spec expired
  (8-hour TTL). Re-send the full `spec` with the same `chart_id`.
- **Q:** Why is my saved chart HTML a white page in Quick Look?
  **A:** The kernel is JavaScript and Quick Look doesn't run it.
  Open the file in a browser, or export a standalone SVG by
  serializing `svg.outerHTML` and flattening the CSS-variable colors
  to their hex fallbacks.
- **Q:** Can a malicious spec inject script into my page?
  **A:** Renderers build SVG via `createElementNS` and `textContent`
  only — spec strings land as text nodes and attribute values, never
  as markup. The spec payload is additionally `<`-escaped when
  embedded.
- **Q:** Does a box chart compute quartiles for me?
  **A:** No — box rows carry pre-computed `min`, `q1`, `median`,
  `q3`, `max`. The kernel never aggregates; summarize your samples
  first.
- **Q:** Do charts work in the dark theme?
  **A:** Yes — colors and text read host CSS variables
  (`--chartkit-c1..c6`, `--text-primary`, `--border`) and follow the
  surrounding theme automatically.

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
