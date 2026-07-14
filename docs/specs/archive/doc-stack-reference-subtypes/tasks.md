# Tasks — Doc-Stack Reference Subtypes
**Status:** killed (2026-07-14) — triage decision (matrix-2026-07-14): approved 2026-05-16, parked 2026-06-09, no movement since
| Phase | Status | Owner | Notes |
|---|---|---|---|
| Phase 0 — Inventory + hand-crafted samples | in progress | | 0.1 + 0.2 done 2026-05-26 (see `phase0-data/`). 0.3–0.6 await editorial pass. |
| Phase 1 — Design + meta-templates | gated on Phase 0 | | Only if matrix says PROCEED |
| Phase 2 — Generator + classifier wiring | gated on Phase 1 | | attune-author work |
| Phase 3 — Regenerate corpus + RAG benchmark | gated on Phase 2 | | Cross-package: attune-author + attune-help + attune-rag |

---

## Phase 0 — Inventory + samples (cheap, ~$5–10 in LLM cost for polish samples)

**Goal:** validate the subtype hypothesis with hand-crafted output before writing any generator code.

- [x] **0.1** Inventory current reference templates across the workspace. Output: `phase0-data/reference-inventory.csv` with columns `package, feature, current-content-shape (tabular-with-classes / tabular-with-functions / mostly-empty), lines, target-subtype`. Cover attune-ai, attune-help, attune-author, attune-rag, attune-gui. **Done 2026-05-26** — 117 reference docs across 5 packages, see `phase0-data/reference-inventory.csv` + `phase0-data/inventory-summary.md`.
- [x] **0.2** Compute distribution. What % of references would be procedural? tabular? free-form? Sanity-check the spec's premise. **Done 2026-05-26** — 72 tabular (61.5%), 26 procedural (22.2%), 9 free-form (7.7%), 10 ambiguous (8.5%). Premise confirmed: ~30% of corpus benefits from new subtypes.
- [ ] **0.3** Pick one feature per subtype for sample rendering:
  - Procedural: `attune-ai/.help/templates/security-audit/reference.md` (skill with steps + parameter).
  - Tabular: keep the current output for a feature with real classes (e.g. `attune-help/.help/templates/manifest/reference.md`).
  - Free-form: `attune-ai/.help/templates/ops-dashboard/reference.md` (architecture-flavored).
- [ ] **0.4** Hand-craft sample output for each subtype. Just markdown — no template engine yet. This is the "ceiling" the generator must approach.
- [ ] **0.5** Qualitative comparison. Side-by-side: current reference output vs. hand-crafted subtype output. Is the gap real? Score on (a) information density, (b) user-readable structure, (c) RAG keyword coverage.
- [ ] **0.6** Apply pre-committed matrix in `decisions.md`. Write `phase0-findings.md`. Route the decision.

**Budget cap:** $10. Phase 0 LLM cost is just polish samples for the hand-crafted refs; the hand-crafting itself is free.

---

## Phase 1 — Design + meta-templates (only if Phase 0 says PROCEED)

- [ ] **1.1** Resolve D1 (subtype detection location), D2 (polish prompts), D4 (auto-detection precedence). Update `decisions.md`.
- [ ] **1.2** Three Jinja2 meta-templates in `~/attune-author/src/attune_author/meta_templates/`:
  - `reference_procedural.md.j2`
  - `reference_tabular.md.j2` (likely the current `reference.md.j2` renamed)
  - `reference_free_form.md.j2`
- [ ] **1.3** Selector function in attune-author that picks the right meta-template given source signals + frontmatter override. Unit-test all branches.
- [ ] **1.4** Polish prompt addenda per subtype, if D2 lands on option (c). One LLM-call A/B per subtype on the Phase 0 hand-crafted samples to validate the addenda actually move the output toward the hand-crafted ceiling.

---

## Phase 2 — Generator + classifier wiring (attune-author work)

- [ ] **2.1** Wire the selector into the doc-gen pipeline. Default: auto-select. Override: frontmatter.
- [ ] **2.2** Backward-compat: any existing reference with no signals defaults to tabular (current behavior). No silent migration.
- [ ] **2.3** Generate a sample regen for one workspace package (attune-ai). Diff vs. current corpus. Human-eyeball the output.

---

## Phase 3 — Workspace regen + RAG benchmark (cross-package)

- [ ] **3.1** Regenerate `.help/templates/` for all five sibling packages using the new subtypes. Commit the regen in each package separately.
- [ ] **3.2** Run attune-rag's golden-query benchmark harness against the new corpus. Record P@1 delta per package.
- [ ] **3.3** Apply the Phase 1 matrix outcome from `decisions.md`. If RAG didn't improve, decide between PARTIAL ROLLOUT or partial revert.
- [ ] **3.4** Cross-link enrichment scope (D3) — if (b) "split into follow-up spec," draft the follow-up here; if (a) "bundle," add a Phase 4.

---

## Retirement criteria

- Phase 0 routes to RETIRE per the matrix.
- 90 days pass without Phase 0 being started.
- A different doc-corpus spec ships and obviates the subtype need.

Retirement note in `decisions.md` with one-line summary.
