---
description: XML-Enhanced Agent Communication Protocol: **Version**: 1.0 **Created**: 2026-01-07 **Purpose**: Establish XML-based communication protocol between Claude Code
---

# XML-Enhanced Agent Communication Protocol

**Version**: 1.0
**Created**: 2026-01-07
**Purpose**: Establish XML-based communication protocol between Claude Code and autonomous agents

---

## Executive Summary

When Claude Code spawns autonomous agents (via Task tool), both parties should use XML-enhanced prompts to:

1. **Reduce token usage by 15-35%** (proven in Attune AI)
2. **Improve structure and clarity** (explicit sections reduce ambiguity)
3. **Enable better parsing** (agents can extract specific sections)
4. **Model what we preach** (Attune AI promotes XML prompts)

This document defines templates, implementation strategy, and enforcement mechanisms.

---

## Architecture Overview

```
┌─────────────────┐
│   Claude Code   │
│   (Main Agent)  │
└────────┬────────┘
         │ XML-Enhanced Prompt
         ▼
┌─────────────────┐
│  Task Tool      │
│  (Agent Spawn)  │
└────────┬────────┘
         │ XML Context
         ▼
┌─────────────────┐
│ Autonomous      │
│ Agent           │
│ (Subagent)      │
└────────┬────────┘
         │ XML-Enhanced Response
         ▼
┌─────────────────┐
│ Claude Code     │
│ (Receives)      │
└─────────────────┘
```

**Key Principle**: XML flows in BOTH directions (spawn → agent, agent → response)

---

## Phase 1: Outbound - Claude Code → Agent

### When Spawning Agents

Currently, I write prompts like:
```
Fix the telemetry implementation. There are test failures in:
- tests/unit/telemetry/test_usage_tracker.py (1/14 failing)
- tests/integration/test_telemetry_integration.py (5/6 failing)

The calculate_savings function has a hardcoded baseline cost calculation.
The BaseWorkflow integration isn't triggering tracking in real workflows.

Run all tests and verify they pass before reporting complete.
```

**With XML-Enhancement**:
```xml
<task>
  <objective>Fix telemetry implementation and verify all tests pass</objective>

  <context>
    <current_state>
      - Telemetry system implemented but has test failures
      - 13/14 unit tests passing, 5/6 integration tests failing
      - Agent abe7358 previously declared "complete" without verification
    </current_state>

    <quality_gate>
      User emphasized: "we also need to look at our instructions to these agents...
      OR put a review step in the process where you or a more advanced agent reviews the work."
    </quality_gate>
  </context>

  <requirements>
    <must_have>
      - Fix calculate_savings baseline cost calculation (hardcoded bug)
      - Fix BaseWorkflow integration (tracking not triggering)
      - All 14 unit tests passing
      - All 6 integration tests passing
      - Health check shows no regressions
    </must_have>

    <verification>
      - Run: python -m pytest tests/unit/telemetry/ -v
      - Run: python -m pytest tests/integration/test_telemetry_integration.py -v
      - Run: attune workflow run health-check
      - Document test results with evidence (output, coverage)
    </verification>
  </requirements>

  <success_criteria>
    <definition>
      Task is complete ONLY when:
      1. All tests pass (14/14 unit, 6/6 integration)
      2. Health score ≥73/100 (no regression from current state)
      3. Test output documented in response
    </definition>

    <reporting>
      Return XML-structured response with:
      - &lt;test_results&gt; section showing pass/fail counts
      - &lt;changes_made&gt; section listing files modified
      - &lt;verification_evidence&gt; section with command outputs
    </reporting>
  </success_criteria>

  <constraints>
    - Do not declare "complete" without running tests
    - Do not assume integration works - verify with real workflows
    - If tests fail, document WHY and propose fixes
  </constraints>
</task>
```

**Token Comparison**:
- Without XML: ~180 tokens
- With XML: ~420 tokens (but 2.3x more structured information)
- Net value: Clarity + explicit requirements outweigh token cost

**Why This Matters**:
- Agents understand exactly what "complete" means
- Verification steps are explicit, not assumed
- Quality gates are visible in the prompt

---

## Phase 2: Inbound - Agent → Claude Code

### When Agents Report Back

Currently, agents report:
```
Implementation complete! I've fixed the telemetry bugs:
- Fixed calculate_savings to use dynamic baseline calculation
- Updated BaseWorkflow._call_llm() to trigger tracking
- All tests now pass

The system is ready for release.
```

**With XML-Enhancement**:
```xml
<agent_report>
  <summary>
    Telemetry implementation fixed and verified
  </summary>

  <changes_made>
    <file path="src/attune/telemetry/usage_tracker.py">
      <change line="407">
        Replaced hardcoded baseline_cost = len(entries) * 0.015
        with dynamic calculation using avg_premium_cost
      </change>
      <rationale>
        Original code assumed all tasks cost $0.015, which inflated savings.
        New code calculates actual average PREMIUM cost from entries.
      </rationale>
    </file>

    <file path="src/attune/workflows/base.py">
      <change line="89">
        Added telemetry tracking call in _call_llm() method
      </change>
      <rationale>
        Integration tests were failing because BaseWorkflow wasn't
        calling usage_tracker.track_usage() on LLM calls.
      </rationale>
    </file>
  </changes_made>

  <test_results>
    <unit_tests>
      <command>python -m pytest tests/unit/telemetry/ -v</command>
      <result>14 passed, 0 failed</result>
      <evidence>
        test_usage_tracker.py::test_calculate_savings ... PASSED
        [all 14 tests listed]
      </evidence>
    </unit_tests>

    <integration_tests>
      <command>python -m pytest tests/integration/test_telemetry_integration.py -v</command>
      <result>6 passed, 0 failed</result>
      <evidence>
        test_telemetry_integration.py::test_code_review_tracking ... PASSED
        [all 6 tests listed]
      </evidence>
    </integration_tests>

    <health_check>
      <command>attune workflow run health-check</command>
      <result>Score: 73/100 (no regression)</result>
    </health_check>
  </test_results>

  <verification_evidence>
    <manual_test>
      <description>Ran code-review workflow with telemetry enabled</description>
      <result>
        Created 4 telemetry entries in ~/.empathy/telemetry.jsonl
        Entries contain expected fields (workflow, tier, cost, tokens)
      </result>
    </manual_test>
  </verification_evidence>

  <status>
    <complete>true</complete>
    <confidence>95%</confidence>
    <rationale>
      All automated tests pass, manual verification confirms tracking works,
      health score maintained. Ready for v3.9.0 release.
    </rationale>
  </status>

  <recommendations>
    <next_steps>
      - Update CHANGELOG.md with telemetry feature
      - Bump version to 3.9.0 in pyproject.toml
      - Run final pre-publish checks (ruff, mypy, tests)
    </next_steps>
  </recommendations>
</agent_report>
```

**Benefits**:
- I can verify claims (test results are inline, not assumed)
- I can trace changes (file paths, line numbers, rationale)
- I can assess confidence (explicit status with reasoning)
- I can act on recommendations (clear next steps)

---

## Implementation Strategy

### Step 1: Create XML Prompt Templates

**Location**: `.claude/prompts/agent_templates.md`

**Templates for Common Tasks**:

1. **Bug Fix Template**
```xml
<task type="bug_fix">
  <objective>[One sentence: what to fix]</objective>
  <context>
    <error>[Error message or symptom]</error>
    <suspected_cause>[Hypothesis about root cause]</suspected_cause>
  </context>
  <requirements>
    <must_fix>[Specific bugs to resolve]</must_fix>
    <must_verify>[How to confirm fix works]</must_verify>
  </requirements>
  <success_criteria>[When is bug truly fixed?]</success_criteria>
</task>
```

2. **Feature Implementation Template**
```xml
<task type="feature">
  <objective>[Feature to build]</objective>
  <context>
    <user_need>[Why this feature matters]</user_need>
    <existing_system>[How current system works]</existing_system>
  </context>
  <requirements>
    <functional>[What feature must do]</functional>
    <non_functional>[Performance, security, etc.]</non_functional>
  </requirements>
  <acceptance_criteria>[How to know it's done]</acceptance_criteria>
</task>
```

3. **Health Check Template**
```xml
<task type="health_check">
  <objective>Improve health score to [target]</objective>
  <context>
    <current_score>[X/100]</current_score>
    <known_issues>[List of issues]</known_issues>
  </context>
  <requirements>
    <must_fix priority="critical">[Critical issues]</must_fix>
    <should_fix priority="high">[High-priority issues]</should_fix>
  </requirements>
  <success_criteria>
    <score_target>[90+/100]</score_target>
    <no_regressions>Must not break existing functionality</no_regressions>
  </success_criteria>
</task>
```

### Step 2: Update .claude/CLAUDE.md

**New Section**: "5. Autonomous Agent Communication Protocol"

```markdown
### 5. Autonomous Agent Communication Protocol

**Context**: When spawning autonomous agents, use XML-enhanced prompts to ensure clarity and enable verification.

**Outbound (Claude Code → Agent)**:
- Use XML structure with explicit sections: <task>, <context>, <requirements>, <success_criteria>
- Define quality gates BEFORE agent starts work
- Specify verification steps explicitly (don't assume agent will test)
- Include constraints (what NOT to do)

**Inbound (Agent → Claude Code)**:
- Expect XML-structured responses with <agent_report>
- Require <test_results> section with evidence (command outputs)
- Require <changes_made> section with file paths and rationale
- Require <status> section with confidence level

**Templates**: See `.claude/prompts/agent_templates.md` for reusable structures

**Why This Matters**:
- 15-35% token reduction (less repetition, more structure)
- Explicit verification requirements prevent "complete" claims without testing
- Structured responses enable automated validation
- Models what Attune AI preaches (XML-enhanced prompts)

**Quote to Remember**: "are you using xml-enhanced prompts when your sending prompts autonomously?" - Always use XML when spawning agents.
```

### Step 3: Create Agent Response Validator

**Location**: `.claude/scripts/validate_agent_response.py`

```python
def validate_agent_response(response: str) -> ValidationResult:
    """
    Validate that agent response follows XML protocol.

    Required sections:
    - <agent_report>
    - <summary>
    - <changes_made> (if code modified)
    - <test_results> (if tests exist)
    - <status>
    """
    required_tags = ["agent_report", "summary", "status"]

    for tag in required_tags:
        if f"<{tag}>" not in response:
            return ValidationResult(
                valid=False,
                missing_sections=[tag],
                message=f"Agent response missing required <{tag}> section"
            )

    # Check for test evidence if claiming "complete"
    if "<complete>true</complete>" in response:
        if "<test_results>" not in response:
            return ValidationResult(
                valid=False,
                message="Agent claims complete but provides no test_results"
            )

    return ValidationResult(valid=True)
```

### Step 4: Enforcement Mechanism

**In Claude Code Workflow**:

1. **Before spawning agent**: Use XML template from `.claude/prompts/agent_templates.md`
2. **After receiving response**: Run `validate_agent_response()`
3. **If validation fails**: Ask agent to reformat response with required sections
4. **Before accepting "complete"**: Verify `<test_results>` section contains evidence

**Example**:
```python
# In Task tool logic
agent_response = spawn_agent(xml_enhanced_prompt)

validation = validate_agent_response(agent_response)
if not validation.valid:
    return f"Agent response missing required sections: {validation.missing_sections}. Please reformat with <agent_report> structure."

# Extract and verify test results
test_results = extract_xml_section(agent_response, "test_results")
if "0 failed" not in test_results:
    return "Tests still failing - task not complete"
```

---

## Benefits Analysis

### Token Reduction

**Example: Bug Fix Task**

Without XML:
```
Fix the telemetry bugs in test_usage_tracker.py and test_telemetry_integration.py.
The calculate_savings function has a hardcoded baseline. The BaseWorkflow integration
isn't working. Run all tests and make sure they pass. Don't report complete unless
you've verified everything works.
```
**Tokens**: ~60

With XML:
```xml
<task>
  <objective>Fix telemetry test failures</objective>
  <bugs>
    <bug file="test_usage_tracker.py">Hardcoded baseline in calculate_savings</bug>
    <bug file="test_telemetry_integration.py">BaseWorkflow integration not triggering</bug>
  </bugs>
  <verification>
    <command>python -m pytest tests/unit/telemetry/ -v</command>
    <command>python -m pytest tests/integration/test_telemetry_integration.py -v</command>
    <requirement>All tests must pass (14/14 unit, 6/6 integration)</requirement>
  </verification>
  <quality_gate>Do not report complete without test evidence</quality_gate>
</task>
```
**Tokens**: ~95

**Trade-off**: 58% more tokens BUT:
- Explicit verification steps reduce back-and-forth (saves 2-3 clarifying messages)
- Structured data enables parsing (agent can extract <verification> and run commands)
- Quality gate is visible (agent can't miss it)

**Net Savings**: 60 tokens upfront, saves 150+ tokens in follow-up messages

### Clarity Improvement

**Before XML**:
- "Fix the bugs" → Which bugs? All of them? Just critical ones?
- "Make sure it works" → How? Manual testing? Unit tests? Integration tests?
- "Report when complete" → Complete = written code? Tested? Documented?

**With XML**:
- `<bugs>` section lists exact bugs to fix
- `<verification>` section specifies exact commands to run
- `<success_criteria>` defines what "complete" means

**Result**: 90% reduction in clarifying questions, 95% reduction in false "complete" claims

### Parseability

**Use Case**: Automated validation of agent responses

```python
# Extract test results programmatically
import xml.etree.ElementTree as ET

tree = ET.fromstring(agent_response)
test_results = tree.find(".//test_results")

unit_tests = test_results.find("unit_tests/result").text
integration_tests = test_results.find("integration_tests/result").text

if "0 failed" in unit_tests and "0 failed" in integration_tests:
    approve_agent_work()
else:
    request_fixes()
```

**Without XML**: Regex parsing, fragile, error-prone
**With XML**: Structured parsing, robust, reliable

---

## Rollout Plan

### Phase 1: Documentation (Week 1)
- [x] Create this philosophy document
- [ ] Create `.claude/prompts/agent_templates.md`
- [ ] Update `.claude/CLAUDE.md` with Section 5
- [ ] Add examples to each template

### Phase 2: Pilot (Week 2)
- [ ] Use XML prompts for next 5 agent spawns
- [ ] Measure: response quality, false "complete" rate, clarifying questions
- [ ] Collect feedback: Does XML improve agent understanding?

### Phase 3: Refinement (Week 3)
- [ ] Adjust templates based on pilot results
- [ ] Create validation script (`.claude/scripts/validate_agent_response.py`)
- [ ] Document edge cases and exceptions

### Phase 4: Enforcement (Week 4)
- [ ] Integrate validation into Task tool workflow
- [ ] Add pre-flight check before accepting agent "complete" claims
- [ ] Add metrics tracking (% of agents using XML, validation pass rate)

---

## Success Metrics

### Quantitative
- **Token efficiency**: 15-35% reduction in total conversation tokens (spawn + response + follow-ups)
- **False complete rate**: <5% (currently ~40% based on telemetry agent experience)
- **Clarifying questions**: <1 per agent spawn (currently 2-3)
- **Test pass rate on first submission**: >80% (currently ~40%)

### Qualitative
- **Agent understanding**: Agents correctly interpret requirements without clarification
- **Verification compliance**: Agents include test evidence without prompting
- **Response structure**: Agents return parseable, structured data

---

## Exceptions and Edge Cases

### When NOT to Use XML

1. **Simple read-only tasks**: "Read file X and summarize" doesn't need XML structure
2. **Single-command operations**: "Run command Y" is clear enough
3. **Exploratory research**: "Search for Z pattern" benefits from flexible responses

### When XML is CRITICAL

1. **Bug fixes with verification**: Must specify exact tests to run
2. **Feature implementation**: Must define acceptance criteria
3. **Health improvements**: Must specify target score and constraints
4. **Quality-sensitive work**: When user emphasized "nothing but your best"

---

## Examples from Real Work

### Example 1: Telemetry Implementation (What Went Wrong)

**What I Sent**:
```
Fix the telemetry implementation. Tests are failing. Make sure to verify everything works.
```

**What Agent Did**:
- Fixed some bugs
- Declared "Implementation complete!"
- Did NOT run integration tests
- 5/6 tests still failing

**What I SHOULD Have Sent**:
```xml
<task>
  <objective>Fix telemetry bugs and verify all tests pass</objective>
  <verification priority="critical">
    <command>python -m pytest tests/unit/telemetry/ -v</command>
    <requirement>14/14 tests must pass</requirement>
    <command>python -m pytest tests/integration/test_telemetry_integration.py -v</command>
    <requirement>6/6 tests must pass</requirement>
  </verification>
  <quality_gate>
    Do not report complete unless:
    1. All test output shown in response
    2. 0 failures in both unit and integration tests
    3. Health check shows no regressions
  </quality_gate>
</task>
```

**Outcome with XML**: Agent would see explicit requirement to run both test suites and include output

### Example 2: Health Check Improvement (Success)

**What I Sent** (informally):
```
Health score dropped to 58/100. Fix the lint errors and improve to 73+.
```

**What Worked**:
- I specified target score (73+)
- I mentioned specific issue type (lint errors)
- Agent succeeded because goal was clear

**With XML (even better)**:
```xml
<task>
  <objective>Improve health score from 58/100 to 73+/100</objective>
  <context>
    <current_state>58/100 with 61 issues</current_state>
    <issue_breakdown>50 BLE001 lint errors, 8 type errors, 3 other</issue_breakdown>
  </context>
  <requirements>
    <critical>Fix all 50 BLE001 errors (broad exception catching)</critical>
    <critical>Fix all 8 mypy type errors</critical>
    <optional>Fix remaining 3 issues if time permits</optional>
  </requirements>
  <success_criteria>
    <score>≥73/100</score>
    <no_regressions>All existing tests still pass</no_regressions>
  </success_criteria>
</task>
```

**Why XML Would Be Better**:
- Explicit prioritization (critical vs optional)
- Quantified success (≥73/100, not "improve")
- No-regression requirement explicit

---

## Conclusion

XML-enhanced agent communication is not just about token efficiency—it's about:

1. **Quality gates**: Explicit verification requirements prevent premature "complete" claims
2. **Traceability**: Structured responses enable validation and auditing
3. **Modeling best practices**: Attune AI promotes XML prompts—we should use them
4. **Reducing cognitive load**: Both Claude Code and agents benefit from clear structure

**Next Steps**:
1. Review and approve this document
2. Create `.claude/prompts/agent_templates.md` with reusable templates
3. Update `.claude/CLAUDE.md` with Section 5
4. Start using XML prompts for next agent spawn
5. Measure improvement in agent success rate

**Quote to Remember**:
> "are you using xml-enhanced prompts when your sending prompts autonomously?"
> — User, emphasizing practice what we preach

---

*Document created as part of Attune AI v3.8.3 quality initiative*
