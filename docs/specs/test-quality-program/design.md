# Design: Test Quality Program
**Status:** approved
---

## Phase 2: Design

### Architecture

Umbrella spec executed as a long-running sequence of small PRs.
No per-module sub-specs — each module gets a PR, a CHANGELOG
entry, and a row in `docs/COVERAGE_BUG_LOG.md`. The spec itself
stays open indefinitely; "completion" of an individual module is
its merged PR, not a spec status change.

```text
This spec (umbrella)
├── prioritization rubric         (Phase 2 — once)
├── per-module loop ("playbook")  (Phase 2 — once)
├── bug-class taxonomy            (Phase 2 — once)
└── module execution cycles       (Phase 3+ — many, indefinitely)
    ├── module A — PR #NNN, log entry, CHANGELOG
    ├── module B — PR #NNN, log entry, CHANGELOG
    └── ...
```

### Prioritization rubric

For each source module under `src/attune/` (and
`src/attune_software/` if any), compute:

```text
score = customer_weight × coverage_gap × risk_multiplier × usage_discount
```

Where:

**customer_weight** (1-5): How directly users encounter this
module. Higher means closer to a user-typed command or
user-visible output.

| Weight | Description | Examples |
|--------|-------------|----------|
| 5 | User-invoked directly (CLI entrypoint, MCP tool handler, ops route handler) | `cli_minimal.py`, `mcp/server.py`, `ops/routes/*.py`, `mcp/workflow_handlers.py` |
| 4 | Workflow internals shaping user-visible output | report formatters, output renderers, voice/formatter modules |
| 3 | Composed by user-invoked code (agents, models, retrievers that workflows orchestrate) | `agents/release/`, `models/registry.py`, RAG retriever |
| 2 | Middleware, validators, security boundaries (user-invisible but on every request) | `security/path_validation.py`, `mcp/rate_limiter.py`, `ops/middleware.py` |
| 1 | Deep plumbing (registries, dispatch tables, internal data classes) | `workflows/data_classes.py`, internal mixins |

**coverage_gap** (0.0-1.0): `1.0 - current_line_coverage`.
Compute from the latest `coverage.xml` produced by CI. Module
not in the coverage report → use `1.0` (treat as unknown).

**risk_multiplier**:
- `2.0` — security-sensitive: handles untrusted input, performs
  auth, validates paths, enforces sandboxing, signs/verifies,
  decrypts. Identify by import of `attune.security.*`, presence
  of `_validate_file_path`, or operation on `request.*` /
  `tool_input` fields.
- `1.5` — data-handling: persists user data, manipulates
  telemetry, writes to `~/.attune/`, mutates memory graph.
- `1.0` — else.

**usage_discount** (Phase 4): `min(1.0, inbound_imports / N)` with
`N = 5`. `inbound_imports` is the count of distinct files **outside the
module's own package** that import it — measured by `score_test_quality.py`
from the `from attune.… import …` / `import attune.…` statements across
`src/attune/` (both the direct `from pkg.mod import X` and the
parent-package `from pkg import mod` forms are counted). A module no code
imports is treated as under-used and its score is scaled toward zero, so
**orphan / "Removed" modules** (which previously topped the rubric on
weight×gap alone) sink out of the working set. `N = 5` was chosen so a
module needs a handful of real callers to earn full weight; tune it if
the working set skews too far toward or away from heavily-shared modules.

**Exemption — entry points are not discounted.** Weight-5 modules
(CLI / MCP / `__main__` / ops route handlers) are *invoked*, not
imported, so a zero inbound-import count is expected for them and must
not demote them; they always use `usage_discount = 1.0`. Without this
guard the discount would wrongly zero the most user-facing modules.

**Output of one scoring pass:** ranked CSV at
`docs/specs/test-quality-program/rubric_cache.csv` with
columns `module,customer_weight,coverage_gap,risk_multiplier,
inbound_imports,score,covered_pct,excluded,last_modified`. Refresh on
demand (when CI coverage XML changes meaningfully) and write back to
the same file. The top 20 rows are the working set; sessions pick from
there.

### Per-module loop ("the playbook")

For each module taken on:

```text
a. INVENTORY      What's covered, what isn't, what already exists
b. READ           Source first — identify behaviors and smells
c. DETERMINISM    Run existing tests solo AND in suite under xdist
d. FIX            Production bugs found in (b) and (c)
e. TRIAGE         Tests that stay / get rewritten / get deleted
f. WRITE          New tests for uncovered behaviors per "meaningful"
g. VERIFY         Module meets meaningful criteria + tests deterministic
h. SHIP           PR + CHANGELOG note + COVERAGE_BUG_LOG entry
```

Detail per step:

**(a) Inventory.** `coverage report -m --include="src/attune/<module>/*"`
to see current %. `grep -rl "import.*<module>\|from.*<module>"
tests/` to find existing tests. Note any `@pytest.mark.skip`,
`xfail`, or `integration` markers on the existing tests.

> **Diagnostic for the rubric — silently-skipped suites.** When a
> picked module has a *surprisingly low* `covered_pct` AND a
> non-trivial test file already exists, grep the test file for
> `pytest.importorskip(` BEFORE writing any new tests. If the suite
> gates the whole module on `importorskip("X")` and `X` isn't in the
> `[dev]` extra, every test silently skips in CI — so the module reads
> as undertested when its tests simply never ran. The fix is then one
> line in `pyproject.toml` (add `X` to `[dev]`), not a new test file.
> Same family as the usage-discount: the rubric is measuring a
> *measurement artifact*, not a real gap.

**(b) Read the source.** Walk public API surface. Note each
`raise`, each `if/elif/else` chain on enums or string switches
(2A candidates), each `for ... return ... if last_exception:`
(2B candidates), each `if x > 0: ... / x` (2C candidates), each
filter on already-filtered data (2D candidates). Note timing
smells: `time.sleep`, `time.time`, `datetime.utcnow` (naive),
`Path.rename` (Windows fragility), `sys.modules` manipulation in
tests, module-level state, sleep-based synchronization.

**(c) Determinism check.** Run existing tests three ways:
```bash
pytest tests/unit/<module>/                          # isolated
pytest tests/unit/<module>/ -p no:cacheprovider      # no cache
pytest tests/unit/ -n auto -k <module_keyword>       # under xdist
```
Any test passing in (1) but failing in (3) is cross-test
pollution — Class 5 bug, log it.

**(d) Fix.** Production bugs (Class 1-4) go in immediately,
either as part of the test PR or as a sibling PR if the change
touches >1 module. If a bug requires public-API change, **stop
and surface** — don't fold silently. Test-reliability bugs
(Class 5) get fixed alongside.

Two corollaries that follow from the Class 2 definition but
deserve to be explicit:

- **Dead defensive code → delete. Do not test it.** A Class 2
  branch is unreachable; writing a test for it requires
  contorting inputs in ways production code can't produce.
  Delete the branch, re-run coverage, and accept that the
  module's *natural ceiling* has moved up. The ceiling is
  wherever genuinely-reachable branches end — typically
  ~98% on modules with unreachable post-import code
  (dotenv/tiktoken try-imports), 100% on most others.
- **Never contort tests to hit a coverage number.** The
  rubric optimizes meaningful coverage, not line %. Step
  (f) writes tests for uncovered *behaviors*, not for
  uncovered lines. If a line resists testing, it's a (d)
  candidate (delete or fix), not an (f) candidate.

**(e) Triage existing tests.**

| Existing test shape | Action |
|---|---|
| Asserts on real public behavior, passes deterministically | Keep |
| Asserts on real behavior, sometimes flaky | Diagnose Class 5 root cause, rewrite |
| Asserts on implementation detail (mock internal helper, check it was called) | Rewrite to assert observable behavior, or delete if behavior already covered by sibling test |
| Asserts behavior that production no longer has | Delete with note in PR body |
| Mock-driven test where the mock target moved (see `ignored-tests/decisions.md` for canonical examples) | Either rewrite against real surface or delete with note |

**Surface non-trivial rewrites before doing them.** If
triage produces more than ~5 deletions or any rewrites of tests
not authored in the current session, pause and confirm scope.

**(f) Write new tests.** Anchor each new test to a behavior
named in "meaningful coverage" (requirements.md §Definition).
Prefer real objects to mocks per criterion 5. If a behavior
genuinely needs network/disk/subprocess: mark
`@pytest.mark.integration` and document why.

**(g) Verify.**
- Module meets the 5 meaningful-coverage criteria. Judgment
  call; the criteria list is the rubric.
- New tests run deterministically: full suite under `-n auto`
  three times in a row, zero flakes.
- Line coverage on the module is stable or improved (drops
  acceptable if a Class 2 deletion removed dead code).

**(h) Ship.**
- PR title: `test(<module>): meaningful coverage pass` (or
  `fix(<module>): <bug> + tests` if bugs dominate)
- CHANGELOG: line under `## [Unreleased]` →
  `### Internal` describing scope (modules touched, bug classes
  surfaced, tests added/removed).
- `docs/COVERAGE_BUG_LOG.md`: append session entry with bug
  classifications, links to commits, and module deltas.

### Bug-class taxonomy

Extend the existing log's classes 1-4 with class 5. All five
have stable definitions so the log stays scannable.

| Class | Name | Definition |
|-------|------|------------|
| 1 | Crash path nobody triggered | Production code throws on a real input shape; no test exercised the path. Fix the code. |
| 2 | Dead defensive code | Looks defensive but is unreachable; couldn't actually defend. Sub-patterns 2A-2D documented in COVERAGE_BUG_LOG. Fix by deleting or converting to raise. |
| 3 | Test mocking around the bug | Test passes by mocking the broken caller. Coverage looks fine; production is wrong. Fix the production code, rewrite the test against real surface. |
| 4 | Load-bearing comment nobody re-validated | Constraint encoded as a code comment is now stale. The bug is in the documented constraint, not the code. Re-validate and either remove the comment or codify the constraint as a test. |
| 5 | Test-reliability bug | Test is non-deterministic (timing/race), polluted by another test (sys.modules, global state, filesystem), or platform-fragile (Windows path semantics, macOS symlinks, time.time resolution). Fix in tests, not production. |

Class 5 is the home for the CLAUDE.md "Lessons Learned" patterns
that today have no formal classification.

### Relationship to sibling specs

| Sibling | Relationship |
|---------|-------------|
| `test-infrastructure/` (complete) | Built the CI execution model this program runs against. No further interaction. |
| `coverage-canonical-pattern/` (draft) | Owns CI coverage collection. This program consumes its `coverage.xml` output for the rubric. If it ships sub-canonical results, this program's rubric input degrades but the per-module loop still works. |
| `coverage-exclusion-policy/` (approved) | Owns the denominator. When the per-module loop finds a module that should be excluded rather than covered, hand off to that spec with a documented reason. |
| `ignored-tests/` (approved, resolved) | Demonstrated the "delete aspirational, reconcile drift" pattern at the file level. This program does it at the module level. |
| `redis-decoupling/` (approved) | Replaces fake Redis with real Redis. Its output is consumed by this program's loop step (f) — modules that depended on faked Redis become coverable for real once decoupling lands. |

### Risks

| # | Risk | Mitigation |
|---|------|------------|
| 1 | The rubric is gamed — sessions pick the highest-score module that's also easiest, ignoring the harder high-score ones. | "Working set" is top 20 rows. The next session must pick from that set; if the easiest is repeatedly chosen, the harder rows stay near the top and surface visibly over time. |
| 2 | "Meaningful coverage" is too subjective; future sessions interpret it inconsistently. | The 5 criteria in requirements.md §Definition are concrete enough to anchor judgment. Disagreements surface in PR review. |
| 3 | Bug-class 5 (test reliability) becomes a dumping ground for any test fix. | Definition is precise (non-determinism, pollution, platform-fragility). Other test refactors that don't fit don't get logged — only the bug-class entries do. |
| 4 | The spec stays "draft" forever because there's no obvious closure condition. | Closure isn't the goal — this is a standing program. Status moves to `active` after the first proof-of-concept module ships. Status only becomes `closed` if the program is wound down deliberately. |
| 5 | Scope creep into production architecture changes mid-loop. | Step (d) has an explicit "if a bug requires public-API change, stop and surface" rule. Surface, get agreement, then handle as a separate PR. |
| 6 | Rubric output is stale because nobody recomputes it. | Cache file `rubric_cache.csv` records its computation timestamp. Sessions should re-run scoring if the cache is older than ~2 weeks or after any large refactor. The scoring script is a small Python file in `scripts/`. |
| 7 | The 5th bug class duplicates existing CLAUDE.md lessons without adding signal. | The log is the durable home for class-5 entries; CLAUDE.md is for cross-cutting *lessons* (how to avoid the pattern). Both exist for different consumers. |

### Decisions to make at execution time

- **D1.** First module pick. After the rubric runs, the top 3-5
  candidates are surfaced; one is chosen by the session (or
  Patrick) based on energy / complexity / risk fit. Likely
  candidates from rough survey: `cli_minimal.py` (customer
  weight 5, single test file = high gap), `mcp/server.py`
  (weight 5, security-sensitive 2x, currently in exclusion
  list — investigate before scoring), `mcp/workflow_handlers.py`
  (weight 5, dispatches every MCP workflow call), `ops/routes/*`
  (weight 5, new surface).
- **D2.** Rubric script location. Default
  `scripts/score_test_quality.py`; output to
  `docs/specs/test-quality-program/rubric_cache.csv`. May move
  if a more natural location surfaces.
- **D3.** Coverage source. The rubric needs a recent
  `coverage.xml`. Initial pass can use whatever the latest CI
  artifact produced or a local `pytest --cov=src/attune
  --cov-report=xml` run. Document the source in the cache file
  header.
