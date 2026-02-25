---
description: "Multi-Agent Team Coordination: Task distribution,
  shared patterns, conflict resolution, and team execution
  using Attune's coordination and SDK agent APIs."
---

# Multi-Agent Team Coordination

**Difficulty**: Advanced
**Time**: 30 minutes
**Prerequisites**: Redis running locally, `attune-ai`
installed

---

## Overview

This tutorial shows how to coordinate multiple AI agents
using Attune's real coordination primitives:

- **AgentCoordinator** — Redis-backed task queue with
  agent registration, claiming, and broadcasting
- **TeamSession** — Shared context and signaling between
  agents in a collaborative session
- **PatternLibrary** — Shared pattern discovery so one
  agent's learning benefits the whole team
- **ConflictResolver** — Weighted scoring to resolve
  conflicting pattern recommendations
- **SDKAgentTeam** — Parallel/sequential agent execution
  with quality gates

---

## Installation

```bash
pip install attune-ai
redis-server  # Must be running for coordination
```

---

## Part 1: Task Distribution with AgentCoordinator

The `AgentCoordinator` uses Redis to distribute tasks
across agents. Agents register, claim pending tasks, and
broadcast results.

```python
from attune.coordination import AgentCoordinator, AgentTask
from attune.memory import get_redis_memory

# Connect to Redis
memory = get_redis_memory()

# Create a coordinator for a code review team
coordinator = AgentCoordinator(
    short_term_memory=memory,
    team_id="code_review_team",
)

# Register three specialized agents
coordinator.register_agent(
    "security_agent",
    capabilities=["security_review", "vulnerability_scan"],
)
coordinator.register_agent(
    "performance_agent",
    capabilities=["performance_review", "profiling"],
)
coordinator.register_agent(
    "style_agent",
    capabilities=["style_review", "linting"],
)

print(f"Active agents: {coordinator.get_active_agents()}")
# Output: Active agents: ['security_agent',
#   'performance_agent', 'style_agent']
```

### Add and Claim Tasks

```python
# Add tasks to the queue
coordinator.add_task(AgentTask(
    task_id="review_auth_module",
    task_type="security_review",
    description="Review authentication module for vulns",
    priority=9,
    context={"files": ["src/auth.py", "src/tokens.py"]},
))

coordinator.add_task(AgentTask(
    task_id="review_query_perf",
    task_type="performance_review",
    description="Check database query performance",
    priority=7,
    context={"files": ["src/db/queries.py"]},
))

# Security agent claims the highest-priority task
task = coordinator.claim_task(
    "security_agent",
    task_type="security_review",
)

if task:
    print(f"Claimed: {task.description} (priority {task.priority})")
    # Output: Claimed: Review authentication module for
    #   vulns (priority 9)

    # Do the work, then complete the task
    coordinator.complete_task(
        task.task_id,
        result={
            "issues_found": 2,
            "severity": "high",
            "details": "SQL injection in login endpoint",
        },
        agent_id="security_agent",
    )
```

### Broadcast Messages

```python
# Broadcast an infrastructure change to all agents
coordinator.broadcast(
    message_type="infrastructure_change",
    data={
        "change": "Database connection pool reduced",
        "old_value": "max_connections=200",
        "new_value": "max_connections=50",
        "action_required": True,
    },
)

# Aggregate results from all completed tasks
results = coordinator.aggregate_results()
print(f"Completed: {results['total_completed']}")
print(f"By agent: {results['by_agent']}")
```

---

## Part 2: Shared Context with TeamSession

A `TeamSession` gives agents a shared workspace. Agents
join a session, share data with `share()`, read it with
`get()`, and communicate via `signal()`.

```python
from attune.coordination import TeamSession
from attune.memory import get_redis_memory

memory = get_redis_memory()

# Create a session for reviewing PR #42
session = TeamSession(
    short_term_memory=memory,
    session_id="pr_review_42",
    purpose="Review PR #42: Add user profile images",
)

# Agents join the session
session.add_agent("security_agent")
session.add_agent("performance_agent")

# Security agent shares its analysis scope
session.share("analysis_scope", {
    "files": ["src/upload.py", "src/images.py"],
    "lines_of_code": 340,
    "risk_areas": ["file upload validation", "path handling"],
})

# Performance agent reads the shared scope
scope = session.get("analysis_scope")
print(f"Reviewing {scope['lines_of_code']} lines")
print(f"Risk areas: {scope['risk_areas']}")
# Output:
# Reviewing 340 lines
# Risk areas: ['file upload validation', 'path handling']
```

### Signaling Between Agents

```python
# Security agent signals a finding
session.signal(
    signal_type="finding",
    data={
        "agent": "security_agent",
        "severity": "high",
        "file": "src/upload.py",
        "line": 42,
        "issue": "No file type validation on upload",
    },
)

# Performance agent checks for signals
signals = session.get_signals(signal_type="finding")
for s in signals:
    data = s.get("data", {})
    print(f"[{data.get('agent')}] {data.get('issue')}")
# Output:
# [security_agent] No file type validation on upload
```

---

## Part 3: Shared Pattern Library

The `PatternLibrary` lets agents contribute reusable
patterns and query for relevant ones. One agent's discovery
benefits the entire team.

```python
from attune.pattern_library import Pattern, PatternLibrary

library = PatternLibrary()

# Security agent contributes a pattern it discovered
library.contribute_pattern(
    "security_agent",
    Pattern(
        id="validate_upload_type",
        agent_id="security_agent",
        pattern_type="security",
        name="Validate file upload MIME type",
        description=(
            "Always validate MIME type and extension on "
            "file uploads. Reject executable types."
        ),
        confidence=0.92,
        tags=["security", "file-upload", "validation"],
        context={"domain": "web", "risk": "high"},
    ),
)

# Performance agent contributes a different pattern
library.contribute_pattern(
    "performance_agent",
    Pattern(
        id="batch_image_processing",
        agent_id="performance_agent",
        pattern_type="performance",
        name="Batch image processing with pipeline",
        description=(
            "Process uploaded images in batches using "
            "Redis pipeline instead of one-at-a-time."
        ),
        confidence=0.88,
        tags=["performance", "redis", "batch"],
        context={"domain": "web", "bottleneck": "io"},
    ),
)

print(f"Library stats: {library.get_library_stats()}")
# Output:
# Library stats: {
#   'total_patterns': 2,
#   'total_agents': 2,
#   'total_usage': 0,
#   'average_confidence': 0.9,
#   ...
# }
```

### Query Patterns by Context

```python
# A new agent queries the library for relevant patterns
context = {
    "domain": "web",
    "task_type": "file_upload",
    "tags": ["security", "validation"],
}

matches = library.query_patterns(
    "style_agent",
    context,
    min_confidence=0.8,
)

for match in matches:
    p = match.pattern
    print(
        f"  {p.name} (confidence: {p.confidence:.0%}, "
        f"relevance: {match.relevance_score:.0%})"
    )
    print(f"    From: {p.agent_id}")
    print(f"    Why: {match.matching_factors}")

# Output:
#   Validate file upload MIME type (confidence: 92%,
#     relevance: 70%)
#     From: security_agent
#     Why: ['1 context matches', '1 tag matches']
```

### Record Outcomes and Link Patterns

```python
# Record that using the pattern was successful
library.record_pattern_outcome("validate_upload_type", success=True)

# Link related patterns so agents discover both
library.link_patterns(
    "validate_upload_type",
    "batch_image_processing",
)

# Get related patterns
related = library.get_related_patterns("validate_upload_type")
print(f"Related: {[p.name for p in related]}")
# Output: Related: ['Batch image processing with pipeline']
```

---

## Part 4: Conflict Resolution

When two agents recommend conflicting approaches, the
`ConflictResolver` uses weighted scoring across confidence,
success rate, recency, context match, and team priorities.

```python
from attune.coordination import (
    ConflictResolver,
    ResolutionStrategy,
    TeamPriorities,
)
from attune.pattern_library import Pattern

# Configure team priorities
priorities = TeamPriorities(
    security_weight=0.4,
    readability_weight=0.3,
    performance_weight=0.2,
    maintainability_weight=0.1,
)

resolver = ConflictResolver(
    default_strategy=ResolutionStrategy.WEIGHTED_SCORE,
    team_priorities=priorities,
)

# Two agents disagree on approach
security_pattern = Pattern(
    id="strict_validation",
    agent_id="security_agent",
    pattern_type="security",
    name="Strict input validation with allowlist",
    description="Validate all inputs against an allowlist",
    confidence=0.90,
    tags=["security", "validation"],
)

perf_pattern = Pattern(
    id="lazy_validation",
    agent_id="performance_agent",
    pattern_type="performance",
    name="Lazy validation on hot path",
    description="Defer validation to reduce latency",
    confidence=0.75,
    tags=["performance", "optimization"],
)

# Resolve the conflict
result = resolver.resolve_patterns(
    patterns=[security_pattern, perf_pattern],
    context={"team_priority": "security"},
)

print(f"Winner: {result.winning_pattern.name}")
print(f"Strategy: {result.strategy_used.value}")
print(f"Confidence: {result.confidence:.0%}")
print(f"Reasoning: {result.reasoning}")
# Output:
# Winner: Strict input validation with allowlist
# Strategy: weighted_score
# Confidence: 72%
# Reasoning: Selected 'Strict input validation with
#   allowlist' based on weighted scoring (top factors:
#   confidence: 90%, team_alignment: 80%). Preferred
#   over: Lazy validation on hot path
```

### Resolution Statistics

```python
stats = resolver.get_resolution_stats()
print(f"Total resolutions: {stats['total_resolutions']}")
print(f"Strategies used: {stats['strategies_used']}")
print(f"Avg confidence: {stats['average_confidence']:.0%}")
```

---

## Part 5: Team Execution with SDKAgentTeam

`SDKAgentTeam` runs multiple `SDKAgent` instances in
parallel (or sequentially) and evaluates quality gates on
their results.

```python
import asyncio
from attune.agents.sdk import SDKAgent, SDKAgentTeam
from attune.agents.sdk.sdk_team import QualityGate

# Create specialized agents with system prompts
security_agent = SDKAgent(
    agent_id="security-reviewer",
    role="Security Reviewer",
    system_prompt=(
        "You are a security code reviewer. Analyze code "
        "for vulnerabilities. Return JSON with 'score' "
        "(0-100) and 'findings' dict."
    ),
)

perf_agent = SDKAgent(
    agent_id="perf-reviewer",
    role="Performance Reviewer",
    system_prompt=(
        "You are a performance reviewer. Identify "
        "bottlenecks and inefficiencies. Return JSON "
        "with 'score' (0-100) and 'findings' dict."
    ),
)

# Build a team with quality gates
team = SDKAgentTeam(
    team_name="Code Review Team",
    agents=[security_agent, perf_agent],
    quality_gates=[
        QualityGate(
            name="min_security_score",
            agent_role="Security Reviewer",
            metric="score",
            threshold=70.0,
            required=True,
        ),
        QualityGate(
            name="min_perf_score",
            agent_role="Performance Reviewer",
            metric="score",
            threshold=60.0,
            required=False,  # Advisory, not blocking
        ),
    ],
    parallel=True,  # Run agents concurrently
)


async def run_review():
    result = await team.execute({
        "files": ["src/auth.py"],
        "diff": "def login(user, password): ...",
    })

    print(f"Team: {result.team_name}")
    print(f"Success: {result.success}")
    print(f"Total cost: ${result.total_cost:.4f}")
    print(f"Time: {result.execution_time_ms:.0f}ms")

    for gate, passed in result.quality_gate_results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  Gate '{gate}': {status}")

    for agent_result in result.agent_results:
        print(
            f"\n  [{agent_result.role}] "
            f"score={agent_result.score}, "
            f"tier={agent_result.tier_used}, "
            f"escalated={agent_result.escalated}"
        )


asyncio.run(run_review())
```

Each `SDKAgent` uses progressive tier escalation: it
starts on the CHEAP tier and automatically escalates to
CAPABLE, then PREMIUM if the cheaper tier fails.

---

## Part 6: Putting It All Together

Here's a complete workflow combining all the primitives:

1. **Coordinator** distributes review tasks
2. **TeamSession** shares context between agents
3. **SDKAgentTeam** runs agents in parallel
4. **PatternLibrary** captures what agents learn
5. **ConflictResolver** resolves disagreements

```python
import asyncio
from attune.coordination import (
    AgentCoordinator,
    AgentTask,
    ConflictResolver,
    TeamSession,
)
from attune.agents.sdk import SDKAgent, SDKAgentTeam
from attune.memory import get_redis_memory
from attune.pattern_library import Pattern, PatternLibrary

async def coordinated_review(files: list[str]):
    """Run a coordinated multi-agent code review."""
    memory = get_redis_memory()

    # 1. Set up coordination
    coordinator = AgentCoordinator(memory, team_id="review")
    session = TeamSession(memory, session_id="review_pr99")
    library = PatternLibrary()
    resolver = ConflictResolver()

    # 2. Share review scope
    session.share("scope", {"files": files})

    # 3. Run agents in parallel
    team = SDKAgentTeam(
        team_name="PR Review",
        agents=[
            SDKAgent(
                role="Security Reviewer",
                system_prompt="Review for security issues.",
            ),
            SDKAgent(
                role="Performance Reviewer",
                system_prompt="Review for performance.",
            ),
        ],
        parallel=True,
    )

    result = await team.execute({"files": files})

    # 4. Capture patterns from findings
    for agent_result in result.agent_results:
        if agent_result.success and agent_result.findings:
            library.contribute_pattern(
                agent_result.agent_id,
                Pattern(
                    id=f"review_{agent_result.agent_id}",
                    agent_id=agent_result.agent_id,
                    pattern_type=agent_result.role.lower(),
                    name=f"Finding from {agent_result.role}",
                    description=str(agent_result.findings),
                    confidence=agent_result.confidence,
                ),
            )

    # 5. Signal completion
    session.signal("review_complete", {
        "success": result.success,
        "cost": result.total_cost,
        "agents": len(result.agent_results),
    })

    # 6. Broadcast results
    coordinator.broadcast("review_done", {
        "files": files,
        "passed": result.success,
    })

    return result

result = asyncio.run(coordinated_review(["src/auth.py"]))
print(f"Review {'passed' if result.success else 'failed'}")
print(f"Cost: ${result.total_cost:.4f}")
```

---

## API Quick Reference

| Class | Import | Key Methods |
| ----- | ------ | ----------- |
| `AgentCoordinator` | `attune.coordination` | `add_task()`, `claim_task()`, `complete_task()`, `broadcast()`, `register_agent()` |
| `TeamSession` | `attune.coordination` | `add_agent()`, `share()`, `get()`, `signal()`, `get_signals()` |
| `PatternLibrary` | `attune.pattern_library` | `contribute_pattern()`, `query_patterns()`, `link_patterns()`, `get_library_stats()` |
| `ConflictResolver` | `attune.coordination` | `resolve_patterns()`, `get_resolution_stats()` |
| `SDKAgent` | `attune.agents.sdk` | `process()` |
| `SDKAgentTeam` | `attune.agents.sdk` | `execute()` |

---

## Troubleshooting

### "Connection refused" errors

Redis must be running. Start it with:

```bash
redis-server
```

### Agent claims return None

No pending tasks match the requested `task_type`. Check
that tasks were added with the correct type.

### SDKAgent returns empty results

Set `ANTHROPIC_API_KEY` in your environment. Without it,
agents fall back to rule-based responses.

---

## Next Steps

- [Agent Coordination Demo](../../../examples/agent_coordination_demo.py) —
  Working demo of CoordinationSignals
- [Orchestration](../../../src/attune/orchestration/) —
  DynamicTeam and MetaOrchestrator for automatic team
  composition
- [Agent State](../../../src/attune/agents/state/) —
  Persistent state and recovery for long-running agents
