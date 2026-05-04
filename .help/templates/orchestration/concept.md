---
type: concept
feature: orchestration
depth: concept
generated_at: 2026-05-04T02:35:39.974459+00:00
source_hash: 15dce809a43de06ae9f042882afecc50f3b625050abdca81b878a832140002f0
status: generated
---

# Orchestration

Orchestration coordinates multiple AI agents working together on complex tasks, automatically managing task distribution, conflict resolution, and result aggregation through Redis-backed coordination.

## Core coordination patterns

The orchestration system supports six composition patterns for different collaboration scenarios:

- **Sequential** — Agents work one after another, passing results down the chain
- **Parallel** — Multiple agents work simultaneously on different parts
- **Debate** — Agents propose competing solutions, then vote on the best approach
- **Teaching** — Expert agents guide novice agents through complex workflows
- **Refinement** — Agents iteratively improve each other's work across multiple passes
- **Adaptive** — Dynamic team composition based on task requirements and agent availability

## Task distribution and coordination

**AgentCoordinator** serves as the central Redis-backed hub that:
- Queues tasks with priority levels (1-10 scale)
- Routes tasks to agents based on capabilities and availability
- Tracks agent heartbeats and removes inactive agents after 5 minutes
- Aggregates results from completed tasks by type
- Broadcasts messages to all active team members

**AgentTask** represents individual work units with:
- Task type and description
- Assignment status (pending/claimed/completed)
- Priority level and creation timestamp
- Context data passed between agents
- Result storage for completed work

## Conflict resolution

When multiple agents produce competing solutions, **ConflictResolver** automatically chooses the best option using configurable strategies:

**Weighted scoring** considers:
- Team priorities (readability 30%, performance 20%, security 30%, maintainability 20%)
- Pattern types (security patterns score highest at 1.0, style patterns lowest at 0.5)
- Confidence levels from each contributing agent

**Resolution results** include the winning pattern, rejected alternatives, confidence score, and reasoning for the decision.

## Team sessions

**TeamSession** enables collaborative work through:
- Shared data storage accessible to all session members
- Signal broadcasting for real-time coordination
- Session-scoped agent registration and management
- Purpose tracking for focused collaboration

Agents can share intermediate results, coordinate on subtasks, and signal completion or need for help within a session context.

## Dynamic team assembly

The system automatically assembles teams based on:
- Task complexity (simple/moderate/complex)
- Domain requirements (security, testing, documentation, etc.)
- Available agent capabilities and current workload
- Resource constraints and execution strategies

Teams scale from single enhanced agents for simple tasks to multi-agent debate patterns for complex architectural decisions.
