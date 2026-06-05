# Decisions: Bulletin Curator

> Records design decisions and deviations made during
> implementation. Companion to [`design.md`](design.md) and
> [`tasks.md`](tasks.md).

**Status:** in progress
**Last updated:** 2026-06-05

---

## Phase 2 — Agent invocation (2026-06-05)

### D1 — Forced tool-use uses the raw `anthropic` SDK, not `claude_agent_sdk`

`design.md` "Agent invocation" sketched the forced-tool-use call as
`ClaudeAgentOptions(model=..., tools=[{...schema...}], tool_choice={...})`.
Introspecting `claude_agent_sdk` 0.1.63 showed that shape is not
supported:

- `ClaudeAgentOptions` has **no `tool_choice` field**.
- Its `tools` field is `list[str] | ToolsPreset | None` — an allowlist
  of tool *names*, not raw Anthropic tool definitions with schemas.

The agent SDK routes through the `claude` CLI's own tool loop and
can't force a single guaranteed-schema call. The curator is a single
synthesis call (no subagents, no agent loop, no file tools), so the
right fit is the **raw `anthropic` SDK with forced `tool_choice`** —
the canonical CLAUDE.md lesson "Forced Anthropic tool-use is the
cleanest path to guaranteed-schema JSON," the same pattern
`attune_rag`'s `FaithfulnessJudge` uses. Implemented in
`src/attune/curator/core.py::_query_opus`.

This is the "research subagents confabulate SDK signatures —
introspect before coding" lesson in action: a one-minute
`dataclasses.fields()` check caught a design assumption that would
otherwise have produced non-working code.

### D2 — Model is `claude-opus-4-6`, not `claude-opus-4-7`

`design.md` named `claude-opus-4-7`. That model id never existed in
this codebase — the standard Opus here is `claude-opus-4-6` (27 source
references, `cost_tracker.BASELINE_MODEL`, and the only Opus-4 priced
in `MODEL_REGISTRY`). The curator uses `claude-opus-4-6` so cost
computation resolves against real pricing. The model is a module
constant (`_CURATOR_MODEL`) and a `run_curator(model=...)` override, so
bumping it later is a one-line change.

### D3 — `max_budget_usd` is advisory in v1

`design.md` relied on `claude_agent_sdk`'s built-in `max_budget_usd`
hard cap. The raw `anthropic` SDK has no equivalent. A single call's
cost is naturally bounded (source readers cap at ≤50 rows × ≤500 chars
each; output capped at 4096 tokens), so v1 keeps `max_budget_usd` in
the signature and **logs a warning** when the realized cost exceeds it
rather than aborting mid-call. A hard pre-flight estimate-and-skip can
land later if Phase 4 live runs show the cost drifting high.

### D4 — Source validation drops an item if *any* cited id is unknown

`design.md` says drop items whose `sources` reference unknown ids.
Implemented strictly: an item survives only if **every** id in its
`sources` resolves to a real `SourceItem` from the inputs. Strictness
is the faithfulness lever — a partially-fabricated citation is still a
fabrication. Drops are logged at WARNING.
