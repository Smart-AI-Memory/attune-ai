# Decisions — Website update: dashboard maturity + fold-back
**Status:** approved
**Owner:** Patrick
**Opened:** 2026-05-10
**Companion specs:**
- `~/attune-gui/specs/dashboard-quality-pass/` — engineering polish (sentence case, humanised timestamps, generic command result renderer, profile chip cleanup, sidecar reload-dir fix)
- `~/attune-gui/specs/fold-attune-gui-into-attune-ai/` — packaging consolidation (`pip install attune-gui` → `pip install attune-ai[gui]`)

---

## Problem

The attune-ai marketing site at `~/attune/attune-ai/website/` was last meaningfully updated before three substantial shifts that are now real or imminent:

1. **The dashboard is now a usable feature surface.** Living Docs, the polish-corpus job, the rag-query results page, and the Commands inline-result rendering all shipped 2026-05-10. None of them are reflected on the site.
2. **A dashboard-quality-pass spec is in-review** that finishes the polish work. When it lands, the site's feature claims should match the actual quality bar.
3. **The fold-back-into-attune-ai spec is drafted** — when it lands, `pip install attune-gui` becomes `pip install attune-ai[gui]`, the standalone PyPI package becomes a deprecation shim, and the canonical entrypoint is one product, one install, two faces.

The current site doesn't tell that story. Install instructions point at the standalone `attune-gui` package; feature pages don't mention Living Docs or the polish-corpus workflow; there's no "what does the dashboard do for me" page distinct from the rest of attune-ai.

---

## Decision: why a separate spec

The dashboard and fold-back specs are *engineering* specs — they describe what the code does. The website spec is *narrative* — it describes how we tell users about it. They share the same source events but produce different artifacts and have different reviewers (eng vs. content / SEO).

Keeping them separate also keeps each spec's blast radius bounded. If the fold-back slips, the dashboard feature page already shipped and is still useful. If a screenshot goes stale, it doesn't block engineering work.

---

## Decisions made (resolved during 2026-05-11 review)

These were "open questions" in the original draft. Promoted to decisions; only the genuinely-open ones move below.

| Question | Decision |
|----------|----------|
| Dashboard as `/dashboard` route or section of `/how-it-works`? | **Own route** at `/dashboard`. Substantial enough story to own a URL; SEO benefits from the keyword. |
| Screenshots: real workspace or staged demo workspace? | **Staged** — `attune-ai` itself as the visible workspace, with carefully chosen polish/scan/regen states so each screenshot tells one story. |
| How prominent should "Living Docs" become? | **Top of homepage hero, under a one-line tagline.** It's the differentiator. |
| Pre-fold copy on the standalone `attune-gui` package | **Pre-announce 4–6 weeks before the fold lands** (revised from "only after fold lands"). Add a banner to attune-gui's PyPI README: "This package will become `attune-ai[gui]` in v7.0 — see migration guide." Setting expectations gives users feedback time; holding the announcement until D-day makes the migration feel forced. |
| Changelog tone | Write for **"an existing attune-ai user who skipped 2 releases"** — that's the common reader. Plain English, no commit-message verbs, lead with what the user sees. |
| Migration callout placement | **Sticky banner on the homepage + a dedicated `/migrate` page (or `/docs/migrating-from-attune-gui`).** Banner runs **from v7.0 release through v7.1** (one minor cycle, ~4 weeks). Auto-retires via a CI job that compares `pyproject.toml` version to a sentinel date. |

---

## Open questions

| Question | Lean | Notes |
|----------|------|-------|
| Should the Dashboard feature page link out to a live demo? | Defer — needs a hosted demo first | Out of scope for this spec; revisit after fold-back |
| Do we want a "compare attune-ai vs attune-cli" page? | No | Confuses the story. One product, multiple surfaces. |

---

## Out of scope (explicit)

- **Pricing changes.** The fold doesn't change pricing.
- **Visual / brand identity refresh.** Keep the existing design system; only update content.
- **Marketing automation, email lists, social-post drafting.** Separate effort.
- **Customer-success content** (tutorials, case studies). Separate effort.
- **The attune-gui standalone repo's own README/docs.** Handled in the fold-back spec, not here.
- **Live demo deploy.** Linked to but not built here.

---

## Resolution criteria

Spec closes when:

1. Phase 1 (pre-fold) tasks complete and visible on `~/attune-ai/website/` deploy
2. Phase 2 (post-fold) tasks complete on the same deploy after the fold-back ships
3. Acceptance criteria in `requirements.md` all pass
4. Link checker (`lychee` or equivalent) added to CI as a non-blocking job, escalated to required after Phase 2 ships
5. Screenshot capture workflow (`design.md` task 4) committed and runs on tagged releases
