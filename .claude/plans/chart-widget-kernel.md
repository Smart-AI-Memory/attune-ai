# Chart-widget kernel

**Outcome:** Widgets LLMs can create and update efficiently — the model emits a
declarative JSON spec (~50–200 tokens) or a spec patch; a sealed, deterministic
JS kernel renders. Mirrors the ratified master-doc → deterministic-projector
pattern.

**Done when:** Kernel builds to a single sealed JS artifact ≤20KB; renders
bar/line/scatter/area/heatmap from a JSON spec; a spec-patch update re-renders
without the model re-emitting the widget; size-budget + sealed-boundary
(no cross-imports) gates enforced in CI; one surface (elicitation widget)
shipping charts end-to-end.

**Concerns:** correctness, security, performance.

## Decisions

- **D1 — Home:** `src/attune/widgets/chartkit/` (chair-picked at intake over
  top-level `vendor/`). Ships in the wheel automatically. "Sealed" is enforced
  by CI, not directory position: no `attune` imports inside the kernel source,
  no imports of kernel internals from outside — only the injection loader may
  read the built artifact.
- **D2 — Ceiling:** 20KB = minified bytes of the built `kernel.min.js` (the
  thing that inlines into widgets; not gzip). CI fails the build at 20,481 bytes.
- **D3 — Spec format:** declarative JSON with a `v` version field: type, data,
  encodings, options. Updates are JSON Merge Patch (RFC 7386) — `null` deletes.
- **D4 — First surface:** the elicitation/show_widget path via a new MCP tool
  `chart_render_widget` (spec → kernel-injected HTML). attune-gui dashboard is
  phase 2, reusing the same artifact.
- **D5 — Spec persistence:** Redis memory backend, `chart:{chart_id}` → current
  spec (session TTL), so a later turn can patch without re-sending. Legible
  degradation: when Redis is unavailable the tool says so and requires a full
  spec — never a silent fallback.
- **D6 — Toolchain:** esbuild + node:test as dev-deps inside `chartkit/`
  (package.json local to the sealed dir); CI job runs build, tests, size gate,
  boundary gate. Python side stays pytest.
- **D7 — Theming & safety:** kernel colors/text only via host CSS variables
  (light/dark for free). Every spec string becomes an escaped text node — no
  innerHTML from spec data (XSS).

## Tasks

<task id="T1" name="Scaffold sealed chartkit dir + CI gates">
  <objective>Create src/attune/widgets/chartkit/ with local package.json (esbuild, node:test), a stub kernel that builds to dist/kernel.min.js with a versioned build banner, and CI gates: size budget (fail >20480 bytes) and sealed boundary (no attune imports in kernel source; no external imports of kernel internals; loader may read dist artifact only).</objective>
  <files-to-create>
    <file path="src/attune/widgets/chartkit/package.json"></file>
    <file path="src/attune/widgets/chartkit/src/kernel.js"></file>
    <file path="src/attune/widgets/chartkit/README.md"></file>
    <file path="scripts/check_chartkit_boundary.py"></file>
  </files-to-create>
  <files-to-modify>
    <file path=".github/workflows/chartkit.yml"></file>
  </files-to-modify>
  <validation>
    <check>dist/kernel.min.js builds and carries version banner</check>
    <check>size gate fails a deliberately bloated build in CI dry-run</check>
    <check>boundary script fails on a planted cross-import</check>
  </validation>
  <dependencies></dependencies>
</task>

<task id="T2" name="Spec schema v1 (JSON + pydantic mirror)">
  <objective>Define chart spec v1: v, type (bar|line|scatter|area|heatmap), data, encodings, options. JSON Schema as the contract; pydantic model for Python-side validation with actionable error messages the model can self-correct from.</objective>
  <files-to-create>
    <file path="src/attune/widgets/chartkit/spec.schema.json"></file>
    <file path="src/attune/widgets/chart_spec.py"></file>
    <file path="tests/unit/widgets/test_chart_spec.py"></file>
  </files-to-create>
  <validation>
    <check>valid specs for all 5 types pass; malformed specs return field-level errors</check>
  </validation>
  <dependencies><dep>T1</dep></dependencies>
</task>

<task id="T3" name="Kernel core: scales, axes, legend, tooltip + bar/line">
  <objective>SVG-rendering kernel core — linear/band/time scales, axes with sane tick density, legend, tooltip — plus bar and line renderers. Colors and text via host CSS variables only; all spec strings escaped to text nodes.</objective>
  <files-to-modify>
    <file path="src/attune/widgets/chartkit/src/kernel.js"></file>
  </files-to-modify>
  <validation>
    <check>bar and line render from spec fixtures under node:test</check>
    <check>hostile label strings render inert (no script execution path)</check>
    <check>build stays under size gate</check>
  </validation>
  <dependencies><dep>T2</dep></dependencies>
</task>

<task id="T4" name="Scatter, area, heatmap under the ceiling">
  <objective>Add remaining chart types sharing the core scale/axis machinery. If the ceiling is threatened, chart types earn their way in — report bytes-per-type and stop for a chair call rather than raising the ceiling.</objective>
  <files-to-modify>
    <file path="src/attune/widgets/chartkit/src/kernel.js"></file>
  </files-to-modify>
  <validation>
    <check>all 5 types render from fixtures</check>
    <check>kernel.min.js ≤ 20480 bytes</check>
  </validation>
  <dependencies><dep>T3</dep></dependencies>
</task>

<task id="T5" name="Patch-update path (JSON Merge Patch)">
  <objective>applyPatch(spec, patch) in the kernel per RFC 7386, plus stable per-chart container id so a re-render replaces in place. A patch re-renders the chart without the model re-emitting widget code.</objective>
  <files-to-modify>
    <file path="src/attune/widgets/chartkit/src/kernel.js"></file>
  </files-to-modify>
  <validation>
    <check>RFC 7386 semantics: replace, add, null-delete, nested merge</check>
    <check>patch of data-only re-renders axes correctly (rescale)</check>
  </validation>
  <dependencies><dep>T3</dep></dependencies>
</task>

<task id="T6" name="MCP tool chart_render_widget + Redis spec persistence">
  <objective>New MCP tool: takes chart_id + full spec (create) or chart_id + patch (update); validates via chart_spec.py; persists current spec at chart:{chart_id} in the Redis memory backend (session TTL); returns kernel-injected HTML for show_widget. Legible degradation: without Redis, patches are rejected with a clear message requiring a full spec.</objective>
  <files-to-create>
    <file path="src/attune/widgets/chart_widget_tool.py"></file>
    <file path="tests/unit/widgets/test_chart_widget_tool.py"></file>
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/mcp/server.py"></file>
    <file path="src/attune/mcp/tool_schemas.py"></file>
  </files-to-modify>
  <validation>
    <check>create → patch → patch round-trip renders correct final spec</check>
    <check>Redis-down path returns the legible degradation message, not a stack trace</check>
    <check>injected HTML contains kernel banner and no unescaped spec strings</check>
  </validation>
  <dependencies><dep>T2</dep><dep>T5</dep></dependencies>
</task>

<task id="T7" name="Named component layer + docs">
  <objective>Component presets keyed by semantic role (kpi_tile, time_series, comparison_bars) — name + data expands to a full spec server-side (zero kernel bytes). Skill/docs page teaching the model the spec format, patch idiom, and component names.</objective>
  <files-to-create>
    <file path="src/attune/widgets/chart_components.py"></file>
    <file path="tests/unit/widgets/test_chart_components.py"></file>
    <file path="docs/chartkit.md"></file>
  </files-to-create>
  <validation>
    <check>each preset expands to a schema-valid spec</check>
    <check>docs examples validate against spec.schema.json</check>
  </validation>
  <dependencies><dep>T6</dep></dependencies>
</task>

<!-- spec-state: {"schema_version": 1, "completed": ["T1", "T2", "T3", "T4", "T5", "T6", "T7"], "current": null, "auto_run": false, "last_updated": "2026-08-05T07:57:26.252622+00:00"} -->
