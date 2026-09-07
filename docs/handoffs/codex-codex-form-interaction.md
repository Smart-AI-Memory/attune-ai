# Agent work handoff

## Goal

Advance the approved Task 1B increment-3 Codex form interaction in draft #2450.

## Acceptance criteria

Same-task validated interaction, exactly-once completion, negative lifecycle
and trust-boundary tests, and actual Codex display/submission measurements.

## Scope and assumptions

- Branch: codex/codex-form-interaction; base a9e98f671.
- Worktree: /private/tmp/attune-codex-form-interaction-20260906.
- D14 authorizes this bounded milestone. Zero API spend; manual merge.
- Main and other worktrees are untouched. #2444/#2449 are already merged.

## Current state

The stdio composition root now replays packaged evidence, validates exact
route obligations and provisions a private POSIX installation key before
installing the native runtime. Eight obligations are verified (three package,
five new native); 162 remain pending after integrating prompt refinement from main. Each replay crosses paired real SDK
streams; the child-process receipt also uses normal production bootstrap.
No all-verified synthetic report authorizes production routing.

The distinct surface-native-elicitation transport owns its lifecycle evidence.
Explicit route projection bindings preserve pending RICH/deferred obligations.
The timeout contract is server-deadline => render_failed, no new receipt.
The closed MCP output schema is enforced through structuredContent; the voice
formatter is skipped for this protocol response. Transport exit closes and
detaches runtime state. Acceptance, cancellation, malformed/duplicate/late
answers, expiry, shutdown and validation races have negative regressions.

Only the installation key survives restart. Windows activation fails closed
until a private credential-store/ACL adapter exists. Policy-warm public native
trials are unavailable: terminal completions expose no warm successor. Do not
relabel process reuse as policy warmth. Two accepted live host trials are now
recorded below; repeated display timing and fresh-session discovery are still
missing. Keep the PR draft and do not claim the milestone complete.

## Verification

- Session preflight: 87 passed; dirty main preserved.
- Focused runtime/gate coverage: 338 passed, 95.84% over seven relevant modules.
- Gates/quality: 662 passed before final lifecycle changes; final whole run
  includes these guards. Complexity regression was refactored and five checks passed.
- Two full-run failures were diagnosed: the tool-list test needed the newly
  declared output_schema; three cost-default tests now use an empty private
  patterns directory instead of concurrently created/deleted repository files.
  Adjacent suites: 79 passed. No unrelated production code changed.
- Wheel built offline from cached build dependencies. Its normal stdio entry
  accepted decision/minutes/outcome with one render and one presentation,
  loaded forms 0.14.0 + MCP 1.28.1, and enforced the output schema.
- Wheel: /private/tmp/attune-form-preview-20260906/dist/attune_ai-16.2.1-py3-none-any.whl
- Wheel SHA256: 1109fcaaa3b1a275f798f278d4f693382691f13dc698c5d8a35f88b346fb9200
- Artifact receipt: /private/tmp/attune-form-preview-20260906/probe-home/receipt.json
  (fixture-owned answers; host_paint=false).
- Different-model read-only risk review: review_bootstrap_contract, gpt-5.6-sol,
  evidence-chain receipt; dispositions in the spec and cross-review ledgers.

## Next action

Implementation commit 2e1447b97 is signed and pushed to draft #2450. All local
checks passed; new-head CI is running with no failures at the last probe.
The verified preview is installed at
/Users/patrickroebuck/.attune/runtimes/forms-1109fcaaa3b1 in its own venv,
using frozen core dependencies. A second normal-stdio probe passed from that
installed environment (/private/tmp/form-installed-probe.log). Only the
attune-ai-preview block in ~/.codex/config.toml changed; the main server and
all other settings were compared and preserved. The former preview block is
backed up in that runtime directory as previous-preview.toml. Preview provider
credentials are empty and its state/config paths are isolated.

The September 6 recovery session now exposes `elicitation_route_form` on the
preview. Two live accepted completions are recorded in
`docs/probes/host-surface-parity/codex-routed-form-2026-09-06.md`; Patrick confirmed
the first trial's controls worked. The second used an ordinary band-website
planning request and completed with one render and one presentation.

The elicit source and agents projection now direct appropriate Codex planning
requests to this endpoint, respecting preferences and terminal outcomes.
The current agent read this guidance manually; fresh-session skill discovery
and repeated request-to-visible timing remain unverified. Follow the existing
measurement brief and keep the PR draft while that acceptance is open.

## Commands and logs

Use PYTHONPATH=src with
/Users/patrickroebuck/.codex/worktrees/9c6c/attune-ai/.venv/bin/python.
Full suite wrapper /private/tmp/run_form_interaction_suite.py isolates Redis and
provider credentials. Logs: /private/tmp/form-bootstrap-whole.log,
/private/tmp/form-final-coverage.log, /private/tmp/form-bootstrap-hooks.log,
/private/tmp/form-wheel-probe.log. Pre-commit needs UV_NO_SYNC=1,
UV_PROJECT_ENVIRONMENT set to that venv and
UV_CACHE_DIR=/private/tmp/attune-form-uv-cache.
After any native code/fixture formatting, refresh executed receipts and their
single-source package projections with scripts/project_surface_runtime.py --write.

Final whole-suite receipt: 26,056 passed, 242 skipped, 3 xfailed in 73.04s.

Pinned pre-commit hooks passed; good GPG signature independently verified.

Guidance follow-up verification: 72 projection/config/help checks passed;
final whole tree passed 26,056 tests (242 skipped, 3 xfailed). Log:
`/private/tmp/form-guidance-whole-final.log`. No executable code changed.
Generated concept/reference/quickstart help accompanies the skill mirror.

## PR 2450 CI repair (2026-09-07)

The original head b54417e5a generated native receipts with MCP 1.28.1, but
CI resolved 1.29.1 through the core dependency range. All eleven failing test
IDs traced to the SDK-version-bound implementation digest. An isolated 1.29.1
environment reproduced the mismatch; changing only the version input produced
the exact digest seen in CI.

Pin MCP 1.29.1, replay canonical native and renderer fixtures, and project both
registry and baseline into the package. The new generic dependency guard requires
one exact SDK pin matching the test runtime; no receipt comparison is weakened.
The tradeoff is deliberate receipt regeneration for future SDK upgrades.

Current main includes merged #2456. Its prompt-refinement hook contributes three
additional pending obligations; the merged baseline and registry retain them.
No desktop-trial claim or Windows activation claim changes. The lock refresh
updates only MCP's version, plus resolver normalization of the existing
exceptiongroup/typing-extensions dependency marker.

Repair verification: 354 focused tests passed (bootstrap, native runtime, surface
parity, handoff and spec-status gates), and pinned checks passed. A newly built
wheel installed in a clean venv resolved MCP 1.29.1 and accepted a real stdio
form completion with one renderer attempt and one presentation. Import provenance
was asserted to be site-packages; answers were fixture-owned, host_paint=false.
Initial repair wheel SHA-256:
e395a23d2c17ec9ba9eef3ddb4bf9a7c8e232f2b6bd1f55e8ce120ffe15be0b5.
After capability projection, the rebuilt wheel passed the same clean-install
stdio probe. Final wheel SHA-256:
f85ab92dd0782539b81dd99b496bec3e03136374a86a6e7f51a5b50f1d0abc2f.
Receipt: /private/tmp/attune-2450-artifact/probe-home/receipt.json.
The first complete unit run found nine merged-tool-count failures (22,478 passed):
main and this branch each added a tool, so the combined registry has 55 core /
66 total tools. Regenerated capability claims with project_capabilities.py and
updated the registration assertion to require both prompt_refinement and
elicitation_route_form. All 109 affected checks passed. The final full CI
selection passed: 26,103 passed, 242 skipped, 3 xfailed in 194.87s.
Command: ANTHROPIC_API_KEY='' /private/tmp/attune-2450-ci-venv/bin/python
/private/tmp/run_form_interaction_suite.py -q -n 4 --timeout=60
--timeout-method=thread -m 'not network and not integration' --tb=short.
Log: /private/tmp/attune-2450-final-suite.log.
Different-model review (GPT-5.6 Sol) found no issues across 15 unique repair
files; independent suites passed 14 bootstrap and 95 capability/registration
checks. Next: push the signed merge and repairs, then verify the complete remote
matrix on that exact head. Keep #2450 draft while desktop acceptance is open.

Release 16.3.0 remains deferred until CI repair, native-form integration, and
installed-host/keyboard validation (phases 1–3) are complete, as Patrick requested.
