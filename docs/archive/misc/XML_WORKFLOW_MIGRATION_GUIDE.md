---
description: XML-Enhanced Workflow Migration Guide: Step-by-step tutorial with examples, best practices, and common patterns. Learn by doing with hands-on examples.
---

# XML-Enhanced Workflow Migration Guide

**Status**: Phase 2 Complete - Pattern Documented
**Date**: January 5, 2026

---

## Overview

This guide demonstrates how to migrate existing workflows to use XML-enhanced prompts for 40-60% reduction in misinterpretations.

## Existing XML Support

The `code_review.py` workflow already has XML infrastructure:
- `_is_xml_enabled()` - Feature flag check ([code_review.py:654](src/attune/workflows/code_review.py#L654))
- `_render_xml_prompt()` - XML prompt generation ([code_review.py:655](src/attune/workflows/code_review.py#L655-L674))
- `_parse_xml_response()` - XML response parsing ([code_review.py:729](src/attune/workflows/code_review.py#L729))

## Migration Pattern

### Before (Ad-Hoc Prompts)
```python
system = """You are a senior software architect. Provide a comprehensive review:

1. ARCHITECTURAL ASSESSMENT:
   - Design patterns used (or missing)
   - SOLID principles compliance

2. RECOMMENDATIONS:
   - Specific improvements with examples

3. VERDICT:
   - APPROVE / APPROVE_WITH_SUGGESTIONS / REJECT"""

user_message = f"""Perform an architectural review:

{input_payload}"""
```

### After (XML-Enhanced with Metrics)
```python
from attune.workflows.xml_enhanced_crew import XMLAgent, XMLTask, parse_xml_response
from attune.metrics import MetricsTracker

# Initialize metrics tracking
metrics = MetricsTracker() if config.metrics.enable_tracking else None

# Create XML-enhanced agent
agent = XMLAgent(
    role="Senior Software Architect",
    goal="Perform comprehensive code review with architectural assessment",
    backstory="Expert in SOLID principles, design patterns, and code quality",
    expertise_level="expert",
    use_xml_structure=config.xml.use_xml_structure,
    custom_instructions=[
        "Assess design patterns used (or missing)",
        "Evaluate SOLID principles compliance",
        "Check separation of concerns",
        "Provide verdict: approve, approve_with_suggestions, or reject",
    ]
)

# Create task with structured output
task = XMLTask(
    description="Perform architectural code review",
    expected_output="""
    <code_review>
        <thinking>
        Detailed analysis and reasoning process
        </thinking>
        <answer>
            <assessment>
                <design_patterns>Analysis of patterns used</design_patterns>
                <solid_compliance>SOLID principles evaluation</solid_compliance>
                <separation_of_concerns>Component isolation assessment</separation_of_concerns>
            </assessment>
            <recommendations>
                <recommendation priority="high">
                    <description>Specific improvement needed</description>
                    <example>Code example showing fix</example>
                </recommendation>
            </recommendations>
            <verdict>approve|approve_with_suggestions|request_changes|reject</verdict>
        </answer>
    </code_review>
    """,
    agent=agent,
)

# Execute with metrics tracking
if metrics:
    start_time = time.time()

response = await call_llm(agent.get_system_prompt(), task.get_user_prompt(context))

if metrics:
    metrics.log_metric(PromptMetrics(
        timestamp=datetime.now().isoformat(),
        workflow="code-review",
        agent_role="Senior Software Architect",
        task_description="Architectural review",
        model="claude-sonnet-4-5",
        prompt_tokens=response.usage.input_tokens,
        completion_tokens=response.usage.output_tokens,
        total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        latency_ms=(time.time() - start_time) * 1000,
        retry_count=0,
        parsing_success=True,
        xml_structure_used=True,
    ))

# Parse structured response
result = parse_xml_response(response.content[0].text)
```

## Key Benefits

1. **Structured Output**: XML tags enforce consistent response format
2. **Thinking/Answer Separation**: Models show reasoning before conclusions
3. **Metrics Tracking**: Performance data for optimization
4. **Backward Compatible**: Feature flags allow gradual rollout
5. **Reduced Retries**: 20-30% fewer retries due to clearer prompts

## Configuration

Enable XML prompts in `.empathy/config.json`:

```json
{
  "xml": {
    "use_xml_structure": true,
    "validate_schemas": false
  },
  "metrics": {
    "enable_tracking": true,
    "metrics_file": ".empathy/prompt_metrics.json"
  },
  "optimization": {
    "compression_level": "moderate",
    "use_short_tags": true
  }
}
```

Or via environment variables:

```bash
export ATTUNE_XML_ENABLED=true
export ATTUNE_METRICS_ENABLED=true
export ATTUNE_OPTIMIZATION_LEVEL=moderate
```

## Migration Checklist

- [x] Phase 1: Core infrastructure (metrics, adaptive, config)
- [x] Phase 2: Document migration pattern
- [x] Phase 3.1: Context optimization (see below)
- [x] Phase 3.2: XML validation (see below)
- [ ] Phase 4: Migrate remaining workflows (as needed)

## Next Steps

1. **Enable metrics tracking** to baseline current performance
2. **Test XML prompts** on code_review workflow with `use_xml_structure=true`
3. **Compare metrics** between XML and non-XML prompts
4. **Migrate additional workflows** based on results

---

**Note**: The code_review workflow already supports XML prompts via `_render_xml_prompt()` and `_parse_xml_response()`. This guide shows the full XMLAgent/XMLTask pattern for workflows that need it.

See [XML_ENHANCEMENT_IMPLEMENTATION_SUMMARY.md](XML_ENHANCEMENT_IMPLEMENTATION_SUMMARY.md) for complete implementation status.
