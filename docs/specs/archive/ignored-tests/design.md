# Spec: Resolve `--ignore`-d Test Files

**Status**: approved

---

## Phase 2: Design

### Architecture

Each file gets **classified once**, then resolved on a path that
matches its classification. The classification is data-driven (failure
ratio + cause) and forces a written decision per file before any code
moves.

```
For each --ignore'd file:

  1. CLASSIFY                        ← pure investigation
     │
     ├─ Read failure cause (sample first failure per failing test class)
     ├─ Read production target (does the API still exist? what shape?)
     └─ Pick a path: REPAIR / RECONCILE / RETIRE
     │
     ▼
  2. RESOLVE on chosen path          ← bounded work
     │
     ├─ Path R1 (REPAIR):    fix tests against current production
     ├─ Path R2 (RECONCILE): finish the abandoned refactor
     └─ Path R3 (RETIRE):    delete file, salvage invariants worth keeping
     │
     ▼
  3. UN-IGNORE                       ← single-line pytest.ini change
     │
     └─ Remove --ignore directive, run full suite, commit per file
```

### The classification rule

Apply this rule to each file *before* writing code:

```
                       ┌─────────────────────────────────────────┐
                       │  Does the production code under test    │
                       │  still exist with a similar shape?      │
                       └────┬─────────────────────────┬──────────┘
                            │ yes                     │ no
                            ▼                         ▼
                ┌───────────────────────┐    ┌─────────────────────────┐
                │  Failure ratio < 25%? │    │ RETIRE (Path R3)        │
                └─┬───────────────┬─────┘    │ Tests assert against    │
                  │ yes           │ no       │ a fictional surface.    │
                  ▼               ▼          │ Salvage architectural   │
        ┌──────────────────┐ ┌────────────┐  │ invariants (if any) to  │
        │ REPAIR (Path R1) │ │ RECONCILE  │  │ docs/architecture/ or   │
        │ Real drift, fix  │ │ (Path R2)  │  │ a small targeted test.  │
        │ the assertions   │ │ Big debt — │  └─────────────────────────┘
        │ to match.        │ │ split or   │
        └──────────────────┘ │ rewrite.   │
                             └────────────┘
```

**Why the 25% threshold:** below 25% failures, the test file is
basically working — you're patching a handful of broken assertions.
Above 25%, you're rewriting more than you're keeping, and a clean
rewrite (or retirement) is cheaper than incremental repair. This is a
heuristic, not a law — a 30%-fail file with one obvious root cause
fixing all 30% at once is still REPAIR.

### Per-file initial classification

Apply the rule to each file based on the test-infrastructure audit:

| File | Pass/Fail | Production target | Path |
|------|-----------|-------------------|------|
| `test_orchestrated_release_prep.py` | 30 / 5 (14%) | `src/attune/workflows/orchestrated_release_prep.py` exists | **R1 — REPAIR** |
| `test_composition_patterns.py` | 21 / 14 (40%) | composition patterns exist; "remediation complete" header is stale | **R2 — RECONCILE** |
| `test_execution_and_fallback_architecture.py` | 11 / 41 (79%) | `FallbackPolicy` moved to `fallback_policy.py`; tests admit drift in comments | **R3 — RETIRE** (with salvage) |
| `test_scaffolding_cli.py` | 14 / 28 (67%) | `src/attune/scaffolding/cli.py` exists; mocks point at moved internals | **R3 — RETIRE** (with salvage) — possibly downgrade to R2 if cli.py is small enough to test cleanly |

These are *initial* classifications. Each file's first task is to
re-confirm or revise the classification after a 30-minute read.

### Path R1 — REPAIR (small failure ratio, real drift)

**Applies to:** `test_orchestrated_release_prep.py`

**Steps:**

1. Run the file in isolation, collect all failure tracebacks
   (not just the first).
2. Group failures by root cause. The audit suggests one root cause:
   real workflow execution returns non-`AgentResult` types, breaking
   `isinstance` checks downstream. There may be 1–3 such root causes.
3. For each root cause, decide:
   - **Test is wrong, production is right** → fix the test
     assertion (most common for REPAIR).
   - **Production is wrong, test is right** → this is a real bug;
     stop the test fix, file/fix the production bug, then return.
   - **Contract is ambiguous** → pick the contract that makes the
     fewer changes, document in code comment.
4. Re-run, confirm green, un-ignore, commit.

**Stop conditions:** if more than ~3 distinct root causes, or if any
root cause requires non-trivial production change (>50 lines of
diff), upgrade classification to RECONCILE and split the work.

### Path R2 — RECONCILE (medium failure ratio, partial debt)

**Applies to:** `test_composition_patterns.py`, possibly
`test_scaffolding_cli.py` after re-classification.

**For `test_composition_patterns.py` specifically:** the file's
"XFAIL TEST REMEDIATION - COMPLETED (2026-01-24)" header is *the
diagnostic*. Either:

- **(a)** The Jan 2026 remediation was incomplete — the author
  refactored some tests but not all, and the header overclaimed.
- **(b)** The remediation was complete, but composition-pattern
  production code regressed between Jan and May 2026.

The first task is to **disambiguate (a) vs (b)**. Method:
`git log --oneline --since=2026-01-24 -- src/attune/orchestration/`
plus `git log --oneline --since=2026-01-24 -- tests/unit/orchestration/test_composition_patterns.py`.
If production has churned, suspect (b). If only the test file has
churned, suspect (a).

- **If (a) — test debt only:** finish the mock refactor for the
  remaining failing tests, following the pattern documented in the
  file header.
- **If (b) — production regression:** this is now a production bug
  spec. Stop the test work, file the regression, fix it, then come
  back to un-ignore.

**General R2 rule:** RECONCILE means there's an in-flight refactor
to finish. Don't try to land your own refactor on top — finish what
was started.

### Path R3 — RETIRE (high failure ratio, fictional surface)

**Applies to:** `test_execution_and_fallback_architecture.py`,
possibly `test_scaffolding_cli.py`.

The premise of R3 is that the file is testing a surface that **isn't
the production surface**. Aspirational tests (the "Architectural
Tests" file is explicit about this — "Coverage Target: 95%+ from
21-73%") and mock-driven tests that have lost their target
(`sys.modules["test_generator"] = MagicMock()` is the smell) are
the canonical R3 candidates.

**Steps:**

1. **Salvage pass first (mandatory before deletion).** Read the
   file with one question: *what's the architectural intent here
   that's worth preserving in some form?* For
   `test_execution_and_fallback_architecture.py`, the docstring
   already enumerates 8 invariants ("Task types correctly mapped
   to tiers", "Fallback activates on provider failure", etc.).
   For each invariant, check: does it still hold in current
   production? Is it tested elsewhere? If it's a real invariant
   not tested elsewhere, write a small targeted test (1 file,
   < 200 lines) that asserts it against the *current* production
   surface.
2. **Then delete the original file.**
3. **Document the decision** in `docs/specs/ignored-tests/decisions.md`:
   one paragraph per retired file, naming what was salvaged and
   what was dropped.
4. Un-ignore (the file is gone, so the `--ignore` line is removed
   too), commit.

**Don't:** "fix" 41 failing tests by patching mocks until they pass.
That recreates the same problem six months from now.

### Per-file commit cadence

Resolve **one file per commit**. Each commit:

1. Removes one `--ignore` line from `pytest.ini`.
2. Includes the test work for that file (repair / reconcile /
   retire + salvage).
3. Updates `docs/specs/ignored-tests/decisions.md` with the
   per-file note.
4. Passes full `pytest tests/unit/` under `-n auto` (no new
   failures introduced into the previously-green ~14,075 tests).

This makes regressions trivial to bisect and keeps each PR
reviewable. Four files → four commits, in any order — recommend
starting with R1 (`test_orchestrated_release_prep.py`) for an
early win, then R3 files (cleaner deletions), then R2 last.

### Order of operations rationale

```
  R1 (orchestrated_release_prep)   ← start here. Bounded scope,
                                      builds confidence in the rule.
        │
        ▼
  R3 (execution_and_fallback)      ← salvage-then-delete is mostly
                                      reading + writing one new file.
        │
        ▼
  R3 (scaffolding_cli)             ← OR re-classify to R2 after
                                      reading scaffolding/cli.py.
        │                            Decision deferred to that point.
        ▼
  R2 (composition_patterns)        ← last. Highest unknowns
                                      (need to disambiguate (a) vs (b)
                                      before any code moves).
```

### Out-of-scope cross-references

- **Other ignore mechanisms** (`pytest.mark.skip`, `xfail`, the
  conftest-level skips). Those are not in this spec. If they're
  worth auditing, that's a separate spec.
- **Integration tests** are still ignored by `--ignore=tests/integration/`.
  That's a category exclusion (integration vs unit), not test debt,
  and stays.
- **The 81 currently-skipped + 10 xfailed** tests reported by the
  full-suite run. Not in scope.

### Failure-to-deliver fallback

If, partway through, a file's resolution requires production-code
work that exceeds reasonable scope (rough budget: > 1 day per file),
do **not** force-fix the tests. Instead:

1. Document the production-code blocker in
   `docs/specs/ignored-tests/decisions.md` under that file's note.
2. Mark that file's task as **deferred** in `tasks.md` with the
   blocker named.
3. Move to the next file.
4. The remaining `--ignore` lines stay until the production work
   lands. The spec ends in a partial state with a clear pointer
   to what's left.

This is preferable to either (a) silent test deletion or (b)
patched-into-passing tests that lie about what's covered.
