# Requirements — Doc-Stack Reference Subtypes
**Status:** killed (2026-07-14) — triage decision (matrix-2026-07-14): approved 2026-05-16, parked 2026-06-09, no movement since
**Owner package:** `attune-author` (sibling repo — this spec lives in attune-ai because cross-package specs live here per the spec-viewer-ia precedent)

---

## Problem

The current `reference.md.j2` meta-template in
[`~/attune-author/src/attune_author/meta_templates/reference.md.j2`](/Users/patrickroebuck/attune-author/src/attune_author/meta_templates/reference.md.j2)
is tabular-only — it renders `## Classes` and `## Functions` tables when those fields are populated and nothing else. This is the right shape for code-API surfaces but produces low-signal output for features whose "reference" is:

1. **Procedural** — skills, commands, multi-step tools. The right reference for `/security` is "here's the parameter you can pass, here's the ordered set of steps it runs, here's the output you'll get" — narrative + structure, not just tables.
2. **Free-form** — concept docs, architecture references, decision records. Tables don't fit; mixed paragraphs + examples + diagrams do.

Today, all three subtypes get the same tabular template. The class/function tables on a skill reference are usually empty (skills are markdown, not Python classes), leaving a short, structureless reference doc. The class/function tables on an architecture reference are misleading (they document implementation, not the architectural decisions a user reads "reference" for).

## Why this matters now

- The 11-kind canonical set is fully landed (concept, task, reference, quickstart, troubleshooting, faq, comparison, error, note, tip, warning). The kinds are stable; the question is now subtype fidelity within each kind.
- RAG retrieval quality depends on signal density. A reference doc with only "no public classes" / "no public functions" tables is a near-empty entry in the corpus. Per the existing CLAUDE.md lesson on "Industry terminology won't appear in LLM-polished RAG summaries unless the prompt explicitly invites common domain synonyms," low-content templates have a measurable retrieval cost.
- The cross-link gap noted in [project_doc_stack_next.md](../../../memory/project_doc_stack_next.md) — "most entries say 'None generated yet'" — is downstream of the same issue: reference docs that don't have rich content can't generate rich cross-links.

## Non-goals

- **Not a new kind.** The 11-kind canonical set stays. This is a subtype dimension within `reference` only.
- **Not a generator-rewrite spec.** attune-author's generator/polish pipeline keeps its shape; only the meta-template and a small subtype selector change.
- **Not a forced manual classification.** Subtype selection should be automatic from source signals with a frontmatter override for edge cases.

## Success criteria

1. Three subtype meta-templates exist and produce distinct output shapes when applied to representative features.
2. Subtype auto-selection: skill → procedural, tool with public API → tabular, concept/architecture/decision → free-form. Override via `reference_subtype: <procedural|tabular|free-form>` in source-feature frontmatter.
3. Measurable retrieval improvement: a RAG benchmark sweep (per attune-rag's existing fixture harness) shows the procedural and free-form variants improve P@1 on queries that previously returned low-content tabular reference docs. Improvement target: +10% P@1 on the affected subset.
4. No regression on tabular-subtype features (the ones where the current template already works).

## Open questions

- **DECIDE-1**: Where does subtype detection live — in `attune-author`'s feature classifier, or as a separate pre-template step?
- **DECIDE-2**: Does the polish pass (LLM-polished summaries) need subtype-aware prompts? Or is the same polish prompt fine across subtypes?
- **DECIDE-3**: Cross-link enrichment — bundled into this spec, or a follow-up?

## Phased delivery

Outlined in `tasks.md`. Phase 0 is a measurement of how many existing features fall into each subtype + a hand-crafted sample of each subtype rendered on one representative feature, to validate the design before writing the generator code.

## Related work

- The `help-ia-code-quality` proposal (PR #418) is an instance of this gap manifesting at the kind level (the generated task was wrong-audience for the feature). Subtypes at the reference level are the same shape one level down.
- attune-help's RAG corpus uses these templates as its primary source; improvements compound across the workspace.
- attune-rag's golden-query benchmark harness can validate retrieval improvement empirically (per existing CLAUDE.md lessons on golden-query fixtures).
