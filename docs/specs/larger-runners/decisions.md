# Decisions — Larger CI Runners
**Status:** approved (2026-05-11, revised post-Probe-C)
**Owner:** Patrick

---

## 2026-05-11 update — post-Probe-C revision

The original spec (below) was written mid-tar-pit with the
understanding that attune-ai's 14k-test suite genuinely needed
14+ GB of process memory. **That turned out to be wrong.** Probe C
identified the actual cause: one missing
`patch("threading.Thread")` in
`tests/unit/memory/test_pubsub_direct.py` spawning a zombie
daemon thread that allocated ~100k MagicMocks per file run. After
the one-line fix (PR #212 commit `bcc6bdec`), the full suite peaks
at **130 MB RSS, runs in 1.5 s sequential** — well within the
default 16 GB ceiling.

So the "rescue from OOM" framing of this spec no longer applies.
**The case for larger runners is now smaller** but still
defensible:

1. **Headroom for future growth** — the suite is 14k tests today
   and gaining ~1k/quarter. The next dep cycle (new SDK, more
   workflows) could repeat the squeeze. 32 GB buys ~3-5 years
   of runway without revisiting.
2. **Dev parity** — Patrick's local box is 64 GB; CI at 16 GB
   means "works locally, fails in CI" is a chronic class of
   confusion. Larger runners narrow the gap.
3. **Speed** — 8-core / 32 GB lets `-n auto` use more workers,
   roughly halving matrix wall-clock again on top of Phase 4
   of Probe C (which restores `-n auto` at 4 workers).

**What the spec NO LONGER promises:**

- "Lets us undo the dedicated coverage job split" — coverage job
  now passes cleanly on default runners (post-bcc6bdec). Could
  re-merge into matrix or keep split; lateral move.
- "Lets us undo `-n 1`" — Probe C Phase 4 will do this on default
  runners anyway. Larger runners just multiply available workers.
- "Lets us undo `parallel = true / concurrency`" — keep these;
  harmless and useful.
- "mem-tick instrumentation no longer load-bearing" — already
  true after bcc6bdec; the instrumentation is now diagnostic-only.

**Decision still stands** because of (1)-(3) above, but priority
drops from "blocker for tonight's release" to "nice-to-have for
this month's release cadence."

---

## Problem (original framing, kept for posterity)

GitHub Actions' default `ubuntu-latest` runner has **4 vCPU / 16 GB
RAM**; `macos-latest` has **3 cores / 7 GB**; `windows-latest` has
**4 vCPU / 16 GB**. PR #212's Probe B diagnosed that attune-ai's
14k-test suite under pytest-xdist + branch coverage peaks at
**15.7 GB** on Linux runners — i.e., the default ceiling is
load-bearing for our test setup. Net result: OOM-killed xdist
workers, the `[~98%] PASSED → runner shutdown` flake pattern,
and (most expensively) hours of engineer time spent contorting
test-runner config to fit a 16 GB box.

Patrick's local dev machine has **64 GB**. The "tests pass locally
but fail in CI" class of confusion that follows from a much smaller
CI ceiling has happened twice in two PRs (#207 ci-debt and now
#212).

## Decision

**Move the matrix `test` job to GitHub Actions larger runners
(8-core / 32 GB Linux variant) for `ubuntu-latest`.**

Specifically:

- `runs-on: ubuntu-latest` → `runs-on: ubuntu-latest-large`
  (or equivalent — the exact label depends on what's enabled
  for the Smart-AI-Memory org; verify with
  `gh api repos/Smart-AI-Memory/attune-ai/actions/runs/<id>
  --jq .runner_name` after first run)

macOS and Windows runners stay on the default — they were tighter
on memory but the import chain works there too, and the matrix
has been mostly green on those pre-#212 anyway (modulo
asyncio bugs and other non-memory issues).

## What this lets us undo

Once on 32 GB Linux runners, the following PR #212 contortions
become unnecessary:

- The dedicated `coverage:` job split — bring coverage back into
  the matrix's ubuntu-3.11 entry as before
- `-n 1` override — restore `-n auto` from pytest.ini for matrix
  runs (faster wall-clock)
- `parallel = true` + `concurrency = ["multiprocessing", "thread"]`
  in `[tool.coverage.run]` — keep them (harmless, mildly useful)
- mem-tick instrumentation — keep as opt-in diagnostic but no
  longer load-bearing

Probe C (investigation into "why does the suite hold 14 GB of
process state") becomes a much smaller question: maybe still
worth a look as a hygiene matter, but no longer release-blocking.

## What this does NOT change

- macOS and Windows ceilings unchanged. If `attune-ai` is ever
  meant to run cleanly on a 7 GB macOS install, the suite still
  needs to fit. Right now we don't gate on that — macOS matrix
  entries are correctness checks, not memory-discipline checks.
- The import-chain heaviness remains a real property of the
  codebase. Larger runners are a treatment, not a cure.

## Cost

GitHub Actions larger runner pricing (per
[GitHub docs](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions#per-minute-rates)):

- Linux 8-core / 32 GB: **$0.016/min**
- 75-minute timeout × 4 Python versions × ~50 PR runs/month
  ≈ **15,000 minutes/month** worst-case
- More realistically: ~3,000-5,000 minutes/month
  ≈ **$50-80/month**

For comparison: the PR #212 stabilization work alone consumed
3-4 hours of engineer time. At any normal hourly rate, larger
runners pay for themselves in <2 PRs of saved CI debugging.

## Alternatives considered

1. **Self-hosted runner** on a dev box or DO/Hetzner instance.
   Lower cost ($0-20/mo), more setup, security posture review
   needed, single point of failure. Not chosen for v1; revisit
   if larger-runner cost becomes meaningful.
2. **Trim the import chain** — make heavy SDKs lazy-imported in
   tests, mock more aggressively. Real cleanup work but
   open-ended; doesn't unblock release cadence in the
   near term.
3. **Cap CI parallelism aggressively forever** — what we did
   in PR #212. Works but brittle, and each new dep makes the
   ceiling tighter.
4. **Accept partial coverage gating** — the current PR #212
   compromise (continue-on-error coverage job). Ships, but
   leaves a quality concession in place indefinitely.

Choosing (current decision) over these because: minimal effort,
minimal risk, reversible, and addresses the root cost
(engineer time chasing memory ceilings).

## Rollback

Change `runs-on: ubuntu-latest-large` back to `ubuntu-latest`
in `.github/workflows/tests.yml`. Re-apply the `-n 1` + split-
coverage-job contortions if needed. One commit revert.

---

(per-phase decisions appended as work happens)
