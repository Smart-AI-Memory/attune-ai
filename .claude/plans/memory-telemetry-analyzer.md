# Memory Telemetry Analyzer

**Created:** 2026-07-08
**Status:** EXECUTED 2026-07-08 — all 5 tasks landed, verified live
**Owner:** Patrick + agent

**Execution note:** Task 4 ships the benefit signal as counts (rule
surfacings, distinct rules, top rules) captioned as an upper bound —
never a savings percentage. A module constant
(`INTERVENTION_SIGNAL_CAPTION`) is asserted verbatim by a test so the
discredited "memory saves X%" framing cannot creep back in.

---

## Context

PR #1279 (shipped 10.1.0) added a self-measuring producer for the
short-term memory hooks: [`_memory_telemetry.py`](../../plugin/hooks/_memory_telemetry.py)
appends one JSON line per hook fire to
`~/.attune/telemetry/memory_events.jsonl`. As of 2026-07-08 the live
file holds **162 events across 99 sessions** (~24k est_tokens
injected): 128 `session_recall`, 28 `jit_recall`, 6 `session_stash`.

The producer is healthy and wired into all three hooks. **Nothing
reads the file.** The recalled finding that motivated this work —
"the Redis short-term memory layer had no telemetry for its
token/cost impact, requiring counterfactual modeling instead of
measurement" — is only half-closed: we now *record* impact but
still can't *report* it.

Event shapes (confirmed from live data):

- `session_recall` — `entries`, `injected_chars`, `est_tokens`
- `jit_recall` — `tool`, `rules[]`, `injected_chars`, `est_tokens`
- `session_stash` — `findings`, `written`, `extractor`,
  `injected_chars`, `est_tokens`

---

## Problem

Memory injection is a real, measurable **cost** (tokens added to
context every session) with an unmeasured **benefit** (failures
avoided by surfacing the right rule/finding). Today neither side is
visible: no CLI, no MCP field, no dashboard tile reads
`memory_events.jsonl`.

A load-bearing constraint governs this work. The first
`session_savings` A/B run (2026-07-06) showed **+28% cost/task** on
one-shot tasks — directly contradicting the informal "memory saves
8%" claim (see `memory_cost_claim_grounding.md`). Therefore:

> The analyzer reports **cost as measured fact** and **benefit as a
> clearly-labeled, method-exposed, low-confidence estimate** — never
> as a settled savings number. A defensible savings figure needs a
> continuity/trap task set with repeats ≥3, which this data does not
> contain.

---

## Goals

1. A reader that turns `memory_events.jsonl` into cost aggregates
   (per event type / per session / per day), reusing the existing
   `usage.jsonl` reader pattern in `ops/data.py`.
2. Surface the numbers two ways: a `memory` section in the
   `telemetry_stats` MCP tool, and a row-group on the ops Telemetry
   dashboard tab.
3. A **labeled** benefit-inference estimate derived from
   `jit_recall` rule surfacings — shipped after cost, gated behind
   its own honesty caption, never blocking the cost report.
4. Regression protection against the two documented telemetry-reader
   traps: the `ts` vs `timestamp` field bug and test-pollution of
   the real `~/.attune` JSONL.

---

## End State

`attune`'s telemetry MCP tool and the ops dashboard both answer
"what does short-term memory cost me?" from real logged data, and
offer a captioned "estimated intervention signal" alongside it that
is honest about being an upper-bound heuristic, not a savings claim.

---

## Decisions (record in decisions.md on execute)

- **Measurement scope:** cost (measured) + benefit (labeled
  estimate). Patrick chose benefit inference over cost-only
  2026-07-08; honesty guardrail above is the binding constraint.
- **Surfaces:** MCP tool + dashboard tile (both).
- **Home:** reader extends `ops/data.py` rather than a new module —
  it already owns telemetry reading and the dashboard imports from
  it.

---

## Tasks

Below are self-contained XML task specs for implementation. Tasks
1–3 + 5 deliver the honest cost report and can ship without Task 4;
Task 4 (benefit estimate) is additive and last.

<task id="1" name="memory-events-reader">
  <objective>
    Add read_memory_summary() to ops/data.py: parse
    memory_events.jsonl into cost aggregates grouped by event type,
    session, and day. Pure function, never raises on malformed lines.
  </objective>
  <context>
    <existing-code path="src/attune/ops/data.py">
      read_telemetry_summary() already parses usage.jsonl and buckets
      by_day. Mirror its shape, error tolerance, and return-dict
      style. CRITICAL: memory events use the field "ts" (not
      "timestamp") — read event.get("ts") or event.get("timestamp").
    </existing-code>
    <existing-code path="plugin/hooks/_memory_telemetry.py">
      Canonical event schema: v, ts, event, session_id,
      injected_chars, est_tokens, plus per-event fields (entries /
      tool+rules / findings+written+extractor).
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/ops/data.py">
      <change location="new function read_memory_summary(path=None)">
        Returns dict: {
          "total_events": int, "total_est_tokens": int,
          "distinct_sessions": int,
          "by_event": {event: {"n": int, "est_tokens": int}},
          "by_day": {YYYY-MM-DD: {"n": int, "est_tokens": int}},
          "per_session_avg_tokens": float,
        }. Skip unparseable lines silently. Missing file → zeroed
        summary, not an exception.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>read_memory_summary on a 3-line fixture returns
    total_events==3 and correct est_tokens sum</check>
    <check>reads "ts" field: an event with only "ts" buckets into
    by_day correctly (regression vs the timestamp bug)</check>
    <check>missing file returns a zeroed dict, raises nothing</check>
  </validation>
  <risks>
    <risk severity="medium">The ts-vs-timestamp trap already shipped
    once (Home KPIs read 0). The by_day check above is the guard.</risk>
  </risks>
</task>

<task id="2" name="telemetry-stats-mcp-memory-section">
  <objective>
    Extend the telemetry_stats MCP tool to include a "memory"
    section sourced from read_memory_summary().
  </objective>
  <context>
    <existing-code path="src/attune/mcp/tool_schemas.py">
      telemetry_stats schema lives here; verify the handler location
      via grep -rn "telemetry_stats" src/attune/mcp/.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/mcp/(telemetry_stats handler)">
      <change location="handler result assembly">
        Add result["memory"] = read_memory_summary(). Keep existing
        usage stats untouched — additive only.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>calling telemetry_stats returns a "memory" key with
    by_event and total_est_tokens</check>
    <check>tool count / schema tests still pass (additive field, no
    new tool)</check>
  </validation>
  <risks>
    <risk severity="low">Handler location differs from schema file;
    grep before editing.</risk>
  </risks>
</task>

<task id="3" name="dashboard-memory-rowgroup">
  <objective>
    Add a "Short-term memory" row-group to the ops Telemetry tab
    rendering read_memory_summary(): total tokens injected, per-event
    breakdown, per-session average.
  </objective>
  <context>
    <existing-code path="src/attune/ops/templates/telemetry.html">
      Existing per-workflow rollup table is the styling template to
      match. Data flows through ops/routes/dashboard.py.
    </existing-code>
    <existing-code path="src/attune/ops/routes/dashboard.py">
      Telemetry route builds the context dict; add memory_summary to
      it from read_memory_summary().
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/ops/routes/dashboard.py">
      <change location="telemetry route context">
        context["memory_summary"] = read_memory_summary()
      </change>
    </file>
    <file path="src/attune/ops/templates/telemetry.html">
      <change location="after the per-workflow rollup">
        New section rendering by_event rows + totals. Empty state:
        "No memory events yet" when total_events == 0.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>dashboard Telemetry tab renders the memory section with
    live totals (verify via preview_start + preview_snapshot)</check>
    <check>empty-file case renders the empty-state string, not a
    crash</check>
  </validation>
  <risks>
    <risk severity="low">Template context wiring; verify against the
    running worktree dashboard (already up on :8765).</risk>
  </risks>
</task>

<task id="4" name="benefit-inference-labeled-estimate">
  <objective>
    Add estimate_intervention_signal() deriving a LABELED,
    low-confidence benefit signal from jit_recall rule surfacings —
    NOT a savings claim. Surface it captioned in both surfaces.
  </objective>
  <context>
    <existing-code path="plugin/hooks/_memory_telemetry.py">
      jit_recall events carry tool + rules[]. The producer docstring
      notes these enable "rule surfaced at T → did the matching
      failure occur after" correlation. memory_events.jsonl alone has
      NO failure log, so the honest estimate is an UPPER BOUND:
      count distinct (rule, tool) surfacings as potential
      interventions, not confirmed prevented failures.
    </existing-code>
    <context-note>
      Binding constraint from memory_cost_claim_grounding.md: output
      must be captioned as an estimate with its method stated inline
      ("N rule surfacings that MAY have prevented a failure; upper
      bound, not measured savings"). No cost-savings percentage.
    </context-note>
  </context>
  <files-to-modify>
    <file path="src/attune/ops/data.py">
      <change location="new function estimate_intervention_signal(path=None)">
        Returns {"rule_surfacings": int, "distinct_rules": int,
        "top_rules": [(rule, count)...], "caption": "<honesty
        string>"}. Cost report never depends on this.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>returns distinct_rules and a non-empty caption string
    containing "estimate" / "upper bound"</check>
    <check>MCP + dashboard render the caption verbatim; no bare
    percentage or "saves" wording appears</check>
  </validation>
  <risks>
    <risk severity="high">Presenting this as measured savings
    reintroduces the exact discredited "8% savings" claim. The
    caption + no-percentage rule is the mitigation; a test asserts
    the caption text is present.</risk>
  </risks>
</task>

<task id="5" name="tests-and-regression-guards">
  <objective>
    Fixture-based tests for the reader and estimate, plus the two
    documented-trap regression guards.
  </objective>
  <context>
    <existing-code path="tests/unit/ops/">
      Existing telemetry-reader tests are the pattern. Use a
      tmp_path fixture JSONL with a few of each event type.
    </existing-code>
    <context-note>
      Documented trap: telemetry trackers reached via production code
      paths pollute the real ~/.attune JSONL. Add an autouse conftest
      fixture setting ATTUNE_MEMORY_TELEMETRY=0 for these tests so no
      test writes to the live file.
    </context-note>
  </context>
  <files-to-create>
    <file path="tests/unit/ops/test_memory_summary.py">
      Aggregation totals; ts-field regression (by_day populated from
      "ts"); missing-file → zeroed; malformed line skipped;
      estimate caption present.
    </file>
  </files-to-create>
  <files-to-modify>
    <file path="tests/unit/ops/conftest.py">
      <change location="autouse fixture">
        Set ATTUNE_MEMORY_TELEMETRY=0 via monkeypatch.setenv so
        production-path tracker calls no-op during tests.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>pytest tests/unit/ops/test_memory_summary.py -q passes</check>
    <check>running the suite leaves ~/.attune/telemetry/memory_events.jsonl
    line-count unchanged (no test pollution)</check>
  </validation>
  <risks>
    <risk severity="medium">A conftest env change scoped too broadly
    could mask real behavior in sibling tests; keep the fixture in
    tests/unit/ops/ only.</risk>
  </risks>
</task>
