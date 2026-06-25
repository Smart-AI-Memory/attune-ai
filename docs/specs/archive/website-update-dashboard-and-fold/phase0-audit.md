# Pre-Phase-1 audit — current website state vs spec targets

**Date**: 2026-05-12
**Method**: inventory `website/` against each Phase 1 task's
target artifacts and content references. Source: `git ls-files` +
targeted greps in the `website/` directory of this repo.
**Outcome**: spec is at **0% implemented**, but the audit
surfaces three implementation nuances the spec didn't flag.
Ship-readiness map below.

---

## File artifacts — none exist

Phase 1 requires these new files. All confirmed absent on `main`:

| Task | Target | Status |
|---|---|---|
| 1.1.1 | `website/lib/install-command.ts` | MISSING |
| 1.1.2 | `website/lib/migration-banner.ts` | MISSING |
| 1.1.3 | `scripts/check-migration-banner.ts` | MISSING |
| 1.2.1 | `website/app/dashboard/page.tsx` | MISSING |
| 1.2.2 | `website/public/screenshots/` (any contents) | DIR MISSING |
| 1.2.3 | `website/screenshots/manifest.yaml` | MISSING |
| 1.6.1 | `website/app/migrate/page.tsx` | MISSING |
| 1.8.1 | `.github/workflows/link-check.yml` | MISSING |

## Content references — sparse to absent

| Task | What spec wants | Current state |
|---|---|---|
| 1.3.1 | "Living Docs" as top-of-fold capability on homepage | Only 2 blog posts + `lib/metadata.ts` reference it. NOT on homepage. |
| 1.3.2 | Polish-corpus in feature list / pricing matrix / FAQ | Zero references anywhere on website. |
| 1.4.1 | 2026-05-10 changelog entry (nine-fix session) | Changelog page reads `CHANGELOG.md` via `ReactMarkdown`. No per-PR entry mechanism in website source; entry lives in root `CHANGELOG.md`. |
| 1.5.1 | FAQ "What's the difference between attune-ai and attune-gui?" | Not in `website/app/faq/page.tsx`. |
| 1.5.2 | FAQ "Do I need the dashboard?" | Not in FAQ. |
| 1.6.2 | Migration banner component on homepage | No such component exists. |

## `pip install` distribution (sets Phase 1.1.1's scope)

**63 total occurrences across 10+ files.** Distribution:

| File | Count | Type |
|---|---|---|
| `app/docs/page.tsx` | 6 | Live page — should use the central helper |
| `app/page.tsx` | (in code-block content, see below) | Live page — should use the helper |
| `app/faq/page.tsx` | ? | Live page — should use the helper |
| `app/pricing/page.tsx` | 1 | Live page — should use the helper |
| `app/api/debug-wizard/analyze/route.ts` | ? | Likely runtime context, not user-facing copy |
| `content/blog/*.mdx` (8 files) | 18+ | **Historical blog posts — should NOT be retroactively updated** |

**Implementation nuance #1: Spec's "Replace every hard-coded
`pip install` on the site with a render from this helper"
(1.1.1) is ambiguous.** Two reasonable scopes:

- **Narrow**: Replace only on live navigation pages (`app/*.tsx`
  in app, docs, faq, pricing, contact). Leave blog posts as
  time-stamped historical artifacts that say what was true
  when they were published. **Recommended.**
- **Wide**: Replace everywhere. Breaks the editorial integrity
  of dated blog posts; a 2024-vintage post that says
  `pip install attune-ai` should keep saying that even if the
  canonical install changes in 2026.

The narrow scope cuts the work from "63 places" to ~10 places,
all in `website/app/`. Blog posts skip the helper.

## Existing homepage dashboard mention

Already on the homepage:

```
website/app/page.tsx:26: # 4. attune-gui — local dashboard tying it all together.
website/app/page.tsx:27: #    pip install attune-gui && attune-gui --open
website/app/page.tsx:198: Local dashboard. Browse templates, edit specs, …
website/app/page.tsx:291: Local dashboard. Browse templates, edit specs, run commands, …
```

**Implementation nuance #2: The homepage ALREADY positions
`attune-gui` as "the local dashboard."** Phase 1.2 ("Dashboard
feature page") and Phase 1.3.1 ("Living Docs top-of-fold")
overlap with existing copy that talks about the dashboard but
under the `attune-gui` brand. The implementer needs to decide:

- **Reuse the existing slot.** Rewrite the existing
  "local dashboard" mentions to point at the new `/dashboard`
  page. Keep `attune-gui` as the install command pre-fold.
- **Add a parallel mention.** Risks two competing
  "what's the dashboard?" stories on the homepage.

Recommended: reuse. The existing mentions are exactly where
the spec wants "Living Docs / Dashboard" to land top-of-fold.

## Phase 1.4 — Changelog mechanism

```
website/app/changelog/page.tsx:25: const changelogPath = path.join(process.cwd(), '..', 'CHANGELOG.md');
```

The site's changelog is **a render of the root `CHANGELOG.md`**
via `react-markdown`. There's no per-entry page in the website
source. So Phase 1.4.1 ("Add 2026-05-10 changelog entry") is
actually "add the entry to root `CHANGELOG.md`," not "edit
something in `website/`."

**Implementation nuance #3: Phase 1.4 lives in root
`CHANGELOG.md`, not in `website/`.** Worth noting in the spec
so the implementer doesn't go looking for a website-source
changelog file that doesn't exist.

## What's already adjacent (not Phase 1, but related)

- `website/lib/metadata.ts` — already centralized SEO/metadata.
  The 1.1.1 install-command helper would follow the same
  pattern (export-a-constant). Easy to model on this.
- `website/lib/features.ts` — central features list. Phase
  1.3.2 (polish-corpus in feature list) just adds an entry
  here.

---

## Recommended ship sequence

The spec lists Phase 1 as one PR. The audit suggests **two PRs**
for cleaner review:

### PR-A — Foundation (1.1, 1.4, 1.5)

- 1.1.1 `install-command.ts` helper + `app/*.tsx` replacements
  (narrow scope per nuance #1, ~10 files)
- 1.1.2 `migration-banner.ts` (hidden by default)
- 1.1.3 `check-migration-banner.ts` build-time guard
- 1.4.1 + 1.4.2 changelog entries (to root `CHANGELOG.md`)
- 1.5.1 + 1.5.2 FAQ entries (just appending to existing
  `app/faq/page.tsx` data)
- 1.6.1 `/migrate` page (pre-fold heads-up)

~12 files, low risk, no screenshot dependency. Reviewable in
one sitting.

### PR-B — Dashboard surface (1.2, 1.3, 1.6.2)

- 1.2.1 `app/dashboard/page.tsx`
- 1.2.2 hand-shot screenshots → `public/screenshots/`
- 1.2.3 `screenshots/manifest.yaml`
- 1.2.4 nav wiring
- 1.3.1 + 1.3.2 homepage / features updates (reuse existing
  dashboard mentions per nuance #2)
- 1.6.2 migration banner on homepage (still hidden)

Depends on PR-A's foundation files. Adds the actual
user-visible dashboard story.

### Out of website-repo scope (parking)

- 1.7.1 + 1.7.2 attune-gui PyPI README banner — lives in
  `~/attune-gui` (sibling repo, not in this monorepo).
- 1.8.1 `link-check.yml` — small standalone PR, can ship
  anytime.

---

## Suggested updates to `tasks.md`

If this audit is accepted:

- Add a "Pre-Phase-1 audit" section pointing at this file.
- Note the three implementation nuances (narrow `pip install`
  scope, dashboard-mention reuse, changelog-in-root) inline at
  the relevant tasks.
- Split Phase 1 sub-tasks into PR-A / PR-B groupings.

No status flips needed — the spec correctly shows 0% done.
This audit's value is **scope precision**, not status
correction.
