# Spec: Public Help Site — Tasks

**Status:** complete (2026-06-09) — shipped: `attune-ai-dev/build_help.py`
renders the `.help/` corpus as the public `/help` site; confirmed by
spec triage.

> Phase 3 (task decomposition). Sequenced; each task is a reviewable
> unit. Most carry an XML-enhanced prompt at execution time per
> `.claude/rules/attune/xml-enhanced-prompts.md`.

---

## Tasks

| # | Task | Files | Depends on | Status |
|---|------|-------|------------|--------|
| T1 | Extract brand shell + CSS into shared `_brand.py`; refactor `build_discipline.py` to use it (no visual change) | `attune-ai-dev/_brand.py` (new), `attune-ai-dev/build_discipline.py` | — | todo |
| T2 | `build_help.py` core: render the generated corpus (features + kinds) → `help/<feature>/index.html` + `<kind>.html`, reusing `help_data.list_features`/`get_template` + markdown-it-py | `attune-ai-dev/build_help.py` (new) | T1 | todo |
| T3 | Two-source ingestion (D7, Model A): slug-match `docs/tutorials/*` + `docs/how-to/*` to features; merge matched into feature pages; emit unmatched into `help/guides/`; log the mapping; strip mkdocs admonitions | `attune-ai-dev/build_help.py` | T2 | todo |
| T4 | Landing page: intent nav (do/solve/understand/lookup via `INTENT_GROUPS`) + feature grid + guides section + search box; site nav + link to mkdocs API docs; landing-page link into `/help` | `attune-ai-dev/build_help.py`, `attune-ai-dev/index.html` | T2 | todo |
| T5 | Search index + client searcher: emit `help/search-index.json` (title/feature/kind/url/keywords/snippet) + `help/search.js` (substring + token-overlap rank) | `attune-ai-dev/build_help.py`, `attune-ai-dev/help/search.js` | T2, T3 | todo |
| T6 | Tests: build-script unit tests (renders all features/kinds, search index well-formed, slug-match correctness, admonition stripping) + a link/asset sanity check | `tests/unit/site/test_build_help.py` (new) | T2–T5 | todo |
| T7 | CI rebuild step (D3): on `.help/**` or migrated `docs/{tutorials,how-to}/**` change, run `build_help.py`, auto-commit `help/**`, no hard-fail; respect generated-content whitespace/newline hooks | `.github/workflows/*.yml` | T2–T5 | todo |
| T8 | Redirects (low priority, can be follow-up): emit matched-slug → new-URL map at build; add Vercel redirect rules for cold framework-docs tutorial URLs | `attune-ai-dev/vercel.json`, `build_help.py` | T3 | todo |

---

## Acceptance criteria → coverage

| Criterion (requirements.md) | Task(s) |
|---|---|
| 1. `/help/index.html` browsable (intent + grid) | T4 |
| 2. Every feature → `<feature>/index.html` + per-kind pages | T2 |
| 3. Client-side search over `search-index.json` | T5 |
| 4. Single command, reuses loader + markdown-it-py | T1, T2 |
| 5. `/help` in nav + landing link, clean URLs | T4 |
| 6. CI rebuilds on `.help/` change, no hard-fail | T7 |
| 7. No third renderer (shared loader + markdown-it-py) | T1, T2 |
| 8. Migrated tutorials/how-to render into `/help` | T3 |
| 9. Old tutorial URLs redirect | T8 |

---

## Sequencing notes

- **T1 first** — extract `_brand.py` and prove `build_discipline.py`
  still renders identically (byte-diff the old vs new
  `discipline/index.html`) before building anything new on top.
- **T2 → T3 → T4/T5** is the core build, pipelined. T4 and T5 can run
  in parallel once T3 lands the page set.
- **T6 gates merge**; **T7** lands with or just after the build so the
  public pages don't immediately go stale.
- **T8 is deferrable** to a follow-up PR (cold traffic) — note it in
  the PR if split.

---

## Review gates before execution

Two items need your sign-off when T3/T4 are drafted (flagged in
design.md):

1. **The migration set** — prune which `docs/tutorials/`+`docs/how-to/`
   pages actually move vs stay.
2. **Install page** — landing chip vs `/help` tutorial vs both.

---

## Out of scope (restated)

- mkdocs API/contributor docs (stay; cross-link only).
- Parallel-template-*generator* cleanup (separate debt).
- Public-site regen/editing (read-only).
