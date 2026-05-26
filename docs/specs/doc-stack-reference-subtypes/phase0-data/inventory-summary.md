# Phase 0.1 Inventory Summary

**Spec:** doc-stack-reference-subtypes
**Generated:** 2026-05-26
**Scope:** 5 sibling packages (attune-ai, attune-help, attune-author, attune-rag, attune-gui)

---

## Headline

**117 reference docs across 5 packages.** ~30% (35 of 117) would
benefit from new subtypes per the heuristic. The spec's premise
is **confirmed** by the data — tabular-only is the wrong shape for
a substantial minority of the corpus.

## Distribution by target subtype

| Subtype | Count | % | Notes |
|---|---:|---:|---|
| tabular | 72 | 61.5% | Current template serves these well |
| procedural | 26 | 22.2% | Skills + verb-shaped task references |
| free-form | 9 | 7.7% | Architecture / concept docs |
| ambiguous | 10 | 8.5% | Needs manual review in Phase 0.5 |

## Cross-tab: target subtype × package

| Package | procedural | tabular | free-form | ambiguous | total |
|---|---:|---:|---:|---:|---:|
| attune-ai | 10 | 11 | 4 | 0 | 25 |
| attune-help | 15 | 39 | 5 | 5 | 64 |
| attune-author | 1 | 8 | 0 | 1 | 10 |
| attune-rag | 0 | 12 | 0 | 1 | 13 |
| attune-gui | 0 | 2 | 0 | 3 | 5 |

## Current content shape distribution (the "what we have today" view)

| Shape | Count | Notes |
|---|---:|---|
| subtype-aware-tabular | 39 | attune-help only — already declares `subtype: tabular` |
| tabular-classes-and-functions | 30 | Other packages — fully populated tables |
| subtype-aware-procedural | 15 | attune-help only — already declares `subtype: procedural` |
| tabular-with-classes | 12 | Tables populated for classes only |
| subtype-aware-unknown | 10 | attune-help refs with no subtype declared yet |
| tabular-with-functions | 6 | Tables populated for functions only |
| mostly-empty | 3 | Headers present but tables effectively empty |
| non-tabular | 2 | No tabular sections at all |

## Key observations

1. **attune-help is the ceiling.** 64 of 117 references (55% of
   corpus) already declare a `subtype:` in frontmatter — these
   are the hand-curated standard the meta-template needs to
   approach for the other 4 packages.

2. **Other packages haven't migrated.** attune-ai (25), attune-rag
   (13), attune-author (10), attune-gui (5) — none of the 53
   files outside attune-help carry subtype frontmatter yet. All
   use the current tabular meta-template.

3. **attune-rag is the most tabular-pure.** 12 of 13 references
   are tabular (code-API heavy package); subtype split benefits
   attune-rag the least.

4. **attune-gui has the highest ambiguous rate.** 3 of 5 refs
   ambiguous — small package, may be early-stage, worth manual
   review when sample work begins.

5. **The 10 attune-help "subtype-aware-unknown" entries**
   suggest the subtype frontmatter rollout in attune-help is
   itself incomplete — Phase 0.5 may want to flag these as a
   subset of the manual-review backlog.

## Heuristic limitations (Phase 0.5 manual review will refine)

- The "target subtype" column for non-attune-help packages uses
  keyword pattern matching on feature names. False positives
  possible — e.g. a feature named "ops-dashboard-publish" would
  match "publish" (procedural) before "ops-dashboard" (free-form).
- The "tabular-with-X" classification counts table rows but
  doesn't assess content quality. A reference with 3 trivial
  class rows would still be "tabular-with-classes."
- Ambiguous entries lean on content shape, not feature semantics.

## Phase 0.2 conclusion

**Premise sanity-check: confirmed.** The spec proposes 3 subtypes
to handle the ~30% of corpus the current tabular template
underserves. The data validates this is real surface, not noise.
Phase 0.3+ (hand-crafted sample rendering + qualitative comparison)
can proceed when editorial time is available.

## Files

- `reference-inventory.csv` — per-file row (package, feature,
  current_content_shape, lines, target_subtype). 117 rows.
- `inventory-summary.md` — this document.
