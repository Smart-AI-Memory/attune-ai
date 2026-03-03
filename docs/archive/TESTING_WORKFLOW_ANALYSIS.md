# Testing Workflow Analysis & Optimization Plan

**Date:** January 30, 2026

**Goal:** Improve autonomous test generation workflow to leverage Anthropic's capabilities better and increase workflow coverage

## Status

✅ PHASES 1-3 COMPLETE

---

## Implementation Status

| Phase | Status | Completion Date | Summary |
|-------|--------|-----------------|---------|
| **Phase 1: Critical Fixes** | ✅ COMPLETE | January 30, 2026 | Extended thinking (20K tokens), prompt caching, workflow detection, few-shot learning |
| **Phase 2: Multi-Turn Refinement** | ✅ COMPLETE | January 30, 2026 | Iterative test generation with validation loop (generate → validate → fix → repeat) |
| **Phase 3: Coverage-Guided Generation** | ✅ COMPLETE | January 30, 2026 | Coverage analysis integration with iterative improvement targeting uncovered lines |

### Key Achievements

#### Phase 1 (Completed)

- ✅ Removed source code truncation (3000 chars → full source)
- ✅ Added extended thinking mode (20K token budget)
- ✅ Implemented prompt caching (90% cost reduction)
- ✅ Added workflow detection with regex patterns
- ✅ Created workflow-specific prompts with LLM mocking templates
- ✅ Added few-shot learning examples

#### Phase 2 (Completed)

- ✅ Implemented `_run_pytest_validation()` for failure detection
- ✅ Added `_call_llm_with_history()` for conversation context
- ✅ Implemented `_generate_with_refinement()` with max 3 iterations
- ✅ Integrated refinement into main generation flow
- ✅ Added configuration option `enable_refinement` (default: True)

#### Phase 3 (Completed)

- ✅ Implemented `_run_coverage_analysis()` with pytest-cov integration
- ✅ Added `_extract_uncovered_lines()` for targeted improvement
- ✅ Implemented `_generate_with_coverage_target()` with iterative refinement
- ✅ Integrated coverage-guided generation into main flow
- ✅ Added configuration option `enable_coverage_guided` (default: False)

### Usage

```bash
# Phase 1 only (basic generation)
python -m attune.workflows.autonomous_test_gen <batch> <modules_json> --no-refinement

# Phase 1 + Phase 2 (default - with refinement)
python -m attune.workflows.autonomous_test_gen <batch> <modules_json>

# Phase 1 + Phase 2 + Phase 3 (full stack - slower but highest coverage)
python -m attune.workflows.autonomous_test_gen <batch> <modules_json> --coverage-guided
```

### Validation

Test script created: [scripts/test_phases_2_3.py](../scripts/test_phases_2_3.py)

```bash
python scripts/test_phases_2_3.py
```

---

## Current State Assessment

### Autonomous Test Generation Workflow

**Location:** [src/attune/workflows/autonomous_test_gen.py](../src/attune/workflows/autonomous_test_gen.py)

**How it works:**
1. Reads source code (truncated to 3000 chars)
2. Sends single prompt to Claude Sonnet 4.5
3. Gets test file back
4. Validates syntax
5. Writes to file

**Current Coverage:**
- **Utility modules**: 80-100% (excellent)
- **Workflow execution**: 6-10% (poor)
- **Overall**: 19.39%

---

## Identified Limitations

### 1. **Source Code Truncation** (CRITICAL)

```python
# Current implementation
{source_code[:3000]}{"..." if len(source_code) > 3000 else ""}
```

**Problem:**
- Workflow files are 200-800 lines (workflow.py files ~280-383 lines)
- 3000 chars ≈ 60-80 lines of Python
- Missing 75%+ of context for large files

**Impact:**
- Can't generate tests for methods Claude never sees
- Misses complex error handling logic
- Incomplete understanding of class relationships

### 2. **No Extended Thinking** (HIGH PRIORITY)

**Current:** Single-pass generation with no planning phase

**Missing capability:**
- Extended thinking for test strategy planning
- Analysis of edge cases before writing tests
- Consideration of mocking strategies

**Anthropic Best Practice:**
Use extended thinking for complex tasks requiring planning.

### 3. **No Prompt Caching** (COST OPTIMIZATION)

**Current:** Sends full source code on every retry

**Impact:**
- Wasted tokens on repeated source code
- Higher costs for iterative refinement
- Slower generation

**Anthropic Best Practice:**
Cache static context (source code, requirements) using prompt caching.

### 4. **Single-Turn Generation** (QUALITY ISSUE)

**Current:** Generate once, validate syntax, done

**Missing:**
- Iterative refinement based on validation
- Coverage-guided generation
- Self-correction when tests fail

**Better Approach:**
Multi-turn conversation:
1. Generate initial tests
2. Run them, collect failures
3. Ask Claude to fix specific failures
4. Repeat until high quality

### 5. **Basic Prompt Engineering** (QUALITY ISSUE)

**Current prompt:**
```
Generate comprehensive behavioral tests for this Python module.
...
Return ONLY the complete Python test file content, no explanations.
```

**Missing:**
- Few-shot examples of excellent tests
- Specific coverage targets
- Error pattern examples
- Mocking templates
- XML-tagged structured instructions

### 6. **No Workflow-Specific Logic** (COVERAGE GAP)

**Current:** Same prompt for all modules

**Problem:**
Workflows need special handling:
- Mock LLM API calls
- Mock tier routing decisions
- Mock telemetry
- Mock cache hits/misses
- Test cost calculations

**Current workflow coverage:** 6-10%

---

## Anthropic's Native Testing Capabilities

### What Claude Can Do (That We're Not Using)

#### 1. **Extended Thinking Mode**

```python
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=8000,
    thinking={
        "type": "enabled",
        "budget_tokens": 4000  # Dedicate 4K tokens to thinking
    },
    messages=[...]
)
```

**Benefits:**
- Better test strategy planning
- More thorough edge case analysis
- Structured approach to mocking

#### 2. **Prompt Caching**

```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Here is the source code to test:",
                "cache_control": {"type": "ephemeral"}
            },
            {
                "type": "text",
                "text": source_code,  # This gets cached!
                "cache_control": {"type": "ephemeral"}
            },
            {
                "type": "text",
                "text": "Generate tests focusing on error handling"
            }
        ]
    }
]
```

**Benefits:**
- 90% cost reduction on cached content
- Enables multi-turn refinement
- Can run multiple generation strategies cheaply

#### 3. **Tool Use for Validation**

```python
tools = [
    {
        "name": "run_pytest",
        "description": "Run pytest on generated tests to validate",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_file": {"type": "string"}
            }
        }
    }
]
```

**Benefits:**
- Claude can validate its own tests
- Iterative refinement until tests pass
- Self-debugging capability

#### 4. **Few-Shot Learning with Examples**

Provide 2-3 examples of excellent tests as part of the prompt:

```python
prompt = f"""Here are examples of excellent behavioral tests:

EXAMPLE 1: Testing a workflow class
{example_workflow_test}

EXAMPLE 2: Testing with mocked LLM
{example_llm_mock_test}

Now generate similar tests for: {module_name}
"""
```

**Benefits:**
- Consistent test quality
- Proper mocking patterns
- Coverage best practices

---

## Recommended Improvements

### **Phase 1: Critical Fixes** (1-2 hours)

#### 1.1 Remove Source Code Truncation

```python
# BEFORE (bad)
{source_code[:3000]}

# AFTER (good)
# Send full source code with prompt caching
{source_code}  # No truncation!
```

**Implementation:**
- Use prompt caching to avoid cost explosion
- For very large files (>10K lines), intelligently chunk by class/function

#### 1.2 Add Prompt Caching

```python
def _generate_with_llm(self, module_name: str, module_path: str, source_file: Path, source_code: str) -> str | None:
    # Cache the source code and requirements
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": self._get_test_requirements(),  # Cached
                    "cache_control": {"type": "ephemeral"}
                },
                {
                    "type": "text",
                    "text": self._get_example_tests(),  # Cached
                    "cache_control": {"type": "ephemeral"}
                },
                {
                    "type": "text",
                    "text": f"SOURCE CODE:\\n```python\\n{source_code}\\n```",
                    "cache_control": {"type": "ephemeral"}
                },
                {
                    "type": "text",
                    "text": f"Generate comprehensive tests for {module_name}"
                }
            ]
        }
    ]

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=20000,
        messages=messages
    )
```

**Cost savings:** 90% on repeated generations

#### 1.3 Enable Extended Thinking

```python
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=16000,  # Output tokens
    thinking={
        "type": "enabled",
        "budget_tokens": 4000  # Thinking budget
    },
    messages=[...]
)
```

**Quality improvement:** Better test planning, more edge cases

---

### **Phase 2: Workflow-Specific Improvements** (2-3 hours)

#### 2.1 Detect Workflow Files

```python
def _is_workflow_module(self, source_code: str, module_path: str) -> bool:
    """Detect if module is a workflow requiring special handling."""
    indicators = [
        "class.*Workflow",
        "execute.*async def",
        "tier_routing",
        "LLMProvider",
        "TelemetryCollector"
    ]
    return any(re.search(pattern, source_code) for pattern in indicators)
```

#### 2.2 Workflow-Specific Prompt

```python
def _get_workflow_test_prompt(self, module_name: str, source_code: str) -> str:
    return f"""Generate comprehensive tests for this WORKFLOW module.

CRITICAL: This module makes LLM API calls and requires mocking.

Required mocking strategies:
1. Mock LLM API responses using pytest-mock or unittest.mock
2. Mock tier routing decisions (cheap/capable/premium)
3. Mock telemetry collection
4. Mock cache hits/misses
5. Test cost calculations

Example mocking pattern:
```python
@pytest.fixture
def mock_llm_client(mocker):
    mock = mocker.patch('anthropic.Anthropic')
    mock.return_value.messages.create.return_value = Mock(
        content=[Mock(text="mock response")],
        usage=Mock(input_tokens=100, output_tokens=50)
    )
    return mock

def test_workflow_execution(mock_llm_client):
    workflow = MyWorkflow()
    result = await workflow.execute(input_data)

    # Verify LLM was called correctly
    mock_llm_client.return_value.messages.create.assert_called_once()

    # Verify tier routing
    call_args = mock_llm_client.return_value.messages.create.call_args
    assert call_args.kwargs['model'] == 'claude-sonnet-4-5'  # capable tier

    # Verify result
    assert result is not None
```

SOURCE CODE:
```python
{source_code}
```

Generate tests that:
1. Test successful execution with mocked LLM
2. Test error handling (API failures, timeouts)
3. Test tier routing logic
4. Test telemetry recording
5. Test cost calculation
6. Achieve 40%+ coverage (realistic for workflow classes)
"""
```

**Coverage improvement:** 8% → 40%+ for workflow files

---

### **Phase 3: Multi-Turn Refinement** (2-3 hours)

#### 3.1 Iterative Test Generation

```python
def _generate_with_refinement(self, module_name: str, module_path: str, source_code: str, max_iterations: int = 3) -> str | None:
    """Generate tests with iterative refinement.

    Process:
    1. Generate initial tests
    2. Run them with pytest
    3. If failures, ask Claude to fix
    4. Repeat until tests pass or max iterations
    """

    conversation_history = []

    # Initial generation
    initial_prompt = self._build_generation_prompt(module_name, module_path, source_code)
    test_content = self._call_llm(initial_prompt, conversation_history)

    for iteration in range(max_iterations):
        # Write and validate
        test_file = self._write_temp_test(test_content)
        validation_result = self._run_pytest(test_file)

        if validation_result.passed:
            logger.info(f"✅ Tests passed on iteration {iteration + 1}")
            return test_content

        # Ask Claude to fix failures
        refinement_prompt = f"""The tests you generated have failures:

{validation_result.failures}

Please fix these specific issues and return the complete corrected test file."""

        conversation_history.append({
            "role": "assistant",
            "content": test_content
        })
        conversation_history.append({
            "role": "user",
            "content": refinement_prompt
        })

        test_content = self._call_llm_with_history(conversation_history)

    logger.warning(f"⚠️ Max iterations reached for {module_name}")
    return test_content  # Return best attempt
```

**Quality improvement:** Much higher test pass rate

---

### **Phase 4: Coverage-Guided Generation** (3-4 hours)

#### 4.1 Run Coverage Analysis

```python
def _generate_with_coverage_target(self, module_name: str, source_code: str, target_coverage: float = 0.80) -> str:
    """Generate tests iteratively until coverage target met."""

    test_content = self._generate_initial_tests(module_name, source_code)

    for iteration in range(5):
        # Run coverage
        coverage_result = self._run_coverage(test_content, module_name)

        if coverage_result.coverage >= target_coverage:
            logger.info(f"✅ Achieved {coverage_result.coverage:.1%} coverage")
            return test_content

        # Identify uncovered lines
        uncovered_lines = coverage_result.missing_lines
        uncovered_code = self._extract_lines(source_code, uncovered_lines)

        # Ask Claude to add tests for uncovered code
        refinement_prompt = f"""Current coverage: {coverage_result.coverage:.1%}
Target: {target_coverage:.1%}

Uncovered code:
```python
{uncovered_code}
```

Add tests to cover these lines. Return the COMPLETE test file with additions."""

        test_content = self._refine_tests(refinement_prompt, test_content)

    return test_content
```

**Coverage improvement:** Systematic path to 80%+ coverage

---

## Implementation Plan

### **Weekend Implementation** (7-8 hours total)

#### **Saturday Morning (3 hours)**
1. **Remove source truncation** + add prompt caching (1 hour)
   - Update `_generate_with_llm()` to use full source
   - Implement caching structure
   - Test on 2-3 modules

2. **Add extended thinking** (30 min)
   - Enable thinking mode
   - Validate improved test quality

3. **Workflow detection + special handling** (1.5 hours)
   - Implement `_is_workflow_module()`
   - Create workflow-specific prompt
   - Add mocking examples

#### **Saturday Afternoon (2 hours)**
4. **Multi-turn refinement** (2 hours)
   - Implement conversation history
   - Add pytest validation loop
   - Test on workflow modules

#### **Sunday Morning (2-3 hours)**
5. **Coverage-guided generation** (2 hours)
   - Integrate pytest-cov
   - Extract uncovered lines
   - Iterative coverage improvement

6. **Batch regeneration** (1 hour)
   - Regenerate workflow module tests (batch11 subset)
   - Validate coverage improvements
   - Document results

---

## Expected Outcomes

### **Coverage Targets**

| Module Type | Current | Target | Strategy |
|-------------|---------|--------|----------|
| Utility/Config | 100% | 100% | ✅ Already good |
| AST Analysis | 82% | 90% | Coverage-guided refinement |
| Templates | 90% | 95% | Minor additions |
| **Workflows** | **8%** | **40-50%** | **Workflow-specific mocking** |
| Report Formatters | 2% | 60% | Multi-turn refinement |

### **Quality Improvements**

- **Test pass rate:** 99.9% → 100%
- **Mocking quality:** Basic → Comprehensive (LLM, tier routing, telemetry)
- **Coverage depth:** Surface-level → Deep (error paths, edge cases)
- **Generation cost:** High → 90% lower (prompt caching)

### **Metrics After Implementation**

- ✅ **Overall coverage:** 19.39% → 35%+ (target: +80% improvement)
- ✅ **Workflow coverage:** 8% → 40%+ (target: 5x improvement)
- ✅ **Test quality:** Passes syntax → Passes execution + validation
- ✅ **Generation cost:** $X → $0.10X (90% reduction via caching)
- ✅ **Test count:** 1,421 → 1,600+ (better coverage)

---

## Risk Mitigation

### **Risk 1: Increased Generation Time**

**Mitigation:**
- Parallel generation (use asyncio)
- Cache extensively (90% faster on retries)
- Only iterate when needed (early exit on success)

### **Risk 2: API Costs**

**Mitigation:**
- Prompt caching reduces costs by 90%
- Extended thinking is budgeted (4K tokens max)
- Multi-turn only when validation fails

### **Risk 3: Test Quality Variance**

**Mitigation:**
- Validation loop ensures tests run
- Coverage-guided ensures completeness
- Few-shot examples ensure consistency

---

## Next Steps

1. **Approve this plan** - Confirm direction aligns with goals
2. **Phase 1 implementation** - Critical fixes (1-2 hours)
3. **Validate on workflows** - Test workflow.py coverage improvement
4. **Phase 2-4 if successful** - Full implementation

**Ready to proceed with Phase 1?**
