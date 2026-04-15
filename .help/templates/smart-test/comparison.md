---
type: comparison
feature: smart-test
depth: comparison
generated_at: 2026-04-14T14:44:59.646421+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Smart Test vs alternatives

## Context

Generate comprehensive pytest tests for untested code using AST analysis and AI-powered test synthesis. The smart-test feature offers three distinct workflows for different testing scenarios.

## Feature comparison

| Capability | TestGenerationWorkflow | TestAuditWorkflow | ParallelTestGenerationWorkflow |
|------------|----------------------|-------------------|-------------------------------|
| **Target use case** | Single-module test creation | Coverage gap analysis | Bulk test generation |
| **Analysis method** | AST-based function/class parsing | Multi-agent coverage audit | Combined AST + AI synthesis |
| **Parallelization** | No | No | Yes (batch processing) |
| **AI integration** | Limited | 3 specialized subagents | 2-tier LLM approach |
| **Coverage integration** | Manual | Built-in pytest-cov parsing | Automatic low-coverage discovery |
| **Output format** | Individual test files | Structured audit report | Batch test generation |
| **Best for projects** | < 50 modules | Any size | > 100 modules |

## Performance characteristics

- **TestGenerationWorkflow**: Generates ~10-15 test methods per function with comprehensive parameter testing
- **TestAuditWorkflow**: Processes coverage.json files with 200+ modules in < 30 seconds
- **ParallelTestGenerationWorkflow**: Handles 200 modules in configurable batches (default: 10 modules/batch)

## Use TestGenerationWorkflow when...

- You need detailed, AST-accurate tests for specific functions or classes
- Your codebase has complex type hints that require precise parameter testing
- You want maximum control over test generation logic
- You're working with < 20 modules at a time

## Use TestAuditWorkflow when...

- You need to understand where your test gaps are before writing tests
- You have existing pytest-cov output to analyze
- You want prioritized recommendations for which modules to test first
- You need executive-level test health reporting

## Use ParallelTestGenerationWorkflow when...

- You're starting with low overall coverage (< 50%) across many modules
- You need to generate tests for 50+ modules efficiently
- You want AI-powered test completion that goes beyond basic parameter testing
- You can trade some precision for speed and scale

## Key tradeoffs

**Accuracy vs Speed**: TestGenerationWorkflow provides the most accurate AST analysis but processes one module at a time. ParallelTestGenerationWorkflow is ~10x faster but may miss edge cases in complex codebases.

**Coverage Integration**: Only TestAuditWorkflow and ParallelTestGenerationWorkflow automatically discover low-coverage modules. TestGenerationWorkflow requires manual module specification.

**AI Sophistication**: TestAuditWorkflow uses 3 specialized subagents for nuanced analysis. ParallelTestGenerationWorkflow uses a simpler 2-tier approach optimized for bulk generation.

## Recommended approach

For most projects, start with **TestAuditWorkflow** to identify your biggest test gaps, then use **ParallelTestGenerationWorkflow** to generate tests for the top 20-50 priority modules, and finally use **TestGenerationWorkflow** for any critical modules that need hand-tuned test precision.
