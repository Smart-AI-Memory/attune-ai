# Decisions: Single-Source Help + Docs

Decisions recorded during the 2026-06-21 requirements
interview. Each is the agreed answer to a fork; rationale is
captured so later phases don't relitigate it.

---

## D1 — Direction: single-source, render to both

**Decided:** Author content once; render to BOTH the in-tool
`.help` corpus and the mkdocs site.

**Why:** The two corpora serve different consumers (in-CLI
help vs published site) but document the same features.
Single-sourcing ends the duplication while keeping both
consumers. Rejected: docs-canonical-only (loses the 11-kind
in-tool structure), keep-both-raise-quality (duplication
remains), one-off merges (doesn't fix the architecture).

---

## D2 — Source format: hand-authored structured markdown

**Decided:** One "master file" per feature — YAML frontmatter
plus a fixed set of named markdown sections.

**Why:** Patrick's bar is the hand-authored feel of today's
`docs/` (which the agent authored over time, not via
attune-author). Markdown keeps authoring ergonomic and
git-diffable; the "structure" is a convention over markdown,
not a new serialization. Rejected: YAML/TOML data files
(awkward for long-form prose).

---

## D3 — attune-author repurposed as projector + validator

**Decided:** attune-author's role shifts from *LLM
content-generator* to *deterministic projector + validator*.
It renders the master file into outputs and runs
fact-check/grounding; it does not author or rewrite
canonical prose.

**Why:** LLM authoring of canon is exactly what produced the
fiction (bare-module imports, hallucinated cross-refs).
Removing the LLM from the canonical path preserves the
hand-authored feel and kills the fiction at its root. The LLM
remains an optional drafting assist (D-linked to R9).

---

## D4 — Pilot-first

**Decided:** Prove the full chain on two features before
rollout: `spec-engine` and `models`.

**Why:** ~270 files + a repurposed engine + a new projector +
a help read-path change is too large to land blind.
`spec-engine` (Python-API shape, just worked this session)
and `models` (CLI-reference/tabular shape) give contrasting
content to stress the projector. The rollout playbook (R7) is
written from what the pilot teaches.

---

## D5 — RAG-grounding is a quality mechanism, not a pilot feature

**Decided:** "RAG grounding" means master-file claims are
RAG-grounded/cited against the codebase (via
`rag_knowledge_query`) and fact-checked — so hand-authored
content stays verifiably true to the code. It is NOT a
synonym for picking the `rag-grounding` feature as a pilot.

**Why:** Patrick clarified the intent is verifiable content
quality. This becomes R3; the second pilot feature is chosen
independently for content-shape coverage (`models`).
