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

### First-load fallback: most-recent-feature-added

When `localStorage` is empty (new user, cleared cache), the fallback is
NOT `Project-wide`. It's the feature most recently added to the
registry. Rationale: a new contributor's first dashboard view shouldn't
default to "scan the whole repo"; it should default to "here's the
newest thing being worked on, start here."

**Implementation:** add a sibling helper to `data.py`:

```python
def most_recent_feature_name(project_root: Path | str) -> str | None:
    """Return the LAST feature name in features.yaml insertion order.

    Used by the ops dashboard as the first-load fallback for the
    scope picker when localStorage is empty. Returns None if
    features.yaml is missing or empty.
    """
    # Re-uses the same parse path as list_features() but reads from
    # the cached raw dict pre-sort, returning the last key.
```

The picker display order stays alphabetical (current
`list_features().sort(key=lambda f: f.name)` behavior) — findability in a
long list matters. Only the *fallback selection* uses insertion order.

Server passes `most_recent_feature_name(project_root)` to the template
as a separate context variable, rendered into a tiny JSON config block:

```html
<script id="scope-picker-config" type="application/json">
{"mostRecentFeature": "{{ most_recent_feature_path }}"}
</script>
```

The JS reads this on page load and uses it when `localStorage` is empty.

### Edge cases (confirmed 2026-05-14)

| Case | Behavior |
|------|----------|
| First load, empty `localStorage` | Default to most-recent-feature-added (feature path). |
| User picks `Project-wide` | Saved like any other. They meant it. |
| User picks a feature option | Saved as that feature's path. |
| User picks `Custom path…` and types | Saved as the literal trimmed string. |
| User picks `Custom path…` and leaves blank | Functionally Project-wide (existing `getScope()` returns `null`). Don't save the blank. |
| Saved path no longer matches any feature | Fall to `Custom path…` with the saved string pre-filled. Don't silently drop. |
| `localStorage` disabled / quota exceeded | Picker falls back to `Project-wide` per-load. No errors thrown; degraded but functional. |
| Workflow row doesn't support paths (`n/a`) | Unaffected. No picker, no read, no save. |

## Acceptance criteria

1. On a fresh browser profile (no `localStorage`), loading `/workflows`
   pre-selects the most-recent-feature-added in every path-supporting
   row.
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
