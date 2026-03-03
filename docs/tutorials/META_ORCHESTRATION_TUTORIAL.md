---
description: Meta-Orchestration Tutorial: AI Agents That Compose Themselves: Step-by-step tutorial with examples, best practices, and common patterns. Learn by doing with hands-on examples.
---

# Meta-Orchestration Tutorial: AI Agents That Compose Themselves

**Version:** 4.0.0
**Level:** Beginner to Advanced
**Time:** 30 minutes
**Last Updated:** January 10, 2026

---

## 🎭 What You'll Learn

By the end of this tutorial, you'll understand:

1. **What meta-orchestration is** and why it's a paradigm shift
2. **How to use the three built-in workflows** (Release Prep, Test Coverage Boost, Health Check)
3. **How to compose custom agent teams** using Python
4. **How the system learns** from successful compositions
5. **How to build your own orchestrated workflows**

> **📘 About This Tutorial**
>
> This tutorial uses **software development agents** as examples (security auditing, test coverage, code quality), since the framework is primarily used by developers. However, **meta-orchestration is domain-agnostic** and works with any type of agent.
>
> The Attune AI also includes:
>
> - **Healthcare-specific agents**: HIPAA compliance, patient data validation, clinical workflows
> - **Code analysis tools**: Static analysis, SARIF reports, architectural insights
>
> The meta-orchestration system can compose teams from *any* domain. The principles you learn here apply universally.

---

## 📚 Table of Contents

1. [The Big Idea: From Static to Dynamic](#the-big-idea)
2. [Quick Start: Your First Orchestrated Workflow](#quick-start)
3. [Understanding Agent Templates](#understanding-agent-templates)
4. [The Six Composition Patterns](#composition-patterns)
5. [Building Custom Workflows](#building-custom-workflows)
6. [The Learning Loop](#learning-loop)
7. [Advanced Techniques](#advanced-techniques)
8. [Troubleshooting](#troubleshooting)

---

## <a name="the-big-idea"></a>🧠 The Big Idea: From Static to Dynamic

### The Problem with Traditional Workflows

In traditional AI systems, you manually wire together agents:

```python
# Traditional approach: Manual wiring
security_agent = SecurityAgent()
test_agent = TestAgent()
quality_agent = QualityAgent()

# You decide the execution order
security_results = security_agent.run()
test_results = test_agent.run()
quality_results = quality_agent.run()

# You manually combine results
combined = combine_results([security_results, test_results, quality_results])
```

**Problems:**
- 🔧 **Rigid**: Can't adapt to different tasks
- 📈 **Doesn't scale**: Each new task requires manual wiring
- 🧠 **No learning**: Doesn't improve over time
- 💰 **Inefficient**: Always uses the same agents regardless of task complexity

### The Meta-Orchestration Solution

With meta-orchestration, you describe **what you want**, and the system figures out **how to do it**:

```python
# Meta-orchestration approach: Declarative
from attune.orchestration import MetaOrchestrator

orchestrator = MetaOrchestrator()

# Just describe the task
plan = orchestrator.analyze_and_compose(
    task="Prepare for production release",
    context={"project_path": "."}
)

# System automatically:
# 1. Analyzes task complexity and domain
# 2. Selects optimal agents (security, testing, quality, docs)
# 3. Chooses best composition pattern (parallel for speed)
# 4. Estimates cost and duration
# 5. Executes with quality gates
```

**Benefits:**
- ✨ **Adaptive**: Different tasks get different agent teams
- 📊 **Intelligent**: Chooses optimal composition patterns
- 🎯 **Cost-aware**: Uses cheaper agents when appropriate
- 📚 **Self-learning**: Improves from past successes

---

## <a name="quick-start"></a>🚀 Quick Start: Your First Orchestrated Workflow

### Prerequisites

```bash
pip install attune-ai[developer]==4.0.0
```

### Example 1: Release Preparation (5 minutes)

The **Release Prep** workflow runs 4 validation agents in parallel:

```bash
# Basic usage
attune orchestrate release-prep

# With custom quality gates
attune orchestrate release-prep \
    --min-coverage 90 \
    --min-quality 8 \
    --max-critical 0

# JSON output for CI/CD
attune orchestrate release-prep --json > report.json
```

**What happens:**
1. ✅ **Security Auditor** scans for vulnerabilities
2. ✅ **Test Coverage Analyzer** identifies testing gaps
3. ✅ **Code Quality Reviewer** checks best practices
4. ✅ **Documentation Writer** verifies completeness

All run **in parallel** for speed! ⚡

**Sample output:**

```
============================================================
  RELEASE PREPARATION REPORT
============================================================

  ✓ Security Auditor: No critical issues
  ✓ Test Coverage: 87.5% (target: 80%)
  ✓ Code Quality: 8.2/10 (target: 7.0)
  ⚠ Documentation: 95% (target: 100%)

  🎯 QUALITY GATES
  --------------------------------------------------------
  ✅ All critical gates passed!
  ⚠  1 warning (documentation below 100%)

  ✅ RELEASE APPROVED (confidence: medium)

  Duration: 2.3 seconds
============================================================
```

### Example 2: Test Coverage Boost (10 minutes)

The **Test Coverage Boost** workflow improves test coverage in 3 sequential stages:

```bash
# Basic usage
attune orchestrate test-coverage

# Set target coverage
attune orchestrate test-coverage --target 90

# Specify project root
attune orchestrate test-coverage \
    --project-root ./my-project \
    --target 85
```

**What happens:**
1. 🔍 **Stage 1: Analysis** - Identifies gaps by importance
2. 🔨 **Stage 2: Generation** - Creates tests for high-priority gaps
3. ✅ **Stage 3: Validation** - Verifies tests pass and coverage improves

**Sample output:**

```
============================================================
  TEST COVERAGE BOOST
============================================================

  Target Coverage: 90.0%
  Current Coverage: 75.0%

  🔍 Stage 1: Coverage Gap Analysis
  ✓ Identified 12 high-priority gaps
  ✓ Found 8 untested edge cases

  🔨 Stage 2: Test Generation
  ✓ Generated 23 tests
  ✓ Expected coverage increase: +15%

  ✅ Stage 3: Test Validation
  ✓ All tests pass
  ✓ Final coverage: 90.2%
  ✓ Improvement: +15.2%

  🎯 SUCCESS: Coverage target achieved!

  Duration: 8.7 seconds
============================================================
```

### Example 3: Health Check (2 minutes)

The **Health Check** workflow provides adaptive health assessment with 3 modes:

```bash
# Quick daily check (3 agents in parallel)
attune orchestrate health-check --mode daily

# Comprehensive weekly (5 agents)
attune orchestrate health-check --mode weekly

# Pre-release deep dive (6 agents)
attune orchestrate health-check --mode release

# JSON output for CI integration
attune orchestrate health-check --mode daily --json
```

**What happens:**

- **Daily**: Security, Coverage, Quality (fast parallel check)
- **Weekly**: Adds Performance, Documentation (comprehensive)
- **Release**: Adds Architecture analysis (deep refinement)

**Sample output:**

```text
============================================================
  🏥 HEALTH CHECK REPORT
============================================================

  Health Score: 85/100 (Grade: B)
  Trend: Improving (+5 from last week)
  Duration: 1.2s

  ⚠️  Issues Found (1):
    • Documentation below 100% (92%)

  💡 Recommendations:
    1. 📚 Complete API documentation for 3 modules
    2. ✅ Maintain current test coverage (excellent!)

============================================================
```

---

## <a name="understanding-agent-templates"></a>🤖 Understanding Agent Templates

Agent templates are **reusable archetypes** with specific capabilities. Think of them as specialized experts you can call upon.

### The 7 Built-in Templates

| Template | Tier | Role | Capabilities |
|----------|------|------|--------------|
| **test_coverage_analyzer** | CAPABLE | Test Coverage Expert | analyze_gaps, suggest_tests, validate_coverage |
| **security_auditor** | PREMIUM | Security Auditor | vulnerability_scan, threat_modeling, compliance_check |
| **code_reviewer** | CAPABLE | Code Quality Reviewer | code_review, quality_assessment, best_practices_check |
| **documentation_writer** | CHEAP | Documentation Writer | generate_docs, check_completeness, update_examples |
| **performance_optimizer** | CAPABLE | Performance Optimizer | profile_code, identify_bottlenecks, suggest_optimizations |
| **architecture_analyst** | PREMIUM | Architecture Analyst | analyze_architecture, identify_patterns, suggest_improvements |
| **refactoring_specialist** | CAPABLE | Refactoring Specialist | identify_code_smells, suggest_refactorings, validate_changes |

### Exploring Templates (Python)

```python
from attune.orchestration import get_all_templates, get_template

# List all templates
templates = get_all_templates()
for t in templates:
    print(f"{t.id}: {t.role} ({t.tier_preference})")

# Get specific template
security_template = get_template("security_auditor")
print(f"Role: {security_template.role}")
print(f"Capabilities: {security_template.capabilities}")
print(f"Tools: {security_template.tools}")
```

### Tier System: Cost vs. Capability

- **CHEAP**: Fast, inexpensive (e.g., documentation_writer)
- **CAPABLE**: Balanced performance/cost (e.g., test_coverage_analyzer)
- **PREMIUM**: Highest quality, most expensive (e.g., security_auditor)

The orchestrator **automatically selects tiers** based on task complexity!

---

## <a name="composition-patterns"></a>📐 The Six Composition Patterns

Meta-orchestration provides six **"grammar rules"** for combining agents:

### 1. Sequential (A → B → C)

**When to use:** Pipeline processing where each stage builds on previous results

**Example:** Test coverage boost (Analyze → Generate → Validate)

```python
from attune.orchestration.execution_strategies import SequentialStrategy

strategy = SequentialStrategy()
result = await strategy.execute(agents, context)

# Stage 1 output feeds into Stage 2
# Stage 2 output feeds into Stage 3
```

**Characteristics:**
- ⏱️ Duration: Sum of all stages
- 🔄 Context passing between stages
- 📊 Best for: Iterative improvement, multi-stage pipelines

### 2. Parallel (A ‖ B ‖ C)

**When to use:** Independent validations that can run simultaneously

**Example:** Release prep (Security ‖ Coverage ‖ Quality ‖ Docs)

```python
from attune.orchestration.execution_strategies import ParallelStrategy

strategy = ParallelStrategy()
result = await strategy.execute(agents, context)

# All agents run at the same time
# Results aggregated at the end
```

**Characteristics:**
- ⚡ Duration: Max of all agents (fastest!)
- 🎯 Best for: Independent checks, validation workflows
- 💰 Slightly higher cost (all agents run)

### 3. Debate (A ⇄ B ⇄ C → Synthesis)

**When to use:** Need consensus or multiple perspectives

**Example:** Architecture decisions, design reviews

```python
from attune.orchestration.execution_strategies import DebateStrategy

strategy = DebateStrategy()
result = await strategy.execute(agents, context)

# Agents propose independent solutions
# Synthesis agent reconciles differences
```

**Characteristics:**
- 🤔 Duration: Multiple rounds + synthesis
- 🎯 Best for: Subjective decisions, architecture choices
- 💰 Higher cost (multiple agents + synthesis)

### 4. Teaching (Junior → Expert)

**When to use:** Cost optimization with quality gate fallback

**Example:** Documentation (cheap agent tries, expert validates)

```python
from attune.orchestration.execution_strategies import TeachingStrategy

strategy = TeachingStrategy()
result = await strategy.execute([junior_agent, expert_agent], context)

# Junior attempts task (cheap)
# If quality score < threshold, expert takes over
```

**Characteristics:**
- 💰 Cost: Low if junior succeeds, medium if expert needed
- 🎯 Best for: Tasks where cheaper agents often succeed
- ⚖️ Balances cost and quality

### 5. Refinement (Draft → Review → Polish)

**When to use:** Progressive quality improvement

**Example:** Documentation refinement, code polishing

```python
from attune.orchestration.execution_strategies import RefinementStrategy

strategy = RefinementStrategy()
result = await strategy.execute(agents, context)

# Draft stage (fast, rough)
# Review stage (checks quality)
# Polish stage (final touches)
```

**Characteristics:**
- 📈 Duration: Progressive (each stage improves previous)
- 🎯 Best for: Content creation, iterative improvement
- ✨ Each stage increases quality score

### 6. Adaptive (Classifier → Specialist)

**When to use:** Right-sizing based on task complexity

**Example:** Bug fixes (simple bugs get cheap agent, complex get expert)

```python
from attune.orchestration.execution_strategies import AdaptiveStrategy

strategy = AdaptiveStrategy()
result = await strategy.execute(agents, context)

# Classifier determines complexity
# Routes to appropriate specialist
```

**Characteristics:**
- 🎯 Cost: Depends on task complexity
- 🧠 Best for: Variable complexity tasks
- 📊 Optimizes cost/quality tradeoff

---

## <a name="building-custom-workflows"></a>🛠️ Building Custom Workflows

### Example: Custom Security Deep Dive

Let's build a workflow that uses **Debate** pattern for security analysis:

```python
from attune.orchestration import MetaOrchestrator, get_template
from attune.orchestration.execution_strategies import DebateStrategy

class SecurityDeepDiveWorkflow:
    """Multi-perspective security analysis with debate."""

    def __init__(self):
        self.orchestrator = MetaOrchestrator()

    async def execute(self, project_path: str):
        # Compose security-focused agent team
        plan = self.orchestrator.analyze_and_compose(
            task="Comprehensive security audit with multiple perspectives",
            context={
                "project_path": project_path,
                "domain": "security",
                "capabilities": ["vulnerability_scan", "threat_modeling"]
            }
        )

        # Override with Debate strategy for consensus
        strategy = DebateStrategy()
        result = await strategy.execute(plan.agents, {
            "project_path": project_path
        })

        # Process results
        if result.success:
            print(f"✅ Security audit complete")
            print(f"Consensus: {result.final_output.get('consensus')}")
            print(f"Confidence: {result.final_output.get('confidence')}")

        return result

# Usage
workflow = SecurityDeepDiveWorkflow()
result = await workflow.execute("./my-project")
```

### Example: Cost-Optimized Documentation

Using **Teaching** pattern to minimize costs:

```python
from attune.orchestration import get_template
from attune.orchestration.execution_strategies import TeachingStrategy

class CostOptimizedDocWorkflow:
    """Documentation with cost optimization."""

    async def execute(self, module_path: str):
        # Get cheap and capable agents
        junior = get_template("documentation_writer")  # CHEAP
        expert = get_template("code_reviewer")  # CAPABLE

        # Teaching strategy: junior tries, expert validates
        strategy = TeachingStrategy()
        result = await strategy.execute(
            agents=[junior, expert],
            context={
                "module_path": module_path,
                "quality_threshold": 7.0  # Expert takes over if < 7
            }
        )

        # Check which agent completed the task
        if result.final_output.get("completed_by") == junior.id:
            print(f"💰 Cost-optimized: Junior completed successfully")
        else:
            print(f"🎓 Quality-optimized: Expert took over")

        return result
```

### Example: Progressive Content Refinement

Using **Refinement** pattern for iterative improvement:

```python
from attune.orchestration.execution_strategies import RefinementStrategy

class ContentRefinementWorkflow:
    """Progressive quality improvement for content."""

    async def execute(self, content: str):
        # Get agents for each refinement stage
        drafter = get_template("documentation_writer")
        reviewer = get_template("code_reviewer")
        polisher = get_template("documentation_writer")  # Reuse

        strategy = RefinementStrategy()
        result = await strategy.execute(
            agents=[drafter, reviewer, polisher],
            context={
                "content": content,
                "target_quality": 9.0  # High quality target
            }
        )

        # Show quality progression
        print(f"Draft quality: {result.outputs[0].quality_score}")
        print(f"Review quality: {result.outputs[1].quality_score}")
        print(f"Final quality: {result.outputs[2].quality_score}")

        return result
```

---

## <a name="learning-loop"></a>📚 The Learning Loop: How the System Improves

### How Configuration Store Works

The system **saves successful compositions** and **reuses them** for similar tasks:

```python
from attune.orchestration.config_store import ConfigurationStore
from attune.pattern_library import PatternLibrary

# Initialize store
store = ConfigurationStore(pattern_library=PatternLibrary())

# After successful workflow execution
config = AgentConfiguration(
    id="release_prep_001",
    task_pattern="release_preparation",
    agents=[
        {"role": "security_auditor", "tier": "PREMIUM"},
        {"role": "test_coverage_analyzer", "tier": "CAPABLE"}
    ],
    strategy="parallel",
    quality_gates={"min_coverage": 80}
)

# Save configuration
store.save(config)

# Record outcome
config.record_outcome(success=True, quality_score=87.5)
store.save(config)  # Update metrics
```

### Querying Learned Compositions

```python
# Find best composition for a task
best = store.get_best_for_task("release_preparation")
print(f"Success rate: {best.success_rate:.1%}")
print(f"Avg quality: {best.avg_quality_score:.1f}")
print(f"Usage count: {best.usage_count}")

# Search with filters
proven_configs = store.search(
    task_pattern="release_preparation",
    min_success_rate=0.8,
    min_quality_score=75.0
)

# Reuse proven composition
for config in proven_configs:
    print(f"  {config.id}: {config.success_rate:.1%} success")
```

### Pattern Library Integration

After **3+ successful uses** with **70%+ success rate**, compositions are contributed to the Pattern Library:

```python
# Automatic contribution after thresholds met
if config.usage_count >= 3 and config.success_rate >= 0.7:
    store.pattern_library.contribute_successful_composition(config)
    print(f"✅ Configuration promoted to pattern library!")
```

**Benefits:**
- 📊 Cross-project learning
- 🎯 Team knowledge sharing
- 📈 Continuous improvement

---

## <a name="advanced-techniques"></a>🎓 Advanced Techniques

### 1. Dynamic Agent Selection

Let the orchestrator choose agents based on task analysis:

```python
orchestrator = MetaOrchestrator()

# Orchestrator analyzes task and picks agents automatically
plan = orchestrator.analyze_and_compose(
    task="Improve performance of slow API endpoint",
    context={"domain": "performance"}
)

print(f"Selected agents: {[a.role for a in plan.agents]}")
print(f"Strategy: {plan.strategy.value}")
print(f"Estimated cost: ${plan.estimated_cost:.2f}")
```

### 2. Hybrid Strategies

Combine multiple strategies in one workflow:

```python
class HybridWorkflow:
    """Combines parallel validation + sequential refinement."""

    async def execute(self, project_path: str):
        # Phase 1: Parallel validation
        validators = [
            get_template("security_auditor"),
            get_template("test_coverage_analyzer"),
            get_template("code_reviewer")
        ]

        parallel_strategy = ParallelStrategy()
        validation_results = await parallel_strategy.execute(
            validators,
            {"path": project_path}
        )

        # Phase 2: Sequential refinement if issues found
        if validation_results.has_issues():
            refiners = [
                get_template("refactoring_specialist"),
                get_template("code_reviewer")
            ]

            sequential_strategy = SequentialStrategy()
            refinement_results = await sequential_strategy.execute(
                refiners,
                {"issues": validation_results.issues}
            )

        return validation_results, refinement_results
```

### 3. Custom Agent Templates

Create your own specialized agents:

```python
from attune.orchestration.agent_templates import (
    AgentTemplate,
    AgentCapability,
    ResourceRequirements
)

# Define custom template
api_optimizer = AgentTemplate(
    id="api_optimizer",
    role="API Performance Optimizer",
    capabilities=[
        AgentCapability(
            name="profile_api",
            description="Profile API endpoint performance",
            required_context=["endpoint_url"],
            output_schema={"response_time": "float", "bottlenecks": "list"}
        ),
        AgentCapability(
            name="optimize_queries",
            description="Optimize database queries",
            required_context=["db_connection"],
            output_schema={"queries_optimized": "int", "improvement": "float"}
        )
    ],
    tier_preference="CAPABLE",
    resource_requirements=ResourceRequirements(
        max_tokens=8000,
        timeout_seconds=600
    ),
    tools=["profiler", "query_analyzer", "cache_optimizer"],
    quality_gates={"min_improvement": 20.0}
)

# Register template
from attune.orchestration.agent_templates import AGENT_REGISTRY
AGENT_REGISTRY[api_optimizer.id] = api_optimizer
```

### 4. Conditional Execution

Execute different agents based on runtime conditions:

```python
class ConditionalWorkflow:
    """Adapts execution based on project characteristics."""

    async def execute(self, project_path: str):
        # Analyze project
        has_tests = self._check_tests(project_path)
        has_security = self._check_security(project_path)

        # Build agent list conditionally
        agents = []

        if not has_tests:
            agents.append(get_template("test_coverage_analyzer"))

        if not has_security:
            agents.append(get_template("security_auditor"))

        agents.append(get_template("code_reviewer"))  # Always

        # Execute with appropriate strategy
        strategy = ParallelStrategy() if len(agents) > 1 else SequentialStrategy()
        result = await strategy.execute(agents, {"path": project_path})

        return result
```

---

## <a name="troubleshooting"></a>🔧 Troubleshooting

### Issue: Orchestrator selects wrong agents

**Problem:** Task analysis picks agents that don't match your needs

**Solution:** Provide explicit context hints

```python
# Instead of vague task description
plan = orchestrator.analyze_and_compose(
    task="Fix the code"
)

# Provide explicit domain and capabilities
plan = orchestrator.analyze_and_compose(
    task="Fix security vulnerabilities in authentication module",
    context={
        "domain": "security",
        "capabilities": ["vulnerability_scan", "threat_modeling"],
        "complexity": "high"
    }
)
```

### Issue: Quality gates always fail

**Problem:** Default quality gates are too strict

**Solution:** Customize thresholds

```python
from attune.workflows.orchestrated_release_prep import (
    OrchestratedReleasePrepWorkflow
)

# Custom quality gates
workflow = OrchestratedReleasePrepWorkflow(
    quality_gates={
        "min_coverage": 70.0,      # Lower threshold
        "min_quality_score": 6.0,  # More lenient
        "max_critical_issues": 1,  # Allow 1 critical
        "min_doc_coverage": 80.0   # Adjust docs requirement
    }
)
```

### Issue: Workflows too slow

**Problem:** Sequential execution is bottleneck

**Solution:** Use parallel strategy when possible

```python
# Slow: Sequential
strategy = SequentialStrategy()

# Fast: Parallel (if agents are independent)
strategy = ParallelStrategy()

# Or use Teaching pattern for cost optimization
strategy = TeachingStrategy()  # Cheap agent tries first
```

### Issue: Costs too high

**Problem:** Always using PREMIUM tier agents

**Solution:** Adjust tier preferences or use Teaching strategy

```python
# Option 1: Override agent selection
cheap_agents = [
    get_template("documentation_writer"),  # CHEAP
    get_template("code_reviewer")  # CAPABLE
]

# Option 2: Use Teaching strategy
strategy = TeachingStrategy()  # Tries cheap first, expert if needed

# Option 3: Provide complexity hint
plan = orchestrator.analyze_and_compose(
    task="Write API documentation",
    context={"complexity": "simple"}  # Favors cheaper agents
)
```

### Issue: Configuration not learning

**Problem:** Compositions aren't being saved

**Solution:** Ensure you're recording outcomes

```python
from attune.orchestration.config_store import ConfigurationStore

store = ConfigurationStore()

# Save configuration after creation
config_id = store.save(config)

# IMPORTANT: Record outcome after execution
config.record_outcome(success=True, quality_score=85.0)
store.save(config)  # Update with metrics

# Verify learning
best = store.get_best_for_task(config.task_pattern)
print(f"Usage count: {best.usage_count}")  # Should increment
```

---

## 🎉 Conclusion

You've learned:

✅ **What meta-orchestration is** - AI agents that compose themselves
✅ **How to use built-in workflows** - Release Prep, Test Coverage Boost, Health Check
✅ **The 6 composition patterns** - Sequential, Parallel, Debate, Teaching, Refinement, Adaptive
✅ **How to build custom workflows** - Combining agents and strategies
✅ **How the system learns** - Configuration store and pattern library
✅ **Advanced techniques** - Hybrid strategies, custom templates, conditional execution

### Domain-Specific Extensions

While this tutorial focused on software development workflows, the Attune AI includes additional domain-specific capabilities:

**Healthcare & Compliance:**

- HIPAA compliance validation agents
- Patient data privacy checkers
- Clinical workflow orchestration
- Regulatory audit trail generation

**Code Analysis & Quality:**

- Static analysis with SARIF output
- Architectural dependency mapping
- Security vulnerability scanning
- Technical debt quantification

**Custom Domains:**

The meta-orchestration system is designed to work with agents from *any* domain. You can:

1. Create custom agent templates for your industry
2. Use the same composition patterns (Sequential, Parallel, etc.)
3. Benefit from the learning loop across all domains
4. Mix and match agents from different domains in one workflow

### Next Steps

1. **Experiment** with the built-in workflows
2. **Build** your first custom workflow
3. **Monitor** the learning loop (check configuration store)
4. **Share** successful compositions with your team
5. **Explore** domain-specific features if relevant to your work

### Additional Resources

- [API Reference](../reference/API_REFERENCE.md) - API overview
- [Multi-Agent Reference](../reference/multi-agent.md) - Agent coordination
- Healthcare Wizards - HIPAA compliance and clinical workflows (see `attune wizard --help`)

---

**Welcome to the Meta-Orchestration Era!** 🎭

The future of AI collaboration is dynamic, intelligent, and self-improving. You're now part of that future.

Happy orchestrating! 🚀
