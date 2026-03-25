# /spec — Spec-Driven Development Command

**Created:** 2026-03-24
**Source:** /brainstorm session

## Problem

Attune has the infrastructure for spec-driven development
(brainstorm, read_spec, PipelineOrchestrator, voice layer,
spec_context) but no end-to-end command that walks a user
from idea to shipped code. The `/pipeline` command is a
rough draft — just a prompt, not a real orchestrator.

## Goals

- **Must-have:** Create spec from brainstorm/natural
  language, auto-decompose into XML tasks
- **Must-have:** Review step shows human-readable task
  summaries; power users can see/edit raw XML in the
  plan file
- **Must-have:** Execute tasks one at a time with quality
  gates and user approval between each
- **Must-have:** User can redo a task with different
  instructions before approving
- **Must-have:** "Auto-run remaining" option to skip
  further approvals
- **Must-have:** Voice layer speaks throughout
- **Must-have:** Session resume — if session ends
  mid-execution, next session picks up at the last
  unapproved task

## End State

A user types `/spec`. The system guides them through:

1. **Create** — brainstorm with the user, auto-decompose
   into XML tasks, save to `.claude/plans/<topic>.md`
2. **Review** — show each task in plain language (power
   users can open the file and edit XML directly)
3. **Approve** — user commits to the plan
4. **Execute** — run tasks one at a time with quality
   gates. After each task: approve, redo with new
   instructions, or auto-run the rest
5. **Resume** — if session ends mid-execution, next
   session picks up at the last unapproved task

The plan file in `.claude/plans/` is the single source
of truth — human-readable summaries for normal users,
XML task blocks for the orchestrator, execution state
for resume.

## Approach

1. **Create `/spec` command** — new command in both
   `plugin/commands/spec.md` and
   `src/attune/commands/spec.md` (self-contained)

2. **Create stage: brainstorm → XML decomposition**
   - Reuse existing brainstorm flow for discovery
   - Add auto-decomposition step using
     `TaskDecomposer._parse_tasks_from_xml()` pattern
   - Save plan with both prose summary and XML tasks

3. **Review stage: human-readable task presentation**
   - Parse XML tasks from plan file via `read_spec()`
   - Present each task: name, objective, files affected
   - Use `AskUserQuestion` for approve/edit/reject

4. **Execute stage: task-by-task with approval loop**
   - Extend `PipelineOrchestrator` with approval mode
   - After each task: show voiced output + quality gate
     results
   - `AskUserQuestion` with 3 options: approve, redo
     with instructions, auto-run remaining
   - Redo loop: accept new instructions, re-execute
     same task

5. **Resume: persist execution state in plan file**
   - Add execution state section to plan file (which
     tasks completed, which pending)
   - On `/spec` start, check for plans with incomplete
     execution state
   - Offer to resume or start fresh

6. **Retire `/pipeline`** — remove old command, redirect
   to `/spec`

7. **Wire voice layer** — all output through
   `format_output()`, next steps are spec-aware

8. **Tests** — unit tests for each stage, integration
   test for full flow

## Architecture

### Existing infrastructure to reuse

| Component | Location | Use |
|-----------|----------|-----|
| `read_spec()` | `pipeline/spec_reader.py` | Parse XML tasks from plans |
| `PipelineOrchestrator` | `pipeline/orchestrator.py` | Quality gates + execution |
| `TaskDecomposer` | `wizards/decomposer.py` | XML task parsing |
| `DecomposedTask` | `wizards/decomposer.py` | Standard task dataclass |
| `voice.format_output()` | `voice/formatter.py` | Voiced output |
| `spec_context` | `voice/spec_context.py` | Lifecycle awareness |
| `brainstorm` skill | `.claude/skills/brainstorm/` | Discovery flow |

### New code needed

| Component | Purpose |
|-----------|---------|
| `src/attune/spec/` | New package for spec command logic |
| `spec/runner.py` | Task-by-task execution with approval loop |
| `spec/decomposer.py` | Brainstorm output → XML task decomposition |
| `spec/state.py` | Execution state persistence in plan files |
| `spec/presenter.py` | Human-readable task presentation |

### Execution state format (appended to plan file)

```markdown
## Execution State

<!-- spec-state: {"completed": ["1.1", "1.2"],
"current": "2.1", "auto_run": false,
"last_updated": "2026-03-24T12:00:00"} -->
```

Hidden in an HTML comment so it doesn't clutter the
human-readable plan. `read_spec()` ignores it;
`spec/state.py` reads/writes it.

## Next Steps

- [ ] Design the `AskUserQuestion` flow for each stage
- [ ] Prototype the approval loop with one spec file
- [ ] Extend `PipelineOrchestrator` with pause-between-
      tasks mode
- [ ] Build state persistence (read/write HTML comment
      in plan file)
- [ ] Create `/spec` command and wire all stages
- [ ] Retire `/pipeline`
- [ ] Add tests

## Resolved Questions

- **Import support:** Yes. `/spec` accepts file paths
  and copies them to `.claude/plans/` after validation.
- **Quality gate failures:** Severity-gated. HIGH
  severity (score < 50) forces "Fix and retry" or
  "Acknowledge risk" — no auto-run allowed. MEDIUM/LOW
  shows standard approve/redo/auto-run options.
- **Brainstorm flow:** Delegate to existing `/brainstorm`
  skill. Only addition is auto-decomposition step after
  brainstorm completes.
