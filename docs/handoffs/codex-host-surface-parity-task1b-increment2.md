# Agent work handoff

## Goal

Deliver host-surface-parity Task 1B increment 2 in its own PR, with Claude
reviewing. Increment 3 owns runtime routing and missing production receipts.

## Acceptance criteria

- Every discovered boundary root is registered, with helper provenance intact.
- Each claimed Task 1B check has a failure-sensitive test; unclaimed checks
  remain explicit in the ledger and PR.
- The held R4b observation is folded into the ledger without promoting it to
  a replayable parity receipt.
- At least 90% changed-code coverage, whole-tree run before push, zero spend.

## Scope and assumptions

- Branch: `codex/host-surface-parity-task1b-increment2`.
- Base: `e884f599d732bb1cc5582e77a6113ec32096d489` (main after #2445 and its docs rebuild).
- Codex authors; Claude reviews. Main's separate dirty checkout was untouched.
- Chair ruling, 2026-09-06: inventory success must not imply complete parity;
  missing runtime receipts are explicit increment-3 obligations and cannot
  make routes admissible. Recorded in the Task 1B execution log.

## Current state

- `surface_registry.py`: producer/transport associations, typed obligations,
  digest-bound evidence, explicit pending keys, strict receipt validation,
  experiment metadata checks and a route evidence precondition. D13 replaces
  the embedded baseline copy with a canonical content pin. Validation resolves
  and verifies the fixture before reporting inventory or checking experiments.
- `surface_evidence.py`: installed attune-forms projection/common-collector
  replay. Does not claim stateful attune-ai lifecycle or host-display truth.
- `parity-registry.json`: 35 discovered roots, two declared transport owners,
  three executed package receipts, 155 pending local runtime obligations.
- `receipts.md`: machine receipt explanations, per-check coverage map and R4b
  observation, including the timing-based server-attribution limitation.
- Canonical collaboration contract and its three projections updated.
- Live experiment activation is blocked until current artifact and decision
  references can be verified; synthetic interval tests do not activate trials.
- The runtime route policy is not implemented here. Increment 3 must consume
  the evidence precondition; existing direct compatibility paths are unchanged.

## D13 rebase and current verification

Patrick merged #2445 at `9010a5a034bd594c919f3141e2ba3ad551c6a8f7`
on 2026-09-06. #2444 was then rebased onto current origin/main above with
`git rebase --gpg-sign origin/main`. No conflicts occurred. Before this
handoff update, `git range-diff` reported the parity patch identical to
previous head `225c721cc27fddd10f5cc08f4dc56dd06a79e67b`.
Both upstream Unreleased entries remain above the parity entry; no conflict
markers remain. Fixture regeneration produced no diff. The D13 canonical
pin, both new hook subjects, and the 158-obligation accounting are unchanged.

Current verification uses this checkout's committed `tests/conftest.py` and
`tests/_inference_guard.py`, not an externally injected guard. Guard and
application import paths were verified inside this worktree. Python 3.11.14
in `.venv` loads the released attune-forms 0.14.0. The disposable Redis wrapper
supplies per-worker fixture databases, empty provider keys and a private child
Claude configuration; normal interactive authentication is untouched.

- Fixture regeneration: `.venv/bin/python -c "from pathlib import Path;
  from attune.elicitation.surface_inventory import write_baseline;
  write_baseline(Path('.'),
  Path('docs/specs/host-surface-parity/producer_baseline.json'))"`.
  No diff.
- Gates + quality: `TIKTOKEN_CACHE_DIR=/private/tmp/2445-cold-tiktoken-cache
  ANTHROPIC_API_KEY="" .venv/bin/python /private/tmp/run_2445_suite.py
  tests/unit/gates tests/unit/quality -q -n 0 -o addopts=
  --cov=attune.elicitation.surface_registry
  --cov=attune.elicitation.surface_evidence --cov-branch
  --cov-report=json:/private/tmp/2444-post2445-coverage.json
  --cov-report=term-missing --cov-fail-under=90`.
  **588 passed in 61.75s; 99.49% statement/branch coverage**.
  Registry: all 354 executable lines covered, 99.79% with branches;
  evidence: 98.26%. Log: `/private/tmp/2444-post2445-gates-quality.log`.
- Whole configured tree: `TIKTOKEN_CACHE_DIR=/private/tmp/2445-cold-tiktoken-cache
  ANTHROPIC_API_KEY="" .venv/bin/python /private/tmp/run_2445_suite.py
  tests -n auto`.
  **25,833 passed, 241 skipped, 3 xfailed in 76.49s**, exit 0.
  Log: `/private/tmp/2444-post2445-whole-tree.log`.
  No ad hoc test substitution or selection changes. The merged inference
  isolation suite's integration/network classifications remain in force.
- Collaboration projector `--check`: unchanged projections.
- Pinned pre-commit results, final signed head, remote CI and the exact
  changed-file manifest are recorded on #2444 after this handoff update.
- No API-backed workflow or live-provider probe was run. September 6 usage
  estimates remain unattributed; dates/models do not identify a session.

Historical post-D13 receipt: before #2445 merged, an external guard stopped
standalone #2444 collection with 24 worker errors at two ambient AMS probes
(`/private/tmp/2444-conflicts-whole-tree.log`). That was a failed receipt.
The current committed-guard run above supersedes that blocker. The earlier
combined-head Python 3.12 run passed 25,842 tests; its different interpreter
and selection counts do not replace the current Python 3.11 receipt.

## Next action

Publish the signed rebase with an exact force-with-lease against
`225c721cc27fddd10f5cc08f4dc56dd06a79e67b`, and post current receipts and the
changed-file manifest. Verify fresh CI at the pushed head. Claude reviews;
the chair merges. Previous green CI and review do not certify the new SHA.
Do not auto-merge or launch a paid review agent.

Patrick accepted a subsequent bounded Codex form-to-validated-answer milestone
with repeatable visible-display timing. Its brief is in the session starter;
implementation follows the reviewed #2444 merge on a fresh branch. It is not
part of this increment. The parity gate still asserts parity only over
registry-named subjects; inventory success is not complete runtime parity.

## Historical increment-2 verification before D13

These are historical receipts from the original increment-2 head. They do not
certify the rebased D13 head or replace its required whole-tree validation.

| Claim | Probe actually run | Result |
| --- | --- | --- |
| Merged handoff verified | fetch origin main; log origin/main | #2443 at base above |
| Baseline before source edits | locked venv, parity gate | 54 passed |
| Released registry prerequisite | installed 0.14.0, no editable direct_url; execute canonical targets | 7 non-empty projections; registry f054ffb68bfd…; fixture 4cae50847592… |
| Focused parity and changed-code coverage | parity gate with both new modules, `--cov-fail-under=90` | 141 parity tests; 99.48% combined |
| Repository guards | parity + projector + complexity + deserialize + path-validation tests | 181 passed before final hook/renderer mutation; final whole-tree run covers all guards |
| Whole tree | all configured tests, disposable Redis, empty Claude credentials | 25,638 passed, 241 skipped, 3 xfailed (72.90s) |
| Pinned hooks | pre-commit on all changed files | pass |
| R4b telemetry | reread the held instance's render/submit rows | matching instance, 01:41:28.127872Z to 01:41:51.111595Z on 2026-09-06 |

Use `.venv/bin/python`: the global Python has an older attune-forms without
renderer_registry. The venv was installed with `uv sync --frozen --extra dev
--extra developer`.

Whole-tree environment details: the sandbox initially blocked loopback and
profile fixtures. An unrestricted attempt reached a legacy unmarked Redis
integration module; it was interrupted. The final run used a disposable
loopback Redis with no persistence. A temporary pytest plugin restored its URL
only for `tests/memory/test_redis_integration.py`, after the suite's Redis-env
scrub, with a separate database per worker. No repository tests were excluded.
A dedicated plugin directory avoided shadowing package imports through `/tmp`.
The final run also used empty API keys and a fresh `CLAUDE_CONFIG_DIR` verified
as unauthenticated. Earlier attempts exposed test-launched live SDK agents;
those were stopped. The explicitly requested reviewer alone uses the verified
Claude Max subscription with API credentials removed. Billing for the stopped
earlier test-launched agents was not independently measured; zero spend across
those earlier attempts is therefore not independently certified.


## Approved Claude review corrections (2026-09-06)

Patrick read and approved the posted 13-finding Claude review of 7c21c2863.
Nine findings have code/test corrections; F3 is a clarified trusted-caller
boundary, F4/F11 remain experiment-activation design work, and F12 retains the
required dependency for the shipped replay module. Full dispositions live in
`docs/specs/host-surface-parity/receipts.md`.

Review-fix validation: 195 focused tests passed; gates/quality passed 624 tests
with 99.53% statement/branch coverage over both parity modules. All 43 changed
executable lines are covered. The whole configured tree passed 25,869 tests,
with 241 skips and 3 xfails in 75.20 seconds. Pinned hooks passed.
After formatting, renderer fixture digests were re-derived from actual replay.
Receipts: `/private/tmp/2444-review-gates.log`,
`/private/tmp/2444-review-coverage.json`, `/private/tmp/2444-review-whole.log`,
and `/private/tmp/2444-review-hooks.log`. The whole run used the committed
inference guard, empty API credentials and disposable local Redis.
Remaining: signed commit and push, then another bounded Claude review.
PR #2449 owns the CONTRIBUTING tokenizer-cache CI fix; it is still separate.
Do not merge either PR automatically or start increment 3.


## CONTRIBUTING smoke correction (new run 34038740990)

The newly pushed parity correction still failed `test_token_estimator` because
this branch lacked the static cl100k_base cache preparation. Patrick reported
that exact run; the failure log confirms the inference guard blocked its HTTP
fetch. The identical two-file workflow/test patch from #2449 is now applied
here so #2444 can pass independently. This intentionally overlaps #2449;
whichever merges second must reconcile the shared patch against main.
The inference guard and documented setup commands are unchanged.
Claude's in-flight review remains pinned to bf530993b and does not cover this
subsequent CI-only patch. Fresh local validation and CI are required.


## Latest validation and review

With the CONTRIBUTING cache patch: whole configured tree 25,871 passed,
241 skipped, 3 xfailed (76.96s); workflow/spend regression selection 353 passed,
1 skipped; pinned hooks passed. Logs: `/private/tmp/2444-with-smoke-whole.log`,
`/private/tmp/2444-smoke-regression.log`, `/private/tmp/2444-smoke-hooks.log`.

Claude re-review of bf530993b completed with 12 findings (4 medium, 8 low),
16 files sent and zero omitted. Result: `/private/tmp/2444-claude-review-corrections/result.json`.
It does not cover the later CI patch. Findings remain to be triaged; no clean
review or merge approval is claimed. Actual review runs are now in the R5 ledger.
The two unpublished local rows in #2449's worktree are duplicates of runs now
recorded here; preserve that worktree and reconcile them deliberately later.
Next: push CI patch, verify the new CONTRIBUTING job, then a bounded triage of
the second review. Do not launch another reviewer until concrete findings are
verified and corrected. The runtime-form milestone remains after this PR merges.
