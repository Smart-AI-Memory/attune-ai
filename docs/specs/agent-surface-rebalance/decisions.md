# Decisions

**Status**: phase 0 complete + skills survey complete; **spec retired**
**Decided**: 2026-05-12

---

## D1 — Pick the first conversion target

**Decision**: deferred — see D2.

**Rationale**: the metric the spec asked us to optimize (main-
context byte savings from isolating intermediate orchestrator
text) has a value of zero for both candidates, because both
candidates are already isolated. See D2.

---

## D2 — Retire the spec; the premise is wrong for the candidates

**Decision**: **retire Agent Surface Rebalance**. The premise
fails for the original three candidates (Phase 0 measurement
in this section) AND for all 10 non-analytical skills (the
skills survey in D4). No reframing is endorsed; if a future
need surfaces (e.g. fix-test's remediation loop), it earns
its own spec from scratch.

**What we found in Phase 0**

1. Both `security-audit` and `refactor-plan` are SDK-native
   workflows invoked through MCP tools (`security_audit(...)`
   and `refactor_plan(...)` respectively — verified in
   `plugin/skills/security-audit/SKILL.md:32-36` and
   `plugin/skills/refactor-plan/SKILL.md:36-40`).

2. MCP tool invocations run their workflow inside an
   **isolated SDK session**. The intermediate
   `AssistantMessage` bytes the orchestrator emits
   (6,821 B for security-audit, 4,914 B for refactor-plan)
   never reach the main Claude Code agent's context. Only
   `WorkflowResult.final_output` crosses the workflow ↔
   caller boundary.

3. The actual byte count delivered to the main agent is
   `final_output_bytes`: **3,710 B for security-audit**,
   **486 B for refactor-plan**. Both well under the size
   that triggers context-window pressure.

4. The 12.8x and 10.1x "intermediate-to-summary" ratios we
   measured are real, but they describe **bytes inside the
   isolated SDK session**, not bytes in the parent agent
   context. The spec premise conflated the two.

**What this means for the spec as written**

The requirements doc claims:

> intermediate output bloats the main agent's context window
> unnecessarily. All the intermediate exploration text stays
> in the main agent's context and pushes load-bearing earlier
> content toward the compact threshold.

This is **false** for SDK-native workflows accessed via MCP.
The intermediate exploration stays in the workflow's SDK
session and is discarded when the MCP tool returns.

Converting `security-audit` or `refactor-plan` from "skill
calls MCP tool" to "skill instructs main agent to spawn a
subagent that calls the workflow" would:

- add a level of indirection (Agent tool call wraps MCP tool
  call), and
- save zero bytes in main-agent context, because the MCP tool
  already only returns `final_output`.

**Could it still be valuable somewhere?**

Possibly, but not for these candidates. Three reframings to
consider before retiring the spec:

1. **Skills that don't use MCP** — if any plugin/skills/
   skills instruct the main agent to perform analysis
   directly (rather than dispatching to an MCP workflow),
   their byte cost lands in the main context. None of
   security-audit / refactor-plan / bug-predict / smart-test
   /smart code-quality fit this pattern (all use MCP). Survey
   the remaining 10 skills (attune-hub, coach, doc-gen,
   fix-test, memory-and-context, planning, rag-code-gen,
   release-prep, spec, workflow-orchestration) to find any
   that ARE main-agent-driven. If 1-2 candidates surface, a
   new, narrower spec can frame their conversion correctly.

2. **Reducing `final_output` size** — security-audit's 3,710
   bytes is dominated by 19.66 KB of embedded subagent
   transcripts (rendered via
   `format_subagent_transcripts_markdown`). A summary-only
   variant of the MCP tool (with the full transcripts
   available via a follow-up call) would shrink the parent-
   context cost by ~80%. But this is a workflow change, not
   a subagent-conversion change — different spec entirely.

3. **`plugin/agents/analyzer-base.md` as a standalone
   convention** — the spec also proposed an analyzer-base
   template for future analytical agents. This has value
   independently of the conversion work, but is not load-
   bearing without a real consumer. Land it only when at
   least one analyzer agent actually needs it.

**Next action**

- Set `requirements.md` and `tasks.md` status to `retired`.
- Keep `runs/`, `baseline.md`, `skills-survey.md`, and the
  measurement harness in place — they're cheap to retain and
  will be useful if a related question comes up (e.g.
  measuring real bytes in a skill that DOESN'T isolate, or
  the remediation-agent idea ever gets drafted).

---

## D3 — Budget cap default in the harness

**Decision**: the harness defaults to `depth=standard`. The
quick depth's $2 cap is functionally unusable for multi-
subagent workflows even on the smallest possible target.
Future Phase 0 measurements in this spec (if reactivated)
should default to standard with `ATTUNE_MAX_BUDGET_USD=0` to
avoid mid-run cuts.

**Cost note**: the two completed runs cost $5.03 + $3.75 =
$8.78 of real API usage. Cheaper than guessing wrong by
implementing a conversion that saves zero bytes.

---

## D4 — Skills survey closes the loop; recommend retire

**Decision**: per [skills-survey.md](skills-survey.md), of the
10 non-analytical skills, **zero are clean candidates** for
this spec's pattern.

- 7 already dispatch via MCP/CLI (isolated).
- 1 is a pure router (no analysis).
- 3 are main-agent-driven but each fails the spec fit for a
  different reason: fix-test is a remediator (wrong tool
  permissions); planning is conversational by design; spec's
  per-task approval IS the product.

**Recommend retiring the spec** rather than leaving it paused.
The next reframing that might be worth pursuing
("remediation-agent pattern" for fix-test) is a different spec
shape entirely and should be drafted from scratch if/when
appetite for it surfaces.

**Workproduct to retain**:
- [scripts/phase0/measure.py](../../../scripts/phase0/measure.py)
  — reusable harness
- [baseline.md](baseline.md) + measurement run artifacts
- [skills-survey.md](skills-survey.md) — closes the door so
  a future session doesn't reanimate the spec on the same
  bad mental model
