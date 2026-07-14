# Tasks — empathy-doc-fiction-cleanup

**Status:** complete (2026-06-26) — executed in PR #1109 (5 deletes + 16 repoints, docs-only); D7 EmpathyLLMExecutor correction shipped in PR #1115

Signals verified against `origin/main`: `el` = "Empathy Level" refs,
`hc` = clinical/healthcare keyword refs, `comp` = live companion symbols
imported alongside `EmpathyOS`.

---

## Per-file decision table

| File | el | hc | Decision |
|------|----|----|----------|
| examples/sbar-clinical-handoff.md | 2 | 146 | **Delete** (clinical premise) + nav prune |
| tutorials/examples/sbar-clinical-handoff.md | 1 | 146 | **Delete** (dup, clinical premise) + nav prune |
| pitch/HEALTHCARE_ONE_PAGER.md | 0 | 46 | **Delete** (healthcare-feature pitch, no such feature) |
| examples/adaptive-learning-system.md | 12 | 23 | **Delete** (empathy-level premise) + nav prune |
| tutorials/examples/adaptive-learning-system.md | 11 | 23 | **Delete** (dup) + nav prune |
| reference/llm-toolkit.md | 0 | 16 | **Repoint/excise** — keep EmpathyLLM/PIIScrubber/SecretsDetector/AuditLogger; drop EmpathyOS, encrypt_phi, HIPAA/GDPR/SOC2 claims (D3). (EmpathyLLMExecutor was listed here as dead — it is NOT; see D7. Moot: llm-toolkit never documented it.) |
| reference/glossary.md | 4 | 5 | **Repoint/excise** — drop EmpathyOS; remove "Empathy Level" glossary entries |
| reference/multi-agent.md | 0 | 0 | **Repoint** — drop EmpathyOS, keep PatternLibrary/Pattern |
| reference/pattern-library.md | 0 | 0 | **Repoint** |
| reference/persistence.md | 2 | 0 | **Repoint/excise** empathy-level mentions |
| how-to/practical-patterns.md | 0 | 1 | **Repoint** — keep get_redis_memory/AccessTier/StagedPattern |
| how-to/unified-memory-system.md | 0 | 6 | **Repoint** (real memory ref) |
| how-to/multi-agent-coordination.md | 0 | 0 | **Repoint** |
| how-to/prerequisites.md | 0 | 1 | **Repoint** |
| how-to/project-analysis-and-metrics.md | 0 | 0 | **Repoint** (workflow-runner → direct workflow class) |
| how-to/smart-router.md | 0 | 3 | **Repoint** |
| getting-started/redis-setup.md | 0 | 1 | **Repoint** — keep get_redis_memory |
| examples/multi-agent-team-coordination.md | 2 | 0 | **Repoint** |
| examples/simple-chatbot.md | 0 | 1 | **Repoint** |
| tutorials/examples/simple-chatbot.md | 0 | 1 | **Repoint** (dup) |
| pitch/TECHNICAL_BRIEF.md | 0 | 1 | **Repoint** (single fence) |

5 delete · 16 repoint/excise.

---

## Phased execution

### Phase 1 — deletes + nav prune

- `git rm` the 5 delete files. Grep `mkdocs.yml` +
  `plugin/help/generated/cross_links.json` + markdown links for each;
  prune so `mkdocs build --strict` stays green.

### Phase 2 — repoint EmpathyOS → live API

- Apply D2 per file (workflow-runner → `attune.workflows`; memory →
  companions; LLM → `attune.llm.EmpathyLLM`). Excise empathy-level
  framing (glossary, persistence) and llm-toolkit's dead/compliance
  fiction (D3).
- Every edited/remaining fence import-verified:
  `PYTHONPATH=src python -c "<import>"` exits 0. No fence ships
  unverified.

### Phase 3 — verify + ship

- Acceptance grep (requirements G1/G2) zero outside history.
- Import spot-check of remaining fences.
- `mkdocs build --strict` green.
- One PR, docs-only.

---

## Risks

- **R1.** `docs/examples/*` and `docs/tutorials/examples/*` carry
  near-duplicate files; both copies must be handled (the grep catches
  both). The orchestration PR already cleaned
  `tutorials/examples/multi-agent-team-coordination.md`; the
  `examples/` twin is in this batch.
- **R2.** Deleting nav-linked files breaks `mkdocs build` — Phase 1 nav
  sweep mitigates (the known deletion trap).
- **R3.** Repoint subagents may confabulate EmpathyOS's old method
  names. Mitigation: each fence import-verified; un-repointable fences
  deleted, not faked.
