# Harness 1.6.0 Help delivery handoff

## Goal

Serve the reviewed Harness 1.6.0 Get started page through the existing static
Help publishing bridge, with older guides and evidence retaining their versions.

## Acceptance criteria

- Accept the published export with reference version `1.5.1`, behavior commit
  `ebb5b03b8a4398325df7ddabd28c08186451452e` and current release `1.6.0`.
- Get started describes published 1.6.0. Other guide versions, historical
  records, goal source, assets and bookmarks remain truthful and preserved.
- Serve `code-copy.js` and `release-1.6.0.json` at their public Help paths.
- Retain exact-file, SHA-256, origin, path, symlink and fresh-output checks.
- Import only the exact reviewed Harness commit/export supplied by the lead.
- Completion review: pending with the delivery lead's overall synthesis.

## Scope and assumptions

- Branch: `codex/publish-harness-help-1-6`.
- Isolated clone: `/private/tmp/attune-ai-harness-help-1-6-delivery`.
- Base: `a768eca35a8a86d65b4cd23bf0d4a4a6b7f3d687` (`origin/main`).
- Scope: existing Help importer, required Next.js rewrites, focused tests, this
  handoff, the existing publishing-bridge maintainer note and the later explicitly
  supplied generated export.
- Excluded: #2575's surrounding entry points, runtime/package changes, new
  infrastructure, settings, personal hooks, provider calls and package publication.
- The original handoff held push/merge/deployment. The current rollout go permits final verification, normal integration and established production delivery after the remaining gates pass.

## Current state

Harness #326 is merged as `069b9f010cabcefa076ec292b4a287c49a85d219`.
Its tree equals the reviewed candidate. A fresh import from the actual merge
reproduced the exact 29-file inventory: all 27 payloads and the build record are
byte-identical, with only the source commit/URL in `import.json` updated.
The original candidate imports and evidence remain retained.

The existing hosted Vercel Next.js 16.3.8 production build for website head
`cd95a624bb3681bec29881e0801f4bca1c1bdf14` compiled, type-checked and generated
123 routes successfully, then deployed Ready. This supplies actual Next.js
build evidence; the two local sandbox build failures remain historical.
Authenticated preview HTTP/browser verification remains pending. Do not change
protection settings or create credentials. The current rollout authorization
covers final validation, normal merge and established production delivery after
the remaining checks pass; it does not authorize package publication.

Keep the existing importer and Next.js rewrite pattern. Add only the fixed
`release-1.6.0.json` filename to the existing exception; `code-copy.js` already
matches the safe filename regex. Keep the reference-version invariant, require
the actual current published version and verify mixed-version rendered content.

Must work: the 1.6.0 start page and clipboard asset, the new release record,
unchanged 1.5.1 records, existing goals and historic URLs. Must fail: stale
current-release metadata, changed bytes, extra or escaped paths, unknown dotted
release filenames, symlinked paths and a lookalike source origin. Reject a broad
filename relaxation or global relabeling of old guides.

The bridge and focused tests are authored. The replacement export was imported
initially from exact pushed Harness candidate `fd690080076dad45dea3e4b2f190e4ecf8c0fbf6`
in Harness #326; the merged-source refresh above supersedes that dependency
state. The importer archived that commit and used the existing Python 3.12.2 / Markdown 3.10 interpreter.
All 27 payloads and the build record match the supplied export and the earlier
real candidate `55d61fe2770337e7723f64fa7320ecfd0f7ea386`. Both candidate cohorts
and the original website export remain under `.codex/validation/help-1-6/`.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Isolated source and clean dependency setup | Git base/status and exact-lock `npm ci --ignore-scripts --no-audit --no-fund` | Base matches; 636 packages installed; no tracked dependency changes. |
| Existing filename regex admits the new script | Evaluate the unchanged regex against `code-copy.js` | `true`; no regex expansion needed. |
| Repository preflight | `python3 scripts/collaboration_preflight.py`, then the existing Python 3.10.11 interpreter | Initial default interpreter lacks xdist (`-n` rejected). Existing interpreter passes all 87 governance tests; zero failures, one expected no-linked-main-checkout warning; source status unchanged. |
| Export-independent route and origin checks | `vitest run lib/harness-help/topics.test.tsx -t 'keeps public routes\|refuses a lookalike remote'` | Two pass; six payload-dependent cases intentionally excluded pending export. |
| Static type and lint checks | `tsc --noEmit --incremental false`; scoped ESLint on the three changed website files; `git diff --check` | All pass using the exact locked website dependencies. |
| Handoff template contract | Existing Python 3.10.11: `python -m pytest tests/unit/docs/test_handoff_corpus.py -q -n 0 -p no:cacheprovider` | All 5 tests pass in 9.74s. The old head `9c76063e9fd38f5774513455b94284a788814a36` failed the exact required `## Current state` heading in three CI jobs; this heading-only correction follows the unchanged template and test. |
| Importer and mixed versions | Actual import from candidate `fd69008`, followed by `checkExport` | Pass: 14 pages, exact 29-file inventory and 27 payload hashes; candidate identity remains explicit. |
| Website regressions | `ATTUNE_PYTHON=/Users/patrickroebuck/.pyenv/versions/3.10.11/bin/python npm test` | All 80 tests pass. Initial default-interpreter run passed 79 and failed only the capability test because `claude_agent_sdk` was unavailable; both logs are retained. No assertions or dependencies changed for the retry. |
| Historical preservation | Byte comparison against the retained original export | All 10 original release/preparation/verification records, assets and goals JS/CSS match. |
| Independent external-boundary and artifact review | GPT-6 Astra, separate read-only source and artifact passes | No material findings. It verified 33 source/renderer hashes against candidate `fd69008`, 27 payloads, the exact 29-file inventory and historical preservation. |
| Historical local production builds | `VERCEL_ENV=preview NEXT_TELEMETRY_DISABLED=1 npm run build:vercel` | Both original local attempts exited 1 at the CSS-worker port boundary (`Operation not permitted`, unchanged `Footer.module.css`); original logs remain retained. No third local build was run. The later hosted Next.js preview build at cd95a624 succeeded as recorded above; final-head hosted checks remain required after this rebind. |
| Served-route and production acceptance | Observe exact-head hosted routes after the successful Next.js build | Local loopback serving was not run after the historical local build failures. The existing hosted preview deployed Ready; authenticated preview HTTP/browser verification remains pending. No production deployment has occurred. |

## Next action

Draft PR: https://github.com/Smart-AI-Memory/attune-ai/pull/2590 . Initial commit
`904162074368c7a8d9da3304e9ee144bffe5aa46` is pushed and its GPG signature
verifies locally. This ordinary documentation follow-up records the two build
results without rewriting that commit or changing tested implementation.

Keep the draft at the final-head and authenticated serving gate. The hosted
Next.js build closes the earlier production-build evidence gap. The original
failed local attempts remain retained; no third local build was run. The import
receipt now binds #326's actual merge commit. Before website delivery, finish
the remaining final-head and served-route checks. No synthetic receipt or source
identity was created. This branch touches none of #2575's eight surrounding
entry-point files. No website merge, production deployment or settings action occurred. The existing automatic preview deployment is recorded separately above.

Retained local evidence: `.codex/validation/help-1-6/website-tests.log` (initial
interpreter failure), `website-tests-pinned-python.log` (80 passed),
`website-build.log` and `website-build-permitted.log` (both failed at the worker
port boundary), candidate comparison JSON, both exact candidate imports and the
original website export. Completion-review synthesis remains with the delivery
lead; the current evidence adds no distinct opportunity beyond this bounded
delivery and its existing gates.
