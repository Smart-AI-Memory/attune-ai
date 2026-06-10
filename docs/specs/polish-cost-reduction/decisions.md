# Polish-Cost Reduction — Decisions

**Status:** approved (2026-06-10)

## D1 — Two complementary levers, both wanted (ratified 2026-06-10)

Patrick's directive: "only polish files that require changing …
only files with stale or missing content … minimize API calls to
polish documentation whether it be in .help or docs directories."
Patrick proposed the cadence half ("polish only as part of
release-prep") and ratified both levers explicitly.

- **Lever 1 (cadence — cuts WHEN we pay):** no polish in pre-commit
  or unattended schedules; release-prep is the polish moment.
  Shipped 2026-06-10: `scripts/regenerate_help_templates.py` is now
  check-only (auto-regen path deleted); `help-freshness.yml` is
  report-only unless dispatched with `regen=true`.
- **Lever 2 (incrementality — cuts HOW MUCH we pay):** per-kind
  scaffold-hash skip in attune-author. Design in D3.

## D2 — Accepted trade-off: mid-cycle staleness

Between releases the in-repo `.help` corpus (feeding
`rag_knowledge_query` and attune-ai.dev) runs stale. Accepted: the
freshness surfaces already only warn, and feature-doc staleness
mid-cycle is low-harm. If the site ever deploys mid-cycle, treat
"site publish" as a second polish trigger using the same dispatch.

## D3 — Lever 2 design (attune-author)

Investigated 2026-06-10 (generator.py / polish.py / staleness.py):

- Phase 1 of `generate_feature_templates` (`prepare_polish_phase`)
  already renders the per-kind deterministic scaffold BEFORE any LLM
  call. Insertion point: after rendering kind K's scaffold, compute
  `scaffold_hash` = SHA-256 of the scaffold with volatile
  frontmatter fields (`generated_at`) normalized. Compare to a
  `scaffold_hash` stored in the existing on-disk file's frontmatter
  (help templates) / HTML footer (project docs). Equal → skip the
  kind entirely: no polish call, no write, file keeps its polished
  content and timestamps. Different or missing file → polish as
  today (the existing polish cache may still hit).
- Write `scaffold_hash: <sha>` into frontmatter on every generate so
  the next run can compare. Backward-compatible: files without the
  field are treated as stale once, then carry it.
- Rationale for scaffold-hash over cache-key surgery: the polish
  cache key correctly includes `source_summary` (it IS part of the
  LLM input — changing it can change output). The waste isn't a
  wrong cache key; it's polishing kinds whose CONTENT didn't change.
  "Scaffold unchanged = content not stale = skip" implements
  Patrick's directive directly.
- Feature-level staleness (`check_staleness` reading concept.md's
  `source_hash`) stays as the cheap outer filter; per-kind skip is
  the inner filter.

## D4 — Override mechanism

- Short-term: `status: manual` (existing) on hand-fixed templates;
  applied to `.help/templates/plugin/quickstart.md` 2026-06-10 (its
  regen-produced body instructed users to import internal hook
  modules; hand-rewritten, must not be overwritten).
- The fact-check `skip` config (`[tool.attune-author.fact-check]` in
  pyproject) suppresses findings only — it is NOT content
  preservation; don't confuse the two.
- Durable fix: extend ground-truth injection (the seam exists,
  generator.py `_maybe_polish`) so the generator stops producing the
  fiction classes that required hand-fixes (internal-module imports,
  wrong counts). Tracked as lever-2 follow-up.

## D5 — Release-prep wiring

The release flow (and the /release-execute skill) gains a step:
`attune-author regenerate --help-dir .help --project-root .`
(stale-only), review output (show-before-stage rule), ship as a
docs PR alongside the release-prep PR. With lever 2 landed this
costs only genuinely-changed kinds.
