# Design: Single-Source Help + Docs

**Status:** design approved
**Created:** 2026-06-21
**Builds on:** [requirements.md](requirements.md),
[decisions.md](decisions.md)

---

## Key insight (grounded in spec-engine)

The 11 `.help` kinds and the 4 `docs/` feature pages are not 11+4
independent documents — they are **projections of one smaller
canonical content set**. Evidence from the live spec-engine corpus:

| `.help` kind | Section headings (actual) | Canonical source |
|---|---|---|
| concept | Mental model, Core data structures, Execution entry points, State lifecycle, Presentation layer | Overview + Concepts |
| reference | Classes, Functions, Source files, Tags | Reference (code-derived) |
| task | Prerequisites, <procedures>, Verify success | Tasks |
| quickstart | Step 1–4 | Quickstart |
| comparison | Context, Feature comparison, Tradeoffs, Decision guide | Comparison |
| error | Error signatures, Origins, Diagnose | Failure modes |
| troubleshooting | Symptom table, Diagnosis, Common fixes | Failure modes |
| warning | What to watch, Risk areas, How to avoid | Failure modes |
| faq | Q&A pairs | FAQ |
| note | How packages fit, API boundaries | Notes + Concepts |
| tip | (sparse) | Notes & tips |

| `docs/` page | Section headings (actual) | Canonical source |
|---|---|---|
| how-to/spec-engine | Quick start, Core API, Integration patterns, See also | Quickstart + Tasks + Reference |
| tutorials/spec-engine | Prerequisites, Step 1–6, Complete script, What you learned | Tutorial (a guided path over Tasks) |
| architecture/spec-engine | Purpose, Key classes, Data flow, Design decisions, Extension points | Overview + Concepts + Design & extension |
| reference/spec-engine | Description, Usage, Options, Subcommands, Exit codes | CLI reference (code-derived) |

So the master file needs ~10 canonical sections; everything else is a
**slice + format** of those.

---

## Master-file schema

One file per feature. YAML frontmatter + a fixed set of named H2
sections. The "structure" is a convention over markdown (D2).

```markdown
---
feature: spec-engine
summary: Spec-driven development with approval loops
tags: [spec, planning]
source_globs: [src/attune/spec/**, src/attune/pipeline/**]
cli: { command: spec }        # present only for CLI-backed features
nav:
  help: spec-engine
  mkdocs:
    how-to: how-to/spec-engine
    tutorial: tutorials/spec-engine
    architecture: architecture/spec-engine
    reference: reference/spec-engine
---

## Overview            # mental model; when this feature matters
## Concepts            # data model, lifecycle, package boundaries
## Quickstart          # minimal end-to-end path (numbered steps)
## Tasks               # procedures — each: goal / steps / verify
## Reference           # API (code-derived) + CLI options for cli features
## Comparison          # vs alternatives / layer tradeoffs
## Failure modes       # each: symptom / cause / fix / severity
## FAQ seeds           # author-curated channel-4 input only (D6)
## Notes & tips        # supplementary callouts
## Design & extension  # design decisions, extension points
```

A feature may omit sections it doesn't need (e.g. no `cli:` block →
no CLI reference). The projector treats a missing section as "skip the
outputs that depend on it," never as an error.

---

## Projection map (section → outputs)

| Canonical section | → `.help` kinds | → `docs/` pages |
|---|---|---|
| Overview | concept, note | architecture#purpose, how-to intro |
| Concepts | concept, note | architecture#key-classes, #data-flow |
| Quickstart | quickstart | how-to#quick-start, tutorial seed |
| Tasks | task | how-to#core-api, tutorial steps |
| Reference | reference | reference/* (CLI), architecture#key-classes |
| Comparison | comparison | (optional guide) |
| Failure modes | error, troubleshooting, warning | how-to#integration callouts |
| FAQ seeds | faq (via FAQ Generator, not direct) | global FAQ page (via Generator) |
| Notes & tips | note, tip | inline callouts |
| Design & extension | note | architecture#design-decisions, #extension-points |

Each output target declares the sections it consumes; the projector
renders only those. This table is the contract the projector
implements.

**FAQ exception (D6):** the `FAQ seeds` section is the one section the
projector does **not** render verbatim. Its entries are author-curated
channel-4 input to the FAQ Generator, which merges them with the three
dynamic channels (unmatched queries, telemetry error-frequency, GitHub
issues), deduplicates, and frequency-ranks before producing the
`.help/faq` output and the global FAQ page. The master file feeds the
FAQ; it does not author it.

---

## Open design decisions — recommendations

### DD1 — Projector technology

**Recommend: a new dedicated projector module inside attune-author**,
reusing the existing pieces rather than extending the LLM generator.
Reuse: `_extract_source_info` (AST → classes/functions/signatures) for
the Reference section; the frontmatter/staleness machinery; the
`fact_check` package (incl. this session's `import_repair`). The
generator's LLM polish path is NOT reused for canon (D3). A clean
module keeps the deterministic projector free of the LLM-generation
code that produced the fiction.

### DD2 — Help read-path

**Recommend: project to `.help` files (no consumer change) for the
pilot.** The help system (`help_lookup`, `coach`, MCP) keeps reading
`.help/templates/<feature>/*.md` exactly as today — the projector just
becomes their producer instead of the LLM generator. Satisfies R4 with
zero consumer risk. Reading the master file directly is a possible
later optimization, out of pilot scope.

### DD3 — Master-file location

**Recommend: a new source tree `content/features/<feature>.md`**,
separate from both render targets. Rationale: `docs/` is now an
*output* (feature pages are generated), so the source can't live
there without a source/output collision. Cross-cutting hand-authored
docs (getting-started, philosophy, guides) stay in `docs/` untouched —
only the per-feature pages (how-to/tutorial/architecture/reference)
become projected.

### DD4 — Grounding + fact-check (R3)

Run on the master file before projection:

- **Static fact-check** — `python_refs` (imports/signatures),
  `cli_refs` (flags), `md_links` (cross-refs), reusing
  `import_repair` to auto-correct mis-pathed imports.
- **RAG grounding** — for prose claims about behavior, query
  `rag_knowledge_query` against the codebase and surface
  unsupported claims as a verification report (warn for the pilot;
  promote to a CI gate post-pilot).

### DD5 — Defuse the regen-overwrite trap (R8)

A migrated feature must be **removed from the LLM generator's
feature manifest** (or flagged `source: projected`) so the weekly
regen neither generates nor overwrites it. The projector owns it
instead. This is checked per-feature at migration time.

---

## Pilot plan (spec-engine, then models)

1. Author `content/features/spec-engine.md` by **consolidating the
   existing hand-authored `docs/` pages** (how-to, tutorial,
   architecture, reference) + the good parts of the `.help` corpus
   into the canonical sections. No new prose invented — this is a
   merge, preserving the hand-authored feel.
2. Build the projector module + the projection map (above).
3. Render → `.help/templates/spec-engine/*` + the 4 `docs/` pages.
4. Run fact-check + RAG grounding; resolve findings.
5. Verify the help system serves the projected `.help` unchanged;
   verify `mkdocs build` is clean.
6. Remove spec-engine from the LLM generator manifest (DD5).
7. Repeat for `models` (exercises the `cli:` block + `cli_refs`).
8. Write the rollout playbook (R7) from what steps 1–7 taught.

---

## Still to prototype (resolve during pilot, not before)

- Exact slicing rules where one section feeds differently-formatted
  outputs (e.g. a `Tasks` section → terse `.help/task` vs narrative
  `how-to#core-api`). Likely a light per-output template.
- Whether `Quickstart` is authored or derived from the first Task.
- Whether `tutorial` (a guided narrative) can be projected at all, or
  must stay hand-authored per-feature (it may be the one kind that
  resists pure projection).
- mkdocs nav wiring for projected pages.
