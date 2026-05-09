# Per-file resolution decisions — `--ignore`-d test files

Append-only log. One section per file as it's resolved. See `requirements.md`,
`design.md`, `tasks.md` for the framework.

---

## `tests/unit/workflows/test_orchestrated_release_prep.py`

**Date:** 2026-05-09
**Initial classification:** R1 REPAIR (5/35 fail, 14%)
**Final classification:** **R3 RETIRE — no salvage**
**Action:** File deleted.

**Why the reclassification.** A 30-minute read of
`src/attune/workflows/orchestrated_release_prep.py` surfaced what the
audit didn't: the production module is **explicitly deprecated**.
Header at lines 3–5 reads ".. deprecated:: 5.2.0 — use
`ReleasePrepTeamWorkflow` from `attune.agents.release`. Remove in v6.0."
Current attune-ai is **v6.6.0** (`pyproject.toml`), so the module is
six minor versions past its scheduled removal date and still around for
backwards-compat re-exports.

**Why no salvage.**

- The replacement, `ReleasePrepTeamWorkflow`, exists at
  `src/attune/agents/release/release_prep_team.py:359` and has its
  own tests at `tests/unit/agents/test_release_prep_team.py`.
- The dataclasses being tested (`QualityGate`, `ReleaseReadinessReport`)
  are **duplicated** in `src/attune/agents/release/release_models.py`
  with their own tests at `tests/unit/agents/release/test_release_models.py`.
  The deprecated module re-exports the old copies; the new copies are
  the live ones.
- The 30 "passing" tests were therefore not unique coverage — they
  test code that's on the way out, with parallel coverage already
  in place for the live equivalents.

**Recovering passing tests as active coverage** (G3 from
requirements.md) is moot here: the tests assert the API of a
deprecated module. Rewriting them against the new module would
duplicate `tests/unit/agents/release/test_release_models.py` and
`tests/unit/agents/test_release_prep_team.py`. Better to delete.

**Out-of-scope follow-up:** the production module itself is overdue
for removal (deprecated v5.2.0 → "Remove in v6.0" → we are at v6.6.0).
That deletion is **not** part of this spec — flagging it for a
separate task. Risk to be aware of if removed: the re-exports at
`src/attune/workflows/__init__.py:160` and `src/attune/agents/__init__.py`
must be updated, and downstream consumers may import from the
deprecated path.

---

## `tests/unit/models/test_execution_and_fallback_architecture.py`

**Date:** 2026-05-09
**Initial classification:** R3 RETIRE with salvage (41/52 fail, 79%)
**Final classification:** **R3 RETIRE — no salvage**
**Action:** File deleted.

**Why no salvage.** The file is explicit about its aspirational nature
in the docstring: "Coverage Target: 95%+ (from 21-73%)" and contains
live admissions of drift in code:

```python
# NOTE: FallbackPolicy may not exist or have different API - Gap 3.2
# from attune.models.fallback import FallbackPolicy, FallbackTier
...
# Placeholders for architectural gaps that still exist
FallbackPolicy = None
FallbackTier = None
```

Every fallback test then calls `FallbackPolicy()` against the `None`
placeholder — TypeError on every line. These weren't failing because
of regression; they were never written against real production code.

The salvage step required by Path R3 in design.md (walk the 8
invariants, check existing coverage) showed that **every category is
already covered elsewhere**:

| Test category in retired file | Existing covering tests |
|---|---|
| Cat 1 — Model Registry & Selection | `tests/unit/models/test_registry.py`, `tests/unit/models/test_model_registry_class.py` |
| Cat 2 — LLM Executor Interface | `tests/unit/models/test_empathy_executor_new.py`, `tests/unit/models/test_resilient_executor_coverage.py` |
| Cat 3 — Fallback Policy | `tests/unit/resilience/test_fallback.py` |
| Cat 4 — Circuit Breaker | `tests/unit/resilience/test_circuit_breaker.py`, `tests/unit/trust/test_circuit_breaker.py` |
| Cat 5 — Cost Tracking | `tests/unit/telemetry/test_usage_tracker.py`, `tests/unit/models/test_telemetry_storage_coverage.py` |
| Cat 6 — Routing Decisions | `tests/unit/models/test_adaptive_routing_coverage_boost.py` |
| Cat 7 — Provider Switching | covered by Cat 3 fallback tests |
| Cat 8 — Telemetry & Logging | `tests/unit/telemetry/` directory |

The 11 "passing" tests in the retired file were basic sanity checks
that duplicate the existing `test_registry.py` (e.g. "registry
initializes", "tier cache has 3 entries"). Nothing unique to recover.

**No follow-up production work flagged** — production code under test
is healthy and has live coverage. The retired file was a write-only
artifact of an in-progress sprint that never reconciled with where
the implementation actually landed.

---

## `tests/unit/scaffolding/test_scaffolding_cli.py`

**Date:** 2026-05-09
**Initial classification:** R3 RETIRE with salvage (28/42 fail, 67%) — possibly downgrade to R2 RECONCILE if cli.py is small enough
**Final classification:** **R3 RETIRE — no salvage**
**Action:** File deleted.

**Why no salvage / no downgrade.** The `cli.py` reading
(228 lines, mostly argparse plumbing) confirmed the deprecation
hypothesis but moved the verdict harder, not softer:

- **Production CLI is deprecated.** `src/attune/scaffolding/__main__.py:16`
  unconditionally emits a deprecation notice (`_emit_cli_deprecation(
  "attune.scaffolding", "attune workflow run")`) before invoking
  `main()`. Every user invocation prints "use `attune workflow run`
  instead."
- **Excluded from coverage.** `pyproject.toml:630-631` excludes both
  `*/scaffolding/cli.py` and `*/scaffolding/__main__.py` from coverage
  measurement. The project itself doesn't expect this CLI to be
  tested.
- **No callers in production code.** `cmd_create`, `cmd_list_patterns`,
  `main` are referenced only by the CLI's own `__main__.py` and (was)
  the deleted test file. Not wired into the `attune` console script.
- **Mocks had moved out from under the production code.** The test
  file's heavy `sys.modules["test_generator"] = MagicMock()` and
  `sys.modules["patterns"] = MagicMock()` injections (lines 21–24) are
  the textbook smell for a mock-driven test that lost its target.

The 14 "passing" tests were exercising argparse subcommand wiring for
a deprecated CLI surface. Salvage value: zero.

**Out-of-scope follow-up:** the production module is similarly overdue
for removal. `attune.scaffolding` and `orchestrated_release_prep` are
both legacy CLI/workflow surfaces deprecated in favor of
`attune workflow run`. A separate retirement spec for these modules
themselves would be reasonable — not in scope here. If pursued,
verify nothing on PyPI / in attune-* sibling packages still imports
`attune.scaffolding`.
