# Harness Help source publication handoff

## Goal

Publish a direct Help Center entry and requested command reference for Harness 1.5.0 through existing
PR #2552 and the normal Vercel Git deployment. Patrick explicitly authorized
publication on October 19, 2026. Scope is documentation, website presentation
and necessary links. No product code, dependency pins, credentials, provider
calls or unrelated site changes are authorized.

Tier: structured one-shot. Acceptance: published-package installation works,
release limits are accurate, normal checks pass, and the final public page,
Help navigation and linked targets are verified after deployment.

## Current state

Continued existing branch `feat/harness-help-source-publication` in an isolated
clone; no other owner's checkout was edited. Current main 25e2a3b32 was merged
normally with a signed commit. The original source head 87cb091 and its initial
failures remain in history. That head's security scanner failed provider
authentication/exit 3 and when-green failed HTTP 401. These are unresolved
checks, not zero-finding scanner results. PR #2553 separately owns scanner
repair; PR #2568 separately owns website dependency repairs. Neither is changed
or incorporated by this documentation work.

The `/harness/help/1-5-0/` page uses published PyPI installation, a local
deterministic demo, workflow entry points, release sources and explicit Windows
limits. Voyage AI is Patrick's recommended service; attune-rag is the explicitly
selected local alternative, pinned to 1.2.0 by Harness 1.5.0. Standalone 1.2.1
is separate; automatic outage fallback is only planned.

Help overview/navigation, `/docs/` and the sitemap point to current guidance.
The older seven guides retain 1.3.0 instructions. The former next-release route
is labeled historical and remains noindex; its JSON observations are unchanged.

The newly requested `/harness/help/ai-tools-and-integrations/` reference uses the
same renderer/topic registry, a Typical use command-only index (AI, AI/Human,
Human), actual command/subcommand forms, prompts and expected evidence. Numbered
paths identify prerequisites, approval, returned checkpoint/task handoffs and
separate alternatives. Complete examples remain in existing linked versioned
CLI/canonical procedures. Index entries are typical initiators, not permissions.
The current-release Next link now leads to this reference; Next stays within the
guide version instead of dropping readers into historical 1.3.0 guidance.

## Content provenance

Primary sources: the published v1.5.0 README, pyproject metadata, release notes,
GitHub release and PyPI 1.5.0 metadata, checked October 19. The separately
prepared accepted-main Help bundle and four candidate procedures were reviewed
at tutorials-1-5-preparation/attune-harness/docs/handoffs/tutorials-1.5.0/
accepted-main-review-77d5b2b/help-review. Its candidate wheel178 and retained
wheel859 observations are not relabeled as published-wheel execution evidence.
The public page links those versioned preparation procedures with their limits
and supplies new published-release installation instructions.

The 1.3.0 canonical snapshot/projection, next-release JSON and product pins are
unchanged. Source edits apply Patrick's approved Google documentation baseline;
no entered answers are edited. Local Next 16.3.8 page and metadata guidance was
read before final validation.

## Verification

The installed published 1.5.0 CLI was inspected through 32 top-level command help
pages and 63 nested help selections. All exited 0. The 26 current command names
appear exactly once in the Typical use index and reference rows; six compatibility
commands remain separate. No documented mutation, recovery or model command was
executed for this map. Installed task_cli.py verifies that bound responses carry
their own accepted=true/permissions and cannot be mixed with separate --accept or
intake overrides; the ordered review/repair guidance preserves that distinction.
New navigation coverage passes within the website suite (78 tests). The revised
Next Webpack build passes with 134 pages. Browser inspection confirms the Typical
use index, numbered prerequisite/approval handoffs and the actual starter-to-
reference Next navigation. The original afd1e0ecd Tests workflow is now terminal
success: both native suites, both timezone suites and coverage passed. All earlier
exact-head receipts remain bound to afd1e0ecd and do not qualify this new content.

Read-only collaboration preflight: 87 governance tests passed using the existing
repository interpreter; own-clone cached-main warnings retained. The initial
system Python lacked pytest-xdist. Initial website test discovery selected an
incomplete Python installation; selecting the existing repository interpreter
passes all 77 tests in ten files. The real projection drift check passes.
Published base 1.5.0 was installed in a disposable Python 3.12.2 environment;
version 1.5.0, RAG 1.2.0, CLI help and deterministic demo returned the expected
verified 4, with no provider call. Windows installation syntax is explicitly
not a newly qualified Windows walkthrough.

Targeted ESLint and TypeScript pass. Direct Next Webpack production build
passes with 133 pages. All pinned pre-commit hooks pass. Chrome renders the new
page with readable layout, version notice, runnable fenced commands and visible
Windows/retrieval limits. Final HTTP/link receipts and exact-head hosted checks
must be read before integration. No new independent-model review
is claimed; earlier source reviews retain their original attribution.

## Publication boundary

Patrick's explicit instruction to publish the missing Help page supersedes the
older preparation-only hold for this scoped page. Normal repository checks and
hosting protection still apply. No admin merge, bypass label, scanner waiver,
new model credentials or paid model calls are authorized. Existing Git integration
creates preview deployments from branch updates and production on main merge.
Do not infer a clean scanner result from an empty or skipped audit.

## Authentication investigation

Existing local Claude Pro authentication is available under the repository's
scrubbed safe/strict diagnostic, without API credentials or a new login. No model
was called. Subscription cross-review is explicitly advisory and cannot silently
replace the missing security audit. No zero-model-call equivalent approval was
found. A completed approved exact-head security review is still required.

when-green uses a separate ADMIN_MERGE_TOKEN and fails its initial metadata read.
It is optional opt-in automation; the PR has no auto-merge label/request and the
branch-protection required list excludes that job. Existing gh user authentication
works. After genuine security review and required checks pass, the normal plain
non-admin merge route can use that existing login without repairing automation
credentials. No credentials, labels or protection settings were changed.

## Next action

Finish local validation, commit/push normally to PR #2552 and inspect fresh
exact-head checks and preview. Merge only if the normal gates are satisfied;
otherwise report exact blockers and the reviewable proposal. Delete this handoff
on merge under the repository rule. Verify production HTTP, navigation, source
links and installation fragment after deployment. Completion review: pending.
