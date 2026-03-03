---
description: LLM Workflow Enhancement Plan: **Created:** January 29, 2026 **Status:** Approved - Ready for Implementation **Goal:** Enhance template-based workflows with com
---

# LLM Workflow Enhancement Plan

**Created:** January 29, 2026
**Status:** Approved - Ready for Implementation
**Goal:** Enhance template-based workflows with comprehensive LLM generation

---

## Executive Summary

Following the successful implementation of LLM-based test generation (reaching 90% coverage), we will systematically enhance other template-based workflows to use the same hybrid approach: intelligent LLM generation with fallback templates.

**Key Success Metrics from Test Generation:**
- Generated comprehensive, runnable tests (not placeholders)
- Achieved 80%+ coverage per module
- Reduced manual work by 95%
- Dashboard-integrated with real-time monitoring

---

## Phase 1: High-Impact Workflows (Week 1-2)

### 1. Test Generation Behavioral (`test_gen_behavioral.py`)

**Current State:**
```python
def generate_test_template(self, module_info: ModuleInfo, output_path: Path) -> str:
    # Returns placeholder template with "pass # TODO: Implement"
    return "\n".join(template_lines)
```

**Target State:**
```python
def generate_test_with_llm(self, module_info: ModuleInfo, output_path: Path) -> str:
    # Returns complete, runnable tests with proper assertions
    return llm_generated_comprehensive_tests
```

**Implementation Steps:**
1. Copy `_generate_with_llm()` from `autonomous_test_gen.py`
2. Adapt prompt for behavioral test style
3. Add fallback to template if LLM fails
4. Update CLI to support `--use-llm` flag (default: True)
5. Add tests comparing LLM vs template output

**Effort:** 2-3 hours
**Impact:** High - eliminates "TODO" placeholders
**File:** `src/attune/workflows/test_gen_behavioral.py`

---

### 2. Documentation Generator (`documentation_orchestrator.py`)

**Current State:**
- Uses some AI for analysis
- Template-based docstring generation
- Limited example generation

**Target State:**
- Comprehensive API documentation
- Real, executable code examples
- Usage guides with best practices
- Edge case documentation

**Implementation Steps:**
1. Create `DocumentationLLMGenerator` class
2. Prompt engineering for different doc types:
   - API reference (functions, classes, parameters)
   - Usage examples (copy-paste ready)
   - Best practices (dos and don'ts)
3. Add smart caching (docs rarely change)
4. Integrate with existing pipeline
5. Add quality validation (check examples run)

**Effort:** 1 day
**Impact:** High - better onboarding, fewer support questions
**Files:**
- `src/attune/workflows/documentation_orchestrator.py`
- New: `src/attune/workflows/doc_llm_generator.py`

**Example Prompt:**
```python
prompt = f"""Generate comprehensive API documentation for this Python module.

SOURCE CODE:
{source_code}

Generate:
1. **API Reference**: Document all public functions/classes with:
   - Clear parameter descriptions
   - Return value documentation
   - Raises section for exceptions

2. **Usage Examples**: 3-5 copy-paste ready examples showing:
   - Basic usage
   - Advanced usage
   - Common patterns
   - Edge cases

3. **Best Practices**: Dos and don'ts for using this API

Format as Markdown suitable for MkDocs.
"""
```

---

## Phase 2: Code Quality Workflows (Week 3)

### 3. Code Review (`code_review.py`)

**Current State:**
- Pattern-based issue detection
- Template review comments
- Limited context understanding

**Target State:**
- Deep code understanding
- Contextual suggestions with explanations
- Security vulnerability detection
- Performance optimization recommendations

**Implementation Steps:**
1. Create `CodeReviewLLMAnalyzer` class
2. Multi-stage analysis:
   - **Stage 1 (Cheap)**: Quick pattern detection
   - **Stage 2 (Capable)**: Deep analysis for flagged areas
   - **Stage 3 (Premium)**: Complex security/architecture review
3. Structured output format (JSON)
4. Confidence scores for each finding
5. Integration with existing review pipeline

**Effort:** 1.5 days
**Impact:** High - fewer false positives, better suggestions
**File:** `src/attune/workflows/code_review.py`

**Example Prompt:**
```python
prompt = f"""Perform deep code review on this Python code.

CODE:
{code_snippet}

CONTEXT:
{surrounding_context}

Analyze for:
1. **Security Issues**: SQL injection, XSS, path traversal, etc.
2. **Performance**: Inefficient algorithms, memory leaks
3. **Maintainability**: Code smells, complexity, duplication
4. **Correctness**: Logic errors, edge cases
5. **Best Practices**: Python idioms, type hints

For each issue, provide:
- Severity (critical/high/medium/low)
- Line number
- Clear explanation
- Specific fix suggestion
- Example of correct implementation

Return as JSON array of findings.
"""
```

---

### 4. Refactoring Assistant (`refactor.py`)

**Current State:**
- Template-based refactoring patterns
- Limited understanding of code intent
- Manual verification required

**Target State:**
- Intent-aware refactoring
- Automatic test generation for refactored code
- Safety verification (semantic equivalence)
- Performance comparison

**Implementation Steps:**
1. Create `RefactoringLLMAssistant` class
2. Pre-refactor analysis:
   - Understand current code intent
   - Identify test coverage
   - Flag risky changes
3. LLM-guided refactoring with constraints
4. Post-refactor validation:
   - Generate tests for new code
   - Compare behavior
   - Performance benchmarks
5. Interactive approval workflow

**Effort:** 2 days
**Impact:** Medium-High - safer, more intelligent refactoring
**File:** `src/attune/workflows/refactor.py`

---

## Phase 3: Analysis Workflows (Week 4)

### 5. Bug Prediction (`bug_predict.py`)

**Current State:**
- Pattern-based bug detection
- High false positive rate
- Limited to known patterns

**Target State:**
- Understand code flow
- Predict subtle bugs
- Explain why something is a bug
- Suggest preventive patterns

**Implementation Steps:**
1. Create `BugPredictionLLMAnalyzer` class
2. Multi-pass analysis:
   - **Pass 1**: Static analysis (AST, patterns)
   - **Pass 2**: LLM prediction for flagged areas
   - **Pass 3**: Confidence scoring
3. False positive learning loop
4. Integration with FeedbackLoop for improvement
5. Explanation generation

**Effort:** 1 day
**Impact:** Medium - better bug detection, fewer false positives
**File:** `src/attune/workflows/bug_predict.py`

---

## Implementation Architecture

### Core Pattern: Hybrid LLM Generator

```python
class LLMWorkflowGenerator:
    """Base class for LLM-enhanced workflow generation.

    Provides:
    - LLM generation with fallback
    - Caching for expensive operations
    - Quality validation
    - Dashboard integration
    """

    def __init__(self, model_tier: str = "capable"):
        self.model_tier = model_tier
        self.cache = LRUCache(maxsize=100)

    def generate(self, context: dict, prompt: str) -> str:
        """Generate output with LLM, fallback to template."""
        # Check cache
        cache_key = self._make_cache_key(context)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Try LLM generation
        try:
            result = self._generate_with_llm(prompt)
            if self._validate(result):
                self.cache[cache_key] = result
                return result
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")

        # Fallback to template
        return self._generate_with_template(context)

    def _generate_with_llm(self, prompt: str) -> str:
        """Generate using LLM API."""
        import anthropic
        import os

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=self._get_model_id(self.model_tier),
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

    def _generate_with_template(self, context: dict) -> str:
        """Fallback template generation."""
        raise NotImplementedError("Subclass must implement")

    def _validate(self, result: str) -> bool:
        """Validate generated output."""
        raise NotImplementedError("Subclass must implement")
```

### Usage Example

```python
class TestGeneratorLLM(LLMWorkflowGenerator):
    """LLM-enhanced test generator."""

    def _generate_with_template(self, context: dict) -> str:
        # Existing template logic as fallback
        return create_template(context)

    def _validate(self, result: str) -> bool:
        # Validate generated test can be imported
        return validate_python_syntax(result)

# Usage
generator = TestGeneratorLLM(model_tier="capable")
test_code = generator.generate(
    context={"module": module_info},
    prompt=build_test_generation_prompt(module_info)
)
```

---

## Success Criteria

### Quality Metrics
- [ ] Generated outputs run without manual editing (>95%)
- [ ] LLM fallback rate <5%
- [ ] User satisfaction score >4.5/5
- [ ] Time saved vs template approach >80%

### Performance Metrics
- [ ] LLM generation time <30s per artifact
- [ ] Cache hit rate >60% for repeated operations
- [ ] API cost <$0.10 per generation (capable tier)

### Integration Metrics
- [ ] Dashboard visibility for all LLM workflows
- [ ] Quality feedback loop active
- [ ] A/B testing infrastructure ready

---

## Cost Analysis

### Per-Workflow Cost Estimates

| Workflow | Avg Tokens | Cost/Run (Capable) | Daily Volume | Daily Cost |
|----------|------------|-------------------|--------------|------------|
| Test Generation | 3000 | $0.045 | 100 | $4.50 |
| Documentation | 2500 | $0.038 | 50 | $1.90 |
| Code Review | 2000 | $0.030 | 200 | $6.00 |
| Refactoring | 3500 | $0.053 | 20 | $1.06 |
| Bug Prediction | 1500 | $0.023 | 150 | $3.45 |

**Total Estimated Daily Cost:** $16.91
**Monthly (30 days):** ~$507

### Cost Optimization Strategies
1. **Smart Caching**: Cache repeated operations (60%+ hit rate)
2. **Tiered Routing**: Use cheap tier for simple cases
3. **Batch Processing**: Group similar operations
4. **Fallback Templates**: Use when LLM not needed

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM API downtime | High | Low | Fallback to templates, cache previous results |
| Poor quality output | Medium | Medium | Validation layer, human review for critical paths |
| High API costs | Medium | Medium | Cost monitoring, usage limits, caching |
| Rate limiting | Medium | Low | Request queuing, exponential backoff |

### Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| User confusion | Low | Medium | Clear documentation, gradual rollout |
| Inconsistent results | Medium | Low | Prompt versioning, quality checks |
| Over-reliance on LLM | Medium | Medium | Keep template fallbacks, user education |

---

## Rollout Plan

### Week 1: Foundation
- [ ] Extract `LLMWorkflowGenerator` base class
- [ ] Add to `src/attune/workflows/llm_base.py`
- [ ] Implement caching layer
- [ ] Add quality validation framework
- [ ] Write comprehensive tests

### Week 2: High-Impact Workflows
- [ ] Enhance `test_gen_behavioral.py`
- [ ] Test with 50 modules
- [ ] Gather user feedback
- [ ] Enhance `documentation_orchestrator.py`
- [ ] Generate docs for 10 core modules

### Week 3: Code Quality Workflows
- [ ] Enhance `code_review.py`
- [ ] Run on recent PRs
- [ ] Compare with template-based reviews
- [ ] Enhance `refactor.py`
- [ ] Test with safe refactoring tasks

### Week 4: Analysis & Polish
- [ ] Enhance `bug_predict.py`
- [ ] Run full analysis on codebase
- [ ] Calculate false positive reduction
- [ ] Documentation and guides
- [ ] Performance optimization

### Week 5: Release
- [ ] Create release branch
- [ ] Full test suite
- [ ] Cost analysis
- [ ] User documentation
- [ ] Release v5.1.0 with LLM enhancements

---

## Monitoring & Observability

### Metrics to Track

```python
class LLMWorkflowMetrics:
    """Metrics for LLM-enhanced workflows."""

    llm_requests: int = 0
    llm_failures: int = 0
    template_fallbacks: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_generation_time_ms: float = 0.0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0

    # Quality metrics
    validation_failures: int = 0
    user_edits_required: int = 0
    user_satisfaction_score: float = 0.0
```

### Dashboard Integration
- Real-time LLM usage graphs
- Cost tracking per workflow
- Quality metrics over time
- Cache performance
- Failure rate alerts

---

## Next Steps

1. **Immediate** (Today):
   - Extract base `LLMWorkflowGenerator` class
   - Document API patterns
   - Create tracking issue

2. **Week 1**:
   - Implement foundation
   - Begin test generation enhancement
   - Set up monitoring

3. **Ongoing**:
   - Gather user feedback
   - Optimize prompts
   - Reduce costs
   - Improve quality

---

## Questions & Decisions

### Open Questions
1. Should we support local LLM models (ollama, etc.)?
2. What's the maximum acceptable cost per user per month?
3. Should LLM enhancement be opt-in or opt-out?
4. How do we handle sensitive code (no external API)?

### Decisions Needed
- [ ] Budget approval for API costs
- [ ] Model tier selection (default to capable?)
- [ ] Caching strategy (Redis vs in-memory)
- [ ] Rollout timeline (gradual vs big bang)

---

## References

- **Implementation Example**: `src/attune/workflows/autonomous_test_gen.py`
- **Base Pattern**: Lines 168-263 (`_generate_with_llm`)
- **Success Metrics**: Test generation achieving 90% coverage
- **Dashboard Integration**: `src/attune/telemetry/`

---

**Approved By:** [User]
**Implementation Start Date:** [TBD]
**Target Completion:** 4-5 weeks from start
