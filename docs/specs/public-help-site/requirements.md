# Spec: Public Help Site (attune-ai.dev/help)

> Render the `.help/` corpus as browsable, searchable static pages on
> the public `attune-ai.dev` site — reusing the existing corpus
> loader and markdown renderer rather than adding a third rendering
> path.

---

## Phase 1: Requirements

**Status**: complete — shipped (`attune-ai-dev/build_help.py` + `build-help-site.yml` CI) — verified 2026-06-08 spec triage
`decisions.md`). Design + tasks proceed once requirements are
approved.

### Problem statement

The attune "help system" — 25 features × up to 11 template kinds
(267 markdown templates in `.help/templates/`, registered in
`.help/features.yaml`) — is only reachable two ways today:

1. The **ops dashboard `/help` tab** (`src/attune/ops/routes/help.py`
   + `help_data.py` + Jinja2 templates) — a *live local server*, not
   public.
2. The **`/coach` skill** inside Claude Code — interactive, not a
   browsable web surface.

A `pip install attune-ai` user who lands on `attune-ai.dev` has no
public, browsable home for this content. The corpus is generated,
keyword-rich, and benchmarked (RAG p@1 ≈ 1.0 per
`.help/benchmarks/latest.json`) — it should be the public user-facing
help surface, not locked behind a local dashboard.

The static site (`attune-ai-dev/`) already has the rendering pattern:
`build_discipline.py` renders markdown → HTML with `markdown-it-py`
and an inline brand template, committed as static files served on
Vercel. This spec extends that pattern to the corpus.

### Scope

**In scope:**

- attune-ai.dev/help is the **canonical user help** (D4): generated
  corpus **+ migrated hand-written tutorials/guides**. mkdocs narrows
  to API reference + contributor docs.
- A build script (`attune-ai-dev/build_help.py`) that ingests **two
  markdown sources** (D7) — `.help/templates/*` + `features.yaml`
  (generated corpus) AND selected `docs/tutorials/*` +
  `docs/how-to/*` (hand-written guides) — and emits static HTML under
  `attune-ai-dev/help/`:
  - `help/index.html` — landing: browse-by-intent
    (do / solve / understand / lookup, the groups already defined in
    `help_data.py::INTENT_GROUPS`) + a feature grid.
  - `help/<feature>/index.html` — one feature, links to its kinds.
  - `help/<feature>/<kind>.html` — a rendered template page.
- **Reuse, not reinvent**: the build script consumes the existing
  corpus loader (`src/attune/help` / `help_data.py`) for feature
  listing + frontmatter parsing, and `markdown-it-py` (already a
  `build_discipline.py` dependency) for markdown → HTML. No new
  frontmatter parser, no new markdown renderer.
- **Client-side search** (you confirmed: support search): the build
  emits a static `help/search-index.json` (feature, kind, title,
  keywords, url) and a small vanilla-JS searcher on the landing page.
  Static-host constraint means no server-side attune_rag ranking — a
  lightweight client index instead.
- Brand-consistent styling reusing the `build_discipline.py` token
  set; nav + a landing-page link into `/help`.
- A CI step that rebuilds the help pages when `.help/` changes
  (eventual rebuild — see acceptance criteria 6).

**Out of scope (this spec):**

- **Demoting / re-homing the mkdocs API + contributor docs.** mkdocs
  keeps the API reference, CLI reference, glossary, architecture, and
  contributing — this spec does not touch them beyond cross-linking.
- **The two parallel template *generators* debt.** The CLAUDE.md
  lessons document two markdown-*generation* pipelines (the in-repo
  3-depth stub generator vs `attune-author`'s 11-kind polish). That
  is a *generation* concern, orthogonal to this *rendering* spec.
  Tracked as related-work; not folded in here.
- Editing / regenerating templates from the public site — regen
  stays in the dashboard's admin tools. The public site is
  read-only.
- Embedding-based search — keyword/JSON client index only for v1.

### Acceptance criteria

1. `attune-ai-dev/help/index.html` renders a browsable feature grid
   plus the four intent entry points; opens cleanly on Vercel and in
   a local file open.
2. Each of the 25 features has `help/<feature>/index.html` linking
   every kind it has; each kind renders to a brand-styled HTML page
   from its markdown body.
3. Typing a query in the landing search box returns relevant
   feature/kind hits from the generated `search-index.json`
   (client-side, no server).
4. The build is a single command
   (`python attune-ai-dev/build_help.py`) that **reuses** the
   existing corpus loader + `markdown-it-py` — verified by the script
   importing them rather than reimplementing parsing/rendering.
5. `/help` is reachable from the site nav and the landing page; URLs
   are clean (`attune-ai.dev/help/<feature>/<kind>`).
6. CI rebuilds the help pages when `.help/` content changes and
   commits/deploys the result. Drift does **not** hard-fail CI
   (eventual rebuild, per your call) — a stale page is acceptable
   until the next rebuild.
7. No third markdown renderer is introduced: the dashboard, the
   build script, and `build_discipline.py` all route markdown → HTML
   through `markdown-it-py`; corpus loading goes through one shared
   loader.
8. The migrated hand-written tutorials/guides (`docs/tutorials/*`,
   `docs/how-to/*`) render into `/help` alongside the generated
   corpus, browsable from the same nav (D4/D7).
9. Old framework-docs tutorial URLs redirect to their new
   `/help` homes (low priority; cold traffic — a follow-up task is
   acceptable).

### Non-goals / explicitly deferred

- Parallel-generator cleanup (separate tracked debt).
- Public-site regen / editing (read-only site).
- Versioned/multi-release help (single current corpus only).
- Touching the mkdocs API/contributor docs beyond cross-linking
  (they stay; this spec only re-homes user help).

### Resolved design driver

- **D4 — mkdocs relationship → hybrid** (resolved 2026-06-04, see
  `decisions.md`): attune-ai.dev/help is canonical user help
  (generated corpus + migrated tutorials/guides); mkdocs narrows to
  API reference + contributor docs. D7 captures the two-source
  consequence for the build.
