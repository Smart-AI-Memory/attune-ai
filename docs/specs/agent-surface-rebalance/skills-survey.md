# Non-analytical skills survey

**Status**: complete
**Created**: 2026-05-12
**Purpose**: Validate D2 reframing #1 from
[decisions.md](decisions.md) — find any plugin skill that
runs analysis in the main agent's context (not via MCP) and
would therefore actually benefit from subagent delegation.

## Method

Read every `plugin/skills/<name>/SKILL.md` for the 10 non-
analytical skills (security-audit, refactor-plan, bug-predict,
smart-test, code-quality are excluded — they're the original
candidates and were ruled out in Phase 0). Classify each by
where the work happens:

- **(A) MCP/CLI-isolated** — skill dispatches to an MCP tool
  or CLI workflow. The work runs in a separate SDK/process
  and only the final result returns to the main agent. **No
  benefit from subagent conversion.**
- **(B) Main-agent-driven** — skill instructs the main agent
  to do the work itself (read files, run commands, edit code,
  reason). The intermediate bytes accumulate in the main
  agent's context. **Potential candidate.**
- **(C) Routing/conversation** — skill is a thin chooser that
  routes to other skills, or a pure dialog/picker. No heavy
  lifting. **Not a candidate.**

## Results

| Skill | LOC | Class | Notes |
|-------|----:|:-----:|-------|
| [attune-hub](../../../plugin/skills/attune-hub/SKILL.md) | 90 | C | Pure router. `AskUserQuestion` + table of triggers → other skills. |
| [coach](../../../plugin/skills/coach/SKILL.md) | 226 | A | All paths dispatch to MCP (`help_lookup`, `help_init`, `help_update`, `help_status`, `help_maintain`). |
| [doc-gen](../../../plugin/skills/doc-gen/SKILL.md) | 98 | A | Dispatches to `doc_gen` / `doc_audit` / `doc_orchestrator` MCP tools. |
| [fix-test](../../../plugin/skills/fix-test/SKILL.md) | 85 | **B** | Runs pytest in main agent, parses output, Edits code, re-runs — up to 3 iterations. Loop accumulates in main context. |
| [memory-and-context](../../../plugin/skills/memory-and-context/SKILL.md) | 326 | A | Dispatches to memory_*, context_*, attune_* MCP tools. Long doc but no main-agent work. |
| [planning](../../../plugin/skills/planning/SKILL.md) | 57 | B | Uses `EnterPlanMode` + optional `research_synthesis` MCP. Plan creation IS the conversation — lightweight, not really heavy analysis. |
| [rag-code-gen](../../../plugin/skills/rag-code-gen/SKILL.md) | 84 | A | Calls `attune workflow run rag-code-gen` CLI; workflow runs in its own session. |
| [release-prep](../../../plugin/skills/release-prep/SKILL.md) | 119 | A | Dispatches to `release_prep`/`health_check`/`dependency_check`/`secure_release` MCP tools. |
| [spec](../../../plugin/skills/spec/SKILL.md) | 193 | B | Stage 4 "Execute" runs implementation tasks in main agent. But the per-stage approval IS the product — can't isolate without breaking UX. |
| [workflow-orchestration](../../../plugin/skills/workflow-orchestration/SKILL.md) | 99 | A | Dispatches to all the analytical workflows' MCP tools. |

**Tally**: 7 × (A), 1 × (C), 3 × (B).

## The three (B) candidates, examined

### fix-test — only viable candidate, but wrong shape for this spec

What the main agent currently does:

1. `Bash`: `uv run pytest <target> -v --tb=short` (~40 lines of output)
2. Reason about the failure type (~5-10 sentences)
3. `Edit` the broken file (~10-30 lines of context kept)
4. `Bash`: re-run pytest (~40 lines)
5. If still failing, repeat from step 2, up to 3 attempts

Worst case 3 iterations: ~120 lines of pytest output + 3 rounds
of reasoning + 3 file edits all in the main context. This is
genuine intermediate-byte accumulation — exactly the pattern
the original spec premise described.

**But fix-test is the wrong shape for `analyzer-base.md`:**

The original spec proposed read-only analyzers (Read, Grep,
Glob, Bash-readonly). fix-test needs `Edit`, `Write`, and
`Bash` (running pytest, which can have side effects). It's not
an analyzer — it's a **remediator**. Different convention
required.

A real spec for converting fix-test would need to address:

- Trust model: do you trust a subagent to Edit files in your
  repo without seeing each diff first?
- Bash side effects: does the subagent run pytest with full
  permission, or only against a quarantined subdirectory?
- Failure mode: when the subagent gives up after 3 attempts,
  what does it return to the parent? The full pytest stderr,
  or a summary?
- User control: the current fix-test asks the user nothing
  during the loop. A subagent version could surface less
  information to the parent, which is the entire point —
  but also less opportunity to intervene.

This is a meaningfully different spec. **Recommend filing
separately as "remediation-agent pattern" if pursued; do not
graft onto Agent Surface Rebalance.**

### planning — too lightweight to bother

The planning skill is conversational by design. `EnterPlanMode`
already creates a built-in Claude Code isolation boundary
(plans are user-approved before any implementation). Optional
`research_synthesis` MCP call provides the only heavy lifting,
and it's already MCP-isolated.

Converting planning to a subagent would lose the user-visible
plan iteration that's the entire UX of the skill.

**Not a candidate.**

### spec — UX is the product, can't isolate

Spec is the most complex skill (193 lines). Stage 4 "Execute"
runs implementation tasks in the main agent, which IS
intermediate-byte accumulation — but the user explicitly
wants to see each task implemented, approve it, and decide
whether to continue. That's not byte bloat; it's the entire
purpose of spec-driven development.

A subagent variant of spec where the subagent silently
executes tasks and returns "done" would be functionally
equivalent to autonomous coding, which is a different product.

**Not a candidate.**

## Conclusion

**Zero clean candidates exist for the Agent Surface Rebalance
spec as currently framed.** The only meaningfully main-agent-
driven skill (fix-test) is a remediator, not an analyzer, and
fits a different (hypothetical) spec.

### Recommendation: retire this spec

Update the spec status from `paused` to `retired` with a
pointer to this survey. The work product to keep:

- [scripts/phase0/measure.py](../../../scripts/phase0/measure.py)
  — measurement harness, reusable for any future SDK-byte
  question.
- [baseline.md](baseline.md) + [decisions.md](decisions.md) —
  document the (mis-)premise and the data that invalidated it.
- This survey — documents that no clean candidate exists, so
  the spec doesn't reanimate in a future session on the same
  bad mental model.

### Possible follow-up specs (not endorsed; just naming them)

1. **Remediation-agent pattern** — if fix-test's loop is felt
   to be a problem, a focused spec on whether a subagent
   variant would actually win, with explicit handling of the
   trust/Bash/Edit concerns. **Don't pre-commit to this — it
   may not be worth doing.**
2. **MCP result size reduction** — security-audit returns
   3,710 bytes including 19.66 KB of embedded subagent
   transcripts. A "summary-only" MCP variant + an on-demand
   transcript fetch would shrink the main-context cost by
   ~80%. But this is a workflow-layer change, not a
   plugin/agents change.
3. **`plugin/agents/` convention doc when a real need arises**
   — analyzer-base.md was proposed; with zero analytical
   candidates that would benefit, there's no current consumer.
   Defer until one materializes.
