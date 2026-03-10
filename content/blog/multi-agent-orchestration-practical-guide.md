---
title: "Multi-Agent Orchestration: A Practical Guide with Python Examples"
date: "2026-03-07"
author: "Patrick Roebuck"
excerpt: "Learn how to compose AI agents using Sequential, Parallel, Debate, Teaching, Refinement, and Adaptive patterns. Practical Python examples with Attune AI's orchestration framework."
tags: ["multi-agent", "orchestration", "Python", "AI architecture", "tutorial", "Attune AI"]
published: true
---

# Multi-Agent Orchestration: A Practical Guide with Python Examples

Building sophisticated AI systems often requires more than a single agent. When you need to perform complex analysis, solve multi-faceted problems, or synthesize expertise across domains, multi-agent orchestration becomes essential. Attune AI's orchestration framework provides six composition patterns that enable you to build coordinated teams of AI agents, each specialized for specific tasks.

This guide walks you through each pattern with practical Python examples, real-world use cases, and strategies for building production-grade multi-agent systems.

## Understanding Multi-Agent Orchestration

Multi-agent orchestration is the art of composing multiple AI agents into a coordinated system where:

- Each agent has specialized knowledge or capabilities
- Agents collaborate toward a shared goal
- The orchestration pattern determines how agents interact and influence each other
- Results are synthesized into actionable insights

The key difference from single-agent workflows is **composition complexity**. Instead of one agent handling everything, you distribute tasks across specialized agents and define explicit communication patterns.

Attune AI provides six proven patterns for orchestration:

1. **Sequential** — Linear task pipeline
2. **Parallel** — Concurrent execution with aggregation
3. **Debate** — Multi-perspective synthesis
4. **Teaching** — Expert-guided learning
5. **Refinement** — Iterative improvement loops
6. **Adaptive** — Pattern selection by MetaOrchestrator

## Pattern 1: Sequential Orchestration

Sequential orchestration executes agents one after another, with each agent's output feeding into the next agent's input. This pattern works well when tasks have clear dependencies.

### When to Use Sequential

- Code review pipeline: syntax check → code analysis → security review → documentation check
- Document generation: outline → draft → review → publish
- Debugging workflow: error identification → root cause analysis → solution proposal → validation

### Python Example

```python
from attune.orchestration import SequentialTeam
from attune.agents import CodeQualityReviewer, SecurityAuditor, DocumentationWriter

# Define the sequential pipeline
team = SequentialTeam(
    agents=[
        CodeQualityReviewer(name="quality_agent"),
        SecurityAuditor(name="security_agent"),
        DocumentationWriter(name="docs_agent"),
    ],
    name="code_review_pipeline"
)

# Execute the pipeline
result = team.execute(
    input_data={
        "source_code": source_code,
        "target_audience": "internal_developers"
    }
)

# Each agent processes the previous agent's output
print(f"Quality Issues: {result.stages['quality_agent'].issues}")
print(f"Security Findings: {result.stages['security_agent'].vulnerabilities}")
print(f"Documentation Generated: {result.stages['docs_agent'].content}")
```

### How It Works

1. **Code Quality Reviewer** analyzes the source code and produces a quality report
2. **Security Auditor** receives the quality report and source code, performs security analysis
3. **Documentation Writer** receives both previous outputs and generates API documentation

Each stage receives the full context from previous stages, enabling incremental refinement.

## Pattern 2: Parallel Orchestration

Parallel orchestration runs multiple agents simultaneously on the same input, then aggregates their results. Use this pattern when you need independent analysis from multiple specialists.

### When to Use Parallel

- Multi-perspective code analysis (quality, security, performance all at once)
- Report generation from diverse data sources
- Comprehensive audits (security, compliance, accessibility)

### Python Example

```python
from attune.orchestration import ParallelTeam
from attune.agents import (
    CodeQualityReviewer,
    SecurityAuditor,
    PerformanceOptimizer,
    ArchitectureAnalyst
)

# Define the parallel team
team = ParallelTeam(
    agents=[
        CodeQualityReviewer(name="quality"),
        SecurityAuditor(name="security"),
        PerformanceOptimizer(name="perf"),
        ArchitectureAnalyst(name="architecture"),
    ],
    name="comprehensive_review",
    aggregation_strategy="weighted_summary"  # or "merge", "consensus"
)

# Execute all agents on the same input
result = team.execute(
    input_data={"codebase": codebase, "metrics": metrics},
    max_parallel_workers=4
)

# Aggregate results from all agents
summary = result.aggregated_summary
print(f"Overall Health Score: {summary.health_score}")
print(f"Top Issues by Category:")
for category, issues in summary.issues_by_category.items():
    print(f"  {category}: {len(issues)} issues")
```

### Aggregation Strategies

**Weighted Summary** (default): Each agent's findings weighted by confidence score
```python
aggregation_strategy="weighted_summary",
agent_weights={
    "quality": 0.3,
    "security": 0.4,
    "perf": 0.2,
    "architecture": 0.1
}
```

**Merge**: Combine all findings into a flat list
```python
aggregation_strategy="merge"
```

**Consensus**: Only include findings mentioned by multiple agents
```python
aggregation_strategy="consensus",
min_agreement_threshold=2  # At least 2 agents must agree
```

## Pattern 3: Debate Orchestration

Debate orchestration structures agents to argue different perspectives, then synthesizes their positions into consensus. This pattern is powerful for exploring design tradeoffs and making architectural decisions.

### When to Use Debate

- Architecture decision records (monolith vs microservices)
- Framework selection (React vs Vue)
- API design decisions (REST vs GraphQL)
- Refactoring approach selection

### Python Example

```python
from attune.orchestration import DebateTeam
from attune.agents import ArchitectureAnalyst, RefactoringSpecialist

# Define positions
team = DebateTeam(
    proposer=ArchitectureAnalyst(
        name="proposer",
        position="microservices_architecture"
    ),
    challenger=ArchitectureAnalyst(
        name="challenger",
        position="monolith_architecture"
    ),
    synthesizer=RefactoringSpecialist(
        name="synthesizer"
    ),
    name="architecture_debate",
    rounds=3  # Number of debate rounds
)

# Execute debate
result = team.execute(
    input_data={
        "current_architecture": arch,
        "scaling_requirements": scaling_req,
        "team_size": team_size,
        "timeline": timeline,
    }
)

# Extract synthesis
print("Debate Round Summaries:")
for round_num, round_result in enumerate(result.debate_rounds, 1):
    print(f"\nRound {round_num}:")
    print(f"  Proposer: {round_result.proposer_argument}")
    print(f"  Challenger: {round_result.challenger_argument}")

print(f"\nFinal Synthesis:")
print(f"  Recommendation: {result.synthesis.recommendation}")
print(f"  Trade-offs: {result.synthesis.tradeoffs}")
print(f"  Implementation Plan: {result.synthesis.implementation_steps}")
```

### How Debate Works

1. **Proposer** argues in favor of position A with evidence
2. **Challenger** argues against position A with counterarguments
3. **Synthesizer** analyzes both arguments and identifies valid points from each side
4. **Next Round**: Both agents respond to the synthesizer's observations
5. **Final Synthesis**: Synthesizer produces a nuanced recommendation that acknowledges both perspectives

This pattern is particularly valuable for avoiding "single perspective" decisions and building team buy-in.

## Pattern 4: Teaching Orchestration

Teaching orchestration pairs an expert agent with one or more novice agents. The expert guides the novices through problem-solving, accelerating their learning and improving solution quality.

### When to Use Teaching

- Training junior developers on codebase best practices
- Security education while performing code review
- Architecture guidance for architectural decisions
- Onboarding new team members into specialized domains

### Python Example

```python
from attune.orchestration import TeachingTeam
from attune.agents import (
    SecurityAuditor,
    CodeQualityReviewer,
    TestGenerator
)

# Expert guides novices
team = TeachingTeam(
    expert=SecurityAuditor(
        name="expert_security",
        experience_level="senior"
    ),
    novices=[
        CodeQualityReviewer(name="novice_quality"),
        TestGenerator(name="novice_tests"),
    ],
    name="security_training",
    learning_depth="intermediate"  # light, intermediate, deep
)

# Execute with teaching
result = team.execute(
    input_data={"codebase": codebase},
    teaching_context={
        "focus_areas": ["input_validation", "authentication"],
        "difficulty_level": "intermediate"
    }
)

# Extract learning outcomes
for novice_name, novice_result in result.novice_results.items():
    print(f"\n{novice_name}:")
    print(f"  Findings: {len(novice_result.findings)}")
    print(f"  Expert Guidance:")
    for guidance in novice_result.expert_guidance:
        print(f"    - {guidance.explanation}")
        print(f"      Why: {guidance.reasoning}")

print(f"\nExpert Summary:")
print(f"  Key Lessons: {result.expert_summary.key_lessons}")
print(f"  Novice Readiness: {result.expert_summary.readiness_level}")
```

### Teaching Dynamics

The expert agent:
- Observes novice findings
- Identifies gaps and misunderstandings
- Provides targeted guidance with explanations
- Iteratively coaches novices to higher competency

The novices:
- Develop deeper understanding through guided practice
- Build domain knowledge for future autonomous work
- Improve solution quality through expert feedback

## Pattern 5: Refinement Orchestration

Refinement orchestration runs iterative improvement passes where each agent refines the work of previous agents. This pattern is ideal for tasks requiring incremental quality improvement.

### When to Use Refinement

- Writing and editing (draft → review → polish)
- Test case generation (basic tests → edge cases → performance tests)
- Documentation (first draft → clarity improvements → examples)
- Code generation (initial implementation → optimization → refactoring)

### Python Example

```python
from attune.orchestration import RefinementTeam
from attune.agents import (
    TestGenerator,
    TestValidator,
    CodeSimplifier
)

# Define refinement stages
team = RefinementTeam(
    stages=[
        TestGenerator(name="generator", role="generate_initial_tests"),
        TestValidator(name="validator", role="validate_and_expand"),
        CodeSimplifier(name="simplifier", role="optimize_and_refine"),
    ],
    name="test_refinement",
    max_iterations=3,
    convergence_threshold=0.95  # Stop when quality stabilizes
)

# Execute refinement loop
result = team.execute(
    input_data={"function": target_function, "edge_cases": edge_cases},
    refinement_config={
        "focus_metrics": ["coverage", "clarity", "performance"],
        "quality_threshold": 0.90
    }
)

# Track refinement progress
print("Refinement Progress:")
for iteration, iteration_result in enumerate(result.iterations, 1):
    print(f"\nIteration {iteration}:")
    print(f"  Quality Score: {iteration_result.quality_score:.2f}")
    print(f"  Test Count: {iteration_result.test_count}")
    print(f"  Coverage: {iteration_result.coverage:.1%}")
    print(f"  Changes Made:")
    for change in iteration_result.changes:
        print(f"    - {change}")

print(f"\nFinal Quality: {result.final_quality_score:.2f}")
print(f"Total Iterations: {len(result.iterations)}")
```

### Refinement Loop Mechanics

1. **Generator** produces initial output (tests, documentation, code)
2. **Validator** reviews output, identifies gaps and improvements
3. **Simplifier** optimizes for clarity and efficiency
4. **Quality Check**: Compare current quality to previous iteration
5. **Loop or Exit**: If quality improves and threshold not met, repeat; otherwise, finalize

## Pattern 6: Adaptive Orchestration

Adaptive orchestration uses the MetaOrchestrator to analyze your task and automatically select the optimal composition pattern. This is the most intelligent pattern—describe your goal, and Attune AI builds the right team.

### When to Use Adaptive

- Dynamic task types (mix of analysis, writing, decision-making)
- Unknown optimal strategy (let the framework decide)
- Complex workflows with multiple sub-goals
- Production systems needing self-optimizing orchestration

### Python Example

```python
from attune.orchestration import MetaOrchestrator
from attune.agents import (
    CodeQualityReviewer,
    SecurityAuditor,
    TestGenerator,
    ArchitectureAnalyst,
    RefactoringSpecialist,
    DocumentationWriter
)

# Create MetaOrchestrator with available agents
orchestrator = MetaOrchestrator(
    available_agents=[
        CodeQualityReviewer(),
        SecurityAuditor(),
        TestGenerator(),
        ArchitectureAnalyst(),
        RefactoringSpecialist(),
        DocumentationWriter(),
    ],
    name="intelligent_team_builder"
)

# Describe your goal, get an optimized team
result = orchestrator.optimize(
    goal="Prepare a legacy codebase for public open-source release",
    context={
        "codebase_size": "50k lines",
        "current_quality": "medium",
        "priority": ["security", "documentation", "test coverage"],
        "constraints": {
            "timeline_days": 14,
            "budget_tokens": 1_000_000,
        }
    }
)

# The orchestrator has automatically selected agents and pattern
print(f"Recommended Pattern: {result.pattern}")  # e.g., "Sequential"
print(f"Selected Agents: {[a.name for a in result.agents]}")
print(f"Estimated Cost: {result.estimated_cost} tokens")
print(f"Estimated Time: {result.estimated_duration_hours} hours")

# Execute the automatically-built team
execution_result = result.team.execute(
    input_data={"codebase": codebase, "target_audience": "public"}
)

# Results follow the selected pattern's structure
print(f"\nExecution Complete:")
print(f"  Pattern Used: {execution_result.pattern}")
print(f"  Agents Run: {list(execution_result.stages.keys())}")
print(f"  Total Cost: {execution_result.cost_report.total_cost}")
```

### How MetaOrchestrator Works

1. **Analysis Phase**: Analyzes goal, constraints, and context
2. **Agent Selection**: Selects specialized agents from available pool
3. **Pattern Matching**: Determines optimal composition pattern based on goal
4. **Team Configuration**: Configures selected agents with appropriate tiers (CHEAP, CAPABLE, PREMIUM)
5. **Execution Planning**: Estimates cost, duration, and success probability
6. **Adaptive Execution**: Runs the team, monitoring quality and adjusting if needed

The MetaOrchestrator is particularly powerful because it:
- Selects agents based on task requirements
- Chooses tier levels (cost vs capability tradeoff)
- Picks optimal composition pattern automatically
- Estimates costs before execution
- Can explain its recommendations

## The 14 Agent Templates

Attune AI provides 14 specialized agent templates, each optimized for specific tasks:

| Agent | Specialization | Best For |
|-------|---|---|
| Test Coverage Analyzer | Test analysis | Measuring test completeness |
| Security Auditor | Security analysis | Finding vulnerabilities |
| Code Quality Reviewer | Code standards | Enforcing best practices |
| Documentation Writer | Documentation | Generating docs, guides |
| Performance Optimizer | Performance | Reducing latency, memory |
| Architecture Analyst | System design | Design decisions, migrations |
| Refactoring Specialist | Code improvement | Simplification, cleanup |
| Test Generator | Test creation | Generating test cases |
| Test Validator | Test quality | Validating test effectiveness |
| Report Generator | Report creation | Structured reporting |
| Documentation Analyst | Documentation review | Content evaluation |
| Information Synthesizer | Data synthesis | Combining multiple sources |
| Code Simplifier | Code clarity | Reducing complexity |
| General Purpose | Multi-purpose | Flexible custom tasks |

## Coordinating Multiple Claude Code Instances with Redis

When running multi-agent orchestration across multiple Claude Code sessions or instances, use the Redis plugin to share agent state:

```python
from attune.plugins import AttuneRedis
from attune.orchestration import ParallelTeam

# Configure Redis backend for shared state
redis_plugin = AttuneRedis(
    url="redis://localhost:6379",
    key_prefix="attune:team-run-001"
)

# Build team with shared state
team = ParallelTeam(
    agents=[...],
    state_backend=redis_plugin,
    name="distributed_review"
)

# Any Claude Code instance can access the same team state
result = team.execute(input_data=data)

# Results are synchronized across instances
agents_status = redis_plugin.get_agents_status()
print(f"Running agents: {agents_status}")
```

This enables:
- Running agents on multiple machines
- Coordinating between different Claude Code sessions
- Persisting team state across sessions
- Enabling human-in-the-loop approval steps

## Real-World Use Cases

### Use Case 1: Code Review Team

Prepare code for production with comprehensive review:

```
Sequential Team:
  1. Code Quality Reviewer → finds style, complexity issues
  2. Security Auditor → finds vulnerabilities, compliance gaps
  3. Test Generator → generates missing test cases
  4. Documentation Writer → creates inline documentation
  5. RefactoringSpecialist → proposes improvements
```

Cost: ~30,000 tokens per review
Time: ~2 minutes
Output: Fully reviewed, tested, documented code ready for merge

### Use Case 2: Security Audit Team

Comprehensive security assessment with depth and breadth:

```
Debate Team:
  Proposer: "Current architecture is secure"
    - HTTPS, input validation, rate limiting present
    - Security headers configured

  Challenger: "Attack surface analysis"
    - Third-party dependency risks
    - Secrets management gaps
    - Database access controls

  Synthesizer: Produces prioritized security roadmap
    - Critical fixes (immediate)
    - High priority (sprint)
    - Technical debt (backlog)
```

Cost: ~50,000 tokens
Time: ~3 minutes
Output: Security findings with severity, impact, and remediation steps

### Use Case 3: Release Preparation Team

Adaptive team automatically selects optimal pattern for pre-release validation:

```
MetaOrchestrator analyzes goal: "Prepare v3.0.0 for public release"

Recommended Pattern: Sequential
  1. Test Coverage Analyzer → verify test coverage >90%
  2. Security Auditor → final security sweep
  3. Documentation Analyst → review all documentation
  4. Report Generator → create release notes
  5. Test Validator → validate all test suites pass
```

Cost: Variable (MetaOrchestrator estimates)
Time: Variable (MetaOrchestrator estimates)
Output: Release-ready code with comprehensive validation

## Choosing the Right Pattern

**Sequential** when:
- Tasks have clear dependencies
- Each step builds on previous results
- Order matters

**Parallel** when:
- Tasks are independent
- Need multiple perspectives
- Want comprehensive coverage

**Debate** when:
- Exploring trade-offs
- Need balanced perspective
- Making architectural decisions

**Teaching** when:
- Improving future autonomy
- Building team knowledge
- Training is secondary goal

**Refinement** when:
- Iterative quality improvement
- Need polish and optimization
- Multiple passes add value

**Adaptive** when:
- Task complexity is unknown
- Need intelligent pattern selection
- Want automatic cost estimation

## Getting Started

To start using multi-agent orchestration with Attune AI:

1. **Explore the workflows**: Visit [/workflows/](/workflows/) to see orchestration in action
2. **Try the wizards**: Use [/wizards/](/wizards/) for guided multi-agent setup
3. **Read the framework docs**: Deep dive in [/framework-docs/getting-started/](/framework-docs/getting-started/)
4. **Compare alternatives**: See how Attune AI differs from CrewAI in [/compare/crewai-vs-attune](/compare/crewai-vs-attune)

Multi-agent orchestration transforms how you build AI systems—from rigid pipelines to intelligent, composable teams that adapt to your needs. Start with Sequential orchestration, experiment with Parallel for independent analysis, then graduate to Debate for complex decisions and Adaptive for production-grade intelligence.

---

**Next Steps:**
- Build your first multi-agent team with `/wizard run`
- Deploy with Redis plugin for distributed execution
- Monitor team performance with built-in telemetry
- Scale to production with cost optimization and performance tuning
