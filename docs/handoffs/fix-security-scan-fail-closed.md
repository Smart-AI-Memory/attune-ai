# Security scan failure propagation

## Goal

An incomplete security scan must fail its job and check instead of reporting
zero findings. A completed supported scan with no findings remains distinguishable.

## Acceptance criteria

- Nonzero scanner exit, missing/invalid output and failed analysis cannot pass.
- Critical-finding blocking and existing spend/security controls are preserved.
- Tests exercise the actual workflow bash, analyzer and check JavaScript with stubs.
- Publication remains a draft PR; merge, production deployment and paid scans are held.

## Scope and assumptions

- Branch: `fix/security-scan-fail-closed`, based on main
  `5e11cb025b605d7a6c1725024baf517a9dc8369e`.
- Source changes: `.github/workflows/security-scan.yml` and
  `tests/unit/ci/test_security_scan_fail_closed.py`, plus this required handoff.
- Independent review is non-authoring, same-model Codex; no different-provider claim.
- The supported legacy result is a top-level findings list with critical/medium/low
  severity, case-insensitively, defaulting absent severity to low. Unsupported SDK
  envelopes and severities fail closed; this change does not adapt SDK reports.

## Current state

The scanner exit is captured under bash error handling. Output validation rejects
malformed nested suffixes and any error key. The always-run check uses raw step
outcomes, exit/status and consistent analysis, fails the job before attempting
check publication, and emits an incomplete failure payload. A valid empty result
is explicitly titled **Security Scan Completed — No Findings**. Incomplete output
cannot generate a passed comment.

Triggers, action pins, permissions, timeout, concurrency, spend opt-in, analyzer,
bypass labels and critical blocking condition are preserved. Help #2552 and the
separate helper authentication failure are outside this branch. Existing bypass
asymmetry remains: the blocking step reads label output, while the custom payload
uses the analyzer's `has_bypass=false`. No end-to-end bypass success is claimed.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Incomplete scans cannot pass | 57 workflow-boundary cases, using actual bash/analyzer/JavaScript with CLI and API stubs | Passed locally on POSIX |
| Guards remain intact | Analyzer tests, workflow YAML and spend guards | Combined local run: 424 passed, one existing mypy skip |
| Tests detect weakened behavior | Original-main no-auth/missing-output controls and six deliberate mutations | All caught with assertion failures, zero harness errors |
| Embedded code is exercised | Exact parser coverage and V8 check-body fixture profile | Python 24/24 statements, 8/8 branches; V8 97.96% non-whitespace UTF-16 block-range coverage, not Codecov line coverage |

Subprocess authentication is not inherited and no real scanner/provider/API is
called by these tests. POSIX execution cases skip on non-POSIX systems before
symlink/bash use; a platform-independent raw-outcome wiring guard still runs.
Real scanner/SDK compatibility, live posting and hard-cancellation behavior are
unqualified. Runner termination can prevent later steps despite `always()`.
The unchanged keyless scanner may continue to fail without authentication; this
patch reports that failure honestly and does not create credentials.

## Next action

Follow the draft PR's exact-head automatic checks and retain any authentication
failures separately from source/test failures. Diagnose recoverable regressions
within this patch only. Return the reviewed head and receipts before any merge or
deployment decision; do not retry unrelated jobs or change credentials.
