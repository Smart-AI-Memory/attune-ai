# Agent work handoff

## Goal

Wire attune-ai's existing state-bound Fix preview to the released
attune-forms 0.10.0 MCP Apps transport with truthful fallback behavior.

## Acceptance criteria

- MCP Apps metadata appears only for clients advertising the released UI
  extension and MIME profile.
- The shared attune-forms `ui://` resource is listed and readable through
  attune-ai's MCP server without copied HTML.
- Fix preview results name `fix_workspace_collect_action` in `response`
  mode while execution remains disconnected.
- Clients without the extension retain the current HTML/Markdown/text path.
- Focused tests, package build, and a real stdio protocol round trip pass.

## Scope and assumptions

- Branch/worktree: `codex/fix-mcp-apps` at
  `Documents/Codex/2026-08-29/are/work/attune-ai-fix-mcp-apps`
- Provider/session: Codex advisory-to-chair; Patrick approved the runtime
  follow-up through the PR:2373 merge form.
- Assumptions: attune-forms 0.10.0 is published and verified; MCP Apps
  transport remains presentation-only and the existing Fix collector owns
  validation and authority.

## Current state

- Status: implementation, local verification, and independent cross-provider
  review complete; final staged hooks pending
- Changed files: `CHANGELOG.md`, `pyproject.toml`, `uv.lock`,
  `src/attune/mcp/server.py`, three focused test files, the XML task,
  and this handoff
- Decisions: reuse attune-forms helpers; negotiate metadata fail-closed;
  retain the existing content-only call-tool adapter for legacy clients
- Risks or open questions: host-specific inline rendering remains dependent
  on the client advertising the standard extension; no runtime execution was
  added to the presentation bridge

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Clean isolated branch | `python scripts/collaboration_preflight.py` | pass; dirty primary checkout preserved |
| No overlapping open PR | `gh pr list` filtered to runtime/dependency files | pass; none |
| Released dependency is installed locally | `attune --version`; pip metadata for attune-ai/attune-forms | pass; 16.1.0 / 0.10.0 |
| Focused transport and authority behavior | `pytest` on request/server/schema/Fix files | pass; 123 tests |
| Broader MCP regression | `pytest -q tests/unit/mcp tests/unit/elicitation/test_fix_workspace.py` | pass; 475 tests |
| Formatting and lint | pinned Black plus Ruff on changed Python files | pass |
| Real source-tree stdio negotiation | UI-capable and legacy `ClientSession` probes | pass; metadata negotiated only for the capable client, both kept fallback content |
| Built artifact contract | `uv build`; wheel metadata/source inspection | pass; wheel and sdist built, `attune-forms>=0.10.0,<1.0` present |
| Installed-wheel stdio negotiation | clean `uv run --no-project --with <wheel>` two-session probe | pass; same positive and negative receipts outside the repository |
| Different-model boundary review | `attune-ai:cross-review staged seat=antigravity` | clean; 9 sent, 0 omitted, 0 findings; thread `review-codex-fix-mcp-apps-20260830-0518` |

## Verified findings

- **Test-only / false product alarm:** the first smoke expected only the
  resource URI in tool metadata. The released helper also intentionally
  serializes `visibility: ["model", "app"]`; the live wire result matched the
  helper and the receipt was corrected.
- **Pre-existing release debt / non-blocking:** setuptools emits license-table,
  license-classifier, and broad `MANIFEST.in` warnings during the build. Both
  artifacts complete successfully, and none originates in this change.
- **No verified product defect:** capability negotiation, resource reading,
  response-mode collection, legacy fallback content, and
  `execution_started: false` all passed in source-tree and installed-wheel
  stdio sessions.

## Next action

Run final staged hooks, then commit and publish a PR without merging until
Patrick approves it.
