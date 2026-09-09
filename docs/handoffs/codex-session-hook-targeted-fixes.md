# Agent work handoff

## Goal

Retain all three SessionStart hooks and correct the reliability report's
repository-identity, deadline, monitoring, and provenance failures. Patrick
authorized targeted local fixes on 2026-09-09, initially holding shipping.
After reviewing the local completion report, his subsequent "go" authorized
committing, pushing, opening the PR, and checking required CI before merge.

## Acceptance criteria

- PR commands use the repository and host verified against stamped provenance;
  ambient GH_REPO/GH_HOST and an origin-host change cannot produce foreign verdicts.
- Slow HTTP response bodies cannot outlive the hook process deadline; successful,
  failed, and budget-exhausted lookups remain distinguishable.
- Foreign spec paths and unreadable/cyclic paths remain unverified without
  discarding other findings.
- Help checks cover authored projections, preserve independent findings on errors,
  and reject outside-repository template/source paths.
- Both starter hooks share contained artifact selection and truthful tracked,
  draft, unverified, and filesystem-mtime fallback labels.
- Focused behavioral tests, real process/filesystem receipts, coverage, integration
  guards, independent review, and post-change preflight pass.

## Scope and assumptions

- Project: attune-ai; structured one-shot implementation following reliability review.
- Worktree: `/Users/patrickroebuck/.codex/worktrees/af69/attune-ai`.
- Branch: `codex/session-hook-targeted-fixes`; earlier local implementation commit
  `c15c92103d9ff00c984f7429cf22b47694a1262e` was the reliability-review baseline.
- Corrections follow the baseline commit above; inspect Git for current
  commit/status and the branch's PR for remote checks. No package release is planned.
- Codex integrates local implementation; gpt-5.6-sol supplies the required
  different-model advisory review. Delegations are recorded in the R5 ledger.
- The separate main checkout is dirty and behind cached origin/main; untouched.

## Current state

PR: https://github.com/Smart-AI-Memory/attune-ai/pull/2499. Initial published
head `d868dee78` passed both Linux hook lanes but failed both macOS and both
Windows hook lanes in the HTTP fixture. Windows logs proved the fixture's
parent wrapper bypassed UTF-8 bootstrap. A guarded owned-loopback probe proved
the default fixture opener can be redirected by ambient proxy settings; that
matches the missing-request shape but does not establish the macOS CI cause.
The fixture correction restores the real bootstrap, isolates its local opener,
forces ASCII/proxy conditions in the regression, and preserves worker error
details. Local Python 3.11 with three workers: all 1,122 hook tests passed.
Head `26be85a5c` fixed both Windows lanes; both Linux lanes also pass. Both
macOS lanes still failed before the fixture received HTTP. A guarded DNS-stall
probe reproduced this signature: HTTPServer's reverse lookup spent 4.004s and
timed out, while numeric binding returned 1.2.3 in 0.117s under the same stall.
The final fixture uses numeric binding, explicitly rejects hostname lookups,
and records actual subprocess timeout/OS errors. CI must establish whether
this resolves the macOS failure; DNS is not yet a proven runner root cause.

The full initial CI matrix also exposed a stale broad-catch ratchet, a new
worker stdout anchor absent from the surface baseline, and Python 3.13+
non-strict resolution hiding directory symlink loops. The ratchet now shrinks
4 to 3; the regenerated inventory and subject/pin include the worker anchor.
Spec containment precedes strict resolution, preserving foreign dangling
symlink warnings and distinguishing local missing paths from read failures.
All 671 gates and 35 boundary tests pass locally; real filesystem probes agree
on Python 3.12, 3.13 and 3.14. No production deadline or test timeout was widened.
Check the latest head's remote CI before advancing; red jobs are not passes.

Final combined hooks/gates: 1,796 passed. The full unit run found one stale
packaged inventory copy (22,662 passed, 116 skipped, 3 xfailed); the existing
runtime projector regenerated both package files, and all 278 affected
bootstrap/parity/ledger checks then passed. Pinned pre-commit passed.

All three hooks and their original registrations remain. Corrections are in the
three scripts and their focused test files. The report records the original
reproducers and the remediation evidence; it is the detailed verification index:
[session-hook reliability report](../reports/session-hook-reliability-2026-09-09.md).

New stamps add `repo_host`. Legacy hostless repository stamps now request a
verified re-stamp before named-thread verdicts. Existing user starters were not
automatically rewritten. Unprovenanced context retains its explicit assumption
warning. Untracked handoffs remain usable with a `:draft` label; mtime fallback
is labeled `:fallback`, without claiming commit or authoring chronology.

The PyPI lookup runs in a subprocess that is killed and reaped on timeout.
Authored help uses the existing projector in dry-run mode, comparing rendered
help outputs rather than relying on lossy source hashes. No projector outputs
were changed. Hook registrations remain five, three, and twelve seconds.

## Verification

See the report's local remediation receipts for exact commands and results.
Final results: 260 focused tests passed at 96.16% combined statement/branch
coverage; 87 post-change preflight governance tests, 77 integration/projection
guards, and 28 ledger checks passed. Pinned formatting and lint passed.
Different-model review accepted and closed five additional defects and found
no remaining actionable blocker in the report's scope.
The lead reruns delegated receipts centrally; agent self-reports are not treated
as verification. Real boundary tests include opposite PR fixture states, real
Git origin changes/indexes, real files/symlinks, actual script entrypoints,
owned loopback HTTP success/slow responses, and projector mutation round trips.

Limits: initial local receipts were macOS/Python 3.10; later local and CI
receipts above extend the tested platforms. The actual Claude SessionStart
harness and live GitHub/PyPI services were not exercised. Legacy
help mtime is a hint. Local filesystem stalls are not given a new hard deadline.
Help output drift is checked here; projected docs pages retain their existing
drift gate. No production occurrence rate is inferred from controlled failures.

## Next action

Commit and push the final CI corrections to PR #2499 after review and local
verification, then wait for required CI, including
Windows, before proceeding toward merge. Do not modify the dirty main checkout.
Delete this handoff when the branch merges.
