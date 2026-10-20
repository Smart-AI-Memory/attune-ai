# PR #2566 native MCP receipt refresh

## Goal

Replay native protocol evidence against the MCP 1.30.0 dependency
selected by the existing PR, preserving the current evidence contract.

## Acceptance criteria

- Preserve the MCP 1.30.0 pin and lock selected by PR #2566.
- Reproduce every stored native receipt with the selected SDK, changing only
  the implementation digests in the identical source/package registries.
- Obtain a real different-model review and record its complete scope and triage.
- Qualify the published head through the hosted Python/OS matrix, required
  checks and both normal previews. These hosted results are pending at authoring.
- Keep merge and production on hold; make no further model calls.

## Scope and assumptions

- Branch/worktree: `codex/shepherd-mcp-receipts`, isolated repair worktree;
  publication target is the existing `dependabot/uv/mcp-1.30.0` PR branch.
- Provider/session: Codex integrates; one Claude subscription review advises.
- Starting PR head: `cf7e096459ab3f1546aa6d22954cd255c47fc6d4`.
- PR merge base: `25e2a3b3288f56763be06c4141aacfc72820f469`. This is distinct
  from the starting PR head; neither identifies a newer concurrent change.

## Current state

The branch carries signed repair commit
`d6492b8cb75d34f512f2cfa8c5fca48b78e2fae0`, followed by this handoff update and
the review ledger. Publication to [PR #2566](https://github.com/Smart-AI-Memory/attune-ai/pull/2566)
is authorized for fresh CI and normal previews. Merge and production remain held.
No product code, test predicate, gate, receipt observation or pending obligation
was changed by the repair. Fresh hosted qualification is pending at authoring.

## Change

Ran the existing `scripts/project_surface_runtime.py` projector through its
public `project(write=True)` entry after installing the unit inference guard.
This replays finite fixture-owned SDK exchanges with no network/model. Five
implementation digests changed in the source parity registry and its identical
packaged projection. All other registry fields, receipt observations, pending
obligations, mappings, test assertions and source code remain identical.

## Verification

- Python 3.10.11, isolated MCP 1.30.0 overlay. Other test dependencies were read
  from the existing developer environment; this was not a fresh locked install.
- Before replay: 11 failed / 251 passed in the surface parity/runtime modules.
- After replay: all 262 passed, including actual MCP stdio fixture transport.
- Native evidence, bootstrap, key, policy and selection modules: 128 passed.
- Existing projector check mode passed. JSON comparison confirmed exactly five
  implementation-digest changes and identical source/package projections.
- `git diff --check` passed. No test source, gates or pin policy changed.
- Subsequently, `uv sync --frozen --extra dev --no-editable` succeeded in a
  separate fresh environment: no overlay or borrowed test dependencies.
- In that fresh environment, 396 existing surface parity/runtime, native
  evidence, policy, selection and handoff tests passed on Python 3.10.11.
- An isolated installed-wheel replay reproduced all eight stored receipts,
  including all five native receipts. All 165 pending obligations remain pending.
- `uv --no-cache pip check` reported all 126 installed packages compatible.
- Public PyPI metadata for MCP 1.29.1 and 1.30.0 has identical 21-item
  `Requires-Dist` lists; the 1.30.0 artifact hashes match this lockfile.
- All 26 existing review-ledger gate tests passed after the R5 row was added.

## Review and disposition

One real Claude subscription review completed on 2026-10-20. The moderating
host was Codex (`self_review=false`). It reviewed the complete five-file
candidate at `d6492b8c` against merge base `25e2a3b3`: 14,039 diff characters,
five files sent, none omitted. It did not review this subsequent documentation
and ledger follow-up. No additional model review is authorized or claimed.

Eight comments were triaged in
[`docs/specs/cross-review/receipts.md`](../specs/cross-review/receipts.md).
Four verification/documentation concerns were accepted: release-impact context
is supplied below, fresh locked installation and dependency metadata were
checked, and the hosted matrix remains required. Four claims were rejected
with verbatim claims and source-backed reasons: SDK version is explicitly
hashed by the implementation digest; all five declared native receipts were
replayed; starting PR head and merge base are different provenance boundaries;
and the repository requires a tracked branch handoff. The review is advisory,
not a GitHub approval or a substitute for hosted qualification.

## SDK release impact

The [MCP 1.30.0 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.30.0)
changes stateful Streamable HTTP session limits/expiry, same-origin HTTP
redirect handling, OAuth issuer/resource validation and tool output-schema
reference resolution. The configured repository/plugin MCP entry points use
stdio; the local native receipt fixture uses paired in-memory SDK streams.
The release notes name no direct elicitation, abort or timeout change.

`surface_native_evidence._implementation_digest()` explicitly includes
`version("mcp")`, so changing the SDK changes that digest even when the four
tested protocol observations remain identical. Fresh accept, abort, timeout
and validation-feedback replays support unchanged behavior within those cases.
They do not qualify every custom plugin, external host or HTTP deployment.
The stateful HTTP advisory's stdio exclusion does not remove the dependency
upgrade or hosted-qualification requirement.

## Next action

Verify the remote head still matches the expected starting PR head, publish the
signed repair and documentation/ledger follow-up without overwriting concurrent
work, then monitor the new head's hosted matrix, required checks and previews.
Record terminal results externally to avoid another documentation-only CI cycle.
Local tests do not establish Windows behavior or visible host rendering.
PR #2530 is the older manifest-only duplicate and remains open for owner choice.
Merge and production remain held after CI completes.
