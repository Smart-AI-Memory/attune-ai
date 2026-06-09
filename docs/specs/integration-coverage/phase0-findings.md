# Phase 0 findings — integration-coverage (2026-06-09)

The spec asked: *before building an integration-testing framework, measure
the actual gap.* The measurement flips the premise. **We don't need to
build integration testing — we already have a 351-test suite. It's just
dormant and rotting.**

## 0.1 — Inventory of `tests/integration/`

| Fact | Value |
|---|---|
| Test files | 30 |
| Tests collected | **351** |
| Run in CI? | **No** — `pytest.ini` does *both* `--ignore=tests/integration/` and `-m "not integration"`; `tests.yml` runs `-m "not network and not integration"`. No job runs `pytest -m integration`. |
| No-auth (CI-runnable free) | **22 files** |
| Auth-required (real `ANTHROPIC_API_KEY`) | **8 files** |
| Maintained? | Edited 6 days ago; 16 files touched in 90 days — **actively edited yet never executed** (the maintained-but-unrun paradox) |

**Rot found immediately (from never running):**
- `test_tier1_api.py` imports a non-existent `dashboard.backend.api`
  module (3-month-stale; the dashboard backend was removed) → **breaks
  collection** of the whole subtree.
- `rag/test_rag_workflow.py::test_execute_surfaces_sdk_generic_exception…`
  asserts the **pre-#543** error-result shape → **stale assertion** that
  drifted after the sdk-error-message-fidelity migration.
- The full no-auth run **hangs** without per-test isolation → some tests
  block (subprocess/socket) and need `--timeout` + isolation to run in CI.

## 0.2 — Catchability of recent bugs

| Source | Dominant class | Catchable by |
|---|---|---|
| `docs/COVERAGE_BUG_LOG.md` (per-module program finds) | Class 2 dead code (13), Class 1 crash (3), Class 3 mock-around-bug (1) | **unit** — the per-module program already handles these |
| Production escapes (CHANGELOG / CLAUDE.md lessons, last ~2 wks) | async event-loop blocking (#652), AMS mocked-vs-live (#588/#666/#667), env-var leak into pytest (#653) | **integration** — passed unit tests, caught only by dogfooding |

**Distribution:** routine finds are mostly unit-catchable dead code (the
steady-state program owns those). The **high-impact escapes** — the bugs
that actually reached `main` and users — cluster in a small, recurring
**integration-catchable** class: async/event-loop, mocked-vs-live external
services (AMS/SDK), and env/config leaks. That's exactly the
"passing tests don't prove integration / dogfood catches what unit tests
miss" lesson family, and exactly what the dormant `_with_auth` + live-
backend tests would exercise *if they ran*.

## 0.3 — Decision: **GO, reframed — revive, don't build**

The impact-per-effort winner is **not** a new framework. It's reviving the
suite we have, in three bounded steps:

1. **Prune the rot** (cheap, ~1 PR): delete/fix `test_tier1_api.py`; fix
   the stale rag assertion; add `--timeout` + isolate the hangers.
2. **Wire the 22 no-auth files into CI** as a dedicated `integration`
   job (runs free, no API key) so the suite stops drifting and the
   integration-catchable class is gated going forward.
3. **Auth-required 8 → opt-in nightly / `workflow_dispatch`**, budget-
   bounded on `ANTHROPIC_API_KEY` (real API cost; don't gate PRs on it).

Keep the per-module unit program for the dead-code/crash bulk — integration
coverage is a **targeted complement**, not a second big program.

**Why GO and not NO-GO:** the integration-catchable bug class is real and
recurring (4+ escapes this fortnight), and the marginal cost is low because
the tests already exist — the work is revival + a CI job, not authorship.
**Why reframed:** the spec's "build a framework" premise was wrong; building
new infra on top of 351 ignored tests would compound the waste.

**Next:** Phase 1 = step 1 (prune) + step 2 (wire no-auth job). Step 3
(auth nightly) is a follow-up. Estimated 1–2 PRs.
