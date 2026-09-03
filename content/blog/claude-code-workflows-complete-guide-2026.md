---
title: "Claude Code Workflows: The Complete Guide (2026)"
date: "2026-03-07"
author: "Patrick Roebuck"
excerpt: "Master all 17 AI-powered workflows in Attune AI for Claude Code. From security audits to test generation, learn how each workflow saves time and reduces costs through intelligent multi-tier model routing."
tags: ["Claude Code", "AI workflows", "developer tools", "tutorial", "Attune AI"]
published: true
---

# Claude Code Workflows: The Complete Guide (2026)

*Updated 2026-08-09: savings figures revised for the premium tier's switch to Claude Fable 5 at 2× the former Opus pricing (Attune AI v10.5.0).*

Claude Code workflows represent a paradigm shift in how developers approach repetitive code tasks. Instead of manually reviewing, testing, and documenting code, teams can now invoke intelligent workflows that automatically escalate from cost-effective models to premium reasoning engines only when needed. This complete guide covers all 17 available Claude Code workflows in Attune AI, how they work, and how to master them for maximum productivity and cost savings.

## What Are Claude Code Workflows?

Claude Code workflows are multi-stage automation pipelines that combine natural language prompts with AI reasoning to solve common development challenges. Each workflow:

- Starts with **Haiku** (fast, cheap) for triage and analysis
- Escalates to **Sonnet** (capable) for implementation and complex reasoning
- Escalates to **Claude Fable 5.1** (premium, priced at 2× the former Opus rate) for architectural decisions and synthesis
- Delivers **up to 90% cost savings** compared to using premium models exclusively

This intelligent tier escalation is the core innovation of Attune AI. Instead of paying for Opus on every task, you pay for what you actually need.

## Getting Started with Claude Code Workflows

### Installation (2 minutes)

```bash
pip install attune-ai
```

The zero-config installation means Attune AI is ready to use immediately. It automatically detects your API keys and configures itself.

### First Workflow (5 minutes)

```bash
# Run your first workflow
attune workflow run code-review --input '{"files":["src/main.py"]}'
```

That's it. You've invoked a multi-stage code review workflow that:

1. Haiku scans for obvious issues (format, syntax)
2. Sonnet analyzes code quality and security
3. Opus synthesizes recommendations and reasoning

### Choose Your Path (3 minutes)

Determine how you'll use workflows:

- **Team leads**: Use for automated security and quality gates
- **Individual developers**: Use for on-demand code improvement
- **DevOps engineers**: Integrate into CI/CD pipelines
- **Technical reviewers**: Augment manual code review process

Each approach is supported with different CLI options and integration patterns.

## The 17 Essential Claude Code Workflows

### 1. Code Review (Analysis + Synthesis)

The foundation workflow. Provides comprehensive code analysis with multi-tier escalation.

**What it does:**
- Haiku: Identifies style issues and obvious bugs
- Sonnet: Analyzes architecture, security, performance
- Opus: Synthesizes recommendations with reasoning

**Use when:** You need thorough code review without waiting for humans.

```bash
attune workflow run code-review --input '{"files":["src/api.py","src/models.py"]}'
```

**Cost savings:** 75% vs manual review of same quality.

### 2. Security Audit (Detection + Remediation)

Identifies and explains security vulnerabilities across your codebase.

**What it does:**
- Haiku: Detects common vulnerabilities (injection, auth bypass)
- Sonnet: Analyzes threat vectors and impact
- Opus: Recommends comprehensive security fixes

**Use when:** You need to identify and fix security issues before production.

```bash
attune workflow run security-audit --input '{"path":"src/"}'
```

**Keywords:** CWE coverage, OWASP top 10, threat modeling.

### 3. Bug Prediction (Pattern Detection + Explanation)

Analyzes code patterns to predict likely bugs before they happen.

**What it does:**
- Haiku: Scans for risky patterns (eval, bare except, path traversal)
- Sonnet: Calculates bug probability and impact
- Opus: Explains why patterns are problematic

**Use when:** You want to shift left and catch bugs during development.

```bash
attune workflow run bug-predict --input '{"path":"src/"}'
```

**Coverage:** 200+ detectable patterns with false positive filtering.

### 4. Test Generation (From Code → Parametrized Tests)

Automatically generates comprehensive test suites from source code.

**What it does:**
- Haiku: Parses code and identifies test cases
- Sonnet: Generates parametrized test code
- Opus: Creates edge case tests and assertions

**Use when:** You need fast test coverage for legacy or new code.

```bash
attune workflow run test-gen --input '{"files":["src/utils.py"]}'
```

**Output:** Pytest-compatible test files with parametrization.

### 5. Parallel Test Generation (For Large Projects)

Distributed version of test generation for whole directories.

**What it does:**
- Haiku: Parallelizes across multiple files
- Sonnet: Generates tests in parallel
- Opus: Consolidates and deduplicates tests

**Use when:** You need to generate tests for 100+ files.

```bash
attune workflow run test-gen-parallel --input '{"directory":"tests/generation/"}'
```

**Performance:** 50-80% faster than sequential generation.

### 6. Refactor Planning (Analysis + Strategy)

Recommends refactoring strategies with implementation steps.

**What it does:**
- Haiku: Identifies refactoring opportunities
- Sonnet: Suggests specific refactoring approaches
- Opus: Creates detailed refactoring strategies

**Use when:** You need to improve code structure without breaking functionality.

```bash
attune workflow run refactor-plan --input '{"files":["src/legacy.py"]}'
```

**Output:** Step-by-step refactoring guide with before/after examples.

### 7. Code Simplification (Complexity → Clarity)

Reduces code complexity while preserving functionality.

**What it does:**
- Haiku: Measures complexity and flags complex sections
- Sonnet: Suggests simplifications
- Opus: Validates that simplifications preserve behavior

**Use when:** Code is too complex to maintain or understand.

```bash
attune workflow run simplify-code --input '{"files":["src/complex.py"]}'
```

**Metrics:** Tracks complexity reduction and test pass rate.

### 8. Performance Audit (Profiling + Optimization)

Identifies performance bottlenecks and suggests optimizations.

**What it does:**
- Haiku: Profiles code and flags slow operations
- Sonnet: Suggests optimizations with tradeoffs
- Opus: Recommends architectural changes

**Use when:** Application is slow and you need data-driven optimization.

```bash
attune workflow run perf-audit --input '{"files":["src/core.py"]}'
```

**Benchmarks:** Measures improvement potential before changes.

### 9. Dependency Check (Inventory + Risk Analysis)

Audits dependencies for security vulnerabilities and outdated versions.

**What it does:**
- Haiku: Scans pyproject.toml, requirements.txt, etc.
- Sonnet: Checks for known vulnerabilities
- Opus: Recommends upgrade path with risk assessment

**Use when:** You need to keep dependencies secure and current.

```bash
attune workflow run dependency-check --input '{"manifest":"pyproject.toml"}'
```

**Coverage:** All major package registries (PyPI, npm, cargo, Maven).

### 10. Documentation Audit (Quality + Compliance)

Evaluates and improves documentation quality.

**What it does:**
- Haiku: Scans for missing or outdated documentation
- Sonnet: Evaluates documentation quality
- Opus: Recommends comprehensive improvements

**Use when:** You need to ensure documentation stays current.

```bash
attune workflow run doc-audit --input '{"path":"docs/"}'
```

**Scoring:** Completeness, clarity, accuracy, and currency ratings.

### 11. Documentation Generation (Code → Guides)

Auto-generates documentation from code and docstrings.

**What it does:**
- Haiku: Extracts docstrings and comments
- Sonnet: Generates structured documentation
- Opus: Creates comprehensive guides and tutorials

**Use when:** You need documentation fast without manual writing.

```bash
attune workflow run doc-gen --input '{"path":"src/"}'
```

**Output:** Markdown files ready for publishing.

### 12. Documentation Orchestrator (Audit + Generation)

Coordinates doc-audit and doc-gen into end-to-end documentation
maintenance.

**What it does:**
- Haiku: Runs doc-audit to identify stale sections
- Sonnet: Regenerates stale sections with doc-gen
- Opus: Cross-links and validates the entire doc structure

**Use when:** You need to keep docs in sync with rapidly
changing codebases.

```bash
attune workflow run doc-orchestrator --input '{"path":"."}'
```

**Output:** Unified documentation update with cross-linked
references.

### 13. Release Preparation (Validation + Readiness)

Comprehensive pre-release checklist and validation.

**What it does:**
- Haiku: Checks version, changelog, tests
- Sonnet: Validates security and breaking changes
- Opus: Creates release notes and communication plan

**Use when:** You're preparing a release and want confidence.

```bash
attune workflow run release-prep --input '{"version":"1.2.0"}'
```

**Coverage:** Security, tests, documentation, breaking changes.

### 14. Secure Release Pipeline (End-to-End Release)

Complete release workflow with security gates.

**What it does:**
- Haiku: Runs pre-release checks
- Sonnet: Performs security scanning
- Opus: Creates release artifacts and publishes

**Use when:** You need automated, secure releases.

```bash
attune workflow run secure-release --input '{"publish":true}'
```

**Safety:** No security vulnerabilities pass through.

### 15. Research Synthesis (Multiple Sources → Insights)

Synthesizes research from multiple sources into coherent findings.

**What it does:**
- Haiku: Triage and summarize sources
- Sonnet: Extract key insights and patterns
- Opus: Synthesize comprehensive findings

**Use when:** You're researching a topic and need synthesis.

```bash
attune workflow run research-synthesis --input '{"query":"async patterns in Python"}'
```

**Output:** Structured findings with source citations.

### 16. Orchestrated Health Check (System Analysis)

Comprehensive health check across code, tests, and configuration.

**What it does:**
- Haiku: Runs basic checks (format, linting)
- Sonnet: Analyzes code quality and test coverage
- Opus: Synthesizes overall system health score

**Use when:** You want a holistic view of your project.

```bash
attune workflow run orchestrated-health-check --input '{"path":"."}'
```

**Output:** Health score with prioritized improvement areas.

### 17. Test Audit (Quality + Coverage Analysis)

Evaluates test suite quality and coverage.

**What it does:**
- Haiku: Scans test files and coverage reports
- Sonnet: Analyzes test quality and patterns
- Opus: Recommends test improvements

**Use when:** You need to improve test quality.

```bash
attune workflow run test-audit --input '{"path":"tests/"}'
```

**Metrics:** Coverage %, test isolation, parametrization.

## Progressive Tier Escalation: How It Works

The magic of Attune AI workflows is intelligent tier escalation. Here's how it works:

### Stage 1: Haiku (Cheap)
- Cost: $0.004 per call
- Best for: Triage, classification, straightforward analysis
- Example: "Does this code have obvious bugs?"
- Runtime: 200-500ms

### Stage 2: Sonnet (Capable)
- Cost: $0.03 per call
- Best for: Implementation, complex analysis, synthesis
- Example: "What's the best way to optimize this function?"
- Runtime: 1-3 seconds
- Triggered when: Haiku identifies complex issues

### Stage 3: Opus (Premium)
- Cost: $0.15 per call
- Best for: Architectural decisions, novel problems, synthesis
- Example: "How should we restructure this module?"
- Runtime: 3-10 seconds
- Triggered when: Sonnet encounters novel or architectural issues

### Cost Savings Example

**Code Review of 1000-line application:**

- **Haiku only:** $0.04 (basic style checks)
- **Haiku + Sonnet:** $0.34 (typical case, ~90% cost savings vs premium)
- **Full escalation:** $0.38 (complex application, ~70% cost savings vs premium)
- **Opus only:** $2.40 (16x more expensive than intelligent routing)

## The 5 Interactive Wizards

Workflows are powerful, but wizards provide guided experiences for complex tasks.

### 1. Debug Wizard
Interactive debugging experience with multi-step guidance.

```bash
attune wizard run debug
```

Guides you through: reproduce → isolate → fix → test → verify.

### 2. Refactor Wizard
Step-by-step guidance through complex refactoring.

```bash
attune wizard run refactor
```

Validates each step to prevent regressions.

### 3. Release Prep Wizard
Interactive release preparation with checkpoints.

```bash
attune wizard run release-prep
```

Ensures nothing is missed before production.

### 4. Security Wizard
Guided security vulnerability remediation.

```bash
attune wizard run security
```

Explains each vulnerability and walks through fixes.

### 5. Test Gen Wizard
Interactive test generation with preview and approval.

```bash
attune wizard run test-gen
```

Shows generated tests before adding to project.

## 14 Agent Templates for Team Automation

Beyond individual workflows, Attune AI provides agent templates for team automation:

### Agent Categories

**Code Review Agents:**
- Security-focused reviewer
- Performance-focused reviewer
- Architecture reviewer
- Style/convention enforcer

**Test Agents:**
- Test generation specialist
- Flaky test debugger
- Coverage analyzer
- Test maintenance bot

**Documentation Agents:**
- API documentation specialist
- User guide writer
- Changelog generator
- Deprecation communicator

**DevOps Agents:**
- Security scanner
- Performance monitor
- Dependency updater
- Release coordinator

Each can be customized and deployed as part of your CI/CD pipeline.

## 6 Composition Patterns for Multi-Agent Systems

Workflows can be composed using proven patterns:

### 1. Sequential Pattern
Agents run one after another, each processing output from the previous.

```
Security Scan → Code Review → Test Generation → Documentation
```

### 2. Parallel Pattern
Multiple agents analyze simultaneously and results are merged.

```
    ├─ Security Scan
Code ┤─ Performance Audit
    └─ Test Generation
        ↓
    Merged Findings
```

### 3. Debate Pattern
Multiple agents propose different solutions and reach consensus.

```
Solution A (Agent 1) ──┐
                      ├─ Debate ─→ Consensus ─→ Final Recommendation
Solution B (Agent 2) ──┘
```

### 4. Teaching Pattern
Experienced agent guides junior agent through problem solving.

```
Expert ──→ Guides ──→ Junior ──→ Validates ──→ Result
```

### 5. Refinement Pattern
First agent proposes, subsequent agents refine iteratively.

```
Generate ─→ Review ─→ Refine ─→ Validate ─→ Finalize
```

### 6. Adaptive Pattern
Agent selection and routing changes based on problem type.

```
Problem Type ──→ Router ──→ Specialized Agent ──→ Solution
```

## Integration with CI/CD Pipelines

Workflows integrate seamlessly into CI/CD:

### GitHub Actions Integration

```yaml
- name: Run Security Audit
  run: |
    pip install attune-ai
    attune workflow run security-audit --json > report.json

- name: Parse Results
  run: |
    python scripts/parse_attune_report.py report.json
    exit $(cat exit_code.txt)
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: attune-security-check
      name: Attune Security Check
      entry: attune workflow run security-audit
      language: system
      stages: [commit]
```

### Manual Invocation

```bash
# Interactive CLI
attune workflow run code-review

# JSON output for parsing
attune workflow run bug-predict --json

# Specific files
attune workflow run test-gen --input '{"files":["src/api.py"]}'
```

## Best Practices for Workflow Success

### 1. Match Tool to Task

- **Code Review** → Comprehensive quality assurance
- **Bug Predict** → Shift-left quality
- **Security Audit** → Compliance and risk management
- **Test Gen** → Coverage on legacy code
- **Perf Audit** → Optimization efforts

### 2. Use Escalation Strategically

- Start with Haiku for routine checks
- Escalate to Sonnet for complex issues
- Reserve Opus for architectural decisions
- Monitor your escalation patterns

### 3. Integrate Into Workflows

- **Pre-commit:** Bug prediction
- **PR:** Code review and security
- **Release:** Health check and release prep
- **Incident:** Root cause analysis

### 4. Customize for Your Codebase

```bash
# Exclude certain paths
attune workflow run code-review --input '{
  "files": ["src/"],
  "exclude": ["**/*_pb2.py", "**/migrations/**"]
}'

# Set severity thresholds
attune workflow run security-audit --input '{
  "min_severity": "medium"
}'
```

### 5. Monitor Costs and Patterns

```bash
# View cost report
attune workflow run code-review --cost-report

# See tier escalation stats
attune stats show escalation
```

## Advanced: Custom Workflows

While the 17 built-in workflows cover 90% of use cases, you can create custom workflows:

```python
from attune.workflows import WorkflowBuilder, ModelTier

# Build custom workflow
workflow = (
    WorkflowBuilder("my-custom-analysis")
    .add_stage("scan", ModelTier.CHEAP)
    .add_stage("analyze", ModelTier.CAPABLE)
    .add_stage("recommend", ModelTier.PREMIUM)
    .build()
)

# Run it
result = workflow.execute(input_data)
print(f"Result: {result.output}")
print(f"Cost: ${result.cost_report.total_cost:.4f}")
```

## Comparing to Alternatives

How do Attune AI workflows compare to other approaches?

| Aspect | Manual Review | Static Tools | Attune AI | Premium LLM Only |
|--------|---------------|--------------|-----------|-----------------|
| **Accuracy** | High | Low-Medium | High | Very High |
| **Cost** | High | Low | Low | High |
| **Speed** | Slow | Fast | Medium | Medium |
| **Customization** | Very High | Medium | High | Low |
| **Insight Quality** | Excellent | Basic | Excellent | Excellent |
| **Explanation** | Yes | Limited | Yes | Yes |

Attune AI combines the best of all: accuracy of manual review, speed of automation, cost efficiency of smart routing.

## Common Questions

### Q: How much can I save?

**A:** Savings of up to 90% compared to using premium models for everything, depending on how much of your workload stays on the cheap tier. On an enterprise project running 100 code reviews/week, that can be $1,000/week in savings.

### Q: Will workflows replace code reviewers?

**A:** No. Workflows augment human reviewers. They handle routine checks, freeing reviewers for complex architectural decisions.

### Q: Can I use workflows offline?

**A:** Workflows require API calls to Anthropic's models. You'll need API keys and internet connectivity.

### Q: How do I handle false positives?

**A:** Each workflow has configurable strictness levels and exclusion patterns. Tuple security patterns are automatically filtered.

### Q: Can workflows integrate with my tools?

**A:** Yes. JSON output can be parsed by any tool. See documentation for Slack, GitHub, Jira, and other integrations.

## Moving Forward

Workflows represent the future of developer tools: intelligent automation that understands context, provides explanation, and costs less than manual approaches.

### Start Here

1. Install: `pip install attune-ai`
2. Run first workflow: `attune workflow run code-review --help`
3. Integrate into your CI/CD
4. Explore the 17 workflows systematically
5. Create team automation with agents

### Learn More

- **Getting Started:** [/framework-docs/getting-started/](/framework-docs/getting-started/)
- **Workflow Reference:** [/workflows/](/workflows/)
- **Wizard Guide:** [/wizards/](/wizards/)
- **Compare with CrewAI:** [/compare/crewai-vs-attune](/compare/crewai-vs-attune)
- **GitHub Repository:** [github.com/Smart-AI-Memory/attune-ai](https://github.com/Smart-AI-Memory/attune-ai)

### Get Involved

Questions or feedback on workflows? Open an issue on GitHub or start a discussion. The Attune AI community is active and responsive to feature requests.

---

**Ready to master Claude Code workflows?** Start with the [Getting Started Guide](/framework-docs/getting-started/) and run your first workflow in under 5 minutes. You'll wonder how you ever developed without intelligent automation.
