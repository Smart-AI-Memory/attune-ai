---
name: discovery-sweep
description: "Run every audit at once and triage the findings into act-now / needs-a-look / dismissed buckets. Triggers on: run all audits, full sweep, audit everything, what should I fix, triage findings, discovery sweep, sweep the codebase."
argument-hint: "<path or directory to sweep>"
---

# Discovery Sweep

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="discovery-sweep", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then tell
the user they can say "tell me more" for a step-by-step guide, or
answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Discovery Sweep** — Fans out across every audit source
> (pattern scan, bug-predict, security, dependencies, performance,
> docs, tests), dedups overlapping findings, and triages everything
> into three buckets so you know what to fix first.

This is the aggregate "what should I fix?" pass. For a single
focused audit, use the dedicated skill instead — `security-audit`,
`bug-predict`, `code-quality`, or `deep-review`.

## Scoping

Before running, ask:

1. **Target path**: "Which files or directory should I sweep?"
   Default to `src/` if not specified.
2. **Speed vs. depth**: "Fast pattern-only sweep, or include the
   LLM-backed sources?" (LLM sources cost budget; pattern-only is
   free and quick.)
3. **Budget**: only if including LLM sources — "Spend cap? Default
   is $10.00."

## Execution

Call the `discovery_sweep` MCP tool with the scoped path:

```
discovery_sweep(path="<user-specified path>")
```

Optional knobs:

```
discovery_sweep(path="src/", no_llm=true)          # fast, free
discovery_sweep(path="src/", budget_usd=5.0)       # cap LLM spend
```

Or via CLI:

```bash
uv run attune workflow run discovery-sweep --path <target>
```

## Output

The tool returns three buckets. Present each as its own section:

- **Queue** — findings that auto-routed to "act on these now."
  Render as a markdown table grouped by severity (critical first)
  with clickable file links.
- **Questions** — findings the engine could not auto-route (missing
  location, low confidence, severity conflict, or a source that
  crashed). Show each finding's `reason` and `next_step`.
- **Rejected** — findings filtered out by a deterministic rule
  (below threshold, duplicate of another source). Summarize the
  count; expand only if the user asks.

Close with the run metadata: spend vs. budget, sources that ran,
any source failures, and duration.
