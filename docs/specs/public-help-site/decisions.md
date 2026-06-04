# Spec: Public Help Site — Decisions

> Decisions captured during Phase 1. D4 is intentionally OPEN pending
> a design conversation; design.md is not authored until it resolves.

---

## Decision matrix

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Renderer / loader strategy | **Reuse** the existing corpus loader (`src/attune/help` / `ops/help_data.py`) for feature listing + frontmatter parsing, and `markdown-it-py` for markdown → HTML. No new parser, no new renderer. | `build_discipline.py` already uses `markdown-it-py`; the dashboard already loads + parses the corpus. A static build script is a new *consumer* of those, not a new rendering path. Keeps it to one loader + one markdown lib. |
| D2 | Search | **Static JSON index + small vanilla-JS client search.** Build emits `help/search-index.json` (feature, kind, title, keywords, url). | Static host can't run server-side attune_rag ranking. A client index over the corpus's keyword-rich frontmatter is enough for browse-and-find; no build-time embeddings, no runtime server. |
| D3 | Staleness policy | **Accept eventual rebuild.** CI rebuilds help pages on `.help/` change and deploys; drift does NOT hard-fail CI. | Your call. A stale public page for a few hours is low-cost vs the friction of a hard gate. Pairs with the existing staleness-detection lessons — detect + rebuild, don't block. |
| D4 | Relationship to the mkdocs site | **RESOLVED 2026-06-04 → hybrid.** attune-ai.dev/help is the canonical **user help** = generated `.help/` corpus **+ migrated hand-written tutorials/guides** (`docs/tutorials/`, `docs/how-to/`). mkdocs narrows to **API reference + contributor docs** (mkdocstrings API, CLI reference, glossary, architecture, contributing). | framework-docs is cold (low SEO loss re-homing user help); the corpus is weaker for API reference, so API stays in mkdocs; the tutorials have value and belong in help. Split: learn/do/understand → attune-ai.dev/help; look-up-API/contribute → mkdocs. |
| D7 | Help-site content sources | **Two markdown inputs**: (1) `.help/templates/*` (generated corpus), (2) selected hand-written `docs/tutorials/*` + `docs/how-to/*` (migrated). Same renderer (D1). | Consequence of D4 — the tutorials/guides join the corpus as a second source. Light redirects from old framework-docs tutorial URLs (low priority; cold). |
| D8 | Strategic trajectory (informs design, not v1 scope) | **Full consolidation onto attune-ai.dev is the end state** — eventually the whole docs surface (incl. mkdocs API/contributor reference) lives under attune-ai.dev, and smartaimemory.com traffic redirects to attune-ai.dev. The D4 hybrid is the **first step**, not a permanent split. | Patrick's stated plan (2026-06-04). Design must not assume mkdocs stays on a separate domain forever: keep cross-links domain-relative-friendly, structure `/help` so the API/reference sections can later move under attune-ai.dev, and treat the redirect work (T8) as the seed of an eventual full smartaimemory.com → attune-ai.dev redirect. v1 still ships only user help; the rest is sequenced later. |
| D5 | Site location / deploy | `attune-ai-dev/help/` static dir, served by the existing Vercel project with clean URLs (mirrors `attune-ai-dev/discipline/`). | Reuses the deploy already in place; no new hosting. |
| D6 | Public-site mutability | **Read-only.** Regen/edit stays in the dashboard admin tools. | The public site is a published artifact; mutation belongs to the maintainer surface (dashboard), per the user-vs-maintainer audience lesson. |

---

## D4 framings (resolved — hybrid; framings kept for the record)

**Option (a) — Canonical shift.** attune-ai.dev/help becomes the
primary user-facing help; mkdocs (currently
`smartaimemory.com/framework-docs`) narrows to API reference +
contributor docs.

- Pros: one obvious place users go; the generated, benchmarked corpus
  is the front door; consistent brand on attune-ai.dev.
- Cons: larger blast radius — nav/redirect changes, "where do I go"
  messaging, possible domain-consolidation work, mkdocs content audit
  to decide what's "user help" vs "reference."

**Option (b) — Coexist.** attune-ai.dev/help is the generated-corpus
surface; mkdocs stays the hand-written tutorial + reference surface.

- Pros: additive, smaller, lower risk; ships v1 fast.
- Cons: two help destinations to reconcile in users' minds;
  cross-linking discipline needed so they don't feel like rival docs.

**Things to weigh in the chat:** which domain users actually land on;
whether the hand-written mkdocs tutorials have a home in the
generated model; whether the generated corpus covers enough to be a
front door yet; SEO / link-equity of the existing framework-docs.

---

## Decision-change log

- 2026-06-04 — Initial decisions captured during Phase 1 scoping.
  D1/D2/D3/D5/D6 decided with the user; D4 left OPEN pending a design
  conversation about the mkdocs relationship.
- 2026-06-04 — D4 RESOLVED to the hybrid (canonical user help on
  attune-ai.dev/help = corpus + migrated tutorials; mkdocs → API +
  contributor reference), after the user confirmed framework-docs is
  cold, the tutorials belong in help, and the corpus is weaker for
  API reference. Added D7 (two content sources) as the scope
  consequence. Parallel-template-*generator* debt remains scoped OUT
  (separate cleanup).
- 2026-06-04 — Added D8: Patrick's stated trajectory is FULL
  consolidation onto attune-ai.dev with smartaimemory.com redirecting
  there. The hybrid is the first step. Recorded so the design keeps
  the door open (domain-portable cross-links, /help structured to
  later absorb API/reference) without expanding v1 scope.
