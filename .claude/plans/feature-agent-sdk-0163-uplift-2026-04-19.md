# Feature: claude-agent-sdk 0.1.63 Uplift (attune-ai 6.2.0)

**Date:** 2026-04-19
**Owner:** Patrick Roebuck
**Target release:** attune-ai **6.2.0** (minor bump)
**Scope priorities (per user):** quality / capability + developer UX
**Scope repos (per user):** attune-ai + attune-rag + attune-author

**Scope correction from research:** Agent SDK usage is concentrated in
`attune-ai/src/attune/workflows/` and its shim at `agent_sdk_adapter.py`.
`attune-rag` uses a thin `AsyncAnthropic.messages.create` wrapper (not the
Agent SDK) and should stay that way — adding Agent SDK as a provider
regresses the thin-wrapper design. `attune-author` uses `polish.py`
through the Anthropic SDK directly for per-template rewrites — also not
Agent SDK. So the shipped work in this spec is **attune-ai-only**, even
though the user authorized a broader scope. The other siblings get zero
changes for this release.

---

## Brainstorm

### Context

We bumped `claude-agent-sdk` from 0.1.34 to 0.1.63 earlier today (29
patches). A research pass identified five features added in that range
that are unused in our workflows, three of which map to known pain points
already documented as lessons in `.claude/CLAUDE.md`:

1. **Subagent transcript recovery** (`list_subagents`,
   `get_subagent_messages`, since 0.1.60) addresses the exact failure
   mode captured in the "SDK adapter swallows subagent findings" lesson —
   multi-subagent workflows silently lose per-subagent findings when the
   orchestrator's synthesis is terse or it hits the budget/turn cap.
2. **`TaskBudget`** (since 0.1.51) tells the model its remaining token
   budget so it can pace itself and wrap up cleanly. Our current
   `max_budget_usd` just axes the stream with no feedback — the root
   cause of the "ResultMessage(result=None) silent early termination"
   lesson.
3. **`thinking=`/`effort=` config** (since 0.1.36) gives deep-dive
   workflows real extended thinking. We currently use none of it, even
   for `depth="deep"` runs that spend 40+ turns of budget.
4. **`SystemPromptPreset(exclude_dynamic_sections=...)`** (since 0.1.57)
   would let us keep `cwd` out of the cached prefix and pick up
   cross-run prompt cache hits. Latency win, cost-adjacent (user
   deprioritized cost but the UX impact is positive).
5. **Top-level `skills=` option** (since 0.1.62) would expose our own
   plugin skills as first-class tools to the orchestrator. Novel but
   needs design — deferred.

### Problem

Two of today's multi-subagent workflows (`security_audit`,
`code_review`) have already demonstrated the failure modes that items
1 and 2 directly address — lessons 1 ("SDK adapter swallows subagent
findings") and 2 (silent early termination under `max_budget_usd`) are
in `.claude/CLAUDE.md`. Item 3 is a latent capability gap — we pay for
`depth="deep"` runs but don't give the model the thinking budget that
would actually differentiate deep from standard.

### Goals

Land three testable enhancements in attune-ai 6.2.0 that:

- **Recover subagent findings** in `security_audit` and `code_review`
  so the orchestrator's synthesis is no longer a single point of data
  loss.
- **Switch multi-subagent workflows to `TaskBudget`** (alongside — not
  replacing — `max_budget_usd`) so the model paces itself.
- **Wire `effort="high"`** for `depth="deep"` runs so deep-review,
  security-audit, and code-review at deep depth actually engage extended
  thinking.
- **Add `SystemPromptPreset(exclude_dynamic_sections=...)`** to the
  three primary workflow call sites so cross-run prompt cache hits
  work.

Non-goals for 6.2.0:

- Skills-as-tools (`skills=`) — needs design work to pick which skills
  the orchestrator should be allowed to invoke. Deferred to 6.3.0.
- Distributed tracing, session tagging, MCP runtime control,
  `RateLimitEvent` typed messages — user priority axis excludes cost
  and observability-as-dashboard.
- attune-rag provider changes — thin-wrapper design holds.
- attune-author polish changes — uses Anthropic SDK directly, not
  Agent SDK.

### End state

- `agent_sdk_adapter.py` has a new helper `collect_subagent_transcripts(
  session_id)` returning `dict[str, list[AssistantMessage]]` keyed by
  subagent name, callable after an agent run completes.
- `security_audit.py`, `code_review.py`, and `deep_review.py` (if it
  uses multi-subagent) call this helper and either append the richer
  per-subagent findings to the `WorkflowResult`'s `final_output` OR
  attach them under `metadata["subagent_findings"]` (JSON-serializable
  form).
- `ClaudeAgentOptions(..., task_budget=TaskBudget(total=N), thinking=
  ThinkingConfigAdaptive() if depth=="deep" else None,
  system_prompt=SystemPromptPreset(..., exclude_dynamic_sections=[
  "cwd","git_status"]), ...)` in all three workflows.
- attune-ai 6.2.0 CHANGELOG documents the three changes with before/
  after quality notes.
- Tests: each of the three changes has at least one behavioral test
  that mocks the SDK and asserts the expected wiring.
- The "SDK adapter swallows subagent findings" lesson gets a follow-up
  note pointing at the 6.2.0 fix; the "budget-cap silent termination"
  lesson gets the same.

---

## Tasks

<task id="1" name="subagent-transcript-recovery">
  <objective>
    Add `collect_subagent_transcripts(session_id)` helper to
    `agent_sdk_adapter.py` and wire it into `security_audit` and
    `code_review` so per-subagent findings are recovered after the
    orchestrator's stream closes. Addresses the "SDK adapter swallows
    subagent findings" lesson.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/agent_sdk_adapter.py">
      Current `collect_agent_output` captures only top-level
      `AssistantMessage` and `ResultMessage` content. Subagent messages
      are filtered with `parent_tool_use_id is None`, which drops the
      per-subagent chain entirely.
    </existing-code>
    <existing-code path="src/attune/workflows/security_audit.py">
      Spawns 4-5 subagents in parallel via the `Agent` tool. The
      orchestrator's final synthesis is the only place their findings
      appear in `WorkflowResult.final_output`.
    </existing-code>
    <sdk-api>
      `claude_agent_sdk.list_subagents(session_id) -> list[SubagentInfo]`
      and `claude_agent_sdk.get_subagent_messages(session_id, subagent_id)
      -> list[Message]`. Both take the `session_id` already on
      `ResultMessage.session_id`. Available since SDK 0.1.60.
    </sdk-api>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/agent_sdk_adapter.py">
      <change location="end of file">
        AFTER: new public helper
        ```python
        async def collect_subagent_transcripts(
            session_id: str,
        ) -> dict[str, list[str]]:
            """Return per-subagent text transcripts for a completed run.

            Keys are subagent names (e.g. "vulnerability-scanner");
            values are the assistant-text chunks the subagent emitted,
            in order.

            Returns an empty dict and logs at DEBUG when the SDK version
            doesn't expose the helpers or the session is unknown — this
            is a best-effort enrichment, never a hard requirement.
            """
        ```
      </change>
    </file>
    <file path="src/attune/workflows/security_audit.py">
      <change location="after the orchestrator's result is folded in">
        Call `collect_subagent_transcripts(run_result.session_id)` and
        attach the dict under
        `metadata["subagent_transcripts"]`. Also render a condensed
        markdown block at the end of `final_output` under a `##
        Subagent findings` heading (one section per subagent).
      </change>
    </file>
    <file path="src/attune/workflows/code_review.py">
      <change location="mirror of security_audit wiring">
        Same enrichment pattern.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path="tests/unit/workflows/test_subagent_transcripts.py">
      Mocks `claude_agent_sdk.list_subagents` and
      `get_subagent_messages` to return fixed data. Asserts
      `collect_subagent_transcripts` returns the expected dict shape,
      logs DEBUG and returns `{}` on `AttributeError` (older SDK), and
      survives a malformed `list_subagents` response.
    </file>
  </files-to-create>

  <validation>
    <check>`pytest tests/unit/workflows/test_subagent_transcripts.py` — 4 green.</check>
    <check>Run `attune workflow run security-audit --path src/attune/security/` against the live SDK, assert `metadata["subagent_transcripts"]` has ≥3 non-empty entries.</check>
    <check>Grep `WorkflowResult.final_output` output for a `## Subagent findings` heading.</check>
  </validation>

  <risks>
    <risk severity="medium">
      `list_subagents` / `get_subagent_messages` only exist from SDK 0.1.60. Our new floor (`claude-agent-sdk>=0.1.0,<1.0.0`) admits anything back to 0.1.0 — the helper MUST degrade cleanly when the names aren't importable. Guard with `hasattr(claude_agent_sdk, "list_subagents")` inside the helper, return `{}` otherwise.
    </risk>
    <risk severity="low">
      Subagent transcripts can be large. Cap each subagent's appended block at ~2 KB of rendered text in `final_output`; put the full version only under `metadata["subagent_transcripts"]`. Follows the existing `join_context` truncation pattern.
    </risk>
  </risks>
</task>

<task id="2" name="task-budget-plus-thinking">
  <objective>
    Switch `security_audit`, `code_review`, and `rag_code_gen` from
    `max_budget_usd`-only to `TaskBudget(total=N)` + optional
    `ThinkingConfigAdaptive()` for `depth="deep"` runs. Addresses the
    "budget-cap silent early termination" lesson and opens extended
    thinking on the exact axis users pay for when they pick
    `depth="deep"`.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/agent_sdk_adapter.py">
      `get_max_budget_usd(depth)` returns a USD cap keyed by depth. The
      cap axes the stream without signaling remaining budget to the
      model, which is why subagents don't wrap up cleanly when they hit it.
    </existing-code>
    <sdk-api>
      `TaskBudget(total=N)` passed as `task_budget=...` on
      `ClaudeAgentOptions`. The model sees the remaining budget and
      paces itself. `thinking=ThinkingConfigAdaptive()` + `effort="high"`
      engages extended thinking on deep runs.
    </sdk-api>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/agent_sdk_adapter.py">
      <change location="next to get_max_budget_usd">
        Add `get_task_budget(depth: str) -> TaskBudget`. Map `quick=
        20_000`, `standard=80_000`, `deep=200_000` tokens (rough; tune
        after first real run). Keep `get_max_budget_usd` as a safety
        net.
      </change>
    </file>
    <file path="src/attune/workflows/security_audit.py">
      <change location="ClaudeAgentOptions(...) constructor">
        Add `task_budget=get_task_budget(depth)` and, when `depth ==
        "deep"`, `thinking=ThinkingConfigAdaptive()` + `effort="high"`.
      </change>
    </file>
    <file path="src/attune/workflows/code_review.py">
      <change location="ClaudeAgentOptions(...) constructor">
        Same wiring.
      </change>
    </file>
    <file path="src/attune/workflows/rag_code_gen.py">
      <change location="_run_agent_generate's ClaudeAgentOptions">
        Same wiring. `rag_code_gen` is a single-agent workflow so
        `thinking=` matters less, but `task_budget` is still the right
        primitive.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path="tests/unit/workflows/test_task_budget_wiring.py">
      Mocks `claude_agent_sdk.ClaudeAgentOptions` to capture kwargs.
      Asserts each of the three workflows passes `task_budget` and,
      for deep runs, `thinking` + `effort`.
    </file>
  </files-to-create>

  <validation>
    <check>`pytest tests/unit/workflows/test_task_budget_wiring.py` — green.</check>
    <check>Run `security-audit --depth deep --path src/attune/security/` with the live SDK, confirm no `result=None` silent termination on a normally-long run.</check>
    <check>Spot-check one deep run's `ResultMessage.usage.thinking_tokens` to confirm thinking was actually engaged.</check>
  </validation>

  <risks>
    <risk severity="medium">
      The initial per-depth budgets are rough. Real data from the first
      production run may warrant retuning. Ship conservative upper
      bounds so we don't over-spend; document `get_task_budget`'s
      defaults in a docstring + CHANGELOG so future tuning is easy.
    </risk>
    <risk severity="low">
      `ThinkingConfigAdaptive` availability depends on the model. Gate
      with a depth=="deep" check so cheap/standard runs don't pay for
      thinking they didn't ask for.
    </risk>
  </risks>
</task>

<task id="3" name="exclude-dynamic-sections-for-cache-hits">
  <objective>
    Switch the three workflow call sites from inline `system_prompt=`
    strings to `SystemPromptPreset` that excludes `cwd` and
    `git_status` from the cached prefix. Enables cross-run prompt
    cache hits when the same workflow runs against different
    directories or git states.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/security_audit.py">
      Passes `cwd=resolved_path` alongside a static `system_prompt`
      string. Because `cwd` is dynamic per run, the effective cached
      prefix changes every invocation on a different path — no cache
      reuse.
    </existing-code>
    <sdk-api>
      `SystemPromptPreset(preset="...", exclude_dynamic_sections=[
      "cwd", "git_status"])` on `ClaudeAgentOptions`. Available since
      0.1.57.
    </sdk-api>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/security_audit.py">
      <change location="system_prompt argument construction">
        BEFORE: `system_prompt=_SYSTEM_PROMPT`
        AFTER: `system_prompt=SystemPromptPreset(preset=_SYSTEM_PROMPT, exclude_dynamic_sections=["cwd", "git_status"])`
      </change>
    </file>
    <file path="src/attune/workflows/code_review.py">
      <change location="system_prompt argument construction">
        Same.
      </change>
    </file>
    <file path="src/attune/workflows/rag_code_gen.py">
      <change location="_run_agent_generate system_prompt">
        Same.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>All existing workflow tests still green (no behavioral change expected).</check>
    <check>Run the same workflow twice on different paths in succession; check Anthropic console or `ResultMessage.usage.cache_read_input_tokens` to confirm the second run has a cache hit on the prefix.</check>
  </validation>

  <risks>
    <risk severity="low">
      `SystemPromptPreset` accepts either a preset name or a raw string. Double-check the API shape with `help(SystemPromptPreset)` before shipping; if it only accepts preset names, we need a minor adaptation (pass the raw string via a supported field or skip this task).
    </risk>
  </risks>
</task>

---

## Post-implementation note — Task #3 dropped

During implementation we discovered the research report got the
`SystemPromptPreset` API wrong. Actual shape (from
`claude_agent_sdk.types.SystemPromptPreset.__annotations__`):

```
{"type": Literal["preset"], "preset": Literal["claude_code"],
 "append": NotRequired[str], "exclude_dynamic_sections": NotRequired[bool]}
```

Two blockers make Task #3 inapplicable to our call pattern:

1. `preset` only accepts the literal ``"claude_code"`` — it's a
   wrapper around Claude Code's built-in preset, not a vehicle for
   our custom ``_SYSTEM_PROMPT`` strings.
2. ``exclude_dynamic_sections`` is a **bool**, not a list of
   section names — an all-or-nothing toggle for the preset's
   dynamic sections.

Our workflows already pass static string constants to
``ClaudeAgentOptions(system_prompt=...)`` and ``cwd=`` is a
tool-execution config field (not text injected into the system
prompt), so there's no cache problem to fix here. Task #3 is
dropped from the 6.2.0 scope. Tasks #1 and #2 ship as designed.

## Release packaging

- **attune-ai 6.2.0**: ships tasks 1 + 2 + 3. Minor bump because of the
  new `metadata["subagent_transcripts"]` field and visible
  `final_output` change — material quality improvement.
- **attune-rag**: no changes.
- **attune-author**: no changes.

CHANGELOG entry should cite each lesson the change closes, with links
to the lesson text in `.claude/CLAUDE.md` for future readers.

---

## Explicitly out of scope (deferred)

- **Skills-as-tools (`skills=`)** — needs design work to pick which
  plugin skills the orchestrator is allowed to invoke. Revisit in 6.3.0.
- **Cost / observability features** (distributed tracing, rate-limit
  events, session tagging) — user priority axis excludes these.
- **attune-rag ClaudeProvider migration to Agent SDK** — would regress
  the thin-wrapper design with no clear benefit.
- **attune-author polish migration to Agent SDK** — polish is a
  single-turn rewrite, Agent SDK's multi-turn machinery doesn't apply.

---

## Timeline

- Day 1: tasks 1 + 2 implemented + unit tests.
- Day 2: task 3 + live-run verification + CHANGELOG + release.

Total: ~1-2 dev-days. Shippable in a single release cycle.
