# Agent work handoff

## Goal

Remove the unused vulnerable Nodemailer package and repair the blog frontmatter
dependency chain for the approved Help rollout.

## Acceptance criteria

- Preserve current blog content and email behavior.
- Independently review source and the generated dependency graph.
- Pass a fresh production dependency audit and the affected/full website checks.
- Retain failures and bind validation to the exact source and lock.
- Open a draft PR; retain merge and deployment gates.

## Scope and assumptions

- Branch: `codex/repair-website-security-dependencies`, based on main `25e2a3b3288f56763be06c4141aacfc72820f469`.
- Author: Codex (Sol). Independent reviewer: GPT-6 Astra.
- Patrick approved fixing both dependency paths. This scope covers website npm
  dependencies and blog parsing. SDK audit repair and MCP PR #2566 are separate.

## Current state

- Remove unused Nodemailer. Active Resend email implementation is unchanged.
- Add exact js-yaml 4.3.2 and its types. A common override removes gray-matter's
  old nested YAML/argparse/sprintf-js chain; gray-matter stays 4.0.3.
- Both blog readers use the YAML 4 safe schema. Existing alternate engines for
  repository-controlled frontmatter remain available.
- Source and generated lock accepted independently. Lock SHA-256:
  `5de104e15e066f550f32adbc3b8ffd4baf0c4353a2766634b0afe3a50c31ad2d`.
- Two earlier resolver outputs were rejected and retained. The accepted generated
  graph removes exactly five packages, adds only the types package, preserves
  all 30 libc entries and leaves unrelated package entries unchanged.
- Cold invalid-input boundaries are preserved. The new options also avoid an old
  gray-matter cache interaction on repeated invalid input. YAML 3/4 semantics
  are not identical for every possible document; the current corpus is checked.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Installed graph removes both vulnerable paths | Fresh npm 10 ci from reviewed lock; actual module resolution | Passed; YAML 4.3.2, argparse 2.0.1; removed packages absent |
| Production npm inventory | Fresh npm audit --omit=dev --json | Zero known vulnerabilities; actual exit 0 |
| Existing blog content preserved | Old/new full post and summary capture | All 25 posts exactly equal, including bodies, dates and metadata |
| Parser boundaries and email behavior | Focused website suite | 23 passed |
| Full website suite | npm test | 84 passed, zero failures/errors/skips |
| Type and lint checks | tsc --noEmit; npm run lint | Both passed; three existing lint warnings |
| Production artifact | Direct next build | Passed; existing Edge runtime warnings |
| Built blog routes | Local HTTP list/article/tag/sitemap checks | Passed; 91 routes: list, 25 articles, 64 tags and sitemap |

Receipts remain in the author's local `dependency-repair-v1` evidence directory:
`candidate-validation-readback.json`, raw JUnit/audit logs, source/lock reviews,
corpus captures and rejected resolver results. No live email was sent. The npm
audit is limited to known production dependencies; it is not an SDK security scan
or a complete repository security assessment.

## Next action

Independent final source/evidence review and pinned hooks passed. Open the own-branch
draft PR, then wait for its exact-head CI.
Reconcile the same-function Dependabot #2543 at opening: this change removes the
unused package instead of applying its proposed major upgrade. Keep its branch.
Wait for CI and the repository's merge/deployment gates. Completion review for
the local repair is recorded in the existing private opportunity draft. Remote
CI and rollout completion remain pending.
