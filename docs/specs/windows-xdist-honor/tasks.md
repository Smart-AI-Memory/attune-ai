# Tasks — Windows xdist `-n 1` Honor

**Status:** Draft (2026-05-11) — strict 3-iteration cap per the
tar-pit trip-wire rule

## Phase 1 — Diagnose (one CI run)

- [ ] **1.1** Add a diagnostic step to the Windows matrix job in
      `.github/workflows/tests.yml`:
      ```yaml
      - name: Windows pytest argv diagnostic
        if: runner.os == 'Windows'
        shell: bash
        run: |
          echo "PYTEST_ADDOPTS env: ${PYTEST_ADDOPTS:-<unset>}"
          echo "Effective pytest config:"
          python -m pytest --collect-only -q -n 1 \
            --co 2>&1 | head -5
          echo "xdist workers reported: $(python -c '
          import xdist
          print(xdist.__version__)')"
      ```
      Run once. Determines whether `-n 1` reaches pytest or
      whether `addopts = -n auto` from pytest.ini wins on
      Windows specifically.

## Phase 2 — Fix (try the most likely first)

Pick the first that resolves Phase 1's evidence:

- [ ] **2.1** If pytest.ini addopts wins: set
      `PYTEST_ADDOPTS=` (empty) in the workflow env to neutralize
      pytest.ini's `-n auto` on Windows only, OR use
      `--override-ini="addopts="` in the pytest invocation.
- [ ] **2.2** If shell-arg-passing is the culprit: invoke pytest
      directly without bash on Windows by splitting the step
      into Linux-bash and Windows-PowerShell variants
      (carefully — `shell: bash` was added for a reason in #212).
- [ ] **2.3** If xdist-specific: pin to `pytest-xdist` version
      and file an upstream bug if reproducible. Use
      `--max-worker-restart=0` as a worker-multiplication
      sanity check.

## Phase 3 — Verify

- [ ] **3.1** Re-run CI on the fix branch. Confirm:
      - Windows log shows `[gw0]` only (single worker)
      - Suite completes in <20 min on Windows-latest
      - Linux + macOS jobs still green (regression check)
- [ ] **3.2** If green: open PR, request review, merge.

## Phase 4 — Escalate (if Phase 2 doesn't resolve in 3 attempts)

Per the tar-pit trip-wire rule: stop iterating.

- [ ] **4.1** Add `@pytest.mark.skipif(sys.platform == "win32", ...)`
      to the 4 redis-detection cluster files (test_pubsub_direct,
      test_redis_auto_detect, test_redis_bootstrap,
      test_memory_features). Comment links to this spec.
- [ ] **4.2** File a tracking issue
      ("Windows xdist worker-count override not honored") with
      the Phase 1 diagnostic data attached.
- [ ] **4.3** Mark this spec **Resolved (workaround)** and link
      to the issue.

## Phase 5 — Compose with Probe C Phase 4

When Probe C Phase 4 lands (`-n 1` → `-n auto` everywhere on
default runners), the Windows fix here is unchanged: whatever
mechanism we use to honor `-n 1` will also honor `-n auto`.
The two specs are independent.

## Out of scope

- Investigating xdist behavior on macOS specifically (works
  fine post-Probe-C; not under suspicion)
- Switching Windows runners to a different OS image
- Larger Windows runners (separate spec, see `larger-runners`)
- Adding `pytest-xdist` to the optional-dep skip list
