# Round table — context management features (q-context-mgmt-features-001)

**Convened:** 2026-08-18 · 1 round, halted on convergence (D3) ·
3/3 seats (Claude, Codex, Antigravity) ·
**Chair-promoted** board messages 2, 3, 4, 5.
Full transcript (machine-local, moderator's development data):
`~/.attune/reports/roundtable/q-context-mgmt-features-001.md`.

## Question

Opinion on attune-ai's current context management features
(post-retirement state: the live AST-budget trio with four workflow
consumers; compaction stack retired per
`docs/specs/context-compaction-retirement`).

## Consensus (3/3)

- The retirement was correct; the surviving trio (skeleton
  generator, budget allocator, `fit_source` ladder) is the right
  shape: small, deterministic, consumer-driven.
- Next move is **measurement + new consumers, not new
  infrastructure**. Candidate consumers named by every seat:
  `deep_review`, `refactor_plan`, `bug_predict`,
  `doc_audit`/`code_quality`. Every migration must carry a QUALITY
  receipt (before/after output comparison) — never just
  "consumer wired".
- The chars÷4 budgets (1250/1000/750) are unratified folklore;
  replace with evidence (ladder-outcome telemetry, truncation
  frequency, a stage-level A/B).
- **Redis AST cache: keep deferred** — ast.parse is ~1–2 ms at
  repo-typical file sizes; a cache adds invalidation + ops
  complexity for microsecond gains. Revisit only at
  tens-of-thousands-of-files scale.
- **Provider-adapter inflation: keep dead** absent a concrete
  provider-named failure; burden of proof on resurrection.

## The one real split — cross-file context timing

All seats agree cross-file allocation is the only substantial
roadmap item; the split is WHEN: Antigravity would build a
"neighborhood interface context" packer now (target file full,
imported modules skeleton-only); Codex requires relevance-ranking
design + behavioral evaluation first; the Claude seat arms it only
once a second multi-file consumer exists.

**Moderator's read (presented to chair):** adopt consumer-first +
measurement-first; treat cross-file packing as design-gated
(relevance-first) with the second-consumer trigger as the arming
condition.

## Shared blind-spot warning (2/3 independently)

Prompt-quality regressions have no drift guard — token/latency
telemetry alone can optimize compression mechanics while silently
shipping worse tests/docs/findings. Consumer expansion needs
task-level behavioral benchmarks.

## Member-originated items (R9, triaged to chair)

- [claude] Is any current consumer budget-STARVED at the ported
  limits? (evidence probe)
- [codex] Which downstream task has the clearest
  context-attributable quality failures, and what behavioral
  benchmark exposes them?
- [antigravity] Multi-file ContextPacker as a first-class
  primitive, or leave multi-file budgeting ad-hoc per workflow?
