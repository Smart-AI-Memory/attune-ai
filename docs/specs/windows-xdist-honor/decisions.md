# Decisions — Windows xdist `-n 1` Honor
**Status:** approved (2026-05-11)
**Owner:** Patrick
**Predecessors:** Probe B (coverage-canonical-pattern), Probe C
(probe-c-memory-investigation)

---

## Problem

The CI matrix's pytest invocation uses `-n 1` to override
`pytest.ini`'s `addopts = -n auto`. On Linux and macOS this works
as expected — one xdist worker. **On Windows it doesn't.**
Windows CI runs show multiple worker IDs in the log
(`[gw0]`, `[gw1]`, `[gw2]`), and the suite takes 30-40+ minutes
instead of the expected sequential time.

Evidence from PR #219 post-rebase CI run (commit on top of
2026-05-11 main):

- ubuntu-3.10: 1 failure (pre-existing Py 3.10 `test_chain_executor`
  bug, single worker)
- windows-3.10/11/12/13: each ran ~34 min with **multiple
  workers active** (`gw0`/`gw1`/`gw2` in log), 4 failures per
  run — same redis-detection cluster pattern Probe C identified
- Identical pytest invocation on all platforms

The threading-patch fix from Probe C (PR #212 commit `bcc6bdec`)
fixed the leak Linux saw. Windows still crashes the same tests
because:

1. Multiple workers run despite `-n 1`
2. Each worker accumulates state independently
3. Cumulative memory pressure hits the 16 GB Windows runner
   ceiling
4. Redis-detection cluster tests crash specific workers

So **Probe C's local fix protected Linux + macOS, but Windows
still has the OOM pattern** because the worker count override
isn't being honored.

## Hypothesis

Three candidate causes (need to test):

1. **pytest.ini `addopts` precedence on Windows** — argparse
   may handle `-n auto ... -n 1` differently when invoked via
   pytest's Windows-specific entry point. Worth testing
   `pytest -p no:cacheprovider --override-ini addopts=` style
   isolation.

2. **`pytest-xdist` Windows worker detection** — xdist may
   spawn workers based on `os.cpu_count()` regardless of the
   CLI flag when running through a Windows shell wrapper.

3. **`shell: bash` interaction** — the workflow step has
   `shell: bash` (added in PR #212 for mem-monitoring). On
   Windows this runs Git Bash. Git Bash may pass args
   differently than Windows native shell. Possible the `-n 1`
   is being consumed as a different argument somewhere in the
   shell chain.

The data from rerunning a minimal probe will narrow these.

## Decision

**File this as a scoped investigation spec.** Three iterations
max before escalating:

1. **Probe**: Add `echo $@` (or equivalent) before the pytest
   invocation to log the actual argv pytest sees on Windows.
   Confirms whether `-n 1` is even reaching pytest.
2. **Test override mechanisms**: `--override-ini`,
   `PYTEST_ADDOPTS` env var, explicit `pytest` invocation
   without shell wrapping.
3. **If still stuck**: skip the redis-detection cluster on
   Windows specifically (`@pytest.mark.skipif(sys.platform ==
   "win32", ...)` for the 4 known files) and file a longer-
   term Windows xdist follow-up.

The decision is to **scope the investigation strictly** — not
to spend another 10 hours chasing this like Probe B. The
tar-pit trip-wire rule applies: if these three iterations don't
land it, we mark-and-move-on rather than continue iterating.

## What this does NOT change

- Linux + macOS CI is now stable (post-Probe-C). This spec
  only addresses Windows.
- The `-n 1` cap will eventually be removed entirely once
  Probe C Phase 4 lands (restore `-n auto` everywhere) — but
  Windows would still need this fix because the same problem
  applies to ANY worker-count override, not just `-n 1`.
- The 4 redis-detection test files are useful and stay in
  the suite. They pass on Linux + macOS post-Probe-C.

## Alternatives considered

1. **Drop Windows from the matrix entirely** — too aggressive;
   attune-ai is meant to be cross-platform.
2. **Mark the redis-detection files Windows-skip permanently** —
   loses test coverage on Windows for legitimate code paths.
   Acceptable as a fallback (option 3 in Decision above), not
   a first move.
3. **Switch Windows to default-runner GitHub Actions image** —
   doesn't help; the issue is xdist worker count, not the
   runner itself.
4. **Mark the redis tests `@pytest.mark.serial`** with a
   pytest-xdist `--dist=loadgroup` config — possible but adds
   complexity for one platform.

## Acceptance criteria

- One of:
  - (a) Windows CI shows `[gw0]` only (single worker) and
    suite completes faster than 20 min on Windows-latest, OR
  - (b) Windows CI skips the redis-detection cluster with a
    clear `@pytest.mark.skipif` marker + tracking issue
- Linux + macOS unaffected (regression test in CI to confirm)
- The chosen fix is documented in
  `docs/specs/windows-xdist-honor/decisions.md`

## Out of scope

- Investigating why Linux's `-n 1` override works (working as
  expected; only Windows is broken)
- Generalizing to other pytest-xdist behavioral differences
  on Windows (file separate spec if more issues surface)
- Switching the CI shell from `bash` to PowerShell — that
  would undo the PR #212 mem-monitoring fix

---

(per-phase decisions appended as the investigation proceeds)
