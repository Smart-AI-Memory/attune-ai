# Decisions — Doc-Stack Reference Subtypes
**Status:** killed (2026-07-14) — triage decision (matrix-2026-07-14): approved 2026-05-16, parked 2026-06-09, no movement since
---

## Pre-committed decision matrix (Phase 0 → action)

Per the existing CLAUDE.md lesson on pre-committed decision matrices. Committed BEFORE Phase 0 runs.

| Phase 0 result | Action |
|---|---|
| Hand-crafted procedural + free-form samples are qualitatively better than the current tabular output on the same features | **PROCEED** to Phase 1 design + meta-template work |
| Samples are no better than current — the tabular template was working harder than we thought | **RETIRE** — no real gap |
| Samples are better only for very specific feature shapes (e.g. only skills, not architecture docs) | **NARROW** — proceed with only the validated subtypes (e.g. add procedural only, defer free-form) |
| RAG benchmark on subtype-applied features fails to improve P@1 in Phase 1 | **PARTIAL ROLLOUT** — keep the subtypes for docs-readability but don't claim retrieval improvement |

---

## DECIDE callouts

### D1 — Where does subtype detection live?

**Status:** open

**Options:**
- (a) Inside `attune-author`'s feature classifier (one new field on the existing classifier output).
- (b) Separate pre-template step that reads source-feature frontmatter + path heuristics and emits a subtype hint to the template context.
- (c) Inline in the meta-template itself via Jinja2 conditionals on existing context variables.

**Lean:** (b) — keeps the classifier focused and makes the heuristic auditable. Defer commitment until Phase 0 design.

### D2 — Subtype-aware polish prompts?

**Status:** open

The LLM polish pass (in `~/attune-author/src/attune_author/polish.py` and `polish_prompts.py`) currently uses one prompt across all kinds. Per the existing CLAUDE.md lesson on industry terminology in polished summaries, the polish prompt matters for retrieval quality. Whether subtypes need different prompts is an empirical question.

**Options:**
- (a) One polish prompt regardless of subtype.
- (b) Three prompts, one per subtype.
- (c) Base prompt + subtype-specific addenda (the "industry-terminology" pattern from the lesson, applied per-subtype).

**Lean:** (c) — minimal duplication, follows the established lesson pattern. Validate in Phase 0 by hand-crafting one polished sample per subtype and comparing.

### D3 — Cross-link enrichment scope

**Status:** open

The memory file `project_doc_stack_next.md` bundles "richer cross-linking" with the subtype work. Whether they should be one spec or two:

**Options:**
- (a) Bundle. Both improve reference doc quality; the work is adjacent.
- (b) Split. Cross-link enrichment touches the manifest / sidecar layer, which is a different surface than the meta-templates. Decoupling reduces blast radius per PR.

**Lean:** (b) — split. If Phase 0 endorses subtype work, cross-link enrichment is a follow-up spec that can borrow this spec's benchmark harness.

### D4 — Auto-detection precedence

**Status:** open

When source frontmatter says `reference_subtype: free-form` but the classifier would auto-select `tabular` (e.g. a manually-overridden architecture doc that ALSO has public classes), which wins?

**Lean:** explicit frontmatter wins. Document this clearly.

---

## Resolved decisions

(None yet — this is a draft.)
