# Workflow-probe planted-defect fixtures

Fixture pack for `scripts/workflow_probe_runner.py` — validating the
"working" verdicts from the workflow fleet probe (roundtable
`q-workflow-fleet-health-001`, 2026-08-23, chair-promoted into
`docs/specs/test-quality-program/`). Each fixture plants a KNOWN
defect; the probe runner runs an LLM workflow against a copy and
asserts the workflow actually finds it.

Conventions (same as `tests/fixtures/outcome_first_fix/`):

- **Do NOT fix the seeded defects — the defects ARE the fixture.**
  Each is marked inline with a `# SEEDED BUG:` comment.
- Filenames deliberately avoid pytest discovery (`test_*.py` /
  `*_test.py`), so the main suite never collects them.
- Probes run against a COPY of these files in a temp workdir,
  never against this directory.

## Contents

| Path | Probed workflow | Planted defect |
|------|-----------------|----------------|
| `security/vulnerable_service.py` | security-audit | one `eval()` call (CWE-95) + one fake hardcoded API key |
| `dependency/cve_pins.txt` | dependency-check | pins with known CVEs (requests 2.19.1 / CVE-2018-18074, PyYAML 5.3.1 / CVE-2020-14343) |
| `testgen/orders.py` | test-gen | no defect — a small branchy module with zero tests; emitted tests must import, run, and pass against it |
| `analytical/sample_service.py` | code-review, deep-review, perf-audit, refactor-plan, simplify-code, test-audit, doc-audit | ONE shared multi-defect file (Phase 3): O(n²) scan, duplicated `validate_*` blocks, nested conditional, mutable default arg, swallowed exception, no tests, a missing docstring — each analytical probe asserts its own class |

Notes:

- `dependency/cve_pins.txt` is intentionally NOT named
  `requirements.txt` — GitHub security alerts scan any
  `requirements*.txt` in the repo and would flag the planted pins
  forever. The runner stages it into the probe workdir AS
  `requirements.txt`.
- The fake key in `security/` carries `# pragma: allowlist secret`
  and an obvious `FAKE` marker; detect-secrets excludes `tests/`
  anyway.
- discovery-sweep and release-notes have no committed fixture:
  the sweep probe targets a workdir staged from the three
  fixtures above, and the release-notes probe builds a throwaway
  git repo with planted commit history at run time.

`tests/unit/scripts/test_workflow_probe_runner.py` guards fixture
integrity (the planted defects are still present) for free on
every CI run; the LLM probes themselves are billed and run only
via the script (never per-push CI).
