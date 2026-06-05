# Decisions: attune-verify — Generation Fact-Checker

Design decisions for [attune-verify](requirements.md) beyond the
Phase-1 requirements and Phase-2 design. Newest first.

---

## D1 (2026-06-04): Deterministic resolution is authoritative for entity existence; the semantic judge must be cross-checked against it

**Status:** decided — folds into a `design.md` Phase-2 revision and a
`tasks.md` item.

### Evidence — dogfood, 2026-06-04

Regenerated six stale attune-ai help features
(`cli`, `release-prep`, `memory`, `agents`, `models`,
`configuration`) through attune-author's LLM polish pass, then judged
each `reference.md` with attune-rag's
`FaithfulnessJudge.score(query, answer, passages)` against the feature
source — the exact rag-adapter path `design.md` specs. Every flagged
"unsupported" claim was then cross-checked against the **complete,
untruncated** source tree (grep for `def`/`class`):

| feature | judge score | flagged | real-in-source | genuine hallucinations |
|---------|-------------|---------|----------------|------------------------|
| cli | 0.927 | 7 | 7 | 0 |
| release-prep | 1.000 | 0 | 0 | 0 |
| memory | 1.000 | 0 | 0 | 0 (51 source files dropped from context) |
| agents | 1.000 | 0 | 0 | 0 |
| models | 1.000 | 0 | 0 | 0 |
| configuration | 0.975 | 2 | 2 | 0 |

**All 9 flagged claims were false positives** — real symbols the judge
could not see because they fell outside its `passages` window.
attune-author's polish was actually 100% faithful on all six features.
The dogfood used attune-rag **0.1.23 unmodified**; no rag change was
needed to consume `FaithfulnessJudge`.

### The finding

The semantic judge's accuracy on **entity-existence** claims is
bounded by the completeness of `passages` — and that bound breaks
exactly where it matters most. High-file-count features (`memory` = 75
source files) overflow any context window, so the judge confidently
reports real symbols as "unsupported." A naive **union** of
deterministic and semantic findings would surface every one of these
as a hallucination: the tool cries wolf precisely on the largest, most
valuable targets.

The deterministic checkers have **no such bound**.
`importlib.find_spec`, AST resolution, captured `--help`, and
filesystem stats check against the **real environment**, not a window.
A symbol either resolves or it does not.

### Decision

**Deterministic resolution is authoritative for "does this named
entity exist?" The semantic layer is operationally barred from being
the thing that flags an entity as fake.** Two parts:

1. **Division of labor (reaffirms `requirements.md`, now
   load-bearing).** The semantic layer judges only the meaning-level
   class the deterministic checkers cannot — insecure examples,
   missing security notes, ungrounded claims, semantic mismatch.
   `requirements.md` already scopes it this way *in intent*; today's
   data shows the boundary must be **enforced operationally**, because
   `FaithfulnessJudge` does not respect it on its own (it flagged
   entity-existence claims in every run that had any).

2. **Cross-check suppression (the enforcement mechanism).** Any
   semantic finding whose evidence names an entity that the
   deterministic resolvers **can** resolve is **suppressed as a
   context-truncation false positive** — not surfaced. This is what
   made today's "0 hallucinations" result trustworthy.

### Implementation — carries to design.md / tasks.md

- **v1 (pragmatic):** run both layers, then post-filter — drop any
  semantic finding whose named entity resolves deterministically.
  Cheap; ~the grep-rescue prototyped today.
- **v2 (by construction):** scope the judge prompt to non-entity
  claims, and/or classify each semantic claim (entity-existence vs
  meaning) and route entity claims to the deterministic resolver.
  Eliminates the false-positive class upstream rather than filtering
  it after.
- **`design.md` gap to fix:** the current design presents the
  deterministic and semantic layers as **parallel and independent**
  ("a failure in one does not abort the others" — union semantics).
  This decision makes them **compose**: the deterministic layer
  disciplines the semantic one. The "Public API" and data-model
  sections need a Phase-2 revision describing the suppression step.

### Side findings worth recording

- Three features (`release-prep`, `agents`, `models`) judged with
  **0 supported and 0 flagged** — the judge found no checkable
  structural claims in their `reference.md`. That is a **content**
  signal (thin or non-structural reference docs), not a faithfulness
  signal; "score 1.0" there is degenerate. A real verify run should
  report "0 verifiable entities" distinctly from "all entities
  verified."
- The composition is attune-verify's value-add, not new judging.
  rag grounds and judges; attune-verify brackets the output by making
  deterministic existence authoritative over the judge.

### Status reconciliation — flagged, not resolved here

`design.md` and `tasks.md` headers read "Phase 2/3, awaiting review"
(2026-06-02), but `~/attune-verify` already has `src/`, `tests/`, and
the author-#351 regression fixture committed. Implementation has
started; the spec status should be reconciled with reality (per the
`spec-status-self-truthing` concern). Out of scope for this decision —
noted for a status pass.
