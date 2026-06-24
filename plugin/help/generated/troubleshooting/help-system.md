---
name: help-system
source: content/features/help-system.md
tags:
- help
- templates
- docs
type: troubleshooting
---

# The progressive-depth help engine that discovers features, generates depth-layered templates, and serves contextual help

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `TypeError: 'list' object is not callable` on `report.stale_features()` | `stale_features` is a **property**, not a method | Drop the `()` — `report.stale_features` | high |
| `populate()` returns `None` | Template ID not found in the generated directory | Confirm the ID and `generated_dir`; generate first | medium |
| Stale content served after source changed | Templates not regenerated | Run `run_maintenance(..., dry_run=False)` | medium |
| Cross-links resolve to the wrong/old target | Stale cross-link cache | `invalidate_cross_links_cache()` and retry | low |
| Progressive depth never advances | Session state keyed to a different topic | Check `help.session` state; `reset_session()` to clear | low |

### Risk areas

- **Properties vs methods.** `StalenessReport` and `MaintenanceResult`
  expose counts as properties — calling them raises `TypeError`.
- **`populate` can return `None`.** It is `PopulatedTemplate | None` —
  guard the result before using it.
- **Scope confusion.** The engine is `src/attune/help/`; the doc
  *authoring* tooling and the ops help *tab* are separate surfaces.

### Diagnosis order

1. Confirm the manifest loads: `load_manifest(".help")`.
2. Confirm the template exists: `populate("<id>")` is not `None`.
3. Rule out staleness: `check_staleness(...).stale_features`.
4. For cross-link issues: `invalidate_cross_links_cache()`.
5. For progressive depth: inspect `help.session` state.
