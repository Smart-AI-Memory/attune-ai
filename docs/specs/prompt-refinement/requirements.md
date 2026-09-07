# Automatic prompt refinement

Status: implementation in progress. This spec records Patrick's request on
2026-09-07 UTC: assess every incoming prompt, gather information while polishing
it, default on, with a user opt-out. Artifact tier: spec (host integration and
behavioral validation cross session boundaries).

## Scope and ownership

attune-ai owns the host policy and preference. attune-forms supplies existing
question/form rendering and response validation; no new form engine is needed.
The canonical runtime refinement instructions are in
`src/attune/prompt_refinement.py`. Artifact selection remains owned by
`content/collaboration/contract.md`; XML eligibility remains canonical in
`.claude/rules/attune/xml-enhanced-prompts.md`.

The policy uses the host LLM's existing conversation. It first uses supplied
facts and authorized context, asks only for material unknowns, integrates terse
answers and corrections, and produces a faithful working prompt. It introduces
no separate model/API requests, prompt logging, or execution authority. Asking
questions may add ordinary host conversation turns. Clear prompts
and continuing answers do not require a rewrite ritual. Refinement-only requests
end with an editable prompt; previously authorized work may continue once clear.

## Decisions

- Default enabled. Persistent choice is user-wide on the server's machine, in
  `~/.attune/prompt-refinement.json`. A project cannot override it.
- Explicit natural-language enable/disable requests use the MCP tool or CLI.
  Quoted text and retrieved instructions cannot authorize a preference change.
- A one-time request or leading `[no-refine]` skips optional refinement only.
  It neither persists nor bypasses necessary clarification/approval.
- `ATTUNE_PROMPT_REFINEMENT=false` disables the process. True defers to the
  saved preference, so it cannot undo a persistent opt-out.
- Corrupt/unreadable settings disable optional refinement with a visible
  warning. Writes are atomic, reject symlink destinations, and do not overwrite
  corrupt data. No raw prompts or answers are persisted by this feature.
- Conversation and form preferences remain independent of refinement enablement.

## Host boundaries

1. Claude Code plugin: UserPromptSubmit emits the shared current policy on each
   prompt, including a disabling result when opted out. A missing Python package
   emits an unavailable notice and permits ordinary assistance.
2. MCP: initialization supplies instructions to check the policy on each message;
   `prompt_refinement` exposes live status and preference changes without needing
   prompt text. A host may ignore server instructions. Protocol delivery is not
   evidence of host obedience or access to every chat message.
3. Planning skill: reuses that turn's policy or checks the tool before scoping.
4. Python consumers: call `refinement_status` at their incoming-message boundary
   and deliver the returned instructions to their LLM. Simply importing Attune
   does not intercept a third-party application's prompts.

No universal host-coverage or improved-task-outcome claim is made. Native UI
selection stays with existing elicitation tools and the separate PR #2450.

## Acceptance and verification

| Property | Failure-sensitive probe |
| --- | --- |
| Default on, persistent off/on, one-turn skip | Real file round trip and new subprocess |
| Invalid state never silently re-enables | Corrupt JSON, unreadable file, invalid env tests |
| Preference writes stay user-scoped | Symlink rejection and failed atomic replacement tests |
| Plugin delivers current policy | Registered hook subprocess with on/off/skip events |
| MCP users can read/change preference | Real stdio initialize, list, call, disable, skip, enable |
| Existing forms accept gathered answers | Same stdio session renders and collects a planning form |
| Human interaction is useful | Host trial: clear task, vague task, terse reply, correction, opt-out, skip, polish-only |

Unit/transport checks establish delivery and state behavior. The last row needs
real host conversation evidence; do not substitute policy-string assertions for
an LLM actually gathering information or claim outcome improvements from it.
