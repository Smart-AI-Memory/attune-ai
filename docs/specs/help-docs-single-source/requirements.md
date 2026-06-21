# Requirements: Single-Source Help + Docs

**Status:** requirements (awaiting approval)
**Created:** 2026-06-21
**Owner:** Patrick + agent

---

## Context

Two documentation corpora exist today, fed by the same
attune-author generator with different templates:

- **`.help/templates/<feature>/`** — 25 features × 11 kinds
  (concept, task, reference, quickstart, comparison, error,
  faq, note, tip, troubleshooting, warning) ≈ 270 files,
  LLM-generated. Consumed in-tool by the help system
  (`help_lookup`, `coach`, MCP help tools). One orphan:
  `resilience` (3-kind leftover from the deprecated 3-depth
  generator).
- **`docs/`** — the mkdocs site. Mostly hand-authored
  (getting-started, guides, philosophy, reference, redis,
  rag, …) PLUS attune-author "project-doc kinds"
  (`docs/how-to/`, `docs/tutorials/`, `docs/architecture/`).

The hand-authored `docs/` content was written by the agent
over time (not via attune-author) and has a markedly superior
"hand-authored feel." The LLM-generated `.help` corpus is
lower quality and prone to systematic fiction — e.g. the
bare-module import bug fixed on 2026-06-21
([attune-author#76], [attune-ai#956]).

---

## Problem

- **Duplication.** The same feature is documented twice, in
  two trees, in two formats — double the maintenance.
- **Quality gap.** The generated `.help` corpus lacks the
  hand-authored quality of `docs/`.
- **Fiction risk.** LLM generation of canonical content
  invents imports, signatures, and cross-refs that ship to
  users until a fact-check catches them.

---

## Goals

1. **One canonical source per feature** — a hand-authored
   "master file" — from which both the in-tool `.help` corpus
   and the mkdocs site are produced.
2. **Preserve the hand-authored feel.** The master file is
   hand-authored; the render step never rewrites prose.
3. **Eliminate duplication.** Author once; render to both.
4. **Keep content verifiably true to the code** via fact-check
   plus RAG-grounding against the codebase.
5. **No consumer regression** — the help system keeps working.

---

## Non-Goals

- Re-authoring all 25 features in one pass (pilot-first).
- Changing the mkdocs theme or the in-tool help UX.
- Removing the LLM entirely — it stays as an optional
  drafting assist, never the source of canon.

---

## Requirements

- **R1 — Canonical source.** Each feature has one
  hand-authored "master file": structured markdown (YAML
  frontmatter + a fixed set of named sections). Quality bar =
  today's `docs/`. Where good `docs/` content already exists,
  it becomes the source rather than being regenerated.
- **R2 — Deterministic projector.** A render step (repurposed
  attune-author) projects the master file into the 11 `.help`
  kinds and the mkdocs page(s). It slices/renders only — it
  does not author or rewrite prose. No LLM in the canonical
  path.
- **R3 — Grounding + fact-check.** Code-derived claims
  (imports, signatures, CLI flags, cross-refs) are verified
  against source — reusing `import_repair` / `python_refs` /
  `cli_refs` — AND RAG-grounded/cited against the codebase via
  `rag_knowledge_query`, so the hand-authored content stays
  verifiably true.
- **R4 — No consumer regression.** The help system
  (`help_lookup`, `coach`, MCP) keeps serving. Design decides
  whether it reads the projected `.help` output or the master
  source directly.
- **R5 — Section schema + projection map.** A defined set of
  named sections and an explicit map of which output target
  consumes each section.
- **R6 — Pilot.** Two features end-to-end before rollout:
  `spec-engine` and `models` (chosen for contrasting content
  shapes — Python-API vs CLI-reference/tabular). Acceptance:
  both targets render, the help system serves the result, the
  fact-check/grounding is green, and the hand-authored feel is
  preserved.
- **R7 — Rollout plan.** A documented, repeatable migration
  path for the remaining 23 features, including how existing
  `.help`/`docs` content is folded into each master file.
- **R8 — Defuse the regen-overwrite trap.** The weekly
  attune-author LLM regen must not clobber a migrated feature's
  hand-authored master file. Per-feature opt-out / generator
  repurposing is part of the design.
- **R9 — LLM as optional assist.** The LLM may *draft* a
  section for a human to accept/edit, but never writes
  canonical content directly.

---

## Pilot scope

- **Pilot features:** `spec-engine`, `models`.
- **End-to-end chain proven:** master file → projector →
  `.help` kinds + mkdocs page → help system serves →
  fact-check/grounding green.
- **Exit criterion:** the chain is repeatable and the rollout
  playbook (R7) is written from what the pilot taught.

---

## Open design questions (deferred to design phase)

- Exact section schema and the section→output projection map
  (how 11 `.help` kinds + mkdocs sections derive from one
  file).
- Projector technology: extend attune-author's existing
  generator vs a new dedicated projector module.
- Help read-path: does the help system read projected `.help`
  files (no consumer change) or the master source directly?
- mkdocs nav integration for projected pages.
- How RAG-grounding surfaces (inline citations, a
  verification report, or a CI gate).
- Master-file storage location (under `docs/`, a new
  `content/` tree, or alongside `.help/`).

---

## Risks

- **Regen-overwrite (lesson-driven).** Adding/keeping features
  in the existing generator's manifest triggers a regen that
  overwrites hand-authored content. R8 must be designed before
  any feature is migrated.
- **Scope drift (lesson-driven).** The 11-kind ↔ mkdocs
  mapping may not be 1:1 in practice; grep/verify the real
  content shapes per feature before committing the schema.
- **Two consumers.** Any read-path change must be validated
  against the in-tool help system, not just the mkdocs build.

---

## References

- [attune-author#76] — generator import-repair (merged)
- [attune-ai#956] — spec-engine doc cleanup + drift guard
- `docs/specs/doc-fiction-cleanup/` — prior, distinct surface
- `.claude/lessons.md` — orphan `.help` dirs / regen-overwrite;
  spec-scope-drifts-from-code

[attune-author#76]: https://github.com/Smart-AI-Memory/attune-author/pull/76
[attune-ai#956]: https://github.com/Smart-AI-Memory/attune-ai/pull/956
