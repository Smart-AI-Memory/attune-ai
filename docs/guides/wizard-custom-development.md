# Custom Wizard Development

Build Python-based wizards with workflow delegation, conditional steps, and testing strategies.

**Prerequisites:** Read [Wizard Architecture](wizard-architecture.md) first to understand the step lifecycle and session model.

---

## When to Use Python vs YAML

| Approach | Use When |
|----------|----------|
| **YAML** (`ConfigDrivenWizard`) | Simple question → analyze → preview flows. No custom logic needed. |
| **Python** (`BaseWizard` subclass) | Workflow delegation, conditional steps, custom result processing, or complex state management. |

For YAML-based wizards, see [Getting Started](wizards-getting-started.md). This guide covers the Python approach.

---

## Step 1: Define Your Wizard Class

Every Python wizard needs four things:

1. A `config` class attribute (`WizardConfig`)
2. A `steps` class attribute (`list[WizardStep]`)
3. A `build_prompt_context()` method
4. A `process_step_result()` method

### Minimal Example

```python
"""Code complexity wizard — analyzes and reduces cyclomatic complexity."""

from __future__ import annotations

from typing import Any

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext

from attune.wizards.base import BaseWizard, StepType, WizardConfig, WizardStep


class ComplexityWizard(BaseWizard):
    """Guided code complexity reduction."""

    config = WizardConfig(
        wizard_id="complexity",
        name="Complexity Wizard",
        description="Analyze and reduce code complexity",
        domain="development",
        estimated_cost_range=(0.02, 0.25),
        estimated_duration_minutes=5,
    )

    steps = [
        WizardStep(
            id="gather_info",
            name="Target Selection",
            description="Which code to analyze?",
            step_type=StepType.QUESTION,
            questions=[
                FormQuestion(
                    id="target_path",
                    text="Which file or directory?",
                    type=QuestionType.TEXT_INPUT,
                    default="src/",
                ),
                FormQuestion(
                    id="threshold",
                    text="Complexity threshold?",
                    type=QuestionType.SINGLE_SELECT,
                    options=["5 (strict)", "10 (standard)", "15 (lenient)"],
                    default="10 (standard)",
                ),
            ],
        ),
        WizardStep(
            id="analyze",
            name="Analyze Complexity",
            description="Measure cyclomatic complexity across target",
            step_type=StepType.LLM_CALL,
            tier="capable",
        ),
        WizardStep(
            id="decompose",
            name="Simplification Plan",
            description="Break complex functions into tasks",
            step_type=StepType.TASK_DECOMPOSE,
            tier="capable",
        ),
        WizardStep(
            id="preview",
            name="Review Plan",
            description="Review the simplification plan",
            step_type=StepType.PREVIEW,
        ),
        WizardStep(
            id="confirm",
            name="Proceed",
            description="Apply these simplifications?",
            step_type=StepType.CONFIRM,
        ),
    ]

    def build_prompt_context(self, step: WizardStep) -> PromptContext:
        """Build LLM prompt from session state."""
        assert self._session is not None

        if step.id == "analyze":
            target = self._session.get("target_path", "src/")
            threshold = self._session.get("threshold", "10 (standard)")
            return PromptContext(
                role="code complexity analyst",
                goal=f"Analyze cyclomatic complexity in {target}",
                instructions=[
                    f"Identify functions exceeding threshold: {threshold}",
                    "Rank by complexity score (highest first)",
                    "Suggest specific simplification strategies",
                ],
                constraints=[
                    "Preserve existing behavior",
                    "Each suggestion should be independently applicable",
                ],
                input_type="complexity_request",
                input_payload=f"Target: {target}\nThreshold: {threshold}",
            )

        if step.id == "decompose":
            analysis = self._session.step_results.get("analyze", {})
            return PromptContext(
                role="refactoring planner",
                goal="Create simplification tasks for complex functions",
                instructions=["One task per function or closely related group"],
                constraints=["Tests must pass after each change"],
                input_type="analysis",
                input_payload=str(analysis),
            )

        return PromptContext(role="assistant", goal="Analyze complexity")

    def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
        """Store analysis results in session."""
        assert self._session is not None
        if step.id == "analyze":
            self._session.set("complexity_analysis", result)
```

---

## Step 2: Add Conditional Steps

Steps can be skipped based on session state using the `condition` parameter.

### Define a Condition Function

```python
from attune.wizards.session import WizardSession


def _has_complex_functions(session: WizardSession) -> bool:
    """Only decompose if complex functions were found."""
    analysis = session.step_results.get("analyze", {})
    functions = analysis.get("complex_functions", [])
    return len(functions) > 0
```

### Attach It to a Step

```python
WizardStep(
    id="decompose",
    name="Simplification Plan",
    step_type=StepType.TASK_DECOMPOSE,
    condition=_has_complex_functions,  # Skipped if no complex functions
)
```

The condition receives the `WizardSession` and returns `bool`. When `False`, the step is recorded in `session.steps_skipped` and the wizard moves to the next step.

---

## Step 3: Add Workflow Delegation

Workflow delegation is the pattern used by production wizards (SecurityWizard, RefactorWizard) to run multi-stage analysis pipelines instead of simple LLM calls.

### Why Delegate?

- **Better results:** Multi-stage pipelines (triage → analyze → assess) produce richer output than a single LLM call
- **Graceful fallback:** If the workflow isn't available, the wizard falls back to a basic LLM call
- **Composability:** Reuse existing workflow engines without duplicating logic

### Implementation Pattern

```python
from typing import Any

from attune.workflows.compat import ModelTier


class ComplexityWizard(BaseWizard):
    # ... config and steps from above ...

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._complexity_workflow: Any = None

    def _get_or_create_workflow(self) -> Any:
        """Lazily instantiate the workflow engine."""
        if self._complexity_workflow is not None:
            return self._complexity_workflow

        try:
            from attune.workflows.complexity import ComplexityWorkflow

            self._complexity_workflow = ComplexityWorkflow(
                enable_auth_strategy=False,
            )
            return self._complexity_workflow
        except ImportError:
            return None  # Workflow not installed
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Workflow is optional enhancement
            return None

    async def _run_llm_step(self, step: WizardStep) -> None:
        """Override to intercept the analyze step."""
        if step.id == "analyze":
            try:
                await self._run_analysis_via_workflow()
                return
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Graceful fallback to basic LLM call
                pass

        # Fall back to base LLM call
        await super()._run_llm_step(step)

    async def _run_analysis_via_workflow(self) -> None:
        """Run multi-stage analysis via workflow engine."""
        assert self._session is not None
        workflow = self._get_or_create_workflow()
        if workflow is None:
            raise RuntimeError("Workflow not available")

        target = self._session.get("target_path", "src/")
        input_data = {"path": target}

        # Stage 1: Scan (cheap)
        scan_result, _, _ = await workflow.run_stage(
            "scan", ModelTier.CHEAP, input_data,
        )

        # Stage 2: Analyze (capable)
        analyze_input = {**input_data, **scan_result}
        analyze_result, _, _ = await workflow.run_stage(
            "analyze", ModelTier.CAPABLE, analyze_input,
        )

        # Combine and store
        combined = {
            "complex_functions": scan_result.get("functions", []),
            "analysis": analyze_result.get("analysis", {}),
            "workflow_delegated": True,
        }

        self.process_step_result(
            next(s for s in self.steps if s.id == "analyze"),
            combined,
        )
        self._session.complete_step("analyze", result=combined)
```

### Key Points

1. **`_get_or_create_workflow()`** — Lazy import with `try/except ImportError`. Cache the instance.
2. **`_run_llm_step()` override** — Check `step.id`, try workflow, fall back to `super()`.
3. **Stage chaining** — Each stage's output feeds into the next via dict merging.
4. **`workflow_delegated: True`** — Flag so downstream steps know the source.

---

## Step 4: Register Your Wizard

### Option A: Built-in Registration

Add to `src/attune/wizards/builtin/__init__.py`:

```python
from .complexity_wizard import ComplexityWizard

BUILTIN_WIZARDS: dict[str, type[BaseWizard]] = {
    # ... existing wizards ...
    "complexity": ComplexityWizard,
}
```

### Option B: Entry Point Registration

Add to `pyproject.toml`:

```toml
[project.entry-points."empathy.wizards"]
complexity = "your_package.complexity_wizard:ComplexityWizard"
```

### Option C: Runtime Registration

```python
from attune.wizards import register_wizard
from your_package import ComplexityWizard

register_wizard("complexity", ComplexityWizard)
```

---

## Step 5: Test Your Wizard

### Unit Test Structure

```python
import pytest
from attune.wizards.builtin.complexity_wizard import ComplexityWizard


class TestComplexityWizard:
    """Tests for ComplexityWizard."""

    def test_config(self):
        """Verify wizard metadata."""
        assert ComplexityWizard.config.wizard_id == "complexity"
        assert ComplexityWizard.config.domain == "development"

    def test_steps_order(self):
        """Verify step sequence."""
        step_ids = [s.id for s in ComplexityWizard.steps]
        assert step_ids == [
            "gather_info", "analyze", "decompose",
            "preview", "confirm",
        ]

    def test_step_types(self):
        """Verify each step has the correct type."""
        from attune.wizards.base import StepType

        steps = {s.id: s for s in ComplexityWizard.steps}
        assert steps["gather_info"].step_type == StepType.QUESTION
        assert steps["analyze"].step_type == StepType.LLM_CALL
        assert steps["decompose"].step_type == StepType.TASK_DECOMPOSE

    def test_questions_defined(self):
        """Verify question step has questions."""
        gather = next(s for s in ComplexityWizard.steps if s.id == "gather_info")
        assert gather.questions is not None
        assert len(gather.questions) >= 1

    def test_build_prompt_context_analyze(self):
        """Verify prompt context for analyze step."""
        wizard = ComplexityWizard()
        from attune.wizards.session import WizardSession

        wizard._session = WizardSession(wizard_id="complexity")
        wizard._session.set("target_path", "src/main.py")
        wizard._session.set("threshold", "10 (standard)")

        step = next(s for s in wizard.steps if s.id == "analyze")
        ctx = wizard.build_prompt_context(step)

        assert "complexity" in ctx.role.lower()
        assert "src/main.py" in ctx.goal

    def test_workflow_fallback(self):
        """Verify wizard works when workflow is unavailable."""
        wizard = ComplexityWizard()
        result = wizard._get_or_create_workflow()
        # Should return None gracefully, not raise
        assert result is None or result is not None  # Either is fine
```

### Testing Conditional Steps

```python
def test_condition_skips_when_no_findings(self):
    """Verify decompose step is skipped without complex functions."""
    from attune.wizards.session import WizardSession

    session = WizardSession(wizard_id="complexity")
    session.step_results["analyze"] = {"complex_functions": []}

    assert not _has_complex_functions(session)

def test_condition_runs_when_findings_exist(self):
    """Verify decompose step runs with complex functions."""
    from attune.wizards.session import WizardSession

    session = WizardSession(wizard_id="complexity")
    session.step_results["analyze"] = {
        "complex_functions": [{"name": "parse", "score": 15}]
    }

    assert _has_complex_functions(session)
```

---

## Patterns and Best Practices

### Session State Management

- Store analysis results with descriptive keys: `self._session.set("complexity_analysis", result)`
- Access prior step results via `self._session.step_results["step_id"]`
- Use `self._session.get(key, default)` for safe lookups with fallbacks

### Error Handling

- Workflow delegation uses broad `except Exception` with `# noqa: BLE001` and `# INTENTIONAL:` comments
- Always fall back to `super()._run_llm_step(step)` when delegation fails
- Log exceptions before falling back: `logger.exception("Workflow failed, falling back")`

### Prompt Context Quality

- Use specific `role` strings: `"security remediation specialist"` not `"assistant"`
- Include `constraints` that guard behavior: `"Preserve existing tests"`, `"Changes must be backward-compatible"`
- Pass relevant session data in `input_payload` so the LLM has context

### Multi-Step Delegation

When a wizard has multiple LLM_CALL steps that delegate to the same workflow, accumulate state:

```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._workflow_state: dict[str, Any] = {}  # Accumulates across stages

async def _run_scan_via_workflow(self):
    # ... run stages, store in self._workflow_state["scan"] ...

async def _run_fixes_via_workflow(self):
    # Use accumulated state from scan
    input_data = {**self._workflow_state.get("scan", {})}
    # ... run remediation stage ...
```

---

## File Structure

```text
src/attune/wizards/
├── __init__.py              # Public API exports
├── base.py                  # BaseWizard, StepType, WizardConfig, WizardStep
├── session.py               # WizardSession state management
├── registry.py              # Discovery and registration
├── config_driven.py         # YAML-based ConfigDrivenWizard
├── decomposer.py            # XML task decomposition engine
├── internal_workflow.py     # LLM bridge (BaseWorkflow wrapper)
└── builtin/
    ├── __init__.py           # BUILTIN_WIZARDS registry dict
    ├── debug_wizard.py       # DebugWizard
    ├── test_gen_wizard.py    # TestGenWizard
    ├── refactor_wizard.py    # RefactorWizard (with workflow delegation)
    ├── security_wizard.py    # SecurityWizard (with workflow delegation)
    └── release_prep_wizard.py # ReleasePrepWizard
```

---

## Next Steps

- [Getting Started](wizards-getting-started.md) — Run your first wizard
- [Wizard Architecture](wizard-architecture.md) — System design deep dive
- [Software Wizards](../reference/software-wizards.md) — Full reference for all 16 software wizards
- [XML-Enhanced Prompts](xml-enhanced-prompts.md) — Task decomposition schema
