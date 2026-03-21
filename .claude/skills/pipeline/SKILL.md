---
name: pipeline
description: Spec-driven development lifecycle — from idea to published package
category: hub
aliases: [sdlc, lifecycle]
tags: [pipeline, sdlc, sdd, lifecycle, spec-driven]
version: "1.0.0"
question:
  header: "Pipeline"
  question: "Where do you want to start?"
  multiSelect: false
  options:
    - label: "Full pipeline"
      description: "Start from brainstorm through to release"
    - label: "Development"
      description: "Execute an existing spec with agent teams"
    - label: "Release"
      description: "Full test suite, version bump, changelog, publish"
---

# pipeline

Spec-Driven Development Lifecycle — guided pipeline from
idea to published package.

Three phases with interactive and automatic gates. Jump in
at any phase or run the full flow.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/pipeline` | Full flow — brainstorm to release |
| `/pipeline "topic"` | Full flow with context pre-filled |
| `/pipeline dev` | Execute an existing XML spec |
| `/pipeline release` | Full test suite + release chain |

## Natural Language

Describe what you need:

- "build a new feature end to end"
- "take this spec and build it"
- "run the full lifecycle"
- "I have a plan, execute it"

## Phases

### Phase 1: Analysis & Design (Interactive)

Brainstorm and plan using Socratic discovery. Produces an
XML-enhanced spec with task prompts.

**Uses:** `/brainstorm` then `/plan`
**Output:** `.claude/plans/{topic}.md` with XML task specs
**Gate:** Interactive — user confirms the spec before
proceeding

### Phase 2: Development (Mixed gates)

Execute the XML spec task by task. Each task runs through:

1. **Build** — Claude Code implements the task
2. **Quality gate** (automatic) — parallel agent team:
   `code_reviewer` + `security_auditor` validate the work
3. **Per-task test** (automatic) — test only modified files
4. **Simplify** (automatic) — run code simplification on
   changed files

**Uses:** DynamicTeam with `two_phase` strategy, then
`/quick-test` and `/simplify`
**Gate:** Automatic per task. Interactive only if quality
gate fails.

### Phase 3: Release (Interactive gate)

Pipeline pauses and asks: "Ready to release?"

If yes, runs the full release chain:

1. Full test suite (`uv run pytest`) — integration gate
2. If tests fail: pause and show failures, ask user how
   to proceed (fix and retry, or skip)
3. If tests pass: continue release
4. Version bump (pyproject.toml)
5. Update CHANGELOG.md
6. Update README if needed
7. Commit all changes
8. Push to git repo
9. Clean dist/ and build for PyPI

**Uses:** `/release` chain
**Gate:** Interactive — user must confirm before release.
Full test suite runs as the first step of release, not as
a separate phase.

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST
execute the workflow, not answer ad-hoc.**

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/pipeline` | Start Phase 1 (brainstorm) |
| `/pipeline "topic"` | Start Phase 1 with topic |
| `/pipeline dev` | Start Phase 2 (ask for spec location) |
| `/pipeline release` | Start Phase 3 (release chain) |

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "full lifecycle", "end to end", "start to finish" | Full pipeline from Phase 1 |
| "execute spec", "build from plan", "implement" | Phase 2 |
| "release", "publish", "ship" | Phase 3 |

**IMPORTANT:** When arguments are provided, DO NOT just
display documentation. EXECUTE the action.

### Phase 1 Execution

1. Run `/brainstorm` with the topic (if provided)
2. When brainstorm completes, run `/plan` to produce the
   XML-enhanced spec
3. Save spec to `.claude/plans/{topic}.md`
4. Use `AskUserQuestion` to confirm: "Spec is ready.
   Proceed to Development?"
5. If yes, continue to Phase 2

### Phase 2 Execution

1. Read the XML spec from `.claude/plans/`
2. For each `<task>` in the spec:
   a. Execute the task (create/modify files as specified)
   b. Run quality gate: launch `code_reviewer` and
      `security_auditor` agents in parallel via DynamicTeam
   c. If quality gate passes: run tests on modified files
      (`uv run pytest <modified_test_files>`)
   d. If tests pass: run `/simplify` on modified files
      (automatic, no user input)
   e. If any gate fails: pause and ask user how to proceed
3. When all tasks complete, use `AskUserQuestion`:
   "Development complete. Ready to release?"
4. If yes, continue to Phase 3

### Phase 3 Execution

1. Use `AskUserQuestion` to confirm release
2. If confirmed, run the full test suite first:
   a. `uv run pytest`
   b. If tests fail: show failures, ask user to fix and
      retry or skip
   c. If tests pass: continue
3. Release steps:
   a. Bump version in `pyproject.toml`
   b. Update CHANGELOG.md with changes from this pipeline
   c. Update README.md if needed
   d. Stage and commit: `git add -A && git commit -m
      "feat: <description from spec>"`
   e. Push: `git push`
   f. Clean and build: `rm -rf dist/ && uv run python -m
      build`
4. Report: show version, commit hash, dist files

### CLI Reference

```bash
uv run attune workflow run code-review --path <target>
uv run attune workflow run simplify-code --path <target>
uv run pytest
uv run python -m build
```
