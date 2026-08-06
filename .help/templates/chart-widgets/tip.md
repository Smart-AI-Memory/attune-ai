---
type: tip
name: chart-widgets-tip
feature: chart-widgets
depth: tip
generated_at: 2026-08-06T09:22:53.642618+00:00
source_hash: 71c54fb463f2d49528c971020259edcdfb7d6586f3b95cc9affc5243c6c4e0bb
status: generated
---

# Declarative chart widgets — a ~100-token JSON spec in, sealed-kernel SVG out

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
