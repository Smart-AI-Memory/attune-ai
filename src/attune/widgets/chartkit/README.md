# chartkit — sealed chart kernel

Declarative JSON spec in, SVG out. The model never writes renderer code;
it writes specs and spec patches (JSON Merge Patch, RFC 7386).

## The seal (enforced by CI, not convention)

- **No outward imports.** Kernel source imports nothing outside `src/`
  — no `attune` modules, no npm runtime deps, no `../` escapes. Every
  import starts with `./`.
- **No inward imports.** Nothing in attune imports kernel internals.
  The only sanctioned consumer is the injection loader, which reads the
  built artifact `dist/kernel.min.js` as bytes.
- **Size ceiling.** `dist/kernel.min.js` ≤ 20,480 bytes, enforced by
  `scripts/check_widget_kernel_boundaries.py` in CI. Chart types earn their
  way in under the ceiling; the ceiling does not move.

Extraction to a standalone package must always be a copy, not surgery.
If you are adding an import across this boundary, stop — that is the
thing this directory exists to prevent.

## Develop

```bash
npm install   # once; esbuild only
npm run build # -> dist/kernel.min.js (banner carries the version)
npm test      # node --test
```

Spec schema: `spec.schema.json` (lands in T2). Renderers: T3/T4.
Patch path: T5. MCP tool + persistence: T6. Component presets: T7.
See `docs/chartkit.md` and the spec plan `chart-widget-kernel`.
