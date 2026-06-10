# Design — Windows xdist Worker-Crash Flake Investigation

**Status:** complete (v1, 2026-06-10) — Probe A run, the three known
xdist-worker-crash polluters fixed (#709/#710 + the #728 SDK-spawner),
Probe B/C tooling shipped (`scripts/probe_xdist_flakes/`). Remaining
xfails + Probe D (gated Windows VM repro) are DEFERRED BY DESIGN
(DECIDE-1 caps v1 at Probe C) — reopen only if crashes recur.
**Phase 1:** [requirements.md](./requirements.md) — locked 2026-06-02 (merged via #563)

Translates Phase 1's three DECIDEs into concrete probe-execution
mechanics, the inventory report shape, and the decision tree
ordering. No new user-facing decisions; this file is the
implementation contract for Phase 4.

---

## Phase 1 recap (resolved)

| DECIDE | Resolution | Where it lands here |
|---|---|---|
| DECIDE-1 (investigation depth) | Cap at Probe C; no Windows VM repro unless A+B+C don't converge | "Probe D is gated" section below |
| DECIDE-2 (fix-first vs marker-first ordering) | Inventory-first; pick fix-vs-marker only after Probe A's output | "Decision tree" section below |
| DECIDE-3 (xfail removal) | Remove xfails as the polluter fix lands, one per test in the fix PR | "xfail teardown" section below |

---

## Files touched

| Phase 4 file | Purpose |
|---|---|
| `scripts/probe_xdist_flakes/inventory.py` | Probe A — `gh run list` query + categorization |
| `scripts/probe_xdist_flakes/import_trace.py` | Probe B — module-load import graph trace |
| `scripts/probe_xdist_flakes/fixture_trace.py` | Probe C — pytest fixture graph extraction |
| `docs/specs/windows-xdist-flakes/investigation-report-<date>.md` | Probe output artifact (one file per investigation run) |
| Possibly: `tests/_flaky_markers.py` | If decision tree picks "marker" branch — custom `windows_xdist_flaky` marker |
| Possibly: production-side fix | If decision tree picks "fix" branch — file(s) per polluter discovery |

No new packages, no new top-level directories beyond `scripts/probe_xdist_flakes/`.

---

## Probe A — inventory mechanics

**Input:** the last N days of GitHub Actions runs on the repo
default branch + open PRs.

**Query shape (gh CLI):**

```bash
gh run list \
  --workflow=test.yml \
  --status=failure \
  --limit 200 \
  --json databaseId,status,conclusion,createdAt,headSha,name,event \
  --jq '.[] | select(.name | test("windows"))'
```

Then for each failure run, fetch the per-job log and grep for
`worker.*crashed`:

```bash
gh run view <run-id> --log-failed --job <job-id> 2>&1 \
  | grep -E "worker '[^']+' crashed while running '[^']+'"
```

**Categorization output** (TSV, one row per crash instance):

```
<date>\t<PR-or-main>\t<test-file>\t<test-class>::<test-name>\t<python-version>\t<run-id>
```

Sort + aggregate by `<test-file>` then by `<test-class>::<test-name>`.
Output the top-N files with crash counts:

```
test_file                                      crashes  unique_tests
tests/unit/memory/short_term/test_redis_fallback.py  3        2
tests/memory/test_unified_memory.py                  1        1
tests/agents/test_notifications.py                   2        2
...
```

**Cost budget:** 200 runs × ~3s per `gh run view` ≈ 10 minutes
sequential. Run with `&` background fan-out (per the existing
CLAUDE.md memory) to drop to ~1-2 min. No API calls beyond gh CLI.

**Stop conditions:**

- Inventory finds <5 distinct files affected → fix-the-polluter
  branch of decision tree
- Inventory finds 5-10 files → multi-polluter branch
- Inventory finds 10+ files → marker-based-xfail branch

---

## Probe B — import-graph trace

**Input:** the list of crashing test files from Probe A.

**Mechanics:** for each test file, run

```bash
PYTHONPROFILEIMPORTTIME=1 \
  python -c "import importlib; importlib.import_module('<dotted_module_path>')" \
  2>&1 | grep -v "^import time:"
```

Filter for modules that, during import:

- open sockets (`socket.socket`, `requests.get`, `urllib.request`)
- spawn threads (`threading.Thread.start`)
- launch subprocesses (`subprocess.run`, `Popen`)
- start file watchers (`watchdog`, `inotify`)

Cross-reference: which modules appear in the import graphs of
multiple crashing files? Those are the suspect-polluter candidates.

**Implementation hint:** stdlib only — use `sys.settrace` or
`importlib.abc.MetaPathFinder` to log every import that fires.
Whitelist stdlib + common dev tools (pytest, pluggy) to keep the
output focused on production-code imports.

**Output:** a markdown table per file:

```markdown
| Module | Network | Thread | Subprocess | Filewatch |
|--------|---------|--------|------------|-----------|
| attune.memory.short_term.base_operations | ✓ | ✗ | ✗ | ✗ |
| attune.memory.features | ✓ | ✗ | ✗ | ✗ |
| ... |
```

Then a cross-file aggregation showing modules that appear in N or
more crashing-file import graphs.

---

## Probe C — fixture-graph trace

**Mechanics:** `pytest --collect-only -q --co-source` for each
crashing test, then walk the conftest hierarchy from the test's
directory upward to the repo root. For each conftest, parse
`autouse=True` fixtures and `scope="session"`/`scope="module"`
fixtures.

Look for fixtures that:

- Hit network during setup
- Start background threads or subprocesses
- Mutate global state (env vars, sys.modules, sys.path)
- Allocate sockets / open files in setup that aren't torn down

**Output:** a markdown table per test:

```markdown
### tests/unit/memory/short_term/test_redis_fallback.py::TestX::test_y

| Fixture | Scope | Autouse | Setup cost | Risk signal |
|---------|-------|---------|------------|-------------|
| redis_client | function | False | network | ✓ socket |
| event_loop | function | True | none | ✗ |
| ... |
```

Cross-reference: same as Probe B — fixtures appearing in N or
more crashing tests.

---

## Probe D — gated Windows VM repro (deferred)

**Status:** GATED on Probes A+B+C not converging on a single
polluter. Per DECIDE-1, do NOT execute Probe D in v1.

**If gated open in future:** spin up a Windows GitHub Actions
runner with `tmate` access; reproduce the crash locally with
`pytest -n auto` on a minimal repro fixture; bisect to identify
the timing dependency.

Cost: ~1-2 hours including VM setup. Defer until evidence
warrants.

---

## Decision tree (post-probes)

```
Run Probe A.
├── inventory finds 0-1 distinct files affected
│     → false-alarm; close spec as "no further action"
├── inventory finds 2-4 files
│     ├── Run Probes B + C
│     ├── if single polluter identified → fix-the-polluter
│     │     branch (production-side fix PR + cross-platform
│     │     regression test; xfails removed per DECIDE-3)
│     └── if multiple polluters → one fix PR per polluter
│           (sequence them; remove relevant xfails per PR)
├── inventory finds 5-9 files
│     ├── Run Probes B + C
│     ├── if 1-2 polluters explain ≥80% of crashes → fix-the-
│     │     dominant-polluter branch (rest get marker)
│     └── if no dominant polluter → marker-based-xfail branch
│           (custom pytest marker + systematic application)
└── inventory finds 10+ files
      → marker-based-xfail branch (defer fix work to a v2 spec
        with broader scope; this spec ships only the marker)
```

---

## Marker-based-xfail branch (if selected)

Add a custom pytest marker at `conftest.py` level:

```python
# tests/conftest.py (or pyproject.toml [tool.pytest.ini_options])
markers = [
    "windows_xdist_flaky: known-flaky on Windows under xdist worker pressure (see docs/specs/windows-xdist-flakes/)",
]
```

Apply to crashing tests as `@pytest.mark.xfail(sys.platform == "win32",
strict=False, reason="windows_xdist_flaky")` — distinguishable from
real xfails by the marker name in the reason string.

A cleanup PR can later grep all `windows_xdist_flaky` reasons and
remove them as polluters get fixed.

---

## Fix-the-polluter branch (if selected)

Each polluter fix ships in its own PR:

1. **Root cause description** in commit body — name the
   production-side module + the specific helper / fixture that
   does the repeated probing
2. **Production-side fix** — usually: dedupe repeated network
   probes, cache the negative result, OR cut the timeout from
   5s to 100ms with explicit failure handling
3. **Cross-platform regression test** that runs under `-n auto`
   on macOS/Linux first (where it should pass after fix) and is
   marked `@pytest.mark.skipif(not WINDOWS, ...)` for the actual
   Windows reproducer if needed
4. **xfail teardown** — remove `@pytest.mark.xfail` decorators on
   the affected tests in the SAME PR. Per DECIDE-3, the xfails
   are stand-ins for the underlying issue; removing them is the
   natural completion signal.

---

## xfail teardown sequence (post-fix)

Each fix PR includes a checklist in the commit body:

```
xfails removed in this PR:
- tests/unit/memory/short_term/test_redis_fallback.py::TestMetricsTracking::test_tracks_retries_in_metrics
- tests/unit/memory/short_term/test_redis_fallback.py::TestErrorHandlingEdgeCases::test_handles_max_clients_exceeded
- (etc.)
```

If a fix PR doesn't fully eliminate ALL known flakes, the
remaining xfails stay until a follow-up PR addresses them.
Investigation report is updated to track remaining instances.

---

## Investigation report shape

`docs/specs/windows-xdist-flakes/investigation-report-<YYYY-MM-DD>.md`:

```markdown
# Windows xdist Flake Investigation Report — <date>

**Probe A (inventory):** N distinct files, M total crashes over
last K days. Top-N table.

**Probe B (import traces):** suspect modules listed with cross-
file occurrence counts.

**Probe C (fixture traces):** suspect fixtures listed with cross-
test occurrence counts.

**Decision:** <fix-the-polluter | multi-polluter | marker-based>

**Next-step PR(s):** linked.

**xfails still in place:** explicit list (with line numbers) of
remaining xfailed tests; rationale for each.
```

One report per investigation run. Subsequent reports can
reference older ones to track progress.

---

## Performance budget

- Probe A: ~2 min wall time (parallelized via `&`)
- Probe B: ~30s per file × ≤10 files = ~5 min
- Probe C: ~1 min per file × ≤10 files = ~10 min
- **Total:** ~20 min for the full A+B+C sweep

This is investigation cost paid ONCE. The output PRs are then
sized normally per their own scope.

---

## Rollback strategy

Pure docs PR for design.md. Implementation PRs (Probe scripts +
fix PRs) are each independently revertable.

If the marker-based-xfail branch is chosen and later regretted,
revert the marker addition; the xfails revert with it. If the
fix-the-polluter branch lands a regression, standard `git revert`
applies.

---

## Testing strategy

Probe scripts are stdlib-only and self-contained. Tests for them:

- `tests/unit/scripts/test_probe_inventory.py` — feeds fake
  `gh run list` JSON, asserts categorization output is correct
- `tests/unit/scripts/test_probe_import_trace.py` — feeds a
  controlled module with known import side effects, asserts
  the trace catches them
- `tests/unit/scripts/test_probe_fixture_trace.py` — feeds a
  controlled conftest, asserts the parse extracts autouse +
  scope correctly

Fix PRs ship cross-platform regression tests per the
"fix-the-polluter branch" section above.

---

## Phase 3: Tasks — *(not started; will be authored after this design's approval)*
