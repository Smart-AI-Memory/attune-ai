# Spec: Ops Dashboard — Path Picker (port from attune-gui)

> Replace the bare scope textbox on `/workflows` with a path-picker
> modal patterned on attune-gui's. Reuse the existing
> `/api/fs/browse` endpoint shape and the modal JS as a starting
> point — both dashboards benefit from sharing this surface.

---

## Phase 1: Requirements
**Status:** approved
### Problem statement

The 2026-05-14 QA punch list flagged P2-7 (run-view scope path
overflow). Patrick reframed the underlying UX problem: the
workflow scope picker on `/workflows` currently exposes a bare
`<input>` with a `placeholder="e.g. src/attune/security/"` —
users either know the path they want and type it, or guess.
There's no discovery surface, no path validation feedback, and
no protection against the cross-worktree path bug we just fixed
(B2 / P0-2 adjacent).

Meanwhile **attune-gui already has a working path picker**:
- `GET /api/fs/browse?path=<dir>&annotate=<help|project>` —
  directory listing, hidden-entry suppression, parent navigation,
  optional manifest detection
- A modal in `commands.html` (lazily-injected into the DOM) with
  bread­crumb, parent button, subdir list, "Choose this directory"

Both dashboards benefit from sharing this surface — same UX,
same backend contract, no UI fragmentation.

### Scope

**In scope:**

- Port `/api/fs/browse` endpoint from `attune-gui/sidecar/attune_gui/
  routes/fs.py` to `src/attune/ops/routes/fs.py`. Single-file
  endpoint, ~90 lines.
  - `path` query param (default `~`)
  - `annotate` query param: `help` flag dirs containing
    `features.yaml`, `project` flags dirs containing
    `.help/features.yaml`. For the ops dashboard we add `workspace`
    to flag dirs that are sub-paths of `cfg.project_root` (so the
    user sees which dirs are safely scopeable).
  - Returns `{path, parent, entries[], has_*}` per attune-gui.
- Port the modal JS from `attune-gui/sidecar/attune_gui/templates/
  commands.html` (`openPathPicker(targetInput, browseHint)` and
  helpers) into a new `src/attune/ops/static/js/path_picker.js`.
  - Lazy DOM injection on first open
  - Keyboard nav (Tab, Esc closes, Enter selects)
  - Status banner ("✓ inside workspace" / "⚠ outside workspace —
    workflow will reject" — leveraging the workspace_root we
    already emit for scope-picker validation)
- Wire the picker into the existing scope picker on `/workflows`:
  the `<input class="scope-custom">` gets a `Browse…` button next
  to it; clicking opens the modal pre-rooted at the input's
  current value.
- Match the styling to the dashboard's existing modal language
  (currently none — define minimal CSS that fits the existing
  visual system: bg-elev panel, border, shadow, dark-mode aware).
- Path validation: on "Choose this directory", run the same
  `isScopeInWorkspace` check we added in PR #358; if the chosen
  path is outside the workspace, show the status banner warning
  but still allow the choice (user may want to scope outside
  workspace — server rejects later anyway).
- Server-side: register the new `fs` router in `src/attune/ops/
  server.py` mounted at `/api/fs`.

**Out of scope:**

- File picker (only directories — same as attune-gui's scope)
- Recently-used paths history (Phase 2)
- Bookmarks / favorites (Phase 2)
- Editing the picker from inside the modal (no rename / create)
- Cross-machine file system (local only)

### Acceptance criteria

1. `GET /api/fs/browse?path=/Users/patrickroebuck/attune-ai`
   returns a JSON listing matching the attune-gui contract.
2. The `Browse…` button on `/workflows` opens a modal centered
   over the page.
3. Clicking a subdir in the modal updates the breadcrumb and
   listing. Parent button works. Esc / overlay-click closes.
4. "Choose this directory" sets the input to the breadcrumb path
   and closes the modal.
5. The status banner shows "✓ inside workspace" when the
   breadcrumb is under `cfg.project_root`, "⚠ outside workspace —
   the run endpoint will reject this scope" otherwise.
6. Keyboard accessible: Tab cycles through entries, Enter on a
   subdir navigates into it, Enter on "Choose this directory"
   confirms, Esc cancels.
7. The picker is reusable — adding it to a future page (e.g. the
   `--specs-root` setting on Health, or a future memory browser)
   should be a one-line `data-browse-target` annotation, not a
   re-wiring.

### Non-goals / explicitly deferred

- **Native OS file dialog.** attune-gui briefly used `osascript`;
  switched to in-page modal because tkinter crashes on macOS
  non-main-thread. Stick with the in-page modal.
- **File selection.** Workflow scope is always a directory.
- **Validation of attune-specific markers beyond workspace
  containment.** The `has_manifest` annotations from attune-gui
  are useful for that dashboard's command-picker use case but
  not for ops workflow scoping. Skip the annotation params for
  Phase 1 unless a workflow specifically benefits.

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Port of `fs.py` drifts from attune-gui's contract | Med | Copy the file verbatim and adapt only the security boundary (workspace-root); keep the response shape identical so the JS modal port works unchanged |
| Modal styling clashes with dashboard's visual system | Low | Use existing CSS tokens (`--bg-elev`, `--shadow`, `--border`); reference the spec-detail page's recent markdown-body styling for visual coherence |
| Permission errors on protected dirs blow up the picker | Low | attune-gui handles via 403; the modal shows an inline error and lets the user navigate away |
| Picker reused across pages diverges in behavior | Med | Put `path_picker.js` in `src/attune/ops/static/js/` (shared); pages opt in via a single DOM attribute (e.g. `data-browse-target=".scope-custom"`) |

---

## Reference — attune-gui code to port

**Backend:** `attune-gui/sidecar/attune_gui/routes/fs.py` (88 lines).
The shape is small and self-contained — port verbatim, swap the
attune-gui-specific `_has_manifest` / `_has_project_manifest`
checks for an ops-specific `_in_workspace(cfg)` annotation.

**Frontend:** `attune-gui/sidecar/attune_gui/templates/commands.html`
lines ~585-750. Key functions:
- `openPathPicker(targetInput, browseHint)` — entry point
- `load(path)` — fetches /api/fs/browse and renders the modal
- `closePicker()` — teardown
- The lazy DOM-injection pattern (`document.getElementById('cmd-picker')`)
  is worth keeping; rename to `attune-ops-picker` for the new context.

Test file `attune-gui/sidecar/tests/test_fs.py` covers the backend
endpoint; port those tests too (`tests/unit/ops/routes/test_fs.py`).
