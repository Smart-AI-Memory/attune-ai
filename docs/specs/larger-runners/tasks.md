# Tasks — Larger CI Runners

## Phase 1 — Switch & verify (the actual work)

- [ ] **1.1** Verify the org has larger runners enabled. Check
      [GitHub Actions runner groups settings](https://github.com/organizations/Smart-AI-Memory/settings/actions/runner-groups)
      or run a probe workflow with `runs-on: ubuntu-latest-large`
      to confirm. Cost-attribution + billing limits should be set.
- [ ] **1.2** Update `.github/workflows/tests.yml`:
      - `runs-on: ubuntu-latest` → `runs-on: ubuntu-latest-large`
        on the `test` matrix job's ubuntu entries.
      - Leave macOS and Windows runners on defaults.
- [ ] **1.3** Trigger a fresh CI run. Verify matrix completes in
      reasonable time without OOM.

## Phase 2 — Undo the workarounds (after Phase 1 confirms green)

- [ ] **2.1** Restore `-n auto` in the matrix pytest invocation
      (remove the `-n 1` override).
- [ ] **2.2** Re-merge the `coverage:` job back into the matrix's
      ubuntu-3.11 entry. Or, alternative: keep the dedicated job
      but remove `continue-on-error: true` since OOM is no longer
      expected.
- [ ] **2.3** Decide whether to keep mem-tick instrumentation as
      always-on diagnostic or move it behind a workflow input flag.
- [ ] **2.4** Close PR #212's history with a follow-up note in
      `docs/specs/coverage-canonical-pattern/decisions.md`
      pointing at this spec.

## Phase 3 — Observe & adjust

- [ ] **3.1** After one month on larger runners, check the GitHub
      Actions usage report. Confirm spend is within budget
      ($50-80/month range expected).
- [ ] **3.2** If cost exceeds expectations, evaluate self-hosted
      runner option (Alternative #1 in decisions.md).
- [ ] **3.3** File a smaller follow-up if macOS 7 GB becomes a
      practical blocker for any contributor.

## Out of scope

- Trimming the SDK import chain (Alternative #2). Worth doing
  someday as code hygiene; not blocking on it.
- Self-hosted runner setup. Revisit only if cost forces it.
- Removing `attune-rag` / `attune-help` / `attune-author` from
  core deps to reduce test memory footprint. Architectural
  decision, separate spec.
