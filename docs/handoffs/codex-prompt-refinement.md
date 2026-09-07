# Agent work handoff

## Goal

Automatic, context-first prompt refinement with user-wide opt-out and a one-turn
skip, using existing form/conversation surfaces.

## Acceptance criteria

Default-on policy reaches supported adapters; opt-out survives a new process;
skip preserves preferences; invalid settings do not silently re-enable; actual
MCP transport can read/write preference and collect answers. Live host trials
remain necessary for conversational behavior claims.

## Scope and assumptions

- Branch/worktree: `codex/prompt-refinement`, isolated clone in
  `/private/tmp/attune-prompt-refinement`, based on `d9da9e0e4` from origin/main.
- Provider/session: Codex implements; GPT-5.6 Sol gives bounded advisory review.
- attune-ai owns policy; attune-forms remains the existing elicitation substrate.
- No user plugin installation or real preference was changed by this work.

## Current state

- Shared policy, fixed user setting, CLI/MCP preference controls, MCP initialize
  instructions, plugin prompt hook, planning fallback, docs and projections.
- Draft PR: https://github.com/Smart-AI-Memory/attune-ai/pull/2454.
- Review dispositions: `docs/specs/prompt-refinement/review.md`.
- Separate open native-form PR #2450 overlaps MCP source and inventory files.
  Keep its runtime/evidence changes when integrating; this branch is based on
  merged main and does not depend on that draft's new adapters.
- Missing evidence: actual Claude/Codex host obeying the refinement policy;
  live form UI quality; improvements in task outcomes. No such claims are made.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Clean baseline/process | collaboration_preflight.py using existing project Python | 87 governance tests passed, 0 failures |
| Preference and adapter behavior | tests/unit/test_prompt_refinement.py plus adjacent MCP/elicitation suites | Combined run: 444 passed; new policy/preference module 99.16% coverage |
| Final import-failure case and review ledger | tests/unit/test_prompt_refinement.py plus both ledger gates | 60 passed after the final test addition; policy/preference module remains 99.16% |
| Surface inventory | tests/unit/gates/test_surface_parity.py | 227 passed; new hook keeps pending host obligations |
| Guide navigation | scripts/audit_docs_wiring.py --check nav --format json | No findings |
| Published docs | mkdocs build --strict using temporary docs dependencies | Passed |
| Wheel includes usable module | Import from built .whl in a new subprocess; persist opt-out in temporary home | Passed |
| Capability claims match the added tool | project_capabilities.py --write plus projector, claim-drift, website and tier tests | 127 passed; five generated claim surfaces refreshed |
| CI regression corrections | SDK subprocess gate, utility schemas, both spec-status suites, refinement tests | 208 passed |
| Full local keyless suite | pytest -n 4 --timeout=60 --timeout-method=thread; temporary HOME/USERPROFILE, ATTUNE_REDIS_MOCK=true at collection, blank ANTHROPIC_API_KEY | 25,937 passed, 286 skipped, 3 xfailed; no failures |
| Real host conversation | Vague task, clear task, terse reply, correction, persistent off/on, skip, polish-only | Not run |

## Next action

Check CI on draft PR #2454. CI found an invalid spec status, stale capability counts and utility-tool
expectations, and a missing SDK subprocess guard. Corrections use the canonical
`draft` status, capability projector, updated tool expectation, and existing
`_sdk_gate`. The four failures shared by Ubuntu/macOS/coverage pass locally in
the 208-test regression run. The full local suite also passed (see above).
Earlier local attempts hit sandbox restrictions and then two live-Redis worker
timeouts; their logs were retained outside the repo. Mock mode at collection
prevents selecting live Redis tests and leaves owned-localhost fixture tests active.
One Windows 3.11 lane also timed out in the existing public MCP form test; it
passed a local focused rerun, but fresh Windows CI is still required. The
background update-check denial in its log does not establish the timeout cause.
After CI, run the host conversation
matrix from `docs/specs/prompt-refinement/requirements.md` using the updated
plugin/server in an isolated test session. Preserve raw results, including failures.
