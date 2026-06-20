# Spec: Public Help Site — Design

> Phase 2 (technical design). Resolves how `build_help.py` ingests
> two sources, merges overlapping guides into feature pages, emits a
> client-side search index, and deploys — all reusing the existing
> loader + `markdown-it-py` (no third renderer).

---

## Architecture

`build_help.py` is a **new consumer** of code that already exists,
not a new subsystem:

```
.help/templates/*  ─┐
features.yaml       ├─► attune.ops.help_data (loader, frontmatter,    ┐
docs/tutorials/*    │    INTENT_GROUPS, EXPECTED_KINDS)                │
docs/how-to/*      ─┘                                                  ├─► build_help.py
                         markdown-it-py (commonmark, html=False)       │     │
                         build_discipline.py TEMPLATE/CSS (shared)     ┘     ▼
                                                              attune-ai-dev/help/*.html
                                                              attune-ai-dev/help/search-index.json
```

**Build-time vs deploy-time** (important): the build runs in **CI /
locally** (where `attune` is installed) and **commits the rendered
HTML**. Vercel serves the committed static files as-is and does *not*
run the build — so `build_help.py` importing `attune.ops.help_data`
(which pulls `attune_rag` etc.) is fine: that dependency is only
needed at build time, never at serve time. Mirrors how
`build_discipline.py` already works.

### Reuse map (D1 — no third renderer)

| Need | Reused from | New code |
|---|---|---|
| Feature list, kinds, frontmatter parse | `help_data.list_features`, `get_template`, `EXPECTED_KINDS`, `_parse_template` | none |
| Intent grouping (do/solve/understand/lookup) | `help_data.INTENT_GROUPS` | none |
| Markdown → HTML | `markdown-it-py` (`MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table")`) | none |
| Brand template + CSS tokens | `build_discipline.py` TEMPLATE block | extracted to a shared `_brand.py` so both build scripts import one copy |
| Static hosting + clean URLs | existing Vercel project (`vercel.json`) | redirect rules only |

`_brand.py` extraction is the one refactor: today the HTML shell +
CSS lives inline in `build_discipline.py`. Pull it into
`attune-ai-dev/_brand.py` (a `page(title, body_html, nav_html,
…) -> str` helper); both `build_discipline.py` and `build_help.py`
call it. This keeps brand styling single-sourced rather than copied.

---

## Source ingestion + the overlap problem

Two markdown sources (D7), and they **overlap on names**: `bug-predict`
exists as a `.help` feature **and** `docs/tutorials/bug-predict.md`
**and** `docs/how-to/bug-predict.md`. Three resolutions were
considered:

- **Model A — feature-centric merge (recommended).** Each feature
  page (`/help/<feature>/`) aggregates its generated kinds **plus**
  any tutorial/how-to whose slug matches the feature. Unmatched
  guides (e.g. `build-a-workflow`, `META_ORCHESTRATION_TUTORIAL`,
  `multi-agent-coordination`) fall into a `/help/guides/` catch-all
  section. **One place per topic** — best UX, matches the dashboard's
  feature-centric model.
- Model B — separate sections (`/help/features/` vs `/help/guides/`).
  Simpler build (no matching), but two destinations per topic.
- Model C — corpus only, guides stay in mkdocs. Rejected — D4 says
  guides belong in help.

**Recommendation: Model A.** Slug-match guides to features by
filename stem (`bug-predict.md` → feature `bug-predict`); the build
logs matched vs catch-all so the mapping is auditable.

### Migration set (prune in review)

Proposed to migrate into `/help` (all are user-facing learn/do
content):

- `docs/tutorials/*` — `installation`, `build-a-workflow`,
  `META_ORCHESTRATION_TUTORIAL`, `bug-predict`, `deep-review`,
  `hooks`, `ops-dashboard`, `plugin`, `rag-grounding`,
  `refactor-plan`, `release-prep`, `spec-engine`, `examples/`
- `docs/how-to/*` — the 26 how-to guides (agent-factory,
  auto-chaining, memory-graph, multi-agent-coordination,
  security-architecture, telemetry-and-signals, … etc.)

Staying in mkdocs (API + contributor — out of scope): `docs/reference/`,
`docs/architecture/`, `docs/getting-started/` (install dup — TBD in
review), contributing, `docs/implementation/`.

**Open for your prune in review:** `installation` /
`getting-started` overlap with the attune-ai.dev landing page's
install chip — decide whether install lives on the landing page, in
`/help`, or both.

---

## Output layout (clean URLs)

```
attune-ai-dev/help/
├── index.html                    # landing: intent nav + feature grid + search box
├── search-index.json             # client search index
├── search.js                     # ~40-line vanilla-JS searcher
├── <feature>/
│   ├── index.html                # feature: generated kinds + matched guides
│   └── <kind>.html               # one template (concept/task/reference/…)
└── guides/
    ├── index.html                # catch-all guides not matched to a feature
    └── <guide-slug>.html
```

URLs: `attune-ai.dev/help`, `…/help/bug-predict`,
`…/help/bug-predict/concept`, `…/help/guides/build-a-workflow`.
Vercel clean-URL config already strips `.html`/`index.html`.

---

## Page template + nav

One shared shell via `_brand.py` `page()`:

- Top nav: `attune-ai.dev` ▸ Help, with a back-link to the site root
  and a link to mkdocs API reference ("API & contributor docs →").
- Feature page: H1 + a kind-tab row (the kinds present), the rendered
  body, and a "Guides" block when matched tutorials/how-tos exist.
- Markdown bodies rendered with the same `MarkdownIt` config as
  `build_discipline.py` — `.markdown-body` CSS class so the existing
  prose styles apply (the server-side-markdown-render lesson:
  render-fn + template + CSS must all land together).

---

## Search (D2)

Build-time: walk every rendered page; emit `search-index.json` as a
flat array:

```json
[
  {"title": "Bug Predict", "feature": "bug-predict", "kind": "concept",
   "url": "/help/bug-predict/concept",
   "keywords": "race conditions memory leaks subprocess injection …",
   "snippet": "first ~200 chars of body"}
]
```

`keywords` is drawn from the corpus's keyword-rich frontmatter /
first paragraph (the same signal `help_data._build_inline_summaries`
already extracts). `search.js` does a client-side substring +
token-overlap rank over the index (no server, no embeddings — D2).
Index size for ~270 corpus pages + ~40 guides ≈ tens of KB gzipped —
fine to ship.

---

## Redirects (D4/D7, low priority)

For the migrated tutorials, add Vercel redirects so old
`smartaimemory.com/framework-docs/...tutorial...` URLs (if any are
indexed) point at the new `/help/...` homes. Since traffic is cold
(your read), this is a follow-up task, not a v1 blocker — but the map
is generated at build time (matched-slug → new URL) so the redirect
list can be emitted automatically.

---

## CI (D3 — eventual rebuild, no hard-fail)

A workflow step (e.g. in the docs/site workflow) that, on changes to
`.help/**` or the migrated `docs/tutorials|how-to/**`:

1. runs `python attune-ai-dev/build_help.py`,
2. commits the regenerated `attune-ai-dev/help/**` (auto-commit, like
   other generated artifacts),
3. **does not fail** if pages are stale between runs — drift is
   tolerated until the next rebuild.

Pairs with the generated-content pre-commit lessons (strip trailing
whitespace per line; ensure trailing newline) so the auto-commit
doesn't fight the hooks.

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `build_help.py` importing `attune.ops.help_data` drags heavy deps into the build | Low | Build-time only; CI has `attune` installed. Import the loader funcs lazily; degrade if `attune_rag` absent (loader already does). |
| Slug-match guides to features wrong (false merge) | Medium | Exact stem match only; log matched vs catch-all; review the mapping before first deploy. |
| Two parallel build scripts (`build_discipline` + `build_help`) drift on brand | Low | `_brand.py` single-sources the shell + CSS; both import it. |
| Migrated guides have mkdocs-isms (`!!! note` admonitions, `::: mkdocstrings`) that markdown-it won't render | Medium | Detect + strip/convert admonitions at build; never render `:::` mkdocstrings blocks (those stay in mkdocs API docs, not migrated). |
| Install-page duplication (landing chip vs tutorial) | Low | Decide in review (flagged above). |

---

## Out of scope (restated)

- mkdocs API/contributor docs (stay; cross-link only).
- Parallel-template-*generator* cleanup (separate debt).
- Public-site regen/editing (read-only).
- Embedding-based search.
