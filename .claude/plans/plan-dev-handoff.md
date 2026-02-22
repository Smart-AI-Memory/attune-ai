# Plan-to-Dev Seamless Handoff

**Created:** 2026-02-22
**Source:** /brainstorm session

## Problem

`/plan` and `/dev` hubs have overlapping commands (especially
`refactor`) with no connection between them. Planning produces
output that execution doesn't consume, breaking flow and losing
context across sessions.

## Goals

- Every `/plan` command that produces an actionable plan ends
  with "Ready to execute?" prompt
- Saying yes seamlessly transitions into the corresponding
  `/dev` action with full context preserved (in-session)
- Plans are always saved to `.claude/plans/` as structured
  files
- `/dev` commands can load saved plans from previous sessions
  (cross-session)

## End State

A user types `/plan refactor`, goes through Socratic scoping,
gets a structured plan, and is asked "Execute now?". If yes,
the conversation flows directly into `/dev refactor` with
full context. If no (or if the session ends), the plan is saved
to `.claude/plans/` and can be loaded later via
`/dev refactor --plan <file>`.

## Task Prompts

```xml
<task id="1" name="plan-save-and-prompt">
  <objective>
    Modify /plan skill to always save plans to .claude/plans/
    and add an "Execute now?" prompt at the end of every
    planning flow that transitions to the corresponding
    /dev action.
  </objective>

  <context>
    <existing-code path=".claude/commands/plan.md">
      Current plan.md defines 4 routes: feature, tdd,
      refactor, architecture. Each uses EnterPlanMode but
      has no post-plan handoff behavior. The plan is
      approved and then the conversation ends.
    </existing-code>
    <existing-code path=".claude/commands/dev.md">
      Current dev.md defines 7 routes: review, debug,
      refactor, commit, pr, quality, perf-audit. Each
      starts fresh with AskUserQuestion scoping. No
      mechanism to load a pre-existing plan.
    </existing-code>
  </context>

  <files-to-modify>
    <file path=".claude/commands/plan.md">
      <change location="after each route's behavior section">
        BEFORE:
        Then use EnterPlanMode to plan the refactoring.
        (similar for feature, tdd, architecture)

        AFTER:
        Then use EnterPlanMode to plan the refactoring.

        After the plan is approved:

        1. Save the plan to .claude/plans/{route}-{slug}.md
           using the plan file format (see below)
        2. Use AskUserQuestion to ask: "Plan saved. Ready
           to execute?" with options:
           - "Execute now" - Transition to /dev {route}
             with the plan context already loaded. Do NOT
             re-ask scoping questions — the plan provides
             all context needed.
           - "Save for later" - Confirm the plan file path
             and end.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>
      /plan refactor ends with a saved .md file in
      .claude/plans/ AND an "Execute now?" prompt
    </check>
    <check>
      Choosing "Execute now" transitions to /dev refactor
      without re-asking scoping questions
    </check>
    <check>
      Choosing "Save for later" confirms the file path
      and ends gracefully
    </check>
  </validation>

  <risks>
    <risk severity="low">
      Plan file naming collisions — mitigate with
      timestamp or slug-based naming
    </risk>
  </risks>
</task>

<task id="2" name="dev-plan-loading">
  <objective>
    Modify /dev skill to detect and load saved plans from
    .claude/plans/ when a matching plan exists, enabling
    cross-session continuity.
  </objective>

  <context>
    <existing-code path=".claude/commands/dev.md">
      Current dev.md starts every route with
      AskUserQuestion to scope the work from scratch.
      No mechanism to check for or load existing plans.
    </existing-code>
    <existing-code path=".claude/plans/">
      Plans saved by Task 1 will follow a structured
      format with Problem, Goals, End State, and
      Approach sections.
    </existing-code>
  </context>

  <files-to-modify>
    <file path=".claude/commands/dev.md">
      <change location="top-level behavior section, before route-specific behavior">
        BEFORE:
        (routes go straight to AskUserQuestion scoping)

        AFTER:
        ## Plan Detection (applies to all routes)

        Before starting scoping questions for any route
        (refactor, feature implementation via debug, etc.):

        1. Check .claude/plans/ for recent plans matching
           the current route (e.g., refactor-*.md for
           /dev refactor)
        2. If matching plans exist, use AskUserQuestion:
           "I found a saved plan: {plan-name}. Want to
           pick up where you left off?"
           - "Yes, use this plan" - Read the plan file
             and skip scoping. Go directly to execution
             using the plan's Approach section as the
             implementation guide.
           - "No, start fresh" - Proceed with normal
             AskUserQuestion scoping flow.
        3. If no matching plans exist, proceed normally.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>
      /dev refactor detects existing refactor-*.md plans
      in .claude/plans/
    </check>
    <check>
      Choosing "Yes, use this plan" skips scoping and
      executes based on plan contents
    </check>
    <check>
      Choosing "No, start fresh" falls through to normal
      scoping flow
    </check>
    <check>
      Works correctly when no plans exist (no errors,
      normal flow)
    </check>
  </validation>

  <risks>
    <risk severity="medium">
      Stale plans — old plans may no longer match codebase
      state. Mitigate by showing plan date and asking user
      to confirm relevance.
    </risk>
    <risk severity="low">
      Multiple matching plans — show list and let user
      choose which one.
    </risk>
  </risks>
</task>

<task id="3" name="plan-file-format">
  <objective>
    Standardize the plan file format so /dev can
    reliably parse and execute saved plans. Add metadata
    header for routing and freshness detection.
  </objective>

  <context>
    <existing-code path=".claude/plans/">
      Current plans use ad-hoc markdown formats. Need
      a consistent structure that /dev can rely on.
    </existing-code>
  </context>

  <files-to-modify>
    <file path=".claude/commands/plan.md">
      <change location="add new section: Plan File Format">
        AFTER existing content, add:

        ## Plan File Format

        All saved plans MUST use this format:

        ```markdown
        # {Title}

        **Created:** {YYYY-MM-DD}
        **Source:** /plan {route}
        **Route:** {route}
        **Status:** pending | in-progress | completed

        ## Problem
        {1-2 sentence problem statement}

        ## Goals
        - {Must-have 1}
        - {Must-have 2}
        - {Nice-to-have (marked as such)}

        ## End State
        {Concrete description of done}

        ## Scope
        - **Files:** {list of target files/directories}
        - **Type:** {refactor | feature | tdd | architecture}

        ## Approach
        1. {Step 1 with specific file references}
        2. {Step 2}
        3. {Step 3}

        ## Open Questions
        - {Anything unresolved}
        ```

        The **Route** and **Status** fields are required
        for /dev plan detection. File naming convention:
        `{route}-{slug}-{YYYY-MM-DD}.md`
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>
      Plan files saved by /plan contain Route and Status
      metadata fields
    </check>
    <check>
      /dev can grep for Route: refactor to find matching
      plans
    </check>
    <check>
      File naming follows {route}-{slug}-{date}.md
      convention
    </check>
  </validation>

  <risks>
    <risk severity="low">
      Format migration — existing plans in .claude/plans/
      won't have metadata. /dev should handle missing
      metadata gracefully (fall back to filename matching).
    </risk>
  </risks>
</task>
```

## Execution Order

1. **Task 3** (plan file format) — Define the contract first
2. **Task 1** (plan save and prompt) — Update /plan to
   produce structured plans with handoff
3. **Task 2** (dev plan loading) — Update /dev to consume
   saved plans

## Next Steps

- [ ] Implement Task 3: Standardize plan file format
- [ ] Implement Task 1: Add save + execute prompt to /plan
- [ ] Implement Task 2: Add plan detection to /dev
- [ ] Test full flow: /plan refactor → save → /dev refactor
      loads plan
- [ ] Test cross-session: close, reopen, /dev refactor
      finds saved plan

## Open Questions

- Should completed plans be archived (moved to
  `.claude/plans/archive/`) or just have status updated?
- Should `/dev` auto-detect plans or require explicit
  `--plan` flag?  (Current design: auto-detect with
  user confirmation)
