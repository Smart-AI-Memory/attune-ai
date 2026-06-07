# Spec: CI Test-Matrix Failures

**Status**: complete (2026-05-10) — Phase A `68f19b90`, Phase B `28441852`, Phase C `463df6a5`

---

## Phase 3: Tasks

### Phase 3A — Setup

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Capture the **current** CI baseline. Run `gh run list --workflow=tests --branch=main --limit=1 --json conclusion,jobs` and record the green/red count per OS+Python combo. | CI | todo | Reference for Phase 3D delta checks. |
| 2 | Spot-check that **at least one** test in each failing category currently fails locally too (when run with `pip install -e .[dev]` only, no extras). Confirms the diagnosis isn't CI-environment specific. | local + CI | todo | Quick sanity check. If a test passes locally but fails in CI with the same install, the root cause is something else (e.g. ordering, fixture state) and the spec needs to widen. |

### Phase 3B — Per-phase resolution

Each row is a single PR. Verify the matrix delta after each before
moving on.

| # | Phase | Layer | Status | Notes |
|---|-------|-------|--------|-------|
| 3 | **A: Expand `[dev]` + resolve tiktoken contract.** Edit `pyproject.toml` `[dev]` extra to add `redis>=5.0.0,<8.0.0`, `langchain-anthropic`, and `tiktoken`. Add a new `TestGetEncodingPathsNoTiktoken` test class in `tests/unit/models/test_token_estimator.py` that uses `unittest.mock.patch` on `attune.models.token_estimator.TIKTOKEN_AVAILABLE` to exercise the no-tiktoken fallback path. Push, verify CI: ubuntu + macos jobs go green; Windows still fails on encoding + path-separator. Expected: 8/12 green. | `pyproject.toml`, tests | todo | If `tiktoken` install proves fragile (Rust wheel issues), pin to a known-good version with `--only-binary=:all:`. Last-resort fallback: `pytest.importorskip("tiktoken")` at module top + remove the new no-tiktoken test class (loses coverage). |
| 4 | **B: Windows cp1252 stdout.** Add the `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` idiom (gated on `sys.stdout.encoding != "utf-8"`) to `plugin/hooks/compact_warning.py`, `plugin/hooks/spec_orient.py`, and any sibling `plugin/hooks/*.py` with `sys.stdout.write` / `print()` calls. Push, verify CI: Windows jobs now fail only on the path-separator test. Expected: 11/12 green. | `plugin/hooks/*.py` | todo | Audit ALL `plugin/hooks/*.py` — apply uniformly as a defensive default for hook output. Don't try to guess which scripts are "safe." |
| 5 | **C: Windows path separator.** `git grep ATTUNE_AI_WORKSPACE_ROOTS` to locate the production parser; change `.split(":")` → `.split(os.pathsep)`. Update the test at `tests/unit/hooks/test_session_continuity_state.py:250` to use `os.pathsep.join(...)`. Add a one-line note wherever the env var is documented (CLAUDE.md, README) saying "uses `os.pathsep` (`:` POSIX, `;` Windows)." Push, verify CI: all 12 matrix jobs green. | parser + test + docs | todo | Production fix and test fix ship together. |

### Phase 3C — Verification

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 6 | After Phase 3B #5 lands, **trigger a no-op CI run** (e.g. push a docstring fix to a feature branch). Confirm all 12 matrix jobs green from a clean state. | CI | todo | Catches order-of-operations issues — e.g. a test that passed in earlier phases because of leftover state. |
| 7 | **Dependabot proof.** Find PR #191 or #192 (or the next dependabot PR), wait for it to rebase against the now-green `main`, confirm CI passes. Merge it. | dependabot | todo | This is the G4 success criterion: a dependabot PR lands without manual override of failing CI. |
| 8 | **Tiktoken contract audit.** `grep "tiktoken" pyproject.toml tests/unit/models/test_token_estimator.py` should show consistent treatment: tiktoken in `[dev]` AND test classes covering both `TIKTOKEN_AVAILABLE` paths. | manual | todo | Verifies G3. |
| 9 | **Hook-script audit.** `grep -rE "sys\.stdout\.write\|^\s*print\(" plugin/hooks/` returns no unprotected writes. | manual | todo | Verifies the audit step from Phase 3B #4 was complete. |

### Phase 3D — Spec close

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 10 | Set this spec's status to `complete` (in all three .md files). Optionally write a short retro paragraph in `decisions.md` (create if useful) noting how long CI had been red and what surfaced it. | docs | todo | The "discovered while verifying ignored-tests landing" framing is worth preserving — test-infra debt comes in layers. |

### Failure-to-deliver path

If Phase 3B #3 reveals tests that need a real Redis server (not
just the `redis-py` library):

1. Mark Phase 3B #3 as **partial**.
2. For server-requiring tests, add
   `@pytest.mark.skipif(...)` with a documented reason, or move
   to `tests/integration/` (already excluded from the unit run).
3. Continue with Phases 3B #4 and #5 — independent.
4. The spec ends as **partial**: matrix mostly green, N tests
   documented as skipped on server-less CI. Document the skip
   count in decisions.md.

The spec is **done** when `gh run list --workflow=tests --branch=main --limit=5`
shows 5/5 green and a dependabot PR has landed without CI override.
