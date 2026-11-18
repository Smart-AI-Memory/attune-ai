# Agent work handoff

## Goal

Repair the maintained Harness website journey checker so it follows the published installation entry and rejects a missing installation anchor.

## Acceptance criteria

- The current installation entry passes; wrong destination and missing fragment or anchor fail.
- Existing downstream route, version, hash and historical-archive assertions stay intact.
- Focused tests and the public HTTP journey pass.
- Prepare a draft PR for Patrick's review. Do not merge it.
- Completion review: complete for the checker implementation; PR and desktop experiment review remain pending.

## Scope and state

- Branch: `codex/windows-diagnostic-followup`.
- Base: freshly fetched `origin/main`, `656d1ec308f401e29701bf6b4b5469b5cdf40191`.
- Changed files: the checker, its maintenance README, five behavioral tests and this handoff.
- The checker now follows **Install Harness** for the published version and validates the destination's installation anchor.
- Imported course files, website pages and Harness runtime code are unchanged.
- Patrick authorized preparing this PR and a separate Edge download / Explorer extraction experiment. Checkpoint acceptance, BUILD and merge remain with Patrick.

## Verification

| Claim | Probe | Result |
| --- | --- | --- |
| Current entry and downstream course remain valid | Actual Python checker through loopback HTTP against rendered entry pages and committed exports | Passed |
| Invalid installation destinations fail | Wrong route and missing URL fragment | Both rejected with the expected error |
| Installation target exists | Remove the destination anchor | Rejected with the expected error |
| ZIP integrity checks remain active | Serve a corrupted practice ZIP | Rejected with the expected error |
| Website regression suite passes | `ATTUNE_PYTHON=<existing-project-venv>/bin/python npm test -- --reporter=json` from `website` | 126 passed, 0 failed, 0 pending on 2026-11-18 |
| Public journey still works | Current checker against `https://smartaimemory.com` | Passed at 18:43 UTC on 2026-11-18; both import receipts match Harness `af5d0baeffb34844b0ce55c3d6c10e74ca128637` |
| Formatting and applicable repository checks pass | Pinned pre-commit checks and `git diff --check` | Passed |

The first full suite run used system Python and failed one existing capabilities test because `claude_agent_sdk` was unavailable. The five new tests passed in that run. The clean full-suite run used an existing complete project environment without installing packages or changing tests. These are local results, not a claim about PR CI. The checker tests require Python 3.10 or later, curl and loopback HTTP access.

The checker SHA-256 for the live probe was `ab691926b1921045c0f48b3667739d7a075ee7711b27fa4f9f82543827b540b6`. Independent review found no must-fix issues. Evidence is retained in the session's `checker-pr-and-edge-extraction-20261118` report directory.

## Next action

Open the draft PR, inspect its checks and retain the separate Windows desktop extraction evidence for Patrick's review. Keep the draft on hold; do not infer merge, checkpoint or BUILD authority from successful tests. Delete this handoff when the branch is eventually merged.
