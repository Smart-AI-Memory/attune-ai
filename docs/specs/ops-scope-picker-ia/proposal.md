# Proposal: Ops dashboard scope-picker — remember last-used scope

**Status:** Draft (2026-05-14)
**Author:** Patrick (with Claude as drafter)
**Scope:** `src/attune/ops/` — workflow scope picker UX

---

## Problem

The scope picker shipped in ops-runner-tier2 Phase 2 (#324) renders a
fresh `Project-wide` default on every page load, for every workflow row
that supports `--path`. This makes the most expensive scope — a full-repo
scan — the unmarked default. A user who runs `security-audit` without
touching the picker is opting into a multi-subagent, multi-dollar run
without the UI signalling that choice.

More fundamentally: the picker is designed as a per-row refinement tool,
but the *user's* cognitive model is "I'm working on X scope, show me each
workflow run for X." The two models are out of phase.

## The IA observation

Rather than mark the broad default (defensive), change what the default
*is* (curative). The picker should remember the scope the user most
recently picked, and pre-select it on every path-supporting row at page
load. The user picks once at the start of a session; every workflow
inherits it. They override per-row when they want a one-off.

This collapses the gap between "what the UI defaults to" and "what the
user is actually working on."

## Design

### Storage model

**Single global `localStorage` key.** Not per-workflow.

- Key: `attune-ops:lastScope`
- Value: a literal string — the picker's `value` attribute (`""` for
  Project-wide, a feature path like `src/attune/security/`, or the
  raw text the user typed when they chose Custom path…).

Rationale: the user's working scope is a session-level fact, not a
per-workflow fact. People run multiple workflows against one scope, then
move to a new scope and run more workflows. Per-workflow storage would
fragment that pattern across 24+ keys and miss the cross-workflow
inheritance that's the point of the change.

### Read on page load

For every `[data-scope-picker]` on the page:

1. Read `localStorage.getItem("attune-ops:lastScope")`.
2. If `null` (first-load fallback) → use the **most-recent-feature-added**
   fallback (see below).
3. If the value matches a picker option (`Project-wide`, any feature
   path, or `__custom__`) → set the picker to that option.
4. If the value is a string that doesn't match any feature option →
   set the picker to `__custom__` and pre-fill the custom input with the
   saved string. This handles the case where the saved scope refers to a
   feature that has since been removed from `features.yaml`, or where the
   user typed a custom path.

### Save on change

For every picker `change` event AND every `[data-scope-custom]` `change`
event:

- If the picker resolves to a feature option → save the option value.
- If the picker is `__custom__` → save the custom input's trimmed value
  (or `null` to leave existing value alone, if the input is empty —
  empty Custom path is functionally Project-wide per existing
  `getScope()` semantics in `runner.js:223-235`).

### First-load fallback chain

**Revised 2026-05-14 in response to design feedback.** The original
proposal used the YAML-order LAST feature ("most recently added"); we
switched to the alphabetically FIRST feature plus a new "All code"
option. Rationale: alphabetic-first is more predictable and less
brittle to YAML reordering than "most recently added," and the new
"All code" option gives users a sensible broad scope that's narrower
than `Project-wide`.

The fallback chain on page load is:

1. `localStorage` has a saved scope → use it (could be a feature path,
   a custom path, or `""` for explicit Project-wide).
2. Empty storage, alphabetically-first feature with a path exists →
   pre-select that feature.
3. Empty storage, no path-bearing feature in `features.yaml` →
   pre-select the new **"All code"** option (`value="src/"`).
4. Edge: "All code" is itself a picker option, reachable as a manual
   choice in cases 1 or 2 as well.

**Implementation:** rename the proposed helper from
`most_recent_feature()` to `first_feature()`:

```python
def first_feature(project_root: Path | str) -> Feature | None:
    """Return the alphabetically-first feature with a renderable scope.

    Used by the ops dashboard scope picker as the primary first-load
    fallback when localStorage has no saved scope. Falls back to the
    new "All code" option (src/) when no path-bearing features exist.
    """
    for feature in list_features(project_root):
        if feature.path:
            return feature
    return None
```

The picker display order stays alphabetical (existing
`list_features().sort(key=lambda f: f.name)` behavior).

### Picker option order — revised

The picker now carries a new "All code" option positioned between the
feature list and `Custom path…`:

```
Project-wide                  (the explicit "scan everything" option)
<features, alphabetical>      (feature-scoped runs)
All code (src/)               (NEW — broad-but-not-everything default)
Custom path…                  (toggle, reveals text input)
```

"Custom path…" stays anchored at the bottom as the structurally
different "go beyond the menu" option. "All code" precedes it because
fixed options conventionally come before the input-toggle option.

### Server-injected config

The dashboard route passes two paths into a single JSON config block:

```html
<script id="scope-picker-config" type="application/json">
{"firstFeaturePath": "{{ first_feature_path }}",
 "allCodePath": "{{ all_code_path }}"}
</script>
```

`firstFeaturePath` is the empty string when no path-bearing feature
exists; the JS falls through to `allCodePath` in that case.
`allCodePath` is `"src/"` for attune-ai; future projects with
different code roots can override via configuration without touching
the JS.

### Edge cases (confirmed 2026-05-14)

| Case | Behavior |
|------|----------|
| First load, empty `localStorage`, features exist | Default to alphabetically-first feature with a path. |
| First load, empty `localStorage`, no features | Default to "All code" (`src/`). |
| User picks `Project-wide` | Saved like any other. They meant it. |
| User picks a feature option | Saved as that feature's path. |
| User picks `Custom path…` and types | Saved as the literal trimmed string. |
| User picks `Custom path…` and leaves blank | Functionally Project-wide (existing `getScope()` returns `null`). Don't save the blank. |
| Saved path no longer matches any feature | Fall to `Custom path…` with the saved string pre-filled. Don't silently drop. |
| `localStorage` disabled / quota exceeded | Picker falls back to `Project-wide` per-load. No errors thrown; degraded but functional. |
| Workflow row doesn't support paths (`n/a`) | Unaffected. No picker, no read, no save. |

## Acceptance criteria

1. On a fresh browser profile (no `localStorage`) with features defined,
   loading `/workflows` pre-selects the alphabetically-first feature
   with a path in every path-supporting row. When no path-bearing
   feature exists, the picker pre-selects the "All code" option.
2. After picking a feature in any row and reloading, every
   path-supporting row defaults to that feature.
3. After picking `Custom path…` with a typed string and reloading, every
   path-supporting row defaults to that custom string (in `__custom__`
   mode with the input pre-filled).
4. After picking `Project-wide` and reloading, every path-supporting row
   defaults to `Project-wide`.
5. With a saved scope that no longer matches any feature, the picker
   shows `Custom path…` with the saved string pre-filled.
6. Read-only mode (`--read-only`): scope cell still renders the picker
   with the saved default. (The Run button is hidden in read-only, but
   the picker state is observed and remembered for when the user enables
   runs.)

## Implementation scope

- `src/attune/ops/data.py` — add `most_recent_feature_name()` helper.
- `src/attune/ops/routes/dashboard.py` (or wherever the `/workflows`
  view is rendered) — pass `most_recent_feature_path` into the template
  context.
- `src/attune/ops/templates/workflows.html` — add the JSON config block.
- `src/attune/ops/static/js/runner.js` — read `localStorage` + config
  block on `DOMContentLoaded`; save on `change` events; handle the
  unmatched-saved-path fallback.
- `tests/unit/ops/test_scope_picker.py` — extend existing tests:
  - `most_recent_feature_name` returns last YAML entry / `None` on empty
  - JSON config block rendered correctly into template
  - JS save/restore round-trip (DOM + a stub `localStorage`)
  - Unmatched-saved-path fallback to `Custom path…` pre-fill

**Estimated LOC:** ~60-80 production + ~40-60 test.
**Estimated time:** 45-60 minutes including tests, running locally.

## Out of scope (deferred follow-ups)

- **Per-workflow scope memory.** Considered and rejected (see Storage
  Model rationale). May revisit if usage telemetry shows users
  consistently picking different scopes per workflow.
- **Cross-tab sync via `storage` event.** Two open dashboard tabs would
  see each other's picks. Cheap addition but not core to the IA fix.
- **Path preview** ("security-audit → resolves to `src/attune/security/`")
  — a separate trust-gap fix.
- **Long flat feature list grouping.** Real but scales with feature
  count; only painful when the list is much longer than today's ~25.
- **"Custom path…" placement** in the picker order. Usage-dependent; we
  don't have data yet on whether users mostly pick features or mostly
  type paths.

## Open questions

None blocking. The proposal is fully scoped against Patrick's confirmed
answers from 2026-05-14:

- Storage model: Option 1 (global) — **confirmed**.
- First-load fallback: most-recent-feature-added — **confirmed**.
- All edge cases (Project-wide remembered, Custom path saved literally,
  unmatched paths fall to Custom pre-fill) — **confirmed**.
