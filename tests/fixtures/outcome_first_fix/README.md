# Outcome-First Fix — canonical scenario fixture

The deterministic fixture for the hardened failing-test scenario
(docs/specs/outcome-first-fix/, decisions.md D1): a tiny pricing
module with ONE seeded off-by-one bug, one failing target test,
and green sibling tests.

The done conditions the scenario proves are plural and distinct:

1. the target test passes;
2. the full fixture suite is green;
3. the fix lands in `pricing.py`, never in the tests.

`pricing_suite.py` deliberately does NOT match the repo's pytest
discovery patterns (`test_*.py` / `*_test.py`), so the main suite
never collects the seeded failure. It is executed explicitly, as
a real subprocess boundary, by
`tests/unit/characterization/test_outcome_first_phase0.py`.

Do NOT fix the seeded bug — the bug IS the fixture. Phase 2 runs
`attune fix` against a COPY of this directory.
