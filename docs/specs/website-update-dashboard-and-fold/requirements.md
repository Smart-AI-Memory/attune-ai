# Requirements — Website update: dashboard maturity + fold-back

**Status:** draft

User-facing stories and contracts. See `decisions.md` for context, `design.md` for mitigations, `tasks.md` for the phase plan.

---

## Scope

**In scope:**

- **Updated install copy across the site.** Wherever `pip install attune-gui` appears (homepage, docs, framework-docs, README excerpts), call out the new path: `pip install attune-ai[gui]` once the fold lands; `pip install attune-gui` (with deprecation note) before then. Keep the message stable: one product, two install styles.
- **A "Dashboard" feature page** at `/dashboard` (own route — see `decisions.md`). Covers what the dashboard *is for* (Living Docs, corpus search, commands surface, jobs, summaries), with screenshots of:
  - Living Docs document table with state badges + inline actions.
  - rag-query search results page with linked hits.
  - Commands page with the inline result panel.
  - Summaries page populated by the polish-corpus job.
- **Living Docs explanation in product copy.** This is the workflow innovation worth selling — "your docs stay current with your code." Currently absent from the homepage and how-it-works.
- **Polish-corpus job as a named feature.** Show up in the feature list / pricing matrix / FAQ. Phrasing: "one-click corpus polish — generate path-keyed summaries the RAG retriever uses for boost scoring."
- **Changelog entry** at `/changelog` for the dashboard work shipped 2026-05-10 (the nine-fix session) plus a forward-looking note for the quality-pass + fold-back when they land.
- **FAQ updates:**
  - "What's the difference between attune-ai and attune-gui?" — pre-fold answer: "two packages, one workflow." Post-fold answer: "they're one package now (`attune-ai[gui]`); attune-gui is the dashboard."
  - "Do I need the dashboard?" — honest answer: no, but it's where the workflow tells you what to do next.
- **OG image / opengraph copy** updated if the homepage hero changes.
- **Sitemap / SEO check** that new routes are crawlable; existing dashboard-related URLs in `attune-gui` repo READMEs link to the right `attune-ai` site URLs after the fold.
- **Migration banner + page** per the placement decision (`/migrate`).
- **Pre-fold deprecation banner** on attune-gui's PyPI README 4–6 weeks before the fold ships.

**Out of scope:** see `decisions.md` "Out of scope" section.

---

## User stories

1. *As a new visitor*, I land on the homepage and see "Living Docs that stay current with your code" as a primary capability — not buried under a generic "documentation tooling" tagline.
2. *As a user evaluating attune-ai*, the Dashboard page tells me concretely what I'll see when I run `attune-gui` against my project — screenshots, not abstractions.
3. *As an existing attune-gui user reading the site after the fold-back ships*, I see one canonical install command (`pip install attune-ai[gui]`) and a clear "if you had `attune-gui` installed, here's what changes" callout.
4. *As anyone reading the changelog*, the 2026-05-10 dashboard session is captured as a coherent set of shipped improvements, not a list of disconnected commits.
5. *As a returning attune-gui user 4 weeks before the fold ships*, the package's PyPI README already warns me the rename is coming and links to the migration guide. I don't get blindsided.

---

## Acceptance criteria

A reviewer can verify each in under fifteen minutes on a built preview deploy:

1. **Install copy consistent.** Every `pip install` invocation on the site uses the same command form. No drift between homepage, docs, FAQ, framework-docs.
2. **Dashboard page exists** with at least the four screenshots listed above and a one-sentence description per surface.
3. **Living Docs is visible on the homepage** as a top-level capability. Not just buried in framework-docs.
4. **Polish-corpus mentioned in features** with consistent language across feature page, FAQ, and changelog.
5. **Changelog has an entry** dated 2026-05-10 covering the nine-fix session, written for "an existing attune-ai user who skipped 2 releases" (not commit-message language).
6. **No dead links** to `attune-gui` standalone install paths after the fold ships, verified by `lychee --offline website/` in CI.
7. **Pre-fold deprecation banner** is visible on attune-gui's PyPI page within the 4–6-week window before fold release.
8. **Migration banner auto-retires** between v7.0 and v7.1 (verified by build-time check that compares `pyproject.toml` version to the sentinel date).

---

## Contracts

### C-1 — Install command consistency

The canonical install command is a single string captured in a config file (`website/lib/install-command.ts` or equivalent), imported everywhere it appears on the site. Changing the canonical install requires editing one file. Pre-fold value: `pip install attune-gui`. Post-fold value: `pip install attune-ai[gui]`. The post-fold swap is a one-line PR.

### C-2 — Screenshot freshness

Every screenshot on `/dashboard` has a manifest entry in `website/screenshots/manifest.yaml` with:

```yaml
- file: living-docs-table.png
  captured_at: 2026-05-11
  dashboard_version: 1.3.0
  surface: living-docs
  description: "Document table with state badges and inline actions"
```

The screenshot-capture CI job (see `design.md`) regenerates each on tagged releases and updates `captured_at` + `dashboard_version`. Stale screenshots (where `dashboard_version` lags the live release by 2+ versions) fail a soft check in CI.

### C-3 — Link-checker contract

`lychee --offline website/ docs/` runs as a non-blocking CI job today; escalates to required check the day the fold-back ships. Failure thresholds: any 4xx/5xx on an `attune-gui` path post-fold is a hard fail.

### C-4 — Migration banner lifecycle

Banner component reads from `website/lib/migration-banner.ts`:

```ts
export const MIGRATION_BANNER = {
  showFromVersion: "7.0.0",
  hideFromVersion: "7.1.0",  // exclusive — banner gone in 7.1
  fallbackHideDate: "2026-06-15",  // safety net if version comparison fails
};
```

Build-time check fails if today's date is past `fallbackHideDate` AND the banner is still showing. The date is intentionally tight (~5 weeks from spec-open) so any slip in the v7.0 → v7.1 cycle forces an explicit decision (extend the date or retire the banner) rather than letting it linger silently.

### C-5 — Changelog persona

Every changelog entry is written for "an existing attune-ai user who skipped 2 releases." Concrete guardrails:

- Lead with what the user sees, not what code changed
- Use "you" not "we"
- No commit verbs ("refactored", "moved", "extracted")
- Each entry is 1–3 sentences max; details link out to the relevant docs page
- Group related shipped work into one entry, not per-PR
