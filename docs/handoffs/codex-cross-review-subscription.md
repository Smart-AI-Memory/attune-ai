# Cross-review subscription handoff

## Goal

Patrick requested Claude cross-review of #2444, then explicitly approved
fixing the launcher to recognize verified subscription authentication and
include the complete diff without enabling API spend. Work is isolated on
`codex/cross-review-subscription`, based on origin/main `e884f599d`.
The #2444 worktree and branch are separate and unchanged by this fix.

## Acceptance criteria

- Default API launches remain blocked at a zero cap; only verified subscription
  auth can use the explicitly selected review path.
- Every requested diff file is included or the complete-review launch refuses.
- Regression tests, gates, whole tree and >=90% changed-code coverage pass.
- Claude's actual #2444 review is preserved without claiming absent/partial work
  is clean; publishing its raw text awaits Patrick's explicit approval.

## Current state

- `run_review` accepts explicit `claude_auth="subscription"`; the existing
  API route still checks the unchanged session spend cap before dispatch.
- The new launcher verifies logged-in first-party Pro/Max auth in a child
  with all ANTHROPIC_/CLAUDE environment overrides removed. Auth and review
  use the same safe-mode configuration. Tools and MCP servers are disabled,
  no session is persisted, and the complete brief goes through stdin.
- Unknown, API, helper-based or malformed auth refuses inference. A failed,
  malformed, empty or oversized reply is not presented as a clean review.
  The subscription attempt uses a 900-second bound; the original 300-second
  attempt on the 205,248-character #2444 diff timed out and is recorded absent.
- `require_complete=True` refuses omissions before launch; an explicit
  `diff_cap_chars` supports up to 250,000 characters. Default is still 60,000.
  This fixes the case where a single 82,764-character registry cannot fit
  even a scoped re-lane under the old cap.
- The canonical plugin skill and its mirror describe the opt-in API.
- #2444's fresh CI exposed a companion isolation setup gap: the CONTRIBUTING
  smoke job omitted static tokenizer preparation. It now warms the cache
  before executing the unchanged documented clean-venv setup commands.
  The inference guard and smoke-test assertions remain unchanged.

## Verification

- Focused launch/manifest tests: 81 passed; subscription launcher 100% coverage.
- Broader roundtable, gates, quality, CI and skill-projection selection:
  1,300 passed, 36 skipped in 19.62s; 98.81% combined statement/branch coverage.
  `/private/tmp/cross-review-gates.log` and
  `/private/tmp/cross-review-gates-coverage.json`.
- The complexity ratchet initially rejected the expanded `run_review`.
  Launch validation, authentication dispatch and manifest completeness now
  live in their owning helpers; its measured complexity is 20 (base 19),
  below the existing threshold, without changing the allowlist.
- Controlled smoke reproduction: an empty tokenizer cache failed with
  `InferenceBlocked` (1.23s). Preparing only the static vocabulary before
  pytest made the same guarded test pass (1.08s).
  `/private/tmp/cross-review-cold-smoke.log`,
  `/private/tmp/cross-review-warm-smoke.log`.
- The first whole-tree run found three stale skill-derived help projections;
  their deterministic generators were rerun (no hand edits).
- Whole configured tree: 25,772 passed, 242 skipped, 3 xfailed in 73.41s.
  `/private/tmp/cross-review-whole-final.log`. Final pinned hooks are recorded
  in the PR. The failed earlier runs remain in the local logs.
- Tests use `/private/tmp/run_cross_review_suite.py`, disposable Redis,
  isolated credentials, and the committed inference guard. PYTHONPATH binds
  application imports to this worktree, despite reusing the other worktree's
  Python 3.11 interpreter. Test subprocess calls to Claude are intercepted.

## Review publication

The original #2444 review was published with Patrick's approval and its
corrections have merged through #2444. Main's cross-review ledger records
runs `20260906-1103` and `20260906-1109`, including the later dispositions.
The two local draft rows name those same runs and are deliberately not
re-applied as duplicate, stale `not-triaged` entries. Their exact original
bytes remain in stash `3fae57c9218db74cf222dfd8be3cb057bdb7fcb0` and
`/private/tmp/2449-pre-reconcile-local-ledger.patch`.

## Scope and assumptions

Subscription authentication is evidence of the selected auth path, not a
billing/overage receipt. No API credential or automatic API fallback is
provided. The zero-valued ledger label names the subscription route and does
not assert a zero invoice. Normal interactive auth configuration is unchanged.
The launcher is opt-in, not a change to other roundtable/workflow invokers.

## Main reconciliation — 2026-09-06

Structured one-shot: resolve #2449 against verified main `a9d9401c1`,
retain both feature histories, preserve the local review drafts, and leave
the PR conflict-free after validation. No new product behavior is introduced.

Only `CHANGELOG.md` and `docs/COVERAGE_BUG_LOG.md` conflicted; both sets of
entries are retained. The shared CONTRIBUTING workflow and workflow tests
already match main. Subscription source, tests and skill projections remain
unchanged. A signed merge commit preserves the original signed branch commit.
The dirty main checkout is untouched.

Verification uses the committed inference guard, intercepted launcher tests,
and disposable Redis for the whole configured tree. Logs:
`/private/tmp/2449-reconcile-focused.log`, `/private/tmp/2449-reconcile-whole.log`,
and `/private/tmp/2449-reconcile-hooks.log`. The final handoff is included in
validation before publication. Historical test counts above describe the
original pre-merge tree, not this reconciliation.

## Next action

Verify the signed merge push and GitHub's fresh mergeability/CI at that head.
Leave #2449 open for Patrick to merge. The preserved local-review stash is
historical context, not a patch to blindly reapply over main's final dispositions.
No reviewer, paid inference, auto-merge, release or increment-3 work is authorized.
