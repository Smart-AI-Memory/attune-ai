# Spec: Documentation Wiring Audit

> Doc *plumbing* — links, anchors, nav, `features.yaml` ↔ filesystem
> consistency, and mkdocstrings extraction — is currently maintained
> ad-hoc per-PR. There is no systematic check, so breakage accumulates
> silently. This spec proposes an audit + CI gate that keeps the wiring
> honest as a precondition for a strong release.
>
> **Orthogonal to content correctness.** This spec does not touch what
> docs *say* — only how they connect.
**Status:** shipped (2026-07-20, closed per q-briefing-triage-002 A1) — v1 shipped (scripts/audit_docs_wiring.py + anchor check, #518/#523); v1.1 shipped 2026-07-15 (nav + features + mkdocstrings checks, .audit/orphans.yml — see decisions.md Phase 4 entry); Task 10 (See-Also) deferred
**Created:** 2026-05-30
**Owner:** TBD
**Related:**
- [`doc-fiction-cleanup`](../doc-fiction-cleanup/) — fixes content (dead
  imports, fictional APIs). This spec fixes the wiring underneath.
- `docs-completeness-audit` (sibling, in-flight) — ensures every shipped
  feature has a doc. This spec ensures those docs are wired correctly.
- `docs-release-prep` (sibling, in-flight) — orchestrates the strong
  release; this audit is a precondition.

---

## Problem statement

Documentation wiring breaks silently. Concrete symptoms observed in this
session:

1. **Anchor rot in `API_REFERENCE.md`.** Nine inbound and intra-page
   links point at anchors that no longer exist (`#chainexecutor`,
   `#memorygraph`, `#health-check`, `#code-review`,
   `#resilience-patterns`, `#smartrouter`, `#redisshorttermemory`,
   `#longtermemory`, `#models--execution`). `mkdocs build --strict`
   surfaces them only as `INFO` — they do not fail the build, so they
   accumulate.
2. **`features.yaml` drift.** `.help/features.yaml` `doc_paths` had to
   be hand-synced as docs were moved/retired during `doc-fiction-cleanup`.
   No check asserts the listed paths still exist on disk, nor that newly
   added docs are tracked where appropriate.
3. **Rename fallout.** Renaming `PLUGIN_SYSTEM_README.md` →
   `architecture/plugin-system.md` required hand-grep-and-edit of inbound
   links. There is no nav consistency check; nothing flagged the dangling
   references before the build started complaining.
4. **mkdocstrings opacity.** `docs/reference/*.md` files use `:::`
   directives to auto-extract from `src/`. If a symbol is renamed or
   moved, the extraction silently degrades — no test asserts the
   directives still resolve.
5. **Orphan pages.** `mkdocs build --strict` currently reports ~35 docs
   present in `docs/` but missing from nav (blog posts, retired specs,
   alternates). Some are intentional (blog drafts), some are accidental
   (e.g., `reference/wizards.md`). There is no allowlist; the noise hides
   the real orphans.

These are all *wiring* problems. They will recur the moment someone
moves a file, renames a heading, or adds a doc. The release will not
feel strong if a reader's first click is broken.

---

## Scope

**In scope:**
- **Anchor integrity.** Every `[text](file.md#anchor)` (intra- and
  inter-doc) resolves to a real heading anchor.
- **Nav ↔ filesystem.** `mkdocs.yml` `nav` entries all point at real
  files; every `docs/**/*.md` is either in nav, on an explicit
  intentionally-orphan allowlist, or flagged.
- **`.help/features.yaml` ↔ filesystem.** Every `doc_paths` entry exists
  on disk; conversely, docs covering a tracked feature surface should be
  listed (advisory, not strict).
- **mkdocstrings extraction.** Every `:::` directive resolves to a real
  Python symbol at the documented import path.
- **Reciprocal "See Also" links.** Advisory check — if A links to B as
  See Also, surface where B does not link back. Not enforced.
- **Reusable CI check.** Promote the audit to a CI gate that catches
  regressions on every PR.

**Out of scope:**
- Content correctness — owned by `doc-fiction-cleanup` and
  `docs-completeness-audit`.
- Prose quality, style, SEO, external link checking, search relevance.
- Re-architecting nav structure (this audit catches inconsistency; it
  does not redesign the IA).

---

## Acceptance criteria

- `mkdocs build --strict` produces **zero `INFO`-level link warnings**
  (current baseline: ~9 anchor warnings, ~10 excluded-link warnings,
  ~35 orphan-page warnings — all reduced to zero or explicitly allowed).
- `.help/features.yaml` `doc_paths` matches filesystem reality — no
  entry points at a nonexistent file.
- `mkdocs.yml` nav matches filesystem reality — no dangling entries; an
  explicit `intentionally-orphan.txt` allowlist covers the legitimate
  exceptions (e.g., blog drafts).
- Every `:::` mkdocstrings directive in `docs/reference/*.md` resolves
  to a real, importable symbol.
- `scripts/audit_docs_wiring.py` runs in CI on every PR and fails the
  build on any new regression.

---

## Coverage areas

| Area | Status | Notes |
|------|--------|-------|
| **Problem & scope** | addressed | Five concrete wiring failure modes catalogued above. |
| **Approach** | addressed | Write `scripts/audit_docs_wiring.py` producing a markdown report. Iterate on the report (fix or allowlist each finding) until zero. Promote to CI as a hard gate. Anchor + nav + features.yaml first (cheap); mkdocstrings + reciprocal See-Also second. |
| **Acceptance criteria** | addressed | See section above. |
| **Risks** | addressed | (a) Orphan-page detection produces false positives for intentionally-hidden docs (blog drafts, archived). Mitigation: explicit allowlist file checked into the repo, reviewed during audit. (b) CI gate becomes noisy and people start auto-merging past it. Mitigation: keep the audit script's output actionable — name the file, line, and a one-line fix suggestion. (c) Anchor check may flag legitimate cross-repo or external anchors. Mitigation: scope to intra-docs only in v1. |
| **Cross-spec impact** | addressed | Sibling: `docs-completeness-audit` finds missing docs; this spec ensures present docs are wired. Sibling: `docs-release-prep` consumes this as a precondition. Predecessor: `doc-fiction-cleanup` is removing/renaming docs right now — this audit should run *after* that work lands, or it will fight it. |
| **Tradeoffs** | addressed | (a) Treat current `INFO` anchor warnings as build-failing vs. leave them advisory: choosing build-failing because they are real broken links. (b) Reciprocal See-Also check is opinionated and may not match every author's intent: keeping it advisory, not strict. (c) Auditing mkdocstrings resolution requires importing real Python at audit time — slower but catches real breakage. Worth it. |
| **Rollback** | addressed | The audit script is advisory until promoted to CI; promotion is a one-line workflow change that can be reverted. The allowlist file is plain text; entries can be added at will. No data migration, no schema change, no public API change. |

---

## Open questions

These are flagged for Phase 2 (design) — not blockers for Phase 1
approval.

1. **Anchor source-of-truth on rename.** When a doc renames a heading
   (e.g., `#industry-wizards` → `#configdrivenwizard`), do we keep a
   redirect/alias, or accept the break and update all inbound links? A
   redirect file is more forgiving but introduces a second source of
   truth. Pick a policy before designing the anchor check.
2. **Orphan strictness.** `docs/examples/`, `docs/blog/`, and retired
   `docs/specs/` subtrees are full of "orphan" docs by design. Is the
   right policy: (a) entire subtree allowlisted, (b) every file must be
   individually allowlisted, or (c) certain subtrees nav-hidden but
   build-included? Affects the allowlist file format.
3. **mkdocstrings — already in use, scope of audit.** Confirmed in
   session: `docs/reference/core.md`, `empathy-os.md`, `llm-toolkit.md`,
   `multi-agent.md`, `persistence.md` use `:::` directives. Question:
   is auditing the five known files enough for v1, or do we sweep the
   whole `docs/` tree for any `:::` usage?

---

## Phase 2: Design

**Status:** not started

_To be authored after Phase 1 approval. Will cover: audit script
architecture, allowlist file format, CI workflow shape, report format,
mkdocstrings resolution strategy._

---

## Phase 3: Tasks

**Status:** not started

_To be authored after Phase 2 approval._

---

## Phase 4: Implementation

**Status:** not started
