# Next Session — Quick Start

Pickup card for the per-module loop. Pair with
`design.md` (loop steps) and `requirements.md` (meaningful
criteria + bug taxonomy).

## Refresh the rubric

Only if `rubric_cache.csv` is stale (>~2 weeks) or after a
large refactor:

```bash
pytest tests/unit/ -n auto \
  --cov=src/attune --cov-report=xml:/tmp/coverage.xml -q \
  -m "not network and not integration"

python3 scripts/score_test_quality.py /tmp/coverage.xml
```

Expected ~60s on a clean venv.

## Pick a module

Default: top non-`workflows/` row in `rubric_cache.csv`.

Recommended candidates as of 2026-05-12:

- `src/attune/memory/short_term/conflicts.py` — score 3.35,
  25.4% covered, data-handling risk. No WIP overlap. No
  dedicated test file yet.
- `src/attune/ops/cli.py` — score 3.19, weight 5, 36.2%
  covered. User-typed `attune ops` entry. Some coverage
  at `tests/unit/ops/test_smoke.py`.

Before picking anything under `src/attune/workflows/`,
diff the local WIP branch — see
`memory/project_wip_recovery_2026_05_11.md`.

## Per-module loop

From `design.md`:

a. INVENTORY — coverage %, existing tests, markers
b. READ — source first; identify behaviors and smells
c. DETERMINISM — solo AND under `-n auto`
d. FIX — production bugs (Class 1-4) + test-reliability (Class 5)
e. TRIAGE — keep / rewrite / delete existing tests
f. WRITE — new tests anchored to meaningful criteria
g. VERIFY — meaningful + deterministic (3 back-to-back)
h. SHIP — PR + CHANGELOG + `docs/COVERAGE_BUG_LOG.md` entry

## Worktree gotcha

`uv run attune <cmd>` serves the MAIN repo's source, not the
worktree. When iterating on worktree code, run tests via the
venv directly:

```bash
/Users/patrickroebuck/attune-ai/.venv/bin/python -m pytest \
  tests/unit/<path> --no-header -q
```

## Scope guard

One module per session is ambitious. One module + a real bug
fix is the sweet spot. If a bug requires public-API change
or touches >1 module, STOP and flag — don't fold silently.
