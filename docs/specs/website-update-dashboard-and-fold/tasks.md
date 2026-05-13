# Tasks — Website update: dashboard maturity + fold-back

**Status:** draft — pre-Phase-1 audit done 2026-05-12 ([phase0-audit.md](phase0-audit.md))

Two-phase plan. Phase 1 ships everything that doesn't depend on the fold-back; Phase 2 swaps install commands + adds redirects + automated screenshots once the fold lands. See `decisions.md`, `requirements.md`, `design.md` for context, and `phase0-audit.md` for the current-state inventory + three implementation nuances the spec didn't flag (narrow `pip install` replacement scope, dashboard-mention reuse on homepage, changelog lives in root `CHANGELOG.md`).

---

## Phase 1 — Pre-fold (ship now, with current install command)

Goal: Dashboard story is visible on the site using today's install command. Pre-announce the fold so existing attune-gui users see it coming.

**Audit-driven sequencing recommendation** (see `phase0-audit.md`):
Split Phase 1 into two PRs for cleaner review:
- **PR-A** (Foundation): 1.1, 1.4, 1.5, 1.6.1 — helper file, FAQ entries, migration page. ~12 files, no screenshot dependency.
- **PR-B** (Dashboard surface): 1.2, 1.3, 1.6.2 — dashboard page, homepage updates, banner. Depends on PR-A.

**Three implementation nuances** flagged by the audit:
- 1.1.1 — Replace `pip install` only in `website/app/*.tsx` (~10 places), not in `website/content/blog/*.mdx` (~18 places). Blog posts are time-stamped historical artifacts.
- 1.3.1 — Reuse the existing homepage "local dashboard" copy (lines 26-27, 198, 291 of `app/page.tsx`) rather than adding a parallel mention.
- 1.4.1 — Changelog entries land in **root `CHANGELOG.md`**, which `website/app/changelog/page.tsx:25` renders. No website-source changelog file exists.

### 1.1 — Foundation

- [ ] **1.1.1** Create `website/lib/install-command.ts` with `CANONICAL_INSTALL` + `POST_FOLD_INSTALL` constants and an `installCommand()` helper. Replace every hard-coded `pip install` on the site with a render from this helper.
- [ ] **1.1.2** Create `website/lib/migration-banner.ts` with `showFromVersion` / `hideFromVersion` / `fallbackHideDate` per C-4.
- [ ] **1.1.3** Add `scripts/check-migration-banner.ts` build-time check — fails if `fallbackHideDate` has passed and banner still renders.

### 1.2 — Dashboard feature page

- [ ] **1.2.1** Create `website/app/dashboard/page.tsx`. Hero + 4 surfaces (Living Docs, RAG search, Commands, Summaries).
- [ ] **1.2.2** Capture hand-shot screenshots for each surface (Phase 2 replaces with automation). Store at `website/public/screenshots/`.
- [ ] **1.2.3** Create `website/screenshots/manifest.yaml` with entries for each screenshot (C-2 schema).
- [ ] **1.2.4** Wire `/dashboard` into the site nav.

### 1.3 — Homepage + features

- [ ] **1.3.1** Add "Living Docs" as a top-of-fold capability on the homepage with a one-line tagline.
- [ ] **1.3.2** Add polish-corpus to the feature list / pricing matrix / FAQ with consistent phrasing per `requirements.md` scope.

### 1.4 — Changelog

- [ ] **1.4.1** Add 2026-05-10 changelog entry covering the nine-fix session as 3–5 user-visible bullets per C-5.
- [ ] **1.4.2** Add forward-looking note for the quality-pass + fold-back when they land (placeholder anchor; populated in Phase 2).

### 1.5 — FAQ

- [ ] **1.5.1** Add "What's the difference between attune-ai and attune-gui?" (pre-fold answer: "two packages, one workflow").
- [ ] **1.5.2** Add "Do I need the dashboard?" with the honest "no, but…" answer.

### 1.6 — Migration page

- [ ] **1.6.1** Create `website/app/migrate/page.tsx` with the pre-fold heads-up content. Linked from the FAQ entries.
- [ ] **1.6.2** Add the migration banner component to the homepage. Currently hidden (controlled by `migration-banner.ts`).

### 1.7 — Pre-fold deprecation announcement

- [ ] **1.7.1** Add a banner to attune-gui's PyPI README 4–6 weeks before the planned fold ship date. Non-version-specific phrasing per R-5. Banner links to the `/migrate` page on attune-ai.
- [ ] **1.7.2** (Cross-repo) attune-gui maintainer publishes a new minor version of the standalone package with the README banner.

### 1.8 — Link checker

- [ ] **1.8.1** Add `.github/workflows/link-check.yml` running `lychee --offline website/ docs/` as a non-blocking job.

### 1.9 — Phase 1 review + ship

- [ ] **1.9.1** All `requirements.md` acceptance criteria 1–5 pass on a preview deploy.
- [ ] **1.9.2** Patrick reviews + approves. Single PR merged to main.

---

## Phase 2 — Post-fold (ship the day v7.0 lands)

Goal: swap install commands site-wide, retire the pre-fold banner, replace it with the post-fold migration banner, add redirects, enable automated screenshots.

### 2.1 — Install command swap

- [ ] **2.1.1** Edit `install-command.ts`: `CANONICAL_INSTALL = POST_FOLD_INSTALL`. Verify every install-command render on the site picks up the new value (single source of truth).
- [ ] **2.1.2** Pin the migration banner to v7.0 → v7.1 lifecycle (update `showFromVersion` / `hideFromVersion` per C-4).

### 2.2 — Redirects + link check escalation

- [ ] **2.2.1** Add `attune-gui` → `attune-ai` redirects to `website/next.config.ts`.
- [ ] **2.2.2** Escalate `lychee` job to a required check. Any 4xx/5xx on a post-fold path is a hard fail.

### 2.3 — Migration page swap

- [ ] **2.3.1** Update `/migrate` content from pre-fold heads-up to post-fold "here's what changes."
- [ ] **2.3.2** Update changelog 1.4.2 placeholder with the actual fold entry.
- [ ] **2.3.3** Update FAQ "What's the difference…?" to post-fold answer.

### 2.4 — Automated screenshot capture

- [ ] **2.4.1** Create `.github/workflows/dashboard-screenshots.yml` per `design.md` R-3.
- [ ] **2.4.2** Create `scripts/prepare-demo-state.sh` to deterministically seed the demo workspace (fresh corpus, known summaries, etc.).
- [ ] **2.4.3** Run the workflow against the v7.0 release tag; verify each screenshot regenerates and the manifest updates.
- [ ] **2.4.4** Open a PR with the regenerated screenshots replacing the Phase 1 hand-captures.

### 2.5 — OG / hero refresh (if rebrand calls for it)

- [ ] **2.5.1** Update OG image + opengraph copy if the homepage hero changed substantially in Phase 1.

### 2.6 — Phase 2 review + ship

- [ ] **2.6.1** All `requirements.md` acceptance criteria 6–8 pass on a preview deploy.
- [ ] **2.6.2** Patrick reviews + approves. Single PR merged to main on v7.0 release day.

### 2.7 — Banner retirement (auto)

- [ ] **2.7.1** Around 4 weeks after v7.0 ships (when v7.1 cuts), the migration banner auto-retires per C-4.
- [ ] **2.7.2** Sanity-check the build-time check (`scripts/check-migration-banner.ts`) doesn't fail post-retirement.

---

## Phase 3 — Close

- [ ] **3.1** All acceptance criteria green on production.
- [ ] **3.2** `lychee` runs as required check; passing.
- [ ] **3.3** Screenshot workflow has captured at least one full set on a real release tag.
- [ ] **3.4** Patrick confirms the site tells the story it should.
- [ ] **3.5** Close this spec. Open follow-up specs if Phase 2/3 work surfaced new threads (e.g. live demo deploy, customer-success content).

---

## Out of scope (parking lot)

- Live demo deploy (Dashboard page links to it but doesn't build it)
- Marketing automation / email lists
- Customer-success content (tutorials, case studies)
- Pricing changes
- Visual / brand identity refresh
- Compare-with-CLI page

---

## Rollback plan

Each phase is a single squash-merge. Rollback = `git revert <commit>`. Phasing ensures independence:

- Revert Phase 2 → site shows pre-fold copy with current install command; Phase 1 work still visible
- Revert Phase 1 → site returns to current state; no harm done
- Revert Phase 3 closure tasks → no impact (these are admin-only)
