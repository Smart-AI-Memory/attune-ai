---
type: task
name: use-spec
tags: [skill, task]
source: plugin/skills/spec/SKILL.md
---

# Task: Use the spec skill

Spec Ladders — goal-driven spec development: brainstorm, plan, review, and execute a gated task ladder with recorded approvals. Triggers on: spec, spec ladders, brainstorm and build, plan and execute, idea to code, build from scratch.

Invoke with: `/spec <what to build, or 'resume'>`

## Steps

1. **Define select by need, not by phase.**
   The stage machine already decides WHEN the choice exists; you decide only HOW it is presented. Never add a control because "we are in review" — present the choice because the plan is drafted, the gates passed, and the user has not yet chosen.

2. **Define honor scoped preferences.**
   An explicit override for THIS interaction ("show me the widget this once", "just tell me in text here") outranks a session-wide preference, which outranks the default. The session-wide preference lives in the MCP session context: when the user says "just talk to me" (or equivalent), call `context_set` with key `interaction_preference` and value `conversation`; read it back with `context_get` once per session (and again only when the user changes it) rather than before every render — one read, remembered. `conversation` means present the returned Markdown, not the widget; `default` (or unset) means the widget where the host renders it. A one-time override does not rewrite the stored preference. Keyboard mode (`attune config set keyboard_mode true`) is a separate, project-scoped opt-out for FORMS and is not the session preference.

3. **Define a conversational answer is transcribed, never acted on directly.**
   When the workspace is open and the user says "looks good", "approve", "redo it", or the like, complete the bound payload from the returned Markdown skeleton (`workspace_id`, `revision`, `action_nonce`, `contract_hash`, `title`, `view`, `action`) and submit it through `command_workspace_collect_action`. The Stage 2 `AskUserQuestion` below is the path for hosts WITHOUT the workspace tools; with the workspace open it is not a second path and must not be asked.

4. **Define never re-ask a settled choice.**
   If the user has already named the alternative in words, do not render the control at all — transcribe and submit. If the collector rejects the payload (stale revision, changed contract), re-open the workspace and present the CURRENT choice; do not retry the old payload.

5. **Define presentation never changes authority.**
   Widget and Markdown carry the same binding; only the canonical collector's acceptance advances the revision. A capability change, a preference change, or a progress event grants nothing. If any of these cannot be honored on the current host, say which and
   fall back to the returned Markdown; do not invent a surface. **T4 collection is open (adaptive-session-interactions D10).** On a real
   review stage on the named host, read the next unfilled slot in
   `docs/specs/adaptive-session-interactions/t4-record.md` and serve the
   choice under that slot's condition (A = widget; B = set
   `interaction_preference` to `conversation`, then the Markdown lane), then
   append the row per `t4-protocol.md` before continuing. Synthetic reviews
   and other hosts are exclusions, not slots.


## Related Topics
- **Reference**: Skill: spec — full reference
