# Design — Website update: dashboard maturity + fold-back
**Status:** approved
Technical shape, mitigations, and durable fixes. See `decisions.md` for context, `requirements.md` for user stories, `tasks.md` for the phase plan.

---

## Risks and mitigations

### R-1 — Site copy drifts from reality

Easy to claim features the dashboard doesn't quite ship.

**Mitigation:** every feature claim on the Dashboard page is backed by a screenshot from the live build (see R-3 for the durable fix that keeps screenshots fresh). Reviewers can verify each claim against its screenshot in the same scroll.

### R-2 — SEO churn from URL changes

Old `attune-gui`-specific URLs in READMEs and search results break post-fold.

**Mitigation:** redirects from any old `attune-gui`-specific URLs to the consolidated `attune-ai` equivalents. Add to `website/next.config.ts` (or wherever the existing redirects live) in the same PR that flips the install commands. Verified by `lychee` in CI (see C-3).

### R-3 — Out-of-date screenshots

Dashboard changes faster than marketing copy. Hand-captured screenshots go stale within weeks.

**Durable mitigation:** an automated screenshot-capture workflow, modeled after the diagnostic CI pattern used in `docs/specs/windows-memory-detection/`. A new GitHub Action `.github/workflows/dashboard-screenshots.yml` triggers on tagged releases:

1. Spins up `attune-ai[gui]` against a staged demo workspace (the `attune-ai` repo itself with carefully-prepared state)
2. Uses Playwright to navigate to each documented surface (Living Docs table, RAG search results, Commands inline panel, Summaries page)
3. Captures PNG screenshots at fixed viewport dimensions
4. Updates `website/screenshots/manifest.yaml` with new `captured_at` + `dashboard_version`
5. Opens a PR if any screenshot diff exceeds N% pixel delta

This decouples documentation freshness from manual labor. Phase 2 task — Phase 1 ships hand-captured screenshots so we don't block the feature page on automation.

### R-4 — Changelog gets bloated

The 2026-05-10 session was nine commits. A 1-to-1 mapping would bury the user-facing story.

**Mitigation:** the changelog persona contract (C-5) forces 3–5 user-visible bullet points per shipped event, written for "an existing attune-ai user who skipped 2 releases." Each entry is 1–3 sentences. Commit-level detail lives in the linked docs page, not the changelog.

### R-5 — Pre-announcement causes confusion if the fold slips

If we tell users "this becomes attune-ai[gui] in v7.0" and v7.0 slips by a month, the deprecation banner is wrong for that month.

**Mitigation:** the pre-fold banner uses a *non-version-specific* phrasing — "this package will become `attune-ai[gui]` in an upcoming release; see migration guide" — until the actual v7.0 RC is cut. Then a follow-up swap pins the version. Both versions of the banner ship from the same source file (`migration-banner.ts`) so the swap is one line.

---

## Module-by-module changes

### `website/lib/install-command.ts` (NEW)

Single source of truth for the install command shown anywhere on the site.

```ts
// Switched in Phase 2 when fold-back ships.
export const CANONICAL_INSTALL = "pip install attune-gui";
export const POST_FOLD_INSTALL = "pip install attune-ai[gui]";

export function installCommand(opts: { postFold?: boolean } = {}): string {
  return opts.postFold ? POST_FOLD_INSTALL : CANONICAL_INSTALL;
}
```

Every install-command render imports from here. Swapping commands site-wide is one line.

### `website/lib/migration-banner.ts` (NEW)

Banner lifecycle per C-4. Component reads `showFromVersion`, `hideFromVersion`, `fallbackHideDate`. Build-time check (`scripts/check-migration-banner.ts`) fails the build if today is past `fallbackHideDate` AND the banner is still rendering.

### `website/app/dashboard/page.tsx` (NEW)

The `/dashboard` feature page. Hero section + four surfaces (Living Docs, RAG search, Commands, Summaries) each with screenshot + one-sentence description + "what you do here" callout.

### `website/app/migrate/page.tsx` (NEW)

Migration guide page. Pre-fold: "Heads up — `attune-gui` is becoming `attune-ai[gui]` in an upcoming release. Here's what to expect." Post-fold: "If you had `attune-gui` installed, here's what changes."

### `website/components/Hero.tsx` or `website/app/page.tsx` (UPDATE)

Add "Living Docs" as a primary capability under a one-line tagline. Layout TBD — content team owns the visual treatment.

### `website/app/changelog/page.tsx` (UPDATE)

Add the 2026-05-10 entry. Format: date heading + 3–5 user-visible bullets + link to per-feature docs page.

### `website/app/faq/page.tsx` (UPDATE)

Two new entries per `requirements.md` scope.

### `website/next.config.ts` (UPDATE, Phase 2)

Redirects from `attune-gui`-prefixed paths to `attune-ai` equivalents. Verified by `lychee` in CI.

### `.github/workflows/dashboard-screenshots.yml` (NEW, Phase 2)

Playwright-based automated capture. See R-3.

### `.github/workflows/link-check.yml` (NEW, Phase 1)

`lychee --offline website/ docs/` non-blocking job. Escalated to required check in Phase 2.

---

## Failure modes

| Failure | Behavior |
|---------|----------|
| `install-command.ts` missing on a page that imports it | Build fails immediately — TypeScript catches it. |
| Screenshot manifest entry missing for a referenced screenshot | Soft warning in CI (Phase 1); hard fail (Phase 2). |
| `lychee` finds dead link | Non-blocking warning Phase 1; hard fail Phase 2. |
| Banner build-time check fails (past `fallbackHideDate`, banner still on) | Build fails — forces an explicit decision to either remove the banner or push out the safety date. |
| Migration banner shows wrong version pre-fold-RC | Acceptable — phrasing is intentionally non-version-specific until v7.0 RC. |

---

## Backward compatibility

- Pre-fold install copy stays valid until the fold ships
- Existing dashboard-related URLs in attune-gui's READMEs continue to work via redirects after the fold
- The `attune-gui` PyPI package itself ships as a deprecation shim per the fold-back spec — this website spec doesn't change that package's behavior

---

## Open design questions (require eng input)

- **Screenshot capture viewport sizes.** Match the dashboard's actual responsive breakpoints? Phase 2 task to spec out.
- **Banner CSS placement.** Inside the `<Hero>` or above the nav? Content/design call, not engineering.
- **Demo workspace stability.** Phase 2 work depends on `attune-ai` itself having a "demo state" — fresh corpus, known summaries, etc. Engineering owes content a `scripts/prepare-demo-state.sh` to seed it deterministically.
