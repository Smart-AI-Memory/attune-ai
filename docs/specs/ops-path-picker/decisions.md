# Spec: Ops Path Picker — Decisions

**Status:** approved


> Pre-committed decisions captured 2026-05-14. Triggered by QA
> punch-list item P2-7 reframed by Patrick from "fix the overflow"
> to "give users a real path-selection affordance."

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Reuse vs net-new | **Port from attune-gui** | Patrick: "Both dashboards have good work to share." attune-gui's `fs.py` + modal JS are tested, working, and a ~200-line total port. No reason to design from scratch. |
| Native OS dialog vs in-page modal | **In-page modal** | attune-gui tried `osascript`, switched to in-page after macOS tkinter crashes on non-main thread. Their lesson stands. |
| File or directory | **Directory only** | Workflow scope is always a dir. File picking is Phase 2 if a future workflow needs it. |
| Workspace boundary check | **Soft warning, not hard block** | The "outside workspace" status banner warns; user can still pick. The run endpoint enforces. Matches the existing `isScopeInWorkspace` JS we added in PR #358 — defense-in-depth pattern, not a blocker. |
| Picker JS location | `src/attune/ops/static/js/path_picker.js` | Separate from `runner.js` because the picker is reusable across pages (Workflows now; possibly Health / Memory / a future settings page later). |
| Picker invocation | `data-browse-target="<selector>"` on a button → opens picker pre-rooted at the selector's input | One attribute, no per-page wiring. |
| Endpoint mount | `/api/fs` (matches attune-gui prefix) | Drift would force consumers to know which dashboard they're talking to. Same prefix = code can be reused. |
| Endpoint contract | Identical to attune-gui's `/api/fs/browse` | Documented in attune-gui's `routes/fs.py`; the ops port matches verbatim. |
| `annotate` parameter values | `help`, `project`, **`workspace` (new)** | First two ported from attune-gui. `workspace` is new for ops: flags entries that are inside `cfg.project_root` so the picker's "✓ inside workspace" banner has data to render. |
| Modal styling source | Reuse existing CSS tokens (`--bg-elev`, `--shadow`, `--border`); reference markdown-body styling for visual coherence | Don't introduce a new design language. |
| Test port | Yes — `tests/unit/ops/routes/test_fs.py` | The attune-gui tests cover the meaningful cases (lists subdirs, resolves paths, handles permission errors, hides hidden entries). Port them. |
| Accessibility floor | Tab/Enter/Esc keyboard nav, WCAG 2.5.5 AA hit targets, `aria-modal="true"` + focus trap | Matches the standard set by the Specs page pill click-to-edit pattern. |

---

## Open questions (resolve during design phase)

1. **`features.yaml` / project-manifest annotations.** attune-gui
   uses these to help the user pick a `.help/` dir or project
   root. The ops Workflows page doesn't have an equivalent
   target (any dir under workspace is valid scope). Phase 1
   probably doesn't need these annotations; design phase decides
   whether to keep the support code or strip it.

2. **Modal focus-trap implementation.** Native dialog vs hand-
   rolled focus management vs lightweight library. Probably
   hand-rolled — the existing dashboard ships no JS framework
   and we shouldn't introduce one for a single modal.

3. **Where else to mount the picker.** Workflows is the obvious
   first consumer. Are there other inputs in the dashboard that
   currently accept a path string and would benefit?
   `--specs-root` is server-config (one-time), not in scope.
   Possibly a future Memory browser or settings page.

4. **Recently-used paths.** A simple localStorage list of the
   last 5 picked paths, surfaced at the top of the modal, would
   accelerate common usage. Phase 2 — easy add once Phase 1
   ships and there's a body of "common paths" to surface.

---

## Calibration record

To be filled in during implementation:

- [ ] How many lines does the JS port end up being? Target ≤300.
- [ ] Does the modal feel responsive on the dashboard, or does
  the fetch-render cycle introduce a flash?
- [ ] What's the typical use pattern — pick once and edit, or
  navigate frequently? Informs whether to keep the modal open
  or close on choose.

---

## Decision-change log

- 2026-05-14 — Initial decisions captured. P2-7 in the
  ops-dashboard QA punch list. Patrick reframed from "fix
  overflow" to "give users a real picker reusing attune-gui
  code."
