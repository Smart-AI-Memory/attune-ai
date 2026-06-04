# Tasks: Agent Surface Rebalance

**Status**: retired (2026-05-12, see [decisions.md](decisions.md)) —
Phase 0 + skills survey both invalidated the premise; no clean
candidates exist.

---

## Phase 0 — measure

1. **Baseline token cost.** Run `attune workflow run
   security-audit --path src/attune/security` in an isolated
   session and capture: (a) final main-context token count
   from the SDK's usage telemetry, (b) total intermediate
   `AssistantMessage` text bytes emitted to the parent stream.
   Repeat for `refactor-plan` against the same target. Record
   both in a new `docs/specs/agent-surface-rebalance/baseline
   .md` so the after-shot has something to compare against.

2. **Decide the first conversion target.** Of the candidates
   in requirements, pick the one with the highest
   intermediate-bytes-to-summary-bytes ratio — that's where
   the SDK isolation pattern pays off most. Document the pick
   and the ratio in `decisions.md`.

## Phase 1 — analyzer-base template

3. **Author `plugin/agents/analyzer-base.md`.** Conventions:
   read-only `allowed-tools` (Read, Grep, Glob, Bash for
   read-only commands only — no Edit/Write); budget cap
   default; the summary-schema requirement (every analyzer
   subagent MUST return a final structured summary, not just
   a wall of text); examples of good and bad final messages.
   Length target: under 100 lines. No prescribed prompt — each
   analyzer writes its own; this file is the convention doc.

4. **Add a test that asserts every agent under
   `plugin/agents/` either is `setup-guide.md` (the one-shot
   exception) OR conforms to the analyzer convention (has the
   required frontmatter fields documented in
   analyzer-base.md).** Lives in
   `tests/unit/plugins/test_plugin_agent_conventions.py`.

## Phase 2 — first conversion

5. **Create the first analyzer subagent.** Name per the Phase
   0 pick. Location:
   `plugin/agents/<analyzer-name>.md`. Tool set per
   analyzer-base.md. The subagent's prompt embeds whatever
   was previously in the skill's "do the analysis" middle
   section.

6. **Rewrite the matching skill in `plugin/skills/<name>/SKILL
   .md`** so its instruction to the main agent becomes:
   "Launch the `<analyzer-name>` subagent via the Agent tool
   with the user's scope as the prompt. When it returns, read
   its structured summary and present it to the user verbatim,
   then ask if they want to drill into any finding." The skill
   becomes thin — the analysis logic moved into the subagent.

7. **Add a test that the skill's prompt actually mentions the
   Agent tool and the subagent name.** Same plugin-validation
   pattern as `test_plugin_reference_validation.py`. Catches
   skill-vs-agent drift.

## Phase 3 — measure again, decide on next conversion

8. **After-shot measurement.** Re-run the Phase 0 baseline
   commands against the converted skill. Record in `baseline
   .md` with a delta column. Acceptance: main-context token
   count drops by at least 50%, with no degradation in the
   user-facing summary's actionability (judge by manual read,
   not a metric — include both reports in the doc).

9. **Stop or proceed.** If the measurement clears the
   threshold, repeat Phases 2–3 for the next candidate
   (probably `refactor-plan` if security-audit went first, or
   vice versa). If it doesn't, write a `decisions.md` entry
   explaining what blocked the protection (the SDK is doing
   something different from what we modeled, or the
   intermediate stream was already small) and pause the spec.

## Phase 4 — close

10. **Document the conventions in `docs/CODING_STANDARDS.md`**
    (or a new `docs/PLUGIN_AGENTS.md` if it ends up too long
    for a section): when to write a skill vs an agent, the
    summary-schema rule, the budget-cap defaults.

11. **CHANGELOG entry + spec status → complete.**

---

## Out of band

- Watch for the SDK budget cap interacting with the
  conversion (per the corrected "subagent findings" lesson in
  CLAUDE.md). If the analyzer subagent silently truncates at
  cap, the summary will be missing context — bump
  `max_budget_usd` per analyzer based on Phase 0 measurement.

- Do not refactor MCP tool wiring as part of this spec. The
  MCP tools are the existing public API; they remain unchanged
  whether or not the skill internally delegates to a subagent.
