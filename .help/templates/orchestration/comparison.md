---
type: comparison
name: orchestration-comparison
feature: orchestration
depth: comparison
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 1d31bb00ab6284a8ff06a91f07123af0d56d15af02f09b6311f660814398d142
status: generated
---

# Comparison: Orchestration vs alternatives

## Context

The orchestration module provides two complementary layers for composing agent work:

- **Workflow orchestration** — runs named analysis workflows (Security Audit, Code Review, Deep Review, etc.) in sequence and combines their findings into a single scored report.
- **Meta-orchestration** — composes `BaseWorkflow` instances using one of six execution strategies, controlling agent order, data flow between stages, and quality gates.

Understanding which layer you need — and when a simpler alternative wins — is the goal of this page.

## Strategy comparison

The six composition patterns and the three advanced strategies each serve a distinct execution shape. Use this table to match your use case to the right strategy.

| Strategy | Execution shape | Best for | Key constraint |
|---|---|---|---|
| `SequentialStrategy` | Agents run one after another; output flows forward | Pipelines where each stage depends on the previous result (e.g., `security_audit → dependency_check → release_prep`) | No parallelism; total time = sum of stage times |
| `ParallelStrategy` | All agents run concurrently | Independent analyses where speed matters more than inter-stage data sharing | Agents cannot consume each other's output |
| `DebateStrategy` | Agents argue positions; result is synthesized | Decisions requiring multiple perspectives (architecture trade-offs, risk assessment) | Higher token cost; not suitable for time-sensitive gates |
| `TeachingStrategy` | One agent instructs others | Propagating patterns or constraints across a codebase | Assumes a clear "teacher" agent exists in your template set |
| `RefinementStrategy` | Iterative passes until quality gate passes | Output quality is paramount and latency is acceptable | Can loop; set explicit exit conditions |
| `AdaptiveStrategy` | Strategy is selected at runtime based on task requirements | Unknown or variable workload shapes | Requires `TaskRequirements` to be well-specified |
| `ToolEnhancedStrategy` | Single agent with comprehensive tool access | One-agent tasks that need broad tool reach without multi-agent overhead | Single agent; no composition |
| `PromptCachedSequentialStrategy` | Sequential with a shared cached context (default TTL: 3600 s) | Repeated sequential runs over the same large context (e.g., large codebase scans) | Cache invalidation is time-based, not content-based |
| `DelegationChainStrategy` | Hierarchical delegation up to `max_depth` (default: 3) | Tasks that naturally decompose into sub-tasks with clear ownership | Depth cap enforced; exceeding it raises an error |
| `ConditionalStrategy` | If condition → branch A, else → branch B | Routing based on a single gate (e.g., skip test generation if coverage > 80%) | Binary branching only |
| `MultiConditionalStrategy` | Switch/case across multiple conditions | Multiple routing outcomes from a single decision point | Falls through to `default_branch` if no condition matches |
| `NestedStrategy` / `NestedSequentialStrategy` | Workflows embedded inside workflows | Reusing a registered `WorkflowDefinition` as a step inside a larger pipeline | Nesting depth is capped by `NestingContext.DEFAULT_MAX_DEPTH` |

## Workflow orchestration vs. calling workflows directly

| | Workflow orchestration | Direct workflow call |
|---|---|---|
| **Number of workflows** | Two or more in one pass | Exactly one |
| **Report format** | Single combined report, findings grouped by severity | Workflow-native output |
| **Setup** | Describe what you need; the skill selects and sequences workflows | Call the specific tool (e.g., `doc_orchestrator()`) |
| **Typical time** | Additive (e.g., Security ~2 min + Test Audit ~2 min + Release Prep ~3 min = ~7 min) | Per-workflow time only |
| **Best for** | Pre-release gates, comprehensive reviews, CI chains | Targeted, single-concern analysis |

If you only need one workflow, call it directly. Orchestration adds value when combining two or more passes, not as a general wrapper.

## When to use orchestration

Use the meta-orchestration strategies when:

- Your task requires **multiple agents or analysis passes** whose results must be composed — for example, a Secure Release pipeline that runs `security_audit → dependency_check → release_prep` in sequence.
- You need **conditional routing** at runtime — use `ConditionalStrategy` or `MultiConditionalStrategy` to branch based on quality gates or environment state.
- You want to **reuse registered workflows** as steps inside a larger pipeline — `NestedStrategy` and `NestedSequentialStrategy` let you reference any `WorkflowDefinition` by ID.
- You need **parallel throughput** for independent analyses — `ParallelStrategy` runs agents concurrently when their outputs are not interdependent.
- You have a **repeated large-context workload** — `PromptCachedSequentialStrategy` amortizes context cost across runs within the cache TTL.

Use workflow orchestration (the skill layer) when:

- You want to combine two or more named analysis workflows (Security Audit, Code Review, Deep Review, etc.) and receive a single severity-grouped report.
- You are setting up a **CI gate** (e.g., security + test audit blocking a PR) without writing strategy code.
- You are **onboarding to a module** and want a combined doc audit + code review in one command.

## When not to use orchestration

- **Single workflow, single concern** — call the specific tool directly (e.g., `doc_orchestrator()` for documentation maintenance). Adding a strategy layer for one agent introduces indirection with no benefit.
- **Exploratory or throwaway analysis** — a direct workflow call or a one-off script is faster to set up and easier to discard.
- **Behavior not exposed by the public API** — do not patch strategy internals. Use `register_strategy()` to add a custom `ExecutionStrategy` subclass, or `register_custom_template()` to extend the template registry.
- **Unbounded nesting** — `NestedStrategy` and `DelegationChainStrategy` enforce depth limits. If your design requires deeper nesting, reconsider the pipeline shape rather than raising the cap.

## Decision guide

| Situation | Recommended choice |
|---|---|
| One analysis workflow needed | Call the workflow directly |
| Two or more workflows, want a combined report, no code | Workflow orchestration skill |
| Deterministic multi-stage pipeline with data flow | `SequentialStrategy` or `PromptCachedSequentialStrategy` |
| Independent analyses, speed is priority | `ParallelStrategy` |
| Runtime branching on a condition | `ConditionalStrategy` / `MultiConditionalStrategy` |
| Iterative refinement until quality bar is met | `RefinementStrategy` |
| Reusing an existing workflow as a pipeline step | `NestedStrategy` / `NestedSequentialStrategy` |
| Workload shape is unknown at design time | `AdaptiveStrategy` |
| Single agent needs broad tool access | `ToolEnhancedStrategy` |
| Hierarchical sub-task delegation | `DelegationChainStrategy` (watch `max_depth`) |

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

**Tags:** `orchestration`, `teams`
