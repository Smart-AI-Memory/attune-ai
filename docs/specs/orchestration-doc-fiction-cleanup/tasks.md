# Tasks — orchestration-doc-fiction-cleanup

**Status:** complete (2026-06-26) — shipped in PR #1107 (doc cleanup for the #1096 DynamicTeam/MetaOrchestrator removal); D7 follow-ups tracked separately (#1108, #1111)

Counts (`dyn` = DynamicTeam/SDKAgent refs, `meta` = MetaOrchestrator
refs, `surv` = surviving-symbol refs) verified against `origin/main`
096b228f3.

---

## Per-file decision table

| File | dyn | meta | surv | Decision |
|------|----|----|----|----------|
| docs/ORCHESTRATION_API.md | 24 | 14 | 53 | **Rewrite+excise** — DynamicTeam→AgentTeam; delete MetaOrchestrator API sections; keep 53 surviving refs |
| docs/ORCHESTRATION_USER_GUIDE.md | 1 | 17 | 35 | **Excise+fix** — strip MetaOrchestrator narrative; repoint 1 DynamicTeam ref; keep templates/strategies |
| docs/ARCHITECTURE.md | 6 | 5 | 1 | **Rewrite+excise** |
| docs/reference/API_REFERENCE.md | 3 | 6 | 13 | **Rewrite+excise** |
| docs/architecture/orchestration.md | 6 | 4 | 13 | **Rewrite+excise** |
| docs/how-to/orchestration.md | 2 | 3 | 16 | **Rewrite+excise** |
| docs/reference/orchestration.md | 2 | 1 | 6 | **Rewrite+excise** |
| docs/tutorials/examples/multi-agent-team-coordination.md | 18 | 1 | 0 | **Rewrite** to AgentTeam (OQ1: keep as the worked example) |
| docs/tutorials/META_ORCHESTRATION_TUTORIAL.md | 0 | 11 | 21 | **Delete** (OQ2: dead premise) + nav prune |
| docs/blog/interactive-agent-creation-tutorial.md | 0 | 12 | 0 | **Delete** (pure dead feature) + nav prune |
| docs/integration/claude-code-integration.md | 0 | 10 | 0 | **Excise** MetaOrchestrator sections (keep the doc) |
| docs/getting-started/choose-your-path.md | 0 | 3 | 0 | **Excise** 3 MetaOrchestrator refs (onboarding doc stays) |
| docs/BLOG_COVERAGE_AS_BUG_FINDER.md | 0 | 1 | 0 | **Excise** 1 ref |
| docs/pitch/TECHNICAL_BRIEF.md | 0 | 1 | 0 | **Excise** 1 dead claim |
| docs/COVERAGE_BUG_LOG.md | 1 | 1 | 0 | **Leave** (append-only history) |
| plugin/help/generated/**/orchestration.md (10) | 1–4 | 2–5 | 0–12 | **Regenerate** from source (D4) — never hand-edit |
| plugin/help/generated/concepts/meta-orchestration.md | — | — | — | **Remove at source** (orphan; no source template dir) |

---

## Phased execution

### Phase 0 — open questions RESOLVED (2026-06-26)

- OQ1 → rewrite `multi-agent-team-coordination.md` to AgentTeam.
- OQ2 → delete `META_ORCHESTRATION_TUTORIAL.md` whole, salvaging its
  template section into the canonical templates reference only if that
  maintains/improves quality (no MetaOrchestrator framing).
- OQ3 → prune nav/cross-links to deleted files in the execution PR.
  See `decisions.md` for full text.

### Phase 1 — rewrite DynamicTeam → AgentTeam

- Apply the D1 canonical mapping to the 8 "rewrite/rewrite+excise" docs.
- Every new/edited code fence: verify it imports against `origin/main`
  (`PYTHONPATH=src python -c "<the import line>"`). No fence ships
  unverified (G3).

### Phase 2 — delete dead-feature docs + prune nav

- Delete the two MetaOrchestrator tutorials.
- Grep mkdocs nav (`mkdocs.yml`) + `plugin/help/generated/cross_links.json`
  + any `[...](.../META_ORCHESTRATION_TUTORIAL...)` link for references
  to deleted files; prune so `mkdocs build` stays green.

### Phase 3 — excise scattered MetaOrchestrator refs

- Remove MetaOrchestrator content from the surviving docs
  (integration, getting-started, blog-coverage, pitch). Leave
  surrounding prose coherent — excise, don't leave dangling headers.

### Phase 4 — help layer (single-source)

- Fix `content/features/orchestration.md` (the projector source) +
  `.help/templates/orchestration/*` so no dead symbol survives.
- Remove the orphaned `meta-orchestration` generated concept at the
  manifest/source layer (`.help/features.yaml`) so it stops
  regenerating.
- Regenerate via `scripts/generate_all.py`; commit the resulting
  `plugin/help/generated/` diff as a build product, reviewed but not
  hand-authored.

### Phase 5 — verify + ship

- Acceptance grep returns zero dead symbols outside history (G1).
- Import spot-check of remaining fences passes (G3).
- `mkdocs build` green; help bundle regenerated cleanly.
- One PR, 8 required checks green. Docs-only.

---

## Risks

- **R1 (medium).** Section surgery on the big mixed files
  (ORCHESTRATION_API.md, USER_GUIDE.md) can accidentally drop surviving
  content. Mitigation: diff surviving-symbol counts before/after; they
  must not drop.
- **R2 (low).** Deleting tutorials orphans nav/cross-links → `mkdocs
  build` fail (the known "admin-merge a deletion without checking the
  build docs check" trap). Mitigation: Phase 2 nav sweep + local
  `mkdocs build` before PR.
- **R3 (low).** Hand-editing `plugin/help/generated/` instead of the
  source would be reverted by the next regen. Mitigation: D4 — source
  only.
