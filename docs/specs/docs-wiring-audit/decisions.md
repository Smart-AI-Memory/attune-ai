# Per-decision log — Docs wiring audit

**Status:** approved


Append-only log. Resolutions for the open questions enumerated in
[requirements.md](./requirements.md#open-questions). Each decision
moves the spec one step closer to Phase 1 execution.

---

## Phase 1 approval (2026-05-31)

Three open questions resolved in one session. Spec status flips
from `draft` to `approved`. Phase 1 (design + implement the
wiring-check tooling) can proceed after this lands on `main`.

---

### Q1 — Anchor rename policy: redirect/alias or update all inbound links?

**Decision:** **Update all inbound links, no redirect.** When a
heading is renamed (e.g. `#industry-wizards` →
`#configdrivenwizard`), grep + update every internal link in the
same PR as the rename. No `redirects.yml` shim.

**Rationale:** Single source of truth. A redirects file bloats
over time, becomes a separate corpus of fiction, and undermines
the wiring audit itself — the audit is about link integrity, and
a shim that makes broken links appear unbroken defeats that.
External links (blog posts, conference talks, Stack Overflow)
break with either policy; they're out of scope for an internal
wiring audit anyway. Anchor renames are rare — this isn't a
high-frequency operation that needs ergonomic shims.

**Alternatives considered:**

- **Keep a redirect/alias file** — More forgiving for external
  links, but introduces a second source of truth and adds
  long-term maintenance debt.
- **Hybrid (short-lived alias)** — Both: update inbound links
  AND keep a temporary redirect with a documented removal date.
  Cleanest for users mid-bookmark but adds a tracking obligation
  (someone has to remove the redirect when the date hits, or it
  sticks forever and becomes the unmaintained case anyway).

**Implementation note for Phase 1:**

- The wiring-check tool flags any internal `[…](…#anchor)` whose
  anchor doesn't exist at the target.
- Rename workflow: when renaming a heading, the same commit
  greps `docs/` for the old anchor and updates every inbound
  link. CI enforces zero broken-anchor count.

---

### Q2 — Orphan strictness: subtree, per-file, or nav-hidden?

**Decision:** **Entire subtree allowlisted.** A small allowlist
file (`.audit/orphans.yml`-style) lists subtree paths exempt from
the orphan check. Subtrees on the initial allowlist:

- `docs/examples/`
- `docs/blog/`
- `docs/BLOG_*.md` (top-level blog files)
- `docs/archive/`
- `docs/specs/`
- `docs/pitch/`

**Rationale:** Per-file allowlisting is high-friction — every new
example file requires touching the allowlist, which means in
practice the allowlist grows stale and people stop updating it.
Nav-hidden status would reuse `mkdocs.yml` config but couples the
audit to nav-structure decisions (changing nav can silently break
orphan-check semantics). Subtree allowlist is the right balance:
low maintenance, explicit, decoupled from nav.

**Alternatives considered:**

- **Per-file allowlisting** — Tightest control; in practice
  unmaintained.
- **Nav-hidden subtrees** → exempt from orphan check — Elegant
  reuse of mkdocs config; tightly couples audit semantics to UX
  decisions.

**Implementation note for Phase 1:**

- Allowlist format: YAML list of subtree paths (trailing slash
  for directories, exact match for top-level files).
- The wiring-check tool walks `docs/` for `.md` files, computes
  inbound-link graph, then filters out any file under an
  allowlisted subtree before flagging orphans.
- Real orphans hidden inside an allowlisted subtree are
  acknowledged risk — these subtrees are by-design orphan-friendly,
  so the cost is acceptable.

---

### Q3 — mkdocstrings scope: 5 known files or whole-tree sweep?

**Decision:** **Sweep the whole `docs/` tree.** v1 audits every
`:::` directive across `docs/`, not just the 5 session-confirmed
files (`core.md`, `empathy-os.md`, `llm-toolkit.md`,
`multi-agent.md`, `persistence.md`).

**Rationale:** `grep '^:::'` across `docs/` takes seconds — no cost
to broadening. The 5 known files came from session-time
confirmation, not a comprehensive scan; limiting scope to them
means new mkdocstrings usage in other files goes uncaught, which
is exactly the drift the audit is meant to catch. v1 should
establish a strong pattern from day one.

**Alternatives considered:**

- **Audit only the 5 known files for v1** — Faster Phase 1,
  easier to validate. Defers the whole-tree sweep to v2. Risk:
  unknown mkdocstrings files in other paths continue to drift
  between v1 and v2.

**Implementation note for Phase 1:**

- Wiring-check tool's first pass: `grep -rn '^:::' docs/` to
  build the full `:::` directive inventory.
- Each directive is verified: the referenced symbol (e.g.
  `::: attune.coordination.ConflictResolver`) must resolve in
  current `src/`. Unresolved references fail the audit.
- This subsumes both `mkdocs build --strict` (which would
  surface the same failures at build time) and adds the
  precondition check at lint/CI time.

## Phase 4 approval + v1.1 execution (2026-07-15)

**Decision:** Patrick approved Phase 4 ("docs-wiring-audit approve",
2026-07-15). Tasks 3, 4, 9 shipped the same session in
`scripts/audit_docs_wiring.py` (single-file layout — the deviation
from design.md's package proposal is documented in the script
docstring and stands).

**Scope corrections found at execution** (the spec-drift grep, per
the spec-named-work-scope lesson):

- **Task 4 premise was stale.** features.yaml no longer carries
  per-feature `doc_paths`; features are `status: manual` and the
  feature↔doc consistency the task wanted is owned by the
  projection-drift gate (#1372,
  `tests/unit/authoring/test_projection_drift.py`). The check ships
  adapted: `_docs` entries must exist on disk (error). The unlinked
  reference/how-to advisory half was dropped — projector pages make
  it meaningless.
- **Nav check needed two structural exemptions** the task didn't
  anticipate: (a) `features/` is nav-injected at build time by
  `docs/hooks/feature_nav.py`; (b) projector-emitted
  `<kind>/<feature>.md` pages (reference/how-to/architecture/
  tutorials × features.yaml names) are hub-linked by design
  (mkdocs.yml D12 note). Both exempt in `check_nav`.
- **Warnings are advisory.** Exit code gates on error-severity
  findings only, so adding checks can't instantly break the
  required CI job with advisory noise.

**Findings fixed in the same PR:** 4 dangling `_docs` entries in
`.help/features.yaml` (empathy-os.md, core.md,
adaptive-learning-system.md, sbar-clinical-handoff.md — all deleted
in #1073/#1109, entries never cleaned). `.audit/orphans.yml` seeded
with 11 reasoned entries covering the genuine repo-only orphans
(blog drafts, reports, process notes, one-offs); 67 projector pages
needed no allowlisting thanks to the structural exemption.

**Remaining:** Task 10 (See-Also advisory) stays deferred per the
tasks doc.
