# Workflow Validation Framework

**Goal:** Add structured validation at three levels — input,
stage output, and inter-stage contracts — to all workflows.
Strict by default with per-workflow opt-out.

**Scope:** 6 tasks, ~8 files modified, ~3 files created.

---

## Architecture

```text
execute(**kwargs)
  │
  ├─ validate_input(kwargs)        ← NEW (Task 1)
  │   raises WorkflowValidationError if invalid
  │
  ├─ for each stage:
  │   ├─ run_stage(stage_name, tier, input_data)
  │   ├─ validate_output(stage_output)   ← ENHANCED (Task 3)
  │   │   now checks required_keys per stage
  │   ├─ validate_contract(stage_name, stage_output)  ← NEW (Task 2)
  │   │   checks output schema matches next stage's input
  │   └─ (tier fallback if invalid)
  │
  └─ finalize result
```

---

## Tasks

<task id="1" name="validation-error-and-schema">
  <objective>
    Create WorkflowValidationError exception and
    InputSchema/OutputSchema dataclasses for declaring
    expected fields per workflow and per stage.
  </objective>

  <files-to-create>
    <file path="src/attune/workflows/validation.py">
      WorkflowValidationError(ValueError) — raised on
      validation failures. Includes workflow_name, stage,
      field, and reason.

      InputSchema dataclass:
        required_fields: dict[str, type]  # field_name -> expected type
        optional_fields: dict[str, type]
        validators: dict[str, Callable]   # field_name -> custom check

      StageContract dataclass:
        required_keys: set[str]
        optional_keys: set[str]
        key_types: dict[str, type]

      validate_against_schema(data, schema) -> list[str]
        Returns list of error messages. Empty = valid.
    </file>
  </files-to-create>

  <validation>
    <check>from attune.workflows.validation import
      WorkflowValidationError, InputSchema, StageContract</check>
    <check>WorkflowValidationError is a subclass of ValueError</check>
    <check>validate_against_schema({}, InputSchema(
      required_fields={"path": str})) returns 1 error</check>
  </validation>
</task>

<task id="2" name="input-validation-mixin">
  <objective>
    Add validate_input() method to LLMMixin that checks
    kwargs against the workflow's input_schema. Called at
    the top of execute() before any stage runs.
  </objective>

  <files-to-modify>
    <file path="src/attune/workflows/llm_mixin.py">
      <change location="after validate_output method">
        Add class attribute:
          input_schema: InputSchema | None = None

        Add method:
          def validate_input(self, kwargs: dict) -> None:
              """Validate workflow input against schema.
              Raises WorkflowValidationError if strict and
              invalid. Logs warnings if lenient."""
              if self.input_schema is None:
                  return  # no schema = no validation
              errors = validate_against_schema(
                  kwargs, self.input_schema)
              if errors:
                  raise WorkflowValidationError(
                      workflow_name=self.name,
                      stage="input",
                      errors=errors)
      </change>
    </file>
    <file path="src/attune/workflows/execution_mixin.py">
      <change location="execute() method, after _maybe_setup_cache()">
        BEFORE: self._run_id = str(uuid.uuid4())
        AFTER:
          # Validate inputs against schema (strict by default)
          self.validate_input(kwargs)
          self._run_id = str(uuid.uuid4())
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Workflow with input_schema raises
      WorkflowValidationError when required field missing</check>
    <check>Workflow without input_schema passes any input</check>
    <check>Existing tests still pass (no schema = no change)</check>
  </validation>
</task>

<task id="3" name="stage-contracts">
  <objective>
    Add stage_contracts class attribute to BaseWorkflow and
    a validate_contract() method that checks stage output
    against the declared contract before passing to the next
    stage.
  </objective>

  <files-to-modify>
    <file path="src/attune/workflows/llm_mixin.py">
      <change location="class body, after input_schema">
        Add class attribute:
          stage_contracts: dict[str, StageContract] = {}

        Add method:
          def validate_contract(
              self, stage_name: str,
              stage_output: dict
          ) -> None:
              """Validate stage output against its contract.
              Called after validate_output() succeeds."""
              contract = self.stage_contracts.get(stage_name)
              if contract is None:
                  return
              errors = validate_against_schema(
                  stage_output, contract)
              if errors:
                  raise WorkflowValidationError(
                      workflow_name=self.name,
                      stage=stage_name,
                      errors=errors)
      </change>
    </file>
    <file path="src/attune/workflows/execution_tier_fallback.py">
      <change location="after validate_output() call">
        Add: self.validate_contract(stage_name, stage_output)
        after the existing validate_output() call
      </change>
    </file>
    <file path="src/attune/workflows/execution_standard.py">
      <change location="after stage execution">
        Add: self.validate_contract(stage_name, stage_output)
        after stage result is captured
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Stage with contract raises WorkflowValidationError
      when required key missing from output</check>
    <check>Stage without contract passes any output</check>
  </validation>
</task>

<task id="4" name="enhance-validate-output">
  <objective>
    Enhance the default validate_output() to check
    required_keys from stage_contracts when no custom
    override exists.
  </objective>

  <files-to-modify>
    <file path="src/attune/workflows/llm_mixin.py">
      <change location="validate_output method">
        BEFORE: return True, None (at the end)
        AFTER:
          # Check stage contract required keys if available
          # (lightweight check — full contract validation
          # happens in validate_contract())
          return True, None
      </change>
    </file>
  </files-to-modify>

  <risks>
    <risk severity="low">
      This is lightweight — validate_contract() does the
      real work. This task just ensures validate_output()
      uses required_keys for its pass/fail signal in tier
      fallback decisions.
    </risk>
  </risks>
</task>

<task id="5" name="add-schemas-to-key-workflows">
  <objective>
    Add input_schema and stage_contracts to the 5
    most-used workflows: code-review, security-audit,
    test-gen, perf-audit, simplify-code.
  </objective>

  <files-to-modify>
    <file path="src/attune/workflows/code_review.py">
      <change location="class body">
        input_schema = InputSchema(
            required_fields={"path": str},
            optional_fields={
                "files_changed": list,
                "diff": str,
            })
        stage_contracts = {
            "classify": StageContract(
                required_keys={"risk_level", "analysis"}),
            "review": StageContract(
                required_keys={"findings", "summary"}),
        }
      </change>
    </file>
    <file path="src/attune/workflows/security_audit.py">
      <change location="class body">
        input_schema = InputSchema(
            required_fields={"path": str})
        stage_contracts = {
            "scan": StageContract(
                required_keys={"vulnerabilities"}),
            "assess": StageContract(
                required_keys={"risk_assessment", "flags"}),
        }
      </change>
    </file>
    <file path="src/attune/workflows/test_gen/workflow.py">
      <change location="class body">
        input_schema = InputSchema(
            required_fields={"path": str})
      </change>
    </file>
    <file path="src/attune/workflows/perf_audit.py">
      <change location="class body">
        input_schema = InputSchema(
            required_fields={"path": str})
      </change>
    </file>
    <file path="src/attune/workflows/simplify_code.py">
      <change location="class body">
        input_schema = InputSchema(
            required_fields={"path": str})
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>code-review with no path raises
      WorkflowValidationError</check>
    <check>code-review with path="src/" passes input
      validation</check>
    <check>All 5 workflows import InputSchema without
      error</check>
  </validation>
</task>

<task id="6" name="tests">
  <objective>
    Write tests for the validation framework covering
    all three levels.
  </objective>

  <files-to-create>
    <file path="tests/unit/workflows/test_validation_framework.py">
      Tests:
      - test_input_schema_validates_required_fields
      - test_input_schema_validates_types
      - test_input_schema_allows_optional_fields
      - test_stage_contract_validates_required_keys
      - test_stage_contract_allows_missing_optional
      - test_validate_input_raises_on_missing_field
      - test_validate_input_skips_when_no_schema
      - test_validate_contract_raises_on_missing_key
      - test_validate_contract_skips_when_no_contract
      - test_workflow_validation_error_includes_context
      - test_code_review_input_schema
      - test_code_review_rejects_empty_input
    </file>
  </files-to-create>

  <validation>
    <check>uv run pytest tests/unit/workflows/
      test_validation_framework.py -v passes</check>
  </validation>
</task>

---

## Execution Order

1 → 2 → 3 → 4 → 5 → 6

Tasks 1-3 are sequential (each builds on the prior).
Task 4 is a small enhancement to Task 3's work.
Task 5 depends on Tasks 1-3 (uses the new types).
Task 6 depends on all prior tasks.

## Opt-out Mechanism

Workflows that set `input_schema = None` (the default)
skip input validation entirely. Same for
`stage_contracts = {}`. This means all existing workflows
continue working unchanged until schemas are added.
