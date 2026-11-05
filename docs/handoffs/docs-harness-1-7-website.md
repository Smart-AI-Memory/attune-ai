# Agent work handoff

## Goal

Make the website help users choose useful Harness work and distinguish published
installation from 1.7.0 preparation. Match the positive, practical README message
without changing the release candidate or claiming unverified publication.

## Acceptance criteria

- Benefit-led homepage with real plan/build/review/repair/test/continue outcomes.
- Current entrances install published 1.6.0; 1.7.0 is explicitly preparation.
- Canonical Help export is bound to a reviewed merged source; historical
  commands, anchors, frozen records and evidence identities are retained.
- Website tests, types, scoped lint, production build and route/browser checks.
- Exact release and deployment gates remain visible.

## Scope and assumptions

- Branch/worktree: docs/harness-1-7-website, isolated from website main a768eca35.
- Provider/session: GPT-6; independent read-only documentation and source review.
- Harness source: merged 5159e7a79fbdb84d2982937716043b142534e6e9.
- Published source: af2159516a67172cc8f2a1ff62213296b1b67112, from release-1.6.0.json.
- Fresh public PyPI query on November 5, 2026 returned latest=1.6.0 and no 1.7.0.
- Windows walkthrough and package publication remain with the release owner.

## Current state

- Status: validated candidate; no merge or production deployment.
- Changed files: homepage copy/style/metadata; Docs/FAQ/Pricing current entrances;
  Navigation and Footer; release adapter and its regression checks; canonical
  Help importer, rewrites, integrity tests, generated export and maintainer note.
- Decisions: use /get-started/ and /1-7-0-preparation/ rather than inventing version
  slugs. Keep build.version=1.5.1 as reference provenance and read the current
  published identity/source from published_version and release-1.6.0.json.
- Reused only three bounded importer/config/test paths from prepared #2590.
  Existing #2575/#2579/#2580/#2581 page drafts were inspected, not overlaid.
  No sibling branch/PR was changed or closed.
- Risks: #2590 overlaps the Help import; #2575 and #2579 overlap current entry
  points. Review disposition before merging siblings over this candidate.
  Historical archive/Author cleanups retain their separate scope.
- No Harness README, package, dependency lock, workflow or historical walkthrough
  source was changed. Website-only work has no package changelog entry.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Repository discipline | Existing tools Python collaboration_preflight.py | 87 passed; ambient Python initially lacked xdist |
| Published vs preparation identity | Fresh PyPI JSON plus release adapter and route tests | 1.6.0 published, 1.7.0 absent; preparation separate |
| Website behavior and importer refusals | ATTUNE_PYTHON points to existing project venv; npm test | 83 passed; initial ambient interpreter lacked claude_agent_sdk and old route-count expectation needed refresh |
| Type and lint correctness | tsc --noEmit; scoped eslint | Passed |
| Production artifact | Next.js 16.3.8 build, telemetry disabled | Passed; 123 routes; existing Edge-runtime warnings retained |
| Exact canonical import | harness-help-export.mjs check | 15 pages, 30 files; exact merged 5159e7a source |
| Preservation | Independent hash/code/anchor comparison | Ten frozen records/assets unchanged; historical code blocks preserved, no original IDs removed |
| User journey | Actual local production browser | Homepage task CTA opens goals; current install is 1.6.0; preparation explicitly unpublished |
| Mobile layout | Actual browser at 320 and 390 CSS pixels | Homepage has no horizontal overflow; 320px current guide also fits |
| Final route delivery | HTTP bytes/hash and negative-route check | 36 passed: exact payloads, build/import records, current entrances, unknown-topic404 and historical308 |

## Next action

Push/open a draft PR if permitted. Before
production: coordinate the Windows result and actual 1.7.0 publication with the
release owner, update canonical Help/release metadata there, and reimport that
exact merged source here. Admit the fixed 1.7.0 release-record filename only
after verifying its real source/artifact identity; update adapter/tests and
rerun current-head checks and hosted preview routes. Do not relabel historical
1.5.1 provenance or claim that a website build publishes a package.

Production uses Vercel Git integration on main. Review/merge authorization and
current-head checks are still required; no workflow dispatch, settings change,
credential change, IndexNow ping or production deployment was performed.

## Completion review

The broader goal is a user who can choose useful work, install the actual
published package and inspect the result. This review found current-entry
buttons still pointing to old instructions and a version adapter that would
confuse reference provenance with package publication. The bounded fixes above
address those findings. Post-publication reimport and original user-observation
limits are already explicit in the release handoff and Help bridge; no new
feature or opportunity entry is warranted. A user encounters current onboarding
first. Independent-user comprehension and production acceptance remain open.
