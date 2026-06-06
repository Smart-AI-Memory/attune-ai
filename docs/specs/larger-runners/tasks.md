# Tasks — Larger CI Runners

**Post-Probe-C revision (2026-05-11):** with the threading-patch
fix landed in PR #212 commit `bcc6bdec`, CI is no longer
OOM-pressed on default 16 GB runners. The phases below are now
about *headroom and speed*, not *rescue*. Order of operations
also changed — Probe C Phase 4 (restore `-n auto`) is independent
and runs first; this spec's Phase 1 stacks on top of it.

Sequencing:

1. **Probe C Phase 4** (separate PR) — flip `-n 1` → `-n auto`
   on default runners. Verify green.
2. **This spec Phase 1** — switch to larger runners; multiplies
   the available workers (4 → 8 on Linux) and adds memory
   headroom.
3. **This spec Phase 2** — observe + adjust.

## Phase 1 — Switch to larger runners

- [x] **1.1** Verify the org has larger runners enabled. Check
      [GitHub Actions runner groups settings](https://github.com/organizations/Smart-AI-Memory/settings/actions/runner-groups)
      or run a probe workflow with `runs-on: ubuntu-latest-large`
      to confirm. Cost-attribution + billing limits should be set.
- [x] **1.2** Update `.github/workflows/tests.yml`:
      - `runs-on: ubuntu-latest` → `runs-on: ubuntu-latest-large`
        on the `test` matrix job's ubuntu entries.
      - Leave macOS and Windows runners on defaults.
- [~] **1.3** (verifying on this PR's run) Trigger a fresh CI run. Verify matrix completes
      faster than the default-runner baseline (expectation: ~2x
      speedup from 8 workers vs 4 with `-n auto`).

## Phase 2 — Observe & adjust

- [ ] **2.1** After one month on larger runners, check the GitHub
      Actions usage report. Confirm spend is within budget
      ($50-80/month range expected).
- [ ] **2.2** If cost exceeds expectations, evaluate self-hosted
      runner option (Alternative #1 in decisions.md).
- [ ] **2.3** File a smaller follow-up if macOS 7 GB becomes a
      practical blocker for any contributor.

## ~~Phase 2 — Undo the workarounds~~ (now mostly moot)

The Probe C threading-patch fix already neutralized most of these:

- ~~Restore `-n auto`~~ → handled by Probe C Phase 4 (separate PR)
- ~~Re-merge `coverage:` job~~ → coverage job already passes
  cleanly post-bcc6bdec; keeping it split is fine, no benefit
  to re-merging
- ~~Decide mem-tick fate~~ → already diagnostic-only post-fix;
  keep as opt-in or retire when convenient
- ~~Close out PR #212 history~~ → handled in
  `docs/specs/probe-c-memory-investigation/decisions.md`

## Out of scope

- Trimming the SDK import chain (Alternative #2). Worth doing
  someday as code hygiene; not blocking on it.
- Self-hosted runner setup. Revisit only if cost forces it.
- Removing `attune-rag` / `attune-help` / `attune-author` from
  core deps to reduce test memory footprint. Architectural
  decision, separate spec.
