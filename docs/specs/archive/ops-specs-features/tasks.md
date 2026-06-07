# Tasks — Port spec-handling features from attune-gui to attune ops

**Status:** Phases 1–3 complete (PRs #236, #239, #249); Phase 4 reflection cycle awaiting 2 weeks of usage (target: 2026-05-25). Phase 0 gate verified 2026-05-12 — see [phase0-audit.md](phase0-audit.md).

---

## Phase 0 — Gate (the contract before any code)

**Gate relaxed 2026-05-11** (see decisions.md "Dropped from the
gate" section). Two original conditions removed as
over-correlated to unrelated CI work. The remaining conditions
are sized to what actually matters for ops-specs-features
specifically.

- [x] **0.1a** PR #212 merged
- [x] **0.1b** Most-recent merge cycle's settled CI run on `main`
      shows only known-pre-existing failures (Py 3.10
      test_chain_executor AttributeError, Windows xdist tracked
      in #232). No new failure modes. **Verified 2026-05-12** —
      runs `fca8c2d7` and `7d988f52` both green; one earlier
      flaky-timeout failure not a new mode.
- [x] **0.2** PRs #227, #228 merged + verified in production
- [x] **0.3** No critical open `ops`-labeled issues
- [x] **0.4** (Optional) PR #226 larger runners landed
- [x] **0.5** Re-check decisions.md "What we port / what we do
      NOT port" — has Patrick's usage of attune ops changed in
      the interim such that the scope should adjust? **Verified
      2026-05-12** — scope did NOT need adjustment; the
      originally-decided scope was fully implemented in the
      interim (PRs #236, #239, #249). See `phase0-audit.md`.

## Phase 1 — Federated spec listing read-side

Mirrors `attune-gui sidecar/attune_gui/routes/cowork_specs.py`
GET endpoints. Backend first; frontend follows.

- [x] **1.1** Add `src/attune/ops/routes/specs.py` with:
  - `GET /api/specs` — list all spec dirs across configured
    roots, with phase status for each
  - `GET /api/specs/{slug}` — return content of phase files
    for one spec (read-only)

  **Shipped via PR #236** (`d6d29642`). Routes at `specs.py:159,186`.
- [x] **1.2** Add `--specs-root` flag to `attune ops` CLI;
  default to `docs/specs/` relative to `--project-root`.
  Accept multiple values for multi-root listing (matching
  attune-gui PR #30 pattern).

  **Shipped via PR #236.** CLI flag at `cli.py:45`; config plumbing at
  `cli.py:117` (`specs_roots=tuple(...)`).
- [x] **1.3** Tests at parity with existing ops routes:
  - Empty roots
  - Single root with multiple specs
  - Multi-root with naming collisions (first-root wins,
    documented)
  - Phase file missing
  - Malformed phase file (no `**Status**:` line)

  **Shipped via PR #236.** 54 tests in `tests/unit/ops/test_specs_routes.py`
  + `test_specs_dashboard.py` — all green as of 2026-05-12.

## Phase 2 — Status-flip write-side

- [x] **2.1** Add `PUT /api/specs/{slug}/{phase}/status` route
  — same body as attune-gui's
  (`{"status": "<valid-value>"}`)
- [x] **2.2** Reuse attune-gui's `_STATUS_RE` and
  `_VALID_STATUSES` patterns directly (or copy with
  attribution comment)
- [x] **2.3** Honor the `--read-only` flag added in PR #227 —
  status flip is a mutation, so blocked in read-only mode
- [x] **2.4** Atomic write via existing
  `attune.ops` write helpers (or port `atomic_write` from
  attune-gui)

## Phase 3 — Frontend Specs tab

- [x] **3.1** Add `Specs` tab to nav in
  `src/attune/ops/templates/base.html`, between
  `Workflows` and `Telemetry`
- [x] **3.2** New template
  `src/attune/ops/templates/specs.html` — pattern-match
  attune-gui's `templates/specs.html` (160 lines, simple)
- [x] **3.3** Status-flip dropdown per phase with optimistic
  UI + server-confirmation pattern (similar to runner.js
  workflow row buttons)
- [x] **3.4** Per-spec drill-in showing phase file content
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
