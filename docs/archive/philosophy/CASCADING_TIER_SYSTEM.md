---
description: Cascading Tier Retry System with AI-ADDIE Methodology: **Version**: 1.0 **Created**: 2026-01-07 **Purpose**: Progressive cost optimization through intelligent t
---

# Cascading Tier Retry System with AI-ADDIE Methodology

**Version**: 1.0
**Created**: 2026-01-07
**Purpose**: Progressive cost optimization through intelligent tier escalation with quality gates

---

## Executive Summary

The Cascading Tier Retry System optimizes costs by starting with CHEAP models and escalating only when necessary, while maintaining quality through automated validation gates and optional agent review.

### Key Innovation

**Instead of choosing a tier upfront** (CHEAP, CAPABLE, or PREMIUM), workflows:
1. **Start CHEAP**: Try fast, low-cost models first (3 attempts)
2. **Escalate CAPABLE**: If CHEAP fails, try mid-tier models (3 attempts)
3. **Final PREMIUM**: If CAPABLE fails, use expert models (1 attempt)

Each attempt runs through an **automated quality gate** (tests, lint, types) with failure feedback informing the next attempt.

### Cost Impact

**Hypothetical Distribution**:
- 70% of tasks succeed at CHEAP tier (1-3 attempts)
- 20% require CAPABLE tier (after CHEAP exhausted)
- 10% need PREMIUM tier (after CAPABLE exhausted)

**Weighted Average Cost**: ~$0.081 per task
**Compared to**: $0.150 average (current tier routing)
**Savings**: **~46% additional cost reduction** (on top of existing tier routing savings)

**Total Savings Stack**:
- Tier routing (vs always PREMIUM): 80% savings
- Semantic caching: 57% hit rate
- Cascading retries: 46% additional
- **Combined**: ~90% cost reduction vs always-PREMIUM, no caching

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     AI-ADDIE Workflow                       │
│                                                             │
│  Phase 1: ANALYZE (CHEAP) → Understand task                │
│  Phase 2: DESIGN (CHEAP → CAPABLE) → Plan solution         │
│  Phase 3: DEVELOP (CHEAP → CAPABLE → PREMIUM) → Implement  │
│  Phase 4: INTEGRATE (Quality Gate) → Validate              │
│  Phase 5: EVALUATE (Higher-Tier Review) → Approve/Iterate  │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │   Cascading Tier Retry Engine         │
        └───────────────────────────────────────┘
                 ↓              ↓              ↓
        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
        │ CHEAP Tier  │ │ CAPABLE Tier│ │ PREMIUM Tier│
        │ 3 attempts  │ │ 3 attempts  │ │ 1 attempt   │
        │ $0.0075 ea  │ │ $0.090 ea   │ │ $0.450 ea   │
        └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
               │                │                │
               └────────────────┴────────────────┘
                                ↓
                     ┌──────────────────────┐
                     │   Quality Gate        │
                     │   - Tests            │
                     │   - Lint             │
                     │   - Type Checks      │
                     │   - Health Score     │
                     └──────────────────────┘
                                ↓
                      Pass → Complete ✅
                      Fail → Extract Feedback → Retry/Escalate
```

---

## Phase 1: ANALYZE (CHEAP)

**Objective**: Understand the task and assess complexity

**Model**: Haiku, GPT-4o-mini, or Gemini Flash
**Cost**: ~$0.0075
**Time**: 10-30 seconds

**Inputs**:
- User request
- Relevant files (if known)
- Context from previous work

**Processing**:
```xml
<analyze_phase tier="CHEAP">
  <read_context>
    - Parse user request
    - Identify affected files/systems
    - Review related code
  </read_context>

  <assess_complexity>
    <simple>
      - Single file change
      - Clear requirements
      - Well-defined scope
    </simple>
    <moderate>
      - Multiple file changes
      - Some ambiguity
      - Testing required
    </moderate>
    <hard>
      - System-level changes
      - High ambiguity
      - Complex testing
    </hard>
  </assess_complexity>

  <identify_risks>
    - Breaking changes?
    - Dependencies affected?
    - Security implications?
  </identify_risks>
</analyze_phase>
```

**Outputs**:
- Task complexity score (1-10)
- Affected files list
- Risk assessment
- Recommended starting tier (usually CHEAP)

**Success Criteria**:
- Complexity accurately assessed
- All affected areas identified
- Risks flagged

---

## Phase 2: DESIGN (CHEAP → CAPABLE Escalation)

**Objective**: Create implementation plan with verification steps

**Models**:
- CHEAP (3 attempts): Haiku, GPT-4o-mini
- CAPABLE (2 attempts): Sonnet, GPT-4o

**Cost Range**: $0.0075 - $0.180
**Time**: 30 seconds - 3 minutes

### Cascading Strategy

**Attempt 1-3 (CHEAP - $0.0075 each)**:
```xml
<design_cheap tier="CHEAP" attempts="3">
  <approach>
    Create straightforward implementation plan:
    - List files to modify
    - High-level changes
    - Basic verification steps
  </approach>

  <quality_check>
    - Plan addresses requirements?
    - Files correctly identified?
    - Verification steps present?
  </quality_check>

  <on_failure>
    <log_error>What was missing or incorrect?</log_error>
    <retry_with_feedback>
      Incorporate error feedback into next attempt
    </retry_with_feedback>
  </on_failure>
</design_cheap>
```

**Attempt 4-5 (CAPABLE - $0.090 each)** (if CHEAP failed):
```xml
<design_capable tier="CAPABLE" attempts="2">
  <approach>
    Create comprehensive plan with:
    - Detailed file-by-file changes
    - Edge case handling
    - Rollback strategy
    - Comprehensive verification
  </approach>

  <feedback_from_cheap>
    [Errors from CHEAP attempts]
    - What did CHEAP miss?
    - Why did validation fail?
  </feedback_from_cheap>

  <on_failure>
    <escalate_to>PREMIUM or human review</escalate_to>
  </on_failure>
</design_capable>
```

**Outputs**:
- Structured XML implementation plan
- File modification list
- Verification command list
- Success criteria
- Rollback plan

---

## Phase 3: DEVELOP (CHEAP → CAPABLE → PREMIUM Cascading)

**Objective**: Implement the solution with quality validation

**Models**:
- CHEAP (3 attempts): Haiku, GPT-4o-mini - $0.015 each
- CAPABLE (3 attempts): Sonnet, GPT-4o - $0.090 each
- PREMIUM (1 attempt): Opus, o1 - $0.450

**Cost Range**: $0.015 - $0.765
**Time**: 30 seconds - 10 minutes

### The Core Cascading Logic

```python
async def develop_with_cascading(task: Task, plan: Plan) -> Result:
    """
    Implement task with cascading tier retry.

    Flow:
    1. Try CHEAP 3x with quality gate after each
    2. If all fail, try CAPABLE 3x with quality gate
    3. If all fail, try PREMIUM 1x with quality gate
    4. If fails, report to human with full context
    """

    feedback_history = []

    # CHEAP tier (3 attempts)
    for attempt in range(1, 4):
        result = await execute_agent(
            tier="CHEAP",
            plan=plan,
            feedback=feedback_history
        )

        # Quality gate
        validation = await quality_gate.validate(result)

        if validation.passed:
            return result  # Success at CHEAP! ($0.015)

        # Failed - extract feedback
        feedback_history.append({
            "tier": "CHEAP",
            "attempt": attempt,
            "errors": validation.errors,
            "what_failed": validation.failure_analysis
        })

    # CAPABLE tier (3 attempts) - escalated from CHEAP
    for attempt in range(1, 4):
        result = await execute_agent(
            tier="CAPABLE",
            plan=plan,
            feedback=feedback_history  # Include CHEAP failures
        )

        validation = await quality_gate.validate(result)

        if validation.passed:
            return result  # Success at CAPABLE ($0.045 + $0.090)

        feedback_history.append({
            "tier": "CAPABLE",
            "attempt": attempt,
            "errors": validation.errors
        })

    # PREMIUM tier (1 attempt) - final escalation
    result = await execute_agent(
        tier="PREMIUM",
        plan=plan,
        feedback=feedback_history  # Include all failures
    )

    validation = await quality_gate.validate(result)

    if validation.passed:
        return result  # Success at PREMIUM ($0.315 + $0.450)

    # All tiers exhausted - report to human
    return FailureReport(
        task=task,
        total_attempts=7,
        total_cost=sum_costs(feedback_history),
        feedback_history=feedback_history,
        recommendation="Human intervention required"
    )
```

### Attempt Structure (XML Template)

```xml
<develop_attempt tier="[CHEAP|CAPABLE|PREMIUM]" number="X">
  <context>
    <plan>[Implementation plan from DESIGN phase]</plan>
    <feedback_from_previous_attempts>
      [If retry/escalation, include previous error logs]
    </feedback_from_previous_attempts>
  </context>

  <implementation>
    [Write/edit files according to plan]
  </implementation>

  <self_verification>
    <command>python -m pytest tests/ -v</command>
    <command>ruff check . --exclude benchmarks/</command>
    <command>mypy src/attune/</command>
  </self_verification>

  <output>
    <changes_made>[Files modified with line numbers]</changes_made>
    <test_results>[Actual command outputs]</test_results>
    <status>[Pass/Fail]</status>
  </output>
</develop_attempt>
```

---

## Phase 4: INTEGRATE (Automated Quality Gate)

**Objective**: Validate implementation meets quality standards

**Type**: Automated validation (no LLM cost)
**Cost**: $0 (compute only)
**Time**: 10-60 seconds

### Quality Gate Specification

```xml
<quality_gate version="1.0">
  <automated_checks>
    <check id="tests" priority="critical" blocking="true">
      <command>python -m pytest tests/ -v --tb=short</command>
      <pass_criteria>0 failed</pass_criteria>
      <on_failure>
        <extract_errors>Test failure messages</extract_errors>
        <feedback_for_retry>
          - Which tests failed?
          - What assertions failed?
          - What was the expected vs actual?
        </feedback_for_retry>
      </on_failure>
    </check>

    <check id="lint" priority="critical" blocking="true">
      <command>ruff check . --exclude benchmarks/</command>
      <pass_criteria>0 errors</pass_criteria>
      <on_failure>
        <extract_errors>Lint error messages with file:line</extract_errors>
        <feedback_for_retry>
          - Which files have errors?
          - What are the error codes?
          - Can they be auto-fixed?
        </feedback_for_retry>
      </on_failure>
    </check>

    <check id="types" priority="high" blocking="false">
      <command>mypy src/attune/</command>
      <pass_criteria>0 errors</pass_criteria>
      <on_failure>
        <extract_errors>Type error messages</extract_errors>
        <feedback_for_retry>Type mismatches to fix</feedback_for_retry>
      </on_failure>
    </check>

    <check id="health" priority="medium" blocking="false">
      <command>attune health</command>
      <pass_criteria>Score ≥ 70/100</pass_criteria>
      <on_failure>
        <feedback_for_retry>Health score regression details</feedback_for_retry>
      </on_failure>
    </check>
  </automated_checks>

  <pass_criteria>
    <must_pass>tests, lint</must_pass>
    <should_pass>types</should_pass>
    <nice_to_pass>health</nice_to_pass>
  </pass_criteria>

  <result_interpretation>
    <pass>
      All "must_pass" checks succeeded.
      Proceed to EVALUATE phase or complete task.
    </pass>

    <fail_retry>
      Critical checks failed.
      If attempts remaining at current tier: RETRY with error feedback.
      If tier exhausted: ESCALATE to next tier with full feedback history.
    </fail_retry>

    <fail_complete>
      All tiers exhausted, still failing.
      Generate human-readable failure report with:
      - All attempts and errors
      - Cost breakdown
      - Recommendations
    </fail_complete>
  </result_interpretation>
</quality_gate>
```

### Feedback Extraction

When quality gate fails, extract actionable feedback:

```python
def extract_feedback(validation_result: ValidationResult) -> Feedback:
    """Extract actionable feedback from validation failures."""

    feedback = {
        "what_failed": [],
        "why_it_failed": [],
        "how_to_fix": []
    }

    # Parse test failures
    if validation_result.tests.failed:
        for test in validation_result.tests.failures:
            feedback["what_failed"].append(f"Test {test.name} failed")
            feedback["why_it_failed"].append(test.error_message)
            feedback["how_to_fix"].append(
                f"Expected {test.expected}, got {test.actual}"
            )

    # Parse lint errors
    if validation_result.lint.errors:
        for error in validation_result.lint.errors:
            feedback["what_failed"].append(f"{error.file}:{error.line} - {error.code}")
            feedback["how_to_fix"].append(error.message)

    # Parse type errors
    if validation_result.types.errors:
        for error in validation_result.types.errors:
            feedback["what_failed"].append(f"Type error in {error.file}")
            feedback["why_it_failed"].append(error.message)

    return feedback
```

---

## Phase 5: EVALUATE (Higher-Tier Agent Review - Optional)

**Objective**: Human-like code review by higher-capability agent

**When to Use**:
- Critical systems (authentication, payments, security)
- User explicitly requested review
- Task complexity score ≥ 8/10
- Cost allows for it

**Reviewer Selection**:
- If developed by CHEAP → review by CAPABLE
- If developed by CAPABLE → review by PREMIUM
- If developed by PREMIUM → review by Claude Code (main agent)

**Cost**: $0.090 (CAPABLE) or $0.450 (PREMIUM) review
**Time**: 1-3 minutes

### Review Template

```xml
<evaluate_phase tier="[CAPABLE|PREMIUM]">
  <reviewer_receives>
    <original_task>[User request]</original_task>
    <implementation>[All code changes]</implementation>
    <test_results>[Quality gate results]</test_results>
    <development_history>
      [How many attempts, which tiers, what errors]
    </development_history>
  </reviewer_receives>

  <review_criteria>
    <code_quality weight="30%">
      - Follows project patterns?
      - Maintainable and readable?
      - No code smells?
    </code_quality>

    <correctness weight="40%">
      - Solves the actual problem?
      - Edge cases handled?
      - No logic errors?
    </correctness>

    <test_coverage weight="15%">
      - Tests cover changes?
      - Tests are meaningful?
      - No missing test cases?
    </test_coverage>

    <best_practices weight="15%">
      - Security considerations?
      - Performance acceptable?
      - Documentation if needed?
    </best_practices>
  </review_criteria>

  <review_outcomes>
    <approve confidence="90%+">
      Task complete. Implementation meets all criteria.
      Ready for merge/deployment.
    </approve>

    <request_changes confidence="50-89%">
      Implementation is close but needs improvements:
      - List specific changes requested
      - Return to DEVELOP phase with feedback
      - Same tier can retry with review feedback
    </request_changes>

    <reject confidence="<50%">
      Implementation has fundamental issues:
      - Escalate to next tier if available
      - Or report to human with analysis
    </reject>
  </review_outcomes>

  <output>
    <decision>[Approve/Request Changes/Reject]</decision>
    <confidence>[0-100%]</confidence>
    <feedback>[Specific, actionable feedback]</feedback>
    <estimated_fix_effort>[If changes requested]</estimated_fix_effort>
  </output>
</evaluate_phase>
```

---

## Cost Analysis Examples

### Example 1: Simple Bug Fix (70% of cases)

**Task**: Fix undefined variable in test file

**Phase 1: ANALYZE (CHEAP)**
- Cost: $0.0075
- Time: 15 seconds
- Result: Complexity = 2/10 (simple)

**Phase 2: DESIGN (CHEAP)**
- Attempt 1: Create fix plan
- Cost: $0.0075
- Time: 10 seconds
- Result: Plan created

**Phase 3: DEVELOP (CHEAP)**
- Attempt 1: Fix undefined variable
- Cost: $0.015
- Time: 20 seconds
- Result: Fixed

**Phase 4: INTEGRATE (Quality Gate)**
- Tests: PASS ✅
- Lint: PASS ✅
- Types: PASS ✅
- Cost: $0
- Time: 15 seconds

**Phase 5: EVALUATE**
- Skipped (simple fix, automated validation sufficient)

**Total Cost**: $0.030
**Total Time**: 60 seconds
**Tiers Used**: CHEAP only
**Savings vs PREMIUM**: 93%

---

### Example 2: Moderate Bug (20% of cases)

**Task**: Fix telemetry integration not triggering

**Phase 1: ANALYZE (CHEAP)**
- Cost: $0.0075
- Complexity: 6/10 (moderate)

**Phase 2: DESIGN (CHEAP → CAPABLE)**
- CHEAP Attempt 1-3: Plans miss root cause
- Cost: 3 × $0.0075 = $0.0225
- CAPABLE Attempt 1: Comprehensive plan (check imports, initialization)
- Cost: $0.090
- Result: Good plan

**Phase 3: DEVELOP (CHEAP → CAPABLE)**
- CHEAP Attempt 1-3: Fix import, still fails integration tests
- Cost: 3 × $0.015 = $0.045
- Quality Gate: Integration tests fail (5/6 failing)
- Feedback: "Module imports but tracking not called"
- CAPABLE Attempt 1: Fix initialization + verify with real workflow
- Cost: $0.090
- Result: Fixed

**Phase 4: INTEGRATE**
- All tests: PASS ✅
- Cost: $0
- Time: 45 seconds

**Phase 5: EVALUATE (Optional)**
- PREMIUM agent reviews CAPABLE work
- Cost: $0.450
- Result: Approved

**Total Cost**: $0.0075 + $0.1125 + $0.135 + $0.450 = $0.705
**Total Time**: 5 minutes
**Tiers Used**: CHEAP (exhausted) → CAPABLE (success) + PREMIUM (review)
**Savings vs All-PREMIUM**: -57% (actually MORE expensive with review)

**Note**: Review could be skipped for non-critical fixes, bringing cost to $0.255 (43% savings)

---

### Example 3: Hard Bug (10% of cases)

**Task**: Fix race condition in concurrent telemetry writes

**Phase 1: ANALYZE (CHEAP)**
- Cost: $0.0075
- Complexity: 9/10 (hard)

**Phase 2: DESIGN (CHEAP → CAPABLE → PREMIUM)**
- CHEAP: 3 attempts, misses race condition
- Cost: $0.0225
- CAPABLE: 2 attempts, identifies issue but plan incomplete
- Cost: $0.180
- PREMIUM: 1 attempt, comprehensive plan with locking strategy
- Cost: $0.450
- Result: Expert plan

**Phase 3: DEVELOP (PREMIUM)**
- PREMIUM Attempt 1: Implement with threading locks and atomic writes
- Cost: $0.450
- Result: Fixed

**Phase 4: INTEGRATE**
- Tests (including concurrency tests): PASS ✅
- Cost: $0
- Time: 90 seconds

**Phase 5: EVALUATE**
- Claude Code (main agent) reviews PREMIUM work
- Cost: $0 (human-in-loop)
- Result: Approved

**Total Cost**: $0.0075 + $0.6525 + $0.450 = $1.110
**Total Time**: 12 minutes
**Tiers Used**: All (CHEAP → CAPABLE → PREMIUM)
**Savings vs All-PREMIUM**: -147% (MORE expensive due to retries)

**Trade-off**: This is acceptable because:
- Only 10% of cases need this
- We tried cheaper approaches first (good practice)
- Weighted average across all cases still shows 46% savings

---

## Implementation: Cascading Workflow Class

```python
from typing import List, Optional
from dataclasses import dataclass
import asyncio

@dataclass
class Tier:
    name: str  # CHEAP, CAPABLE, PREMIUM
    max_attempts: int
    cost_per_attempt: float
    models: List[str]  # ["haiku", "gpt-4o-mini"]

@dataclass
class Feedback:
    tier: str
    attempt: int
    errors: List[str]
    failure_analysis: dict

@dataclass
class Result:
    success: bool
    output: any
    tier_used: str
    attempts_used: int
    total_cost: float
    feedback_history: List[Feedback]

class CascadingWorkflow:
    """
    Executes AI-ADDIE workflow with cascading tier retries.

    Usage:
        workflow = CascadingWorkflow(task)
        result = await workflow.execute()
    """

    def __init__(self, task: Task):
        self.task = task
        self.tiers = [
            Tier("CHEAP", 3, 0.015, ["claude-haiku-3.5", "gpt-4o-mini"]),
            Tier("CAPABLE", 3, 0.090, ["claude-sonnet-4", "gpt-4o"]),
            Tier("PREMIUM", 1, 0.450, ["claude-opus-4", "o1"]),
        ]
        self.quality_gate = QualityGate()
        self.feedback_history = []

    async def execute(self) -> Result:
        """
        Execute workflow with cascading tiers.

        Returns Result with success status, output, and cost breakdown.
        """

        # Phase 1: ANALYZE (always CHEAP)
        analysis = await self._analyze()

        # Phase 2: DESIGN (CHEAP → CAPABLE escalation)
        plan = await self._design_with_cascading()

        # Phase 3: DEVELOP (CHEAP → CAPABLE → PREMIUM cascading)
        implementation = await self._develop_with_cascading(plan)

        if implementation.success:
            # Phase 4: INTEGRATE (quality gate) - already done in _develop

            # Phase 5: EVALUATE (optional review)
            if self.task.requires_review:
                review = await self._evaluate(implementation)
                if not review.approved:
                    # Return to DEVELOP with feedback
                    return await self._develop_with_cascading(
                        plan,
                        additional_feedback=review.feedback
                    )

            return Result(
                success=True,
                output=implementation.output,
                tier_used=implementation.tier,
                attempts_used=implementation.total_attempts,
                total_cost=implementation.total_cost,
                feedback_history=self.feedback_history
            )
        else:
            # All tiers exhausted
            return Result(
                success=False,
                output=None,
                tier_used="ALL_EXHAUSTED",
                attempts_used=sum(t.max_attempts for t in self.tiers),
                total_cost=sum(
                    t.max_attempts * t.cost_per_attempt for t in self.tiers
                ),
                feedback_history=self.feedback_history
            )

    async def _develop_with_cascading(
        self,
        plan: Plan,
        additional_feedback: Optional[List[str]] = None
    ) -> Implementation:
        """
        Core cascading logic for DEVELOP phase.
        """

        for tier in self.tiers:
            for attempt in range(1, tier.max_attempts + 1):
                # Execute agent at current tier
                result = await self._execute_agent(
                    tier=tier.name,
                    plan=plan,
                    feedback=self.feedback_history + (additional_feedback or [])
                )

                # Run quality gate
                validation = await self.quality_gate.validate(result)

                if validation.passed:
                    # Success! Return immediately
                    return Implementation(
                        success=True,
                        output=result,
                        tier=tier.name,
                        total_attempts=attempt + sum(
                            t.max_attempts for t in self.tiers[:self.tiers.index(tier)]
                        ),
                        total_cost=self._calculate_cost_so_far()
                    )

                # Failed - log feedback
                feedback = Feedback(
                    tier=tier.name,
                    attempt=attempt,
                    errors=validation.errors,
                    failure_analysis=validation.analyze_failure()
                )
                self.feedback_history.append(feedback)

                # If not last attempt at this tier, retry
                if attempt < tier.max_attempts:
                    continue
                else:
                    # Tier exhausted, escalate to next
                    break

        # All tiers exhausted
        return Implementation(
            success=False,
            output=None,
            tier="ALL_EXHAUSTED",
            total_attempts=sum(t.max_attempts for t in self.tiers),
            total_cost=self._calculate_cost_so_far()
        )

    async def _execute_agent(
        self,
        tier: str,
        plan: Plan,
        feedback: List[Feedback]
    ) -> AgentResult:
        """
        Execute agent at specified tier with feedback from previous attempts.
        """

        # Build XML prompt with feedback
        prompt = self._build_xml_prompt(plan, feedback)

        # Call appropriate model for tier
        model = self._select_model(tier)

        # Execute
        result = await model.execute(prompt)

        return result

    def _build_xml_prompt(self, plan: Plan, feedback: List[Feedback]) -> str:
        """
        Build XML prompt incorporating feedback from previous attempts.
        """

        prompt = f"""
<task type="develop">
  <objective>{plan.objective}</objective>

  <plan>
    {plan.xml_content}
  </plan>

  <feedback_from_previous_attempts>
    {self._format_feedback(feedback)}
  </feedback_from_previous_attempts>

  <requirements>
    {plan.requirements}
  </requirements>

  <verification>
    {plan.verification_commands}
  </verification>
</task>
"""
        return prompt

    def _format_feedback(self, feedback: List[Feedback]) -> str:
        """Format feedback history for prompt."""
        if not feedback:
            return "<none>No previous attempts</none>"

        formatted = []
        for f in feedback:
            formatted.append(f"""
<attempt tier="{f.tier}" number="{f.attempt}">
  <errors>{f.errors}</errors>
  <analysis>{f.failure_analysis}</analysis>
</attempt>
""")

        return "\n".join(formatted)
```

---

## Integration with Existing XML Templates

Update [.claude/prompts/agent_templates.md](.claude/prompts/agent_templates.md) to include cascading option:

```xml
<!-- NEW: Cascading Tier Template -->
<task type="cascading_implementation">
  <objective>[Task to implement]</objective>

  <cascading_config>
    <tier name="CHEAP" attempts="3" cost="$0.015"/>
    <tier name="CAPABLE" attempts="3" cost="$0.090"/>
    <tier name="PREMIUM" attempts="1" cost="$0.450"/>
  </cascading_config>

  <quality_gate>
    <tests required="true">python -m pytest tests/ -v</tests>
    <lint required="true">ruff check .</lint>
    <types required="false">mypy src/</types>
  </quality_gate>

  <feedback_loop>
    On failure: Extract errors, log to feedback history, retry or escalate
  </feedback_loop>

  <review optional="true">
    If task is critical or user-requested, spawn higher-tier review agent
  </review>
</task>
```

---

## When to Use Cascading vs Direct Tier Selection

### Use Cascading When:
- ✅ Task complexity unknown upfront
- ✅ Cost optimization is priority
- ✅ Willing to trade time for cost
- ✅ Task has clear validation criteria (tests, lint)
- ✅ Failure feedback can inform retries

### Use Direct Tier Selection When:
- ✅ Task complexity known (e.g., always hard)
- ✅ Time-critical (can't afford retries)
- ✅ Expensive to validate (e.g., manual QA needed)
- ✅ User explicitly requests specific tier

---

## Rollout Plan

### Phase 1: Pilot (Week 1)
- [ ] Implement CascadingWorkflow class
- [ ] Create quality gate validation system
- [ ] Test with 10 simple bugs
- [ ] Measure: success rate, cost, time

### Phase 2: Expand (Week 2)
- [ ] Add to XML agent templates
- [ ] Test with moderate complexity tasks
- [ ] Measure: escalation rate, savings

### Phase 3: Review System (Week 3)
- [ ] Implement higher-tier agent review
- [ ] Test review approval/rejection flow
- [ ] Measure: review impact on quality

### Phase 4: Production (Week 4)
- [ ] Enable by default for appropriate tasks
- [ ] Document in user guides
- [ ] Monitor: cost savings, user satisfaction

---

## Success Metrics

### Quantitative
- **Cost Reduction**: Target 40-50% additional savings vs direct tier selection
- **Success Rate**: >90% of tasks complete within tier budget
- **Escalation Rate**: <30% escalate beyond CHEAP tier
- **Quality**: 0% regression in test pass rate or health score

### Qualitative
- **User Satisfaction**: Users feel costs are optimized without sacrificing quality
- **Transparency**: Users understand why escalations happened
- **Trust**: Users confident in quality gate validation

---

## Future Enhancements

### 1. Learned Escalation Patterns
Track which tasks escalate and why:
- "Telemetry bugs usually need CAPABLE+"
- "Health checks succeed at CHEAP 95% of time"
- Use ML to predict optimal starting tier

### 2. Dynamic Attempt Limits
Instead of fixed 3-3-1:
- Simple tasks: 2-2-1
- Hard tasks: 3-3-2
- Adjust based on task complexity

### 3. Parallel Attempts
Try CHEAP and CAPABLE in parallel:
- If CHEAP succeeds first: Use it, cancel CAPABLE
- If CAPABLE succeeds first: Use it, cost is marginally higher
- Trades cost for speed

### 4. Hybrid Human-AI Review
- Automated quality gate (always)
- AI agent review (conditional)
- Human review (critical systems only)

---

*Document version 1.0 - Created as part of XML Agent Communication Protocol and AI-ADDIE methodology development*
