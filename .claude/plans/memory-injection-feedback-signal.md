# Memory Injection Feedback Signal

**Created:** 2026-07-08
**Status:** approved — executing Phase 1
**Owner:** Patrick + agent

---

## Context

The memory-telemetry analyzer (shipped #1291) measures the COST side
of short-term memory honestly, and ships the benefit as a labeled
upper-bound (`estimate_intervention_signal`). The frame ratified this
session ([[project_memory_as_insurance]]): memory is insurance;
measure it as premium efficiency + tail-prevention NET OF false
surfacings. The analyzer has the numerator's raw material
(surfacings) but no NOISE denominator.

Key finding: **the noise signal already exists, uninstrumented.**
`forget_entries` / `forget_by_prefix` in
[`session_stash.py`](../../src/attune/memory/session_stash.py) are the
deletion path behind `/recall drop`, `/recall review`, and the
starter reconciler — every deletion is an explicit "this surfaced
finding was wrong / irrelevant / resolved" verdict. Today it returns
a count and logs nothing. This session's two stale findings (bugs
already fixed) would each have been one such verdict.

`forget_by_prefix` delegates to `forget_entries`, so the latter is a
single chokepoint: instrument it once and every deletion path is
captured.

Design wrinkle: the existing producer
(`plugin/hooks/_memory_telemetry.py`) is not importable from `src/`.
So this adds a canonical src-side writer in
`src/attune/telemetry/memory_events.py` (same format, same
`ATTUNE_MEMORY_TELEMETRY` / `DO_NOT_TRACK` gate, never raises). The
hook keeps its own copy for now; convergence is a noted follow-up.

---

## Problem

Memory's benefit can't be a savings %, but it CAN be a bounded-noise
tail-prevention rate — if the noise is measured. There is no signal
today for "a surfaced finding was rejected as noise," even though the
user already produces that signal every time they drop a finding.

---

## Goals

1. Capture explicit rejection verdicts as `memory_feedback` events in
   the same `memory_events.jsonl`, via a src-side writer that inherits
   the existing local-only consent gate.
2. Compute an honest rejection rate (rejected / stash findings
   written) and surface it, labeled, in the MCP tool + dashboard
   panel shipped in #1291.
3. Zero new user friction — pure instrumentation of clicks already
   made.

---

## End State

The Telemetry dashboard and `telemetry_stats` MCP tool report a
`memory_feedback` section: how many surfaced findings were later
rejected as noise, by source, as a rate against findings stashed —
the net-of-noise half of the insurance ledger.

---

## Non-goals (Phase 2 — recorded, NOT built)

- acted-on vs ignored inference from the transcript (did a surfaced
  item precede matching use). Needs transcript correlation; deferred.
- Converging `plugin/hooks/_memory_telemetry.py` onto the new src
  writer. Additive-safe to defer; both write the same format.
- Task-shape injection routing ("don't inject into a one-shot"). That
  falls out of this noise data later; not this PR.

---

## Decisions

- Same file, new `event: "memory_feedback"` type — one analyzer, one
  gate, and a rejection correlates directly against the surfacings it
  rejects.
- Single emit point: `forget_entries` only (forget_by_prefix
  delegates to it). `forget_by_prefix` threads `source`/`cwd` down;
  it does NOT emit, to avoid double-counting.
- Denominator = session_stash `written` sum (of the findings we
  stashed, how many were later dropped) — the cleanest interpretable
  noise rate. Reported labeled, never as "savings".

---

## Tasks

<task id="1" name="src-memory-events-writer">
  <objective>
    Add src/attune/telemetry/memory_events.py with log_memory_event()
    — a canonical, importable-from-src writer mirroring the hook copy:
    same JSONL format + ATTUNE_MEMORY_TELEMETRY / DO_NOT_TRACK gate,
    never raises.
  </objective>
  <context>
    <existing-code path="plugin/hooks/_memory_telemetry.py">
      The format + gate to mirror exactly: v/ts/event/session_id +
      fields, ~/.attune/telemetry/memory_events.jsonl, _FALSEY env
      handling, silent on all exceptions.
    </existing-code>
  </context>
  <validation>
    <check>log_memory_event("memory_feedback", verdict="rejected",
    count=2) appends one parseable line with event=="memory_feedback"</check>
    <check>ATTUNE_MEMORY_TELEMETRY=0 makes it a no-op</check>
    <check>never raises on an unwritable path</check>
  </validation>
</task>

<task id="2" name="instrument-forget-seam">
  <objective>
    Emit a memory_feedback event from forget_entries when a deletion
    succeeds. Thread optional source/cwd through forget_by_prefix.
  </objective>
  <context>
    <existing-code path="src/attune/memory/session_stash.py">
      forget_entries returns the deleted count; forget_by_prefix
      delegates to it. Both are best-effort / never-raise.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/memory/session_stash.py">
      <change location="forget_entries">
        Add optional source="forget" and cwd=None params. After a
        successful forget with count>0, best-effort
        log_memory_event("memory_feedback", verdict="rejected",
        source=source, count=count, cwd=cwd). Import guarded so a
        writer failure never breaks deletion.
      </change>
      <change location="forget_by_prefix">
        Add source/cwd; pass to forget_entries. Do NOT emit here.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>forget_entries with a fake backend deleting 2 ids emits one
    memory_feedback event with count==2</check>
    <check>forget_by_prefix path emits exactly once (no double count)</check>
    <check>deletion still returns the right count when telemetry is
    disabled</check>
  </validation>
  <risks>
    <risk severity="medium">Double-counting if both functions emit.
    Mitigation: only forget_entries emits; a test asserts one event
    per prefix-delete.</risk>
  </risks>
</task>

<task id="3" name="feedback-reader-and-surfaces">
  <objective>
    Add estimate_feedback_signal() to ops/data.py (rejected count,
    by_source, findings_written, rejection_rate, labeled caption), and
    surface it on the telemetry_stats MCP tool + dashboard panel.
  </objective>
  <files-to-modify>
    <file path="src/attune/ops/data.py">
      <change location="new estimate_feedback_signal(path=None)">
        Parse memory_feedback events (rejected count, by source) and
        session_stash `written` sum (denominator). rejection_rate =
        rejected / written (0.0 when written==0). Include a caption
        naming it a noise rate, not savings.
      </change>
    </file>
    <file path="src/attune/mcp/server.py">
      <change location="_get_telemetry_stats memory block">
        Add result["memory_feedback"] = estimate_feedback_signal().
      </change>
    </file>
    <file path="src/attune/ops/routes/dashboard.py">
      <change location="telemetry route">
        context["memory_feedback"] = estimate_feedback_signal(
        cfg.memory_events_path).
      </change>
    </file>
    <file path="src/attune/ops/templates/telemetry.html">
      <change location="in the Short-term memory panel">
        Render rejected count, rejection rate, by-source; caption
        verbatim. Empty state when no feedback yet.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>estimate_feedback_signal on a fixture with 2 rejected + 10
    written returns rejection_rate 0.2</check>
    <check>MCP telemetry_stats returns a memory_feedback key</check>
    <check>dashboard panel renders the rate + caption (verify live)</check>
  </validation>
</task>

<task id="4" name="tests-and-guards">
  <objective>
    Fixture tests for the writer, the seam emit, and the reader;
    reuse the autouse ATTUNE_MEMORY_TELEMETRY=0 pollution guard.
  </objective>
  <files-to-create>
    <file path="tests/unit/ops/test_feedback_signal.py">
      estimate_feedback_signal math + caption present + missing-file
      zeroed.
    </file>
    <file path="tests/unit/memory/test_forget_feedback.py">
      forget_entries emits one memory_feedback event on success (with
      a stub backend + tmp events path); no event when count==0; no
      double-emit via forget_by_prefix.
    </file>
  </files-to-create>
  <validation>
    <check>both test files pass</check>
    <check>full run leaves the live memory_events.jsonl unchanged</check>
  </validation>
</task>
