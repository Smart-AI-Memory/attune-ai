# Polish-Cost Reduction — Requirements

**Status:** complete (2026-06-10) — both levers shipped same day: lever 1 in attune-ai #735, lever 2 in attune-author#53 / v0.15.0 (on PyPI), consumer cap bump #736. Open: Q1 (phantom regenerator) and the gated Project-Docs cleanup.

**Lever-2 receipt at scale (2026-06-11):** first full `.help` regen
via subscription (attune-author v0.16.0 wheel, `--auth-mode sub`,
keyless) made 12 polish calls instead of 44 across 4 stale features
(3 changed kinds each; 8 skipped per feature). 15m16s wall clock,
~76 s/call, zero rate-limit events.

## Problem

LLM polish of generated documentation (`.help/templates/` and
generated `docs/`) is paid repeatedly for content that did not
meaningfully change. Cost surfaces observed 2026-06-10:

1. **Per-commit:** the `regenerate-help-templates` pre-commit hook
   (with `ATTUNE_DOCS_AUTOREGEN=1`) ran `attune-author generate
   <feature> --all-kinds` — a full 11-kind LLM re-polish — on every
   commit touching a feature's source glob. A 40-line hook change
   triggered a 3-template re-polish.
2. **Weekly:** `help-freshness.yml` regenerated every stale feature
   (`--all-kinds`) and opened a PR, on a schedule.
3. **Per-run waste:** `--all-kinds` polishes all 11 template kinds per
   feature even when only some kinds' content changed. The 2026-06-10
   4-feature regen made 44 polish calls; ~10 kinds had real drift.
4. **Cache misses by design:** attune-author HAS a polish cache
   (`~/.attune/polish_cache/`, 30-day TTL) but its key includes the
   full per-feature `source_summary` — any source change in the
   feature's glob busts the cache for ALL kinds at once.

## Requirements

- **R1 (lever 1 — cadence):** no LLM polish in the commit path or on
  an unattended schedule. Polish-bearing regeneration runs at
  RELEASE-PREP cadence (and, when needed, deliberate manual dispatch).
  Pre-commit and scheduled CI surfaces are check/report-only.
- **R2 (lever 2 — incrementality):** a regeneration run polishes only
  template kinds whose content is stale or missing. "Stale" = the
  deterministic pre-polish scaffold for that kind differs from the
  scaffold that produced the existing on-disk file. "Missing" = no
  file on disk. Unchanged-scaffold kinds are skipped entirely (no
  polish call, file untouched).
- **R3 (overrides):** hand-fixes to generated templates survive
  regeneration. Short-term: `status: manual` frontmatter (existing
  attune-author mechanism — skips the file unless `--overwrite`).
  Durable: ground-truth injection into the polish prompt so the
  fixes aren't needed (attune-author already has the injection seam).
- **R4 (no silent staleness):** check-only surfaces still WARN
  loudly: pre-commit prints lagging features; the weekly workflow
  publishes a staleness report to the job summary.
- **R5 (scope):** applies to both the `.help/templates/` corpus and
  attune-author-generated project docs (`docs/how-to/`, etc.) — both
  flow through the same generate/polish pipeline.

## Acceptance criteria

- AC1: committing a source change produces zero LLM calls. ✅ lever 1
- AC2: the weekly workflow run produces zero LLM calls unless
  dispatched with `regen=true`. ✅ lever 1
- AC3: regenerating a feature where only 2 of 11 kinds' scaffolds
  changed makes exactly 2 polish calls (cache misses at most 2).
  ✅ lever 2 (attune-author v0.15.0 — skip matrix covered by 13 tests)
- AC4: a `status: manual` template is untouched by regeneration. ✅
  (existing attune-author behavior; applied to plugin/quickstart.md)

## Open questions

- **Q1:** an unidentified process regenerated the 3 core-depth
  templates (`concept`/`reference`/`task` — the in-repo 3-depth
  generator's fingerprint) of the `plugin` feature twice on
  2026-06-10 around commit time, with `ATTUNE_DOCS_AUTOREGEN` unset
  and both pre-commit regen paths ruled out by their `files:`
  filters. Trigger unknown. Recurred a THIRD time ~03:36-03:43 ET the
  same day (caught live: the files were already modified when
  pre-commit stashed them — note the post-restore mtime is the stash
  RESTORE time, not the write time). Prime suspects: the running
  `attune.mcp.server` processes (one per live session, plus leaked
  ones from prior sessions — `pgrep -f attune.mcp.server`) invoking
  the in-repo 3-depth generator via `help_update`/`help_maintain`.
  Diagnostic next occurrence: `pgrep -f attune.mcp.server`, then
  check each server's recent activity for help-tool calls in that
  window; or temporarily `chmod -w .help/templates/plugin` and see
  what errors.
