---
description: Meta-Workflow UX Improvement Plan: **Version:** 1.0 **Created:** 2026-01-17 **Status:** Planning Phase --- ## Current UX Issues Identified ### 1.
---

# Meta-Workflow UX Improvement Plan

**Version:** 1.0
**Created:** 2026-01-17
**Status:** Planning Phase

---

## Current UX Issues Identified

### 1. **No Real Interactive Form** (Critical)

**Problem:** The `_ask_batch()` method in `form_engine.py` is a placeholder that returns empty dict.

**Current State:**
```python
def _ask_batch(self, questions: list[dict[str, Any]], template_id: str) -> dict[str, Any]:
    """Placeholder - real implementation would call AskUserQuestion"""
    return {}  # No actual interaction!
```

**Impact:**
- Users cannot actually interact with the form
- CLI `run` command doesn't collect user input
- Must provide pre-filled FormResponse programmatically

**Proposed Solution:**
```python
def _ask_batch(self, questions: list[dict[str, Any]], template_id: str) -> dict[str, Any]:
    """Ask questions using AskUserQuestion tool."""
    from attune.tools import AskUserQuestion

    result = AskUserQuestion(questions=questions)
    return result.get("answers", {})
```

---

### 2. **Mock Execution Only** (High Priority)

**Problem:** Real LLM integration (`_execute_agents_real`) exists but is not connected.

**Current Workaround:**
- All executions use mock mode
- No actual AI-powered agent work
- Just simulates costs and durations

**Proposed Solution:**
- Implement LLM API integration layer
- Add proper error handling and retries
- Implement progressive tier escalation logic
- Add real cost tracking via UsageTracker

---

### 3. **Verbose Terminal Output** (Medium Priority)

**Problem:** Too much technical information dumped to terminal.

**Current Output:**
```
📊 Agent Team Created:
   • test_analyzer
     - Tier Strategy: capable_first
     - Tools: coverage.py, pytest-cov, ast_parser
     - Executed: capable tier
     - Cost: $0.25
     - Duration: 4.0s
   ... (repeated for 11 agents)
```

**Issues:**
- Overwhelming for casual users
- No visual hierarchy
- No progress feedback during execution
- Hard to scan quickly

**Proposed Improvements:**

#### Option A: Progressive Disclosure (Recommended)
```
🚀 Executing Test Creation Workflow...

✓ test_analyzer (capable tier, $0.25, 4.0s)
✓ unit_test_generator (capable tier, $0.15, 3.0s)
✓ integration_test_creator (capable tier, $0.25, 4.0s)
... 8 more agents

💰 Total: $1.75 in 33.5s

📊 Summary: Created 145 tests, 82% coverage, 0 failures
📁 Results: .empathy/meta_workflows/executions/test_...-20260117-070612/

View details: attune meta-workflow show-run <run_id> --verbose
```

#### Option B: Progress Bars
```
🚀 Executing Test Creation Workflow...

[████████░░] 80% - test_report_generator (9/11)
Current: Generating coverage HTML report...
Estimated: 10s remaining
```

#### Option C: Rich TUI (Terminal UI)
```
┌─ Test Creation Workflow ─────────────────────────────┐
│ Status: Running (9/11 agents complete)               │
│                                                       │
│ ✓ test_analyzer            capable  $0.25    4.0s   │
│ ✓ unit_test_generator      capable  $0.15    3.0s   │
│ ⏳ test_report_generator   cheap    ...      ...    │
│                                                       │
│ Total Cost: $1.60 | Duration: 29.5s                  │
│                                                       │
│ [Press Q to cancel] [V for verbose]                  │
└───────────────────────────────────────────────────────┘
```

---

### 4. **No Progress Indicators** (High Priority)

**Problem:** No feedback during execution - user doesn't know if it's working or stuck.

**Current Experience:**
```bash
$ attune meta-workflow run test_creation_management_workflow
# ... nothing happens for 30 seconds ...
# ... then dumps all output at once
```

**Proposed Solutions:**

#### Real-Time Progress (Recommended)
```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
) as progress:

    task = progress.add_task("Executing agents...", total=len(agents))

    for agent in agents:
        progress.update(task, description=f"Running {agent.role}...")
        result = execute_agent(agent)
        progress.advance(task)
```

#### Streaming Output
```bash
$ attune meta-workflow run test_creation_management_workflow --stream

🚀 Starting Test Creation Workflow...

⏳ Collecting responses... (Question 1/12)
✓ Collected all responses

⚙️  Generating agent team...
✓ Created 11 agents

🤖 Executing agents:
  ⏳ test_analyzer (capable tier)...
  ✓ test_analyzer completed ($0.25, 4.0s)
  ⏳ unit_test_generator (progressive tier)...
  ✓ unit_test_generator completed ($0.15, 3.0s)
  ...
```

---

### 5. **Terminal-Only Interface** (Medium Priority)

**Problem:** No web UI or visual dashboard for better UX.

**Proposed Enhancements:**

#### Option A: Web Dashboard (Best UX)
```
┌─ Attune AI - Meta-Workflows ──────────────────┐
│                                                        │
│  📋 Available Templates                                │
│  ┌──────────────────────────────────────────────────┐ │
│  │ ▶ Test Creation & Management                     │ │
│  │   12 questions, 11 agents, $0.30-$3.50          │ │
│  │                                                  │ │
│  │ ▶ Code Refactoring                               │ │
│  │   8 questions, 8 agents, $0.15-$2.50            │ │
│  │                                                  │ │
│  │ ▶ Security Audit                                 │ │
│  │   9 questions, 8 agents, $0.25-$3.00            │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  📊 Recent Runs                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │ test_...-20260117-070612  ✓ Success  $1.75      │ │
│  │ code_...-20260117-064532  ✓ Success  $0.89      │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  [Run New Workflow] [View Analytics]                  │
└────────────────────────────────────────────────────────┘
```

**Implementation:**
- Lightweight web server (Flask/FastAPI)
- Vue.js or React frontend
- WebSocket for real-time updates
- Chart.js for cost/performance visualizations

#### Option B: Enhanced CLI with Rich Library
```bash
$ attune meta-workflow dashboard

# Opens interactive TUI with:
# - Template browser
# - Execution history
# - Real-time execution view
# - Cost analytics charts (ASCII art)
```

---

### 6. **Poor Question Flow** (Medium Priority)

**Problem:** Batching questions (4 at a time) is not intuitive for complex workflows.

**Current Experience:**
```
Batch 1/3 (Questions 1-4)
> What is the scope?
> What types of tests?
> Which framework?
> What coverage target?

Batch 2/3 (Questions 5-8)
> What quality checks?
> Analyze or create?
> Update outdated?
> Data strategy?

Batch 3/3 (Questions 9-12)
> Parallel execution?
> Report types?
> CI integration?
> Documentation?
```

**Issues:**
- Context lost between batches
- Can't review previous answers
- No way to go back and change answers
- Feels disjointed

**Proposed Improvements:**

#### Option A: Wizard-Style Flow
```
┌─ Test Creation Workflow - Configuration Wizard ──────┐
│                                                       │
│  Step 1 of 4: Test Scope                             │
│                                                       │
│  ● What is the scope of your testing effort?         │
│                                                       │
│    ( ) Single function/class                         │
│    (●) Entire project (full suite)  ← Selected       │
│    ( ) Multiple modules                              │
│                                                       │
│  ● What types of tests should be created?            │
│                                                       │
│    [✓] Unit tests (functions, classes)               │
│    [✓] Integration tests (module interactions)       │
│    [✓] End-to-end tests (full workflows)             │
│    [ ] Performance/Load tests                        │
│                                                       │
│  [Back] [Next: Test Configuration →]                 │
└───────────────────────────────────────────────────────┘
```

#### Option B: Single-Page Form
```
┌─ Test Creation Workflow - Quick Configuration ───────┐
│                                                       │
│  All Questions (12 total) - Scroll to navigate       │
│                                                       │
│  1. Scope: [Entire project ▼]                        │
│  2. Test types: [3 selected ▼]                       │
│  3. Framework: [pytest ▼]                            │
│  4. Coverage: [80% ▼]                                │
│  5. Quality checks: [3 selected ▼]                   │
│  ...                                                  │
│                                                       │
│  [Cancel] [Save as Draft] [Run Workflow →]           │
└───────────────────────────────────────────────────────┘
```

---

### 7. **No Validation or Helpful Defaults** (Low Priority)

**Problem:** Users must answer all questions, even if defaults would be sensible.

**Proposed Improvements:**

#### Smart Defaults Based on Project Detection
```python
def suggest_defaults(project_path: str) -> dict[str, Any]:
    """Suggest defaults by analyzing project."""

    # Detect testing framework
    if (Path(project_path) / "pyproject.toml").exists():
        config = toml.load("pyproject.toml")
        if "pytest" in config.get("tool", {}):
            framework = "pytest (Python)"

    # Detect current coverage
    if (Path(project_path) / ".coverage").exists():
        current_coverage = get_coverage_percentage()
        suggested_target = min(current_coverage + 15, 95)

    return {
        "testing_framework": framework,
        "coverage_target": f"{suggested_target}%",
        "test_scope": "Entire project (full suite)",
        ...
    }
```

#### Session-Based Defaults (Already Implemented!)
```python
from attune.meta_workflows.session_context import SessionContext

session = SessionContext(memory=memory)

# Use previous choices as defaults
defaults = session.suggest_defaults(
    template_id="test_creation_management_workflow",
    form_schema=template.form_schema
)
```

---

### 8. **No Cost Preview** (High Priority)

**Problem:** Users don't know cost until after execution.

**Proposed Solution:**

#### Pre-Execution Cost Estimate
```
┌─ Cost Estimate ───────────────────────────────────────┐
│                                                        │
│  Based on your selections:                            │
│                                                        │
│  • Entire project scope: +$0.50 (more agents)         │
│  • E2E tests: +$0.30 (expensive execution)            │
│  • Performance tests: +$0.25                          │
│  • Documentation: +$0.15                               │
│                                                        │
│  Estimated Total: $1.50 - $2.50                        │
│  Typical completion time: 5-8 minutes                 │
│                                                        │
│  ⚠️  Actual cost may vary based on:                   │
│     - Codebase size                                   │
│     - Tier escalations                                │
│     - Agent retries                                   │
│                                                        │
│  [Adjust Budget] [Continue →]                         │
└────────────────────────────────────────────────────────┘
```

---

## Implementation Priorities

### Phase 1: Critical UX Fixes (Week 1)

1. **Implement Real Form Collection**
   - Connect `_ask_batch()` to AskUserQuestion tool
   - Add proper error handling
   - Test with all 5 templates

2. **Add Progress Indicators**
   - Implement real-time progress bars with `rich`
   - Add streaming output mode
   - Show current agent and estimated time remaining

3. **Improve Output Formatting**
   - Use progressive disclosure (summary by default)
   - Add `--verbose` flag for detailed output
   - Use `rich` for better terminal formatting

### Phase 2: Enhanced Workflows (Week 2)

4. **Implement Real LLM Integration**
   - Connect `_execute_agents_real()` to model router
   - Add progressive tier escalation
   - Implement proper cost tracking

5. **Add Cost Preview**
   - Calculate estimates based on form responses
   - Show breakdown by agent
   - Add budget controls

6. **Improve Question Flow**
   - Implement wizard-style navigation
   - Add ability to review/edit answers
   - Support going back to previous questions

### Phase 3: Advanced Features (Week 3)

7. **Web Dashboard** (Optional)
   - Build lightweight web UI
   - Add real-time execution monitoring
   - Visualize cost analytics

8. **Smart Defaults**
   - Implement project detection
   - Use session context for personalization
   - Add "Quick Start" mode with all defaults

---

## Quick Wins (Can Implement Today)

### 1. Add --verbose Flag
```python
# In cli_meta_workflows.py
@app.command()
def run(
    template_id: str,
    mock: bool = True,
    verbose: bool = False,  # NEW
):
    if not verbose:
        # Show summary only
        print(f"✓ {agent.role} completed")
    else:
        # Show full details
        print(f"✓ {agent.role}")
        print(f"  - Tier: {result.tier_used}")
        print(f"  - Cost: ${result.cost:.2f}")
        ...
```

### 2. Add Progress Bar
```python
from rich.progress import track

for agent in track(agents, description="Executing agents..."):
    result = execute_agent(agent)
```

### 3. Add Streaming Mode
```python
@app.command()
def run(
    template_id: str,
    stream: bool = False,  # NEW
):
    if stream:
        for agent in agents:
            print(f"⏳ Executing {agent.role}...")
            result = execute_agent(agent)
            print(f"✓ Completed (${'${result.cost:.2f}'}, {result.duration:.1f}s)")
```

---

## Testing Plan

1. **User Testing** with 5 templates:
   - Collect feedback on question flow
   - Measure time to complete forms
   - Identify confusing questions

2. **Performance Testing**:
   - Measure execution time per agent
   - Test with large codebases
   - Validate cost estimates

3. **A/B Testing**:
   - Test different output formats
   - Compare wizard vs single-page forms
   - Evaluate progress indicator styles

---

## Metrics to Track

- **Time to Complete Form:** Target <2 minutes
- **Execution Time:** Target <10 minutes for full project
- **Cost Accuracy:** Estimates within ±20% of actual
- **User Satisfaction:** NPS score >8/10
- **Abandonment Rate:** <10% of started workflows

---

## Conclusion

Current UX issues stem from:
1. Incomplete interactive form implementation
2. Mock-only execution
3. Verbose, overwhelming output
4. Lack of progress feedback
5. Terminal-only interface

**Recommended Next Steps:**
1. Implement real form collection (Critical)
2. Add progress indicators (High Priority)
3. Improve output formatting with rich library (Quick Win)
4. Build web dashboard for better UX (Future Enhancement)

**Estimated Effort:**
- Phase 1 (Critical Fixes): 3-5 days
- Phase 2 (Enhanced Workflows): 5-7 days
- Phase 3 (Advanced Features): 7-10 days

**Total:** 3-4 weeks for complete UX overhaul

---

**Version:** 1.0
**Created:** 2026-01-17
**Next Review:** After Phase 1 implementation
