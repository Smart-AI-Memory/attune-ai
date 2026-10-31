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
  infrastructure, settings, personal hooks, provider calls and deployment.
- No push until the lead directs it. No merge or deployment authority.

## Design and current state

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
from exact pushed Harness candidate `fd690080076dad45dea3e4b2f190e4ecf8c0fbf6`
in Harness #326, which remains a dependency pending merge. The importer archived
that commit and used the existing Python 3.12.2 / Markdown 3.10 interpreter.
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
| Importer and mixed versions | Actual import from candidate `fd69008`, followed by `checkExport` | Pass: 14 pages, exact 29-file inventory and 27 payload hashes; candidate identity remains explicit. |
| Website regressions | `ATTUNE_PYTHON=/Users/patrickroebuck/.pyenv/versions/3.10.11/bin/python npm test` | All 80 tests pass. Initial default-interpreter run passed 79 and failed only the capability test because `claude_agent_sdk` was unavailable; both logs are retained. No assertions or dependencies changed for the retry. |
| Historical preservation | Byte comparison against the retained original export | All 10 original release/preparation/verification records, assets and goals JS/CSS match. |
| Independent external-boundary and artifact review | GPT-6 Astra, separate read-only source and artifact passes | No material findings. It verified 33 source/renderer hashes against candidate `fd69008`, 27 payloads, the exact 29-file inventory and historical preservation. |
| Production build | `VERCEL_ENV=preview NEXT_TELEMETRY_DISABLED=1 npm run build:vercel` | One attempt started at 2026-10-31 07:38:50 UTC; pending, capped at 07:53:50 UTC. IndexNow's production ping is disabled by the existing preview guard. No retry or configuration/dependency change is authorized to obtain a pass. |
| Production serving and public acceptance | Bounded loopback checks after a successful build; deployment separately gated | Pending build; no production delivery claimed. |

## Next action

Prepare the signed commit and own draft PR under the lead's visibility
authorization, explicitly retaining the pending build and #326 dependency.
Observe the existing build until exit or its 15-minute cap; retain failure or
timeout as unverified without retry or infrastructure diagnosis. After a
successful build, perform bounded loopback checks. Before website delivery,
reconcile the import receipt to #326's actual merge commit and verify the
merged-source import. No synthetic receipt or source identity was created. This
branch touches none of #2575's eight surrounding entry-point files.
