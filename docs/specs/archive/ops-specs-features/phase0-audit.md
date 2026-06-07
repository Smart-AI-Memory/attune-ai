# Phase 0 audit — Gate + Scope re-check

**Date**: 2026-05-12
**Method**: verify gate conditions 0.1b and 0.5; verify the
"What we port" scope against the current `src/attune/ops/` state.
**Outcome**: **All gate conditions met. Spec already executed in
practice.** Phases 1–3 are shipped, tested, and live on main.
Tasks.md has stale Phase 1 checkboxes that didn't get flipped after
PR #236 merged.

---

## Gate condition 0.1b — CI status

Most-recent 3 main runs of the Tests workflow:

| Run | SHA | Conclusion | Notes |
|---|---|---|---|
| 25767167766 | `fca8c2d7` | success | PR #288 (test_runner coverage) — latest |
| 25765740637 | `7d988f52` | success | PR #287 (help_commands coverage) |
| 25763743950 | `9bc97bc0` | failure | PR #286 (control_panel coverage); one flaky timeout test (`test_multiple_timeout_decorators_independent` — 50ms threshold). Not the spec's named pre-existing failures, but not a new failure mode either. Subsequent runs green. |

**Verdict: GATE 0.1b SATISFIED.** Two consecutive green runs on
`main`; the one earlier failure was a known-class timing flake on a
50ms threshold, not a new regression. The two named pre-existing
failures (`Py 3.10 test_chain_executor`, Windows xdist `#232`) did
not surface in these runs.

---

## Gate condition 0.5 — Scope re-check

The spec listed (decisions.md "What we port"):

1. ✅ **List specs** across `docs/specs/` — **DONE** via PR #236
2. ✅ **Status display + flip** — **DONE** via PR #239
3. ✅ **Per-spec drill-in (read-only view)** — **DONE** via PR #236 + #239 (templates + routes)

Verified by inspecting `src/attune/ops/`:

| Capability | Implementation |
|---|---|
| `GET /api/specs` | `src/attune/ops/routes/specs.py:159` |
| `GET /api/specs/{slug}` | `src/attune/ops/routes/specs.py:186` |
| `PUT /api/specs/{slug}/{phase}/status` | `src/attune/ops/routes/specs.py:339` |
| `--specs-root` CLI flag | `src/attune/ops/cli.py:45` |
| Multi-root config | `src/attune/ops/cli.py:117` (`specs_roots=tuple(...)`) |
| `_STATUS_RE` + `_VALID_STATUSES` | `src/attune/ops/routes/specs.py:50,62` |
| `--read-only` enforcement | `src/attune/ops/routes/specs.py:351-357` (403 on mutate) |
| Atomic write | `src/attune/ops/routes/specs.py:261` (`_atomic_write`) |
| Specs template | `src/attune/ops/templates/specs.html` |
| Specs tab in nav | confirmed via `/specs/{slug}` links rendered in template |

Tests at parity with spec's Phase 1.3 requirements:

| Phase 1.3 requirement | Test |
|---|---|
| Empty roots | `test_list_specs_empty_roots_returns_empty` |
| Single root with multiple specs | `test_list_specs_single_root_multiple_specs` |
| Multi-root with naming collisions | `test_list_specs_multi_root_collision_preserved` + `test_get_spec_first_root_wins_on_collision` |
| Phase file missing | `test_list_specs_ignores_dirs_without_phase_files` |
| Malformed phase file (no Status line) | `test_list_specs_malformed_status_line` |
| Path traversal rejection | `test_get_spec_rejects_path_traversal` |

Full test run: `pytest tests/unit/ops/test_specs_*.py -n auto` →
**54 passed in 3.63s**.

**Verdict: GATE 0.5 SATISFIED.** Scope did not need adjustment;
the originally-decided scope is fully implemented and matches the
delivered code.

What was NOT ported (per decisions.md):
- Spec creation from slug — confirmed absent (no POST endpoint).
- Phase bootstrap from template — confirmed absent.
- Editor integration — confirmed read-only only.
- Living docs / corpus / template-editor surfaces — confirmed absent.

---

## What's actually left

Per tasks.md, Phase 4 (reflection cycle):

- **4.1** After 2 weeks of usage, log which features are used most → pending usage data, by design
- **4.2** Decide whether Phase 1's read-side is enough → pending usage data
- **4.3** If usage warrants, file a follow-up spec for additional surface → pending usage data

Phase 4 is **time-gated, not work-gated**. It expects 2 weeks of
real-world usage before evaluating whether to expand scope. No
implementation work is pending.

---

## Recommendation

1. **Mark Phase 0 fully satisfied** in tasks.md (currently shows
   `[ ]` on 0.1b and 0.5 — both verified above).
2. **Mark Phase 1 tasks 1.1, 1.2, 1.3 as done** with their resolving
   PR references (#236) — matches the existing Phase 2 / Phase 3
   markings.
3. **Flip spec status** from "Approved & Prioritized (2026-05-11)
   — gate relaxed; ready when next main CI settles" to **"Phases
   1–3 done; Phase 4 reflection cycle awaiting 2 weeks of usage
   (target: 2026-05-25)"**. The implementation half of the spec is
   complete; the reflection half is on a calendar.

The audit does NOT recommend opening a follow-up spec yet — that
decision is Phase 4's whole point and depends on data we don't have.

---

## What this audit does NOT do

Per the Tier-1-pure-audit framing: **no production code changes.**
Only updates the spec's own tracking docs. The implementation has
been on main for days; this PR just brings the spec's checkbox
state in line with reality.
