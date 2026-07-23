# Agent work handoff

## Goal

Finish the chair-approved capability-count projector
(roundtable `q-capability-count-projector-001`): three derived
values projected into a frozen allowlist of claim sites, with
independent drift gates retained and a `--check` step in
import-capable Linux CI.

## Acceptance criteria

- `python scripts/project_capabilities.py --check` exits 0 on a
  synced tree; drift exits 1 with value/target/expected/observed;
  structural failure exits 2 before any write.
- A second `--write` is byte-idempotent.
- Markdown claims carry `<!-- cap:VALUE -->…<!-- /cap -->`
  whole-fragment ownership markers; marketplace JSON is parsed
  (no comment markers); `features.ts` updates only named
  `CAPABILITIES` fields.
- Focused tests cover derivations, unequal registered/core
  totals, all locator types, fail-closed modes, preservation,
  and subprocess exit codes.
- Independent gates keep their own derivation (no projector
  imports) and stay green.

## Scope and assumptions

- Branch/worktree: `codex/capability-projector` at the main
  checkout `~/attune-ai` (Fable session per
  `new session starter.md`; no commit/push/PR made — by
  instruction).
- Provider/session: Claude Fable 5, 2026-07-22 late.
- Assumptions: current derived values 25 skills / 53 registered
  / 47 core-schema; PRs #1605/#1607 will shift tool counts at
  the Monday lift — rerun `--write` after they merge if this
  branch lands later.

## Current state

- Status: implementation complete; all verification receipts
  green; NOT committed (session contract forbade it).
- Changed files (working tree):
  - `scripts/project_capabilities.py` (untracked; reworked —
    marker locators, per-file sequential planning, atomic
    writes, `main(argv, repo=None)`)
  - `tests/unit/scripts/test_project_capabilities.py`
    (untracked; 39 tests)
  - `README.md`, `plugin/README.md`,
    `docs/getting-started/quickstart-plugin.md`,
    `docs/getting-started/mcp-integration.md` (markers + two
    stale counts repaired by `--write`: plugin intro 18→25,
    quickstart natural-language 17→25)
  - `tests/unit/gates/test_claim_drift.py` (5 regexes made
    marker-tolerant via `(?:<[^>]*>)?`; assertions unchanged)
  - `.github/workflows/tests.yml` (coverage job: "Check
    capability count claims" step after badge freshness)
  - `CONTRIBUTING.md` (one-paragraph instruction: capability
    PRs run `--write`)
  - `docs/reports/roundtable/q-capability-count-projector-001.md`
    (untracked design report, unchanged — commit with the rest)
- Decisions: marker grammar `<!-- cap:VALUE -->` one-line spans;
  gate regexes updated (sanctioned by the gate's own
  "update the manifest WITH the wording" rule — independence
  preserved, guarded by
  `test_independent_gates_do_not_import_projector`).
- Risks/open: none known; merge-order interaction with
  #1605/#1607 handled by rerunning `--write`.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Claims synced | `.venv/bin/python scripts/project_capabilities.py --check` | pass (exit 0; 25/53/47) |
| Write idempotent | shasum 6 governed files, rerun `--write`, `shasum -c` | pass (byte-identical) |
| Projector tests | `pytest tests/unit/scripts/test_project_capabilities.py -p no:xdist -o addopts=` | pass (39) |
| Independent gates | `pytest tests/unit/gates/test_claim_drift.py tests/unit/test_website_version_accuracy.py` | pass (29) |
| CI/workflow governance | `pytest tests/unit/ci/` | pass (326, 1 skip) |
| Quality ratchet | `pytest tests/unit/quality/` | pass (5) |
| Scripts neighborhood | `pytest tests/unit/scripts/` | pass (227) |
| Format/lint | pinned pre-commit black + `uv run ruff check` on changed py files | pass |
| Preflight | `python scripts/collaboration_preflight.py` | pass (0 failed) |
| Whitespace | `git diff --check` | clean |

## Next action

Patrick reviews the diff on `codex/capability-projector`,
commits (pre-flight already pinned-black clean), and opens the
PR; delete this handoff when the branch merges.
