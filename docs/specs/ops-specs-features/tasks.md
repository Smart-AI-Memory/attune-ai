# Tasks — Port spec-handling features from attune-gui to attune ops

**Status:** Approved (2026-05-11) — execution gated on Phase 0 conditions

---

## Phase 0 — Gate (the contract before any code)

This phase is the spec's most important deliverable. Without
the gate, this spec is just "add a feature." With it, this
spec is "do the work when the foundation is ready."

- [ ] **0.1** Verify gate conditions before starting Phase 1:
  - [ ] PR #212 merged + 3 consecutive green CI runs on `main`
        + no new CI-fix PRs opened in that window
  - [ ] PRs #227, #228 merged + verified in production
  - [ ] No critical open `ops`-labeled issues
  - [ ] Probe C Phase 4 settled (parallel xdist restored)
  - [ ] (Optional) PR #226 larger runners landed
- [ ] **0.2** Re-check decisions.md "What we port / what we
  do NOT port" — has Patrick's usage of attune ops changed
  in the interim such that the scope should adjust?

## Phase 1 — Federated spec listing read-side

Mirrors `attune-gui sidecar/attune_gui/routes/cowork_specs.py`
GET endpoints. Backend first; frontend follows.

- [ ] **1.1** Add `src/attune/ops/routes/specs.py` with:
  - `GET /api/specs` — list all spec dirs across configured
    roots, with phase status for each
  - `GET /api/specs/{slug}` — return content of phase files
    for one spec (read-only)
- [ ] **1.2** Add `--specs-root` flag to `attune ops` CLI;
  default to `docs/specs/` relative to `--project-root`.
  Accept multiple values for multi-root listing (matching
  attune-gui PR #30 pattern).
- [ ] **1.3** Tests at parity with existing ops routes:
  - Empty roots
  - Single root with multiple specs
  - Multi-root with naming collisions (later root wins?
    error? — decide and document)
  - Phase file missing
  - Malformed phase file (no `**Status**:` line)

## Phase 2 — Status-flip write-side

- [ ] **2.1** Add `PUT /api/specs/{slug}/{phase}/status` route
  — same body as attune-gui's
  (`{"status": "<valid-value>"}`)
- [ ] **2.2** Reuse attune-gui's `_STATUS_RE` and
  `_VALID_STATUSES` patterns directly (or copy with
  attribution comment)
- [ ] **2.3** Honor the `--read-only` flag added in PR #227 —
  status flip is a mutation, so blocked in read-only mode
- [ ] **2.4** Atomic write via existing
  `attune.ops` write helpers (or port `atomic_write` from
  attune-gui)

## Phase 3 — Frontend Specs tab

- [ ] **3.1** Add `Specs` tab to nav in
  `src/attune/ops/templates/base.html`, between
  `Workflows` and `Telemetry`
- [ ] **3.2** New template
  `src/attune/ops/templates/specs.html` — pattern-match
  attune-gui's `templates/specs.html` (160 lines, simple)
- [ ] **3.3** Status-flip dropdown per phase with optimistic
  UI + server-confirmation pattern (similar to runner.js
  workflow row buttons)
- [ ] **3.4** Per-spec drill-in showing phase file content
  (read-only)

## Phase 4 — Observe & adjust

- [ ] **4.1** After 2 weeks of usage, log which features are
  actually used (telemetry: spec listing views, status
  flips, drill-ins)
- [ ] **4.2** Decide whether Phase 1's read-side is enough
  or whether to expand toward attune-gui's create/bootstrap
  flows
- [ ] **4.3** If usage warrants, file a follow-up spec for
  Phase 5

## Out of scope (firm — do not creep)

- Spec creation from slug (`POST /api/specs`)
- Phase bootstrap from template (`POST /api/specs/{slug}/phase`)
- Editor / WYSIWYG / inline-markdown-editing
- Diff view between phase files
- Multi-user collaboration / locking
- Notifications (slack/email/desktop)
- Mobile access
- Spec analytics dashboards
- Anything from attune-gui's living-docs surface
