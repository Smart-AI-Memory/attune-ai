---
type: reference
subtype: procedural
name: skill-planning
category: skill
tags: [skill, plugin]
source: plugin/skills/planning/SKILL.md
---

# Reference: Skill: planning

High-level development planning — features, TDD, architecture review. Triggers on: plan, feature, architecture, design, TDD, strategy.

**Usage:** `/planning <what to plan: feature, tdd, architecture>`

## Prompt refinement before scoping

Use the current turn's Attune refinement hook result, or call
`prompt_refinement(action="status")` if none was supplied. Follow its shared
policy to gather material missing context and incorporate answers into the
working prompt. If the user asks only to polish a prompt, return that prompt
without entering plan execution. An opt-out suppresses optional refinement,
not clarification needed for the actual planning task. Never restart intake
for a user's answer or correction, and never duplicate questions already asked
by refinement. Enable/disable only on the user's explicit request; a one-time
skip does not change the saved preference.

This skill fallback reaches planning invocations. Automatic delivery across
all messages requires a host that runs the plugin hook or follows MCP server
instructions; installing a skill alone does not establish that behavior.

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="spec-engine", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Planning** — Helps you plan features, architecture, and TDD strategy before writing code.

High-level development planning and architecture design.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `feature` | Plan a new feature |
| `tdd` | Plan TDD approach |
| `architecture` | Architecture review |

## MCP Tools

| Tool | What It Does |
| ---- | ------------ |
| `research_synthesis` | Synthesize insights from source documents at a path to inform planning |

Use `research_synthesis` when the user needs to gather
context from a directory of files or docs before planning.
Pass the directory (or file) as `path`; optionally set
`depth` to `quick`, `standard`, or `deep`:

```
research_synthesis(path="<dir or file>", depth="standard")
```

## Scoping

Before asking, reuse the subject, goal, scope, and constraints already
supplied. For ordinary requests such as "Help me plan a website for a
flower shop", ask only the material unknowns; do not make the user classify
the request as a feature, TDD, or architecture exercise first.

**Codex:** use the available built-in question tool for suitable independent
unknowns, without waiting for the user to request a form. In Default mode,
use `request_user_input_async`, respecting its current schema and limits.
Read the `elicit` skill's **Host defaults** for answer retention,
corrections, cancellation, and the asynchronous lifecycle. When the host
delivers replies during the active turn, keep needed questions pending rather
than finishing immediately; otherwise resume when its reply arrives.
The Attune server route and widgets are experimental
in Codex, not prerequisites or automatic fallbacks. Honor a request for
conversation and avoid unnecessary questions when a useful plan can proceed.

**Claude:** call the built-in `AskUserQuestion` directly for suitable
independent unknowns, without waiting for the user to request a form, and
follow its current schema (1–4 questions, 2–4 options each, free text via
the built-in "Other"). Read the `elicit` skill's **Host defaults** for the
synchronous reply lifecycle, answer retention, corrections, cancellation,
and the typed fallback for controls the schema cannot represent. Ask a
subject or problem statement as a plain conversational question when it
has no honest predefined choices. The Attune widget and server route are
experimental on Claude; use them only when the user asks for a form.
Desktop rendering and keyboard behavior remain pending observation.

**Antigravity:** use the `elicit` host default: enhanced conversational
prompts, with native forms experimental.

For engineering planning tasks, clarify only missing dimensions:

1. **Type**: "What kind of planning? Feature spec, TDD
   approach, or architecture review?" Skip when the request implies the type.
2. **Subject**: Depending on type:
   - Feature: "What feature? What problem does it solve?"
   - TDD: "What behavior should the tests verify?"
   - Architecture: "What system? Any specific concerns?"
3. **Scope**: "How deep? Quick outline or detailed plan?"

**Order on every host.** The **Subject** phrasing branches on **Type**,
so never batch all three. On Claude, ask **Type** and **Scope** (both
select-shaped and independent) in one `AskUserQuestion` call when both are
open, then ask **Subject** with the type-specific phrasing —
conversationally unless the conversation supplies honest candidate
options. On hosts not yet reviewed (Gemini is deferred), settle **Type**
first, then gather **Subject** and **Scope** as one form via the `elicit`
skill's compatibility path. If only one dimension is open, ask it as a
single question — never force a one-field form (the §4 batching rule).

## Execution

1. Use `EnterPlanMode` to create a structured plan; on Claude, settle
   any remaining unknown with `AskUserQuestion` before leaving plan mode
2. If context from multiple files is needed, call
   `research_synthesis` first to gather insights
3. Present the plan for user approval before any
   implementation

## Related Topics
- **Reference**: Tool: Research Synthesis (`research_synthesis`)
