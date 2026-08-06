---
type: warning
name: chart-widgets-warning
feature: chart-widgets
depth: warning
generated_at: 2026-08-06T09:22:53.642618+00:00
source_hash: 71c54fb463f2d49528c971020259edcdfb7d6586f3b95cc9affc5243c6c4e0bb
status: generated
---

# Declarative chart widgets — a ~100-token JSON spec in, sealed-kernel SVG out

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
