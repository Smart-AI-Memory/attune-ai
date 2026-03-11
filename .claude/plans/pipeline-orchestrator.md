# Pipeline Orchestrator — Scoping Document

**Created:** 2026-03-05
**Status:** Scoping (not yet approved)

## What We're Building

A Python orchestrator that replaces the prompt-driven
`/pipeline` skill with a real execution engine. Instead of
relying on Claude to interpret markdown instructions, the
orchestrator reads XML task specs, executes them with agent
teams, enforces quality gates, runs tests, and gates
release.

## What Already Exists (Reusable)

| Component | Location | Status |
|-----------|----------|--------|
| DynamicTeam | `orchestration/dynamic_team.py` | Ready — parallel, sequential, two_phase, delegation strategies |
| WorkflowComposer | `orchestration/workflow_composer.py` | Ready — converts workflows to teams with quality gates |
| WorkflowAgentAdapter | `orchestration/workflow_agent_adapter.py` | Ready — bridges BaseWorkflow to SDKAgent interface |
| MultiAgentStageMixin | `workflows/multi_agent_mixin.py` | Ready — `_run_multi_agent_stage()` builds teams from config |
| DynamicTeamBuilder | `orchestration/team_builder.py` | Ready — builds teams from plan dicts |
| Agent templates | `orchestration/agent_templates/builtin_templates.py` | Ready — code_reviewer, security_auditor, code_simplifier, test_generator |
| TaskDecomposer | `wizards/decomposer.py` | Ready — parses XML `<task>` blocks into `DecomposedTask` objects |
| WorkflowBatchRunner | `workflows/workflow_batch_runner.py` | Ready — parallel workflow execution with presets |
| Validation framework | `workflows/validation.py` | Ready — InputSchema, StageContract, WorkflowValidationError |

## What's Missing (New Code)

### 1. Spec Reader (~100 LOC)

Read a `.claude/plans/*.md` file, extract `<task>` blocks,
return a list of `DecomposedTask` objects.

**Reuses:** `TaskDecomposer._parse_tasks_from_xml()` regex
parser already handles this exact format. Wrap it in a
function that reads a file and calls the parser.

```python
# src/attune/pipeline/spec_reader.py

def read_spec(plan_path: str) -> list[DecomposedTask]:
    """Read a plan file and extract XML task blocks."""
    content = Path(plan_path).read_text(encoding="utf-8")
    return TaskDecomposer._parse_tasks_from_xml(content)
```

**Complexity:** Low. The parser exists. This is glue code.

### 2. Pipeline Orchestrator (~300 LOC)

The core engine. For each task in the spec:

1. Execute the task (create/modify files)
2. Run quality gate (code_reviewer + security_auditor
   via DynamicTeam parallel strategy)
3. Run per-task tests on modified files
4. Run simplification on changed files
5. Report results

```python
# src/attune/pipeline/orchestrator.py

class PipelineOrchestrator:
    """Executes an XML spec with agent teams and gates."""

    def __init__(
        self,
        spec_path: str,
        dry_run: bool = False,
    ):
        self.tasks = read_spec(spec_path)
        self.dry_run = dry_run
        self.results: list[TaskResult] = []

    async def run(self) -> PipelineResult:
        """Execute all tasks with quality gates."""
        for task in self.tasks:
            # 1. Execute task
            # 2. Quality gate
            # 3. Per-task test
            # 4. Simplify
            pass
```

**Key decisions:**

- **Quality gate strategy:** Use `WorkflowComposer.compose()`
  with `code_reviewer` + `security_auditor` workflows in
  parallel. Quality gates enforce minimum scores.
- **Test runner:** Shell out to `uv run pytest <files>` for
  modified test files. Parse exit code.
- **Simplify:** Call `SimplifyCodeWorkflow.execute()` on
  changed files.
- **Failure handling:** Pause and return partial result on
  gate failure. Let the caller (skill or CLI) decide to
  retry or skip.

**Complexity:** Medium. Most logic is delegation to
existing components.

### 3. Pipeline Result Models (~50 LOC)

```python
# src/attune/pipeline/models.py

@dataclass
class TaskResult:
    task_id: str
    task_name: str
    executed: bool
    quality_gate_passed: bool | None
    tests_passed: bool | None
    simplified: bool
    error: str | None = None

@dataclass
class PipelineResult:
    spec_path: str
    tasks: list[TaskResult]
    total_cost: float
    duration_ms: int

    @property
    def success(self) -> bool:
        return all(t.executed and t.quality_gate_passed
                   for t in self.tasks)
```

**Complexity:** Low. Pure data.

### 4. Updated Skill Markdown (~50 LOC change)

Update `src/attune/commands/pipeline.md` Phase 2
instructions to call the orchestrator instead of
describing manual steps. The skill still drives Phase 1
(brainstorm/plan) and Phase 3 (release) via prompts — only
Phase 2 gets a Python backing.

**Complexity:** Low. Markdown edit.

## What We're NOT Building

- **Phase 1 orchestrator** — brainstorm + plan works fine
  as prompt-driven Socratic conversation
- **Phase 3 orchestrator** — release is a linear script
  that works well as prompt instructions
- **Cross-session persistence** — pipeline state doesn't
  survive session restarts (future work)
- **CLI command** — no `attune pipeline run` command yet;
  the skill invokes the orchestrator via Python

## Architecture

```
/pipeline skill (prompt-driven)
  |
  Phase 1: /brainstorm + /plan  (existing, unchanged)
  |
  Phase 2: PipelineOrchestrator (NEW)
  |  reads spec -> for each task:
  |    execute task (Claude via Agent tool)
  |    quality gate (DynamicTeam: code_reviewer + security_auditor)
  |    per-task test (subprocess: uv run pytest)
  |    simplify (SimplifyCodeWorkflow)
  |
  Phase 3: /release skill (existing, unchanged)
```

## Task Breakdown

<task id="1" name="spec-reader">
  <objective>
    Create spec_reader.py that reads plan files and
    extracts DecomposedTask objects using existing parser.
  </objective>
  <files-to-create>
    <file path="src/attune/pipeline/__init__.py">
      Package init with public exports
    </file>
    <file path="src/attune/pipeline/spec_reader.py">
      read_spec() function wrapping TaskDecomposer parser
    </file>
  </files-to-create>
  <validation>
    <check>read_spec("workflow-validation-framework.md")
      returns list of DecomposedTask with correct ids</check>
    <check>Empty file returns empty list</check>
    <check>File with no XML returns empty list</check>
  </validation>
  <risks>
    <risk severity="low">TaskDecomposer._parse_tasks_from_xml
      may be a private method — may need to extract or
      duplicate the regex logic</risk>
  </risks>
</task>

<task id="2" name="pipeline-models">
  <objective>
    Create result dataclasses for pipeline execution.
  </objective>
  <files-to-create>
    <file path="src/attune/pipeline/models.py">
      TaskResult and PipelineResult dataclasses
    </file>
  </files-to-create>
  <validation>
    <check>TaskResult and PipelineResult are importable</check>
    <check>PipelineResult.success property works correctly</check>
  </validation>
</task>

<task id="3" name="pipeline-orchestrator">
  <objective>
    Create the core PipelineOrchestrator that executes
    tasks with quality gates, tests, and simplification.
  </objective>
  <files-to-create>
    <file path="src/attune/pipeline/orchestrator.py">
      PipelineOrchestrator class with run() method
    </file>
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/pipeline/__init__.py">
      Export PipelineOrchestrator
    </file>
  </files-to-modify>
  <validation>
    <check>Orchestrator reads spec and iterates tasks</check>
    <check>Quality gate uses DynamicTeam with parallel
      code_reviewer + security_auditor</check>
    <check>Test runner invokes pytest on modified files</check>
    <check>Gate failure pauses and returns partial result</check>
  </validation>
  <dependencies>
    <dep>1</dep>
    <dep>2</dep>
  </dependencies>
  <risks>
    <risk severity="medium">Quality gate needs real LLM
      calls or mocks — tests must mock the DynamicTeam</risk>
    <risk severity="low">SimplifyCodeWorkflow may need
      path input — verify its execute() signature</risk>
  </risks>
</task>

<task id="4" name="tests">
  <objective>
    Write unit tests for spec_reader, models, and
    orchestrator (mocked LLM/team calls).
  </objective>
  <files-to-create>
    <file path="tests/unit/pipeline/__init__.py">Empty</file>
    <file path="tests/unit/pipeline/test_spec_reader.py">
      Tests for read_spec with real plan files
    </file>
    <file path="tests/unit/pipeline/test_models.py">
      Tests for TaskResult, PipelineResult
    </file>
    <file path="tests/unit/pipeline/test_orchestrator.py">
      Tests for PipelineOrchestrator with mocked teams
    </file>
  </files-to-create>
  <validation>
    <check>All tests pass: uv run pytest tests/unit/pipeline/</check>
    <check>Coverage >= 80% for src/attune/pipeline/</check>
  </validation>
  <dependencies>
    <dep>3</dep>
  </dependencies>
</task>

<task id="5" name="wire-skill">
  <objective>
    Update pipeline.md Phase 2 instructions to reference
    PipelineOrchestrator. Add usage example showing how
    Claude should import and call it.
  </objective>
  <files-to-modify>
    <file path="src/attune/commands/pipeline.md">
      Add Python usage block for Phase 2 that imports
      and runs PipelineOrchestrator
    </file>
  </files-to-modify>
  <validation>
    <check>pipeline.md references PipelineOrchestrator</check>
    <check>Import path is correct</check>
  </validation>
  <dependencies>
    <dep>3</dep>
  </dependencies>
</task>

## Effort Estimate

| Task | New LOC | Complexity |
|------|---------|------------|
| spec_reader | ~60 | Low |
| models | ~50 | Low |
| orchestrator | ~250 | Medium |
| tests | ~300 | Medium |
| wire skill | ~30 | Low |
| **Total** | **~690** | **Medium** |

Most of the work is integration — connecting existing
components. The orchestrator is the only piece with real
logic (task loop, gate evaluation, error handling).

## Open Questions

1. **Task execution** — How does the orchestrator
   "execute a task"? Options:
   - a) Shell out to Claude Code CLI (heavy, new process)
   - b) Call Agent tool from the skill prompt (current
     approach, prompt-driven)
   - c) Use LLM call directly via `_call_llm()` (light,
     but limited)
   - **Recommendation:** (b) — the skill prompt tells
     Claude to execute each task, then call the
     orchestrator for quality gate + test + simplify.
     This keeps task execution in Claude's hands (where
     it's good) and only automates the gates.

2. **Gate failure UX** — When a quality gate fails:
   - Return `PipelineResult` with partial results
   - Skill prompt uses `AskUserQuestion` to ask:
     "Gate failed for task X. Fix and retry, or skip?"

3. **Simplify integration** — Does SimplifyCodeWorkflow
   accept a `path` kwarg to its execute()? Need to verify.
