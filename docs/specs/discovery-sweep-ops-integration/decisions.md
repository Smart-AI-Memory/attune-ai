# Decisions — Discovery-Sweep Ops Dashboard Integration

**Status:** draft (2026-05-13)

Records the **why** behind shape choices. New decisions append at
the bottom with date + context.

---

## 1. Carve out from parent discovery-sweep spec (2026-05-13)

**Decision:** Ship the ops-dashboard integration as a separate
spec rather than as Phase 4 of the parent `discovery-sweep`
spec.

**Reasoning:**

- The parent spec's Phase 4 originally bundled both CLI
  deprecation AND ops-dashboard integration. Phase 1.5 of the
  parent split these: CLI deprecation became the new Phase 4
  (closed empty per P2.7 outcome); ops-dashboard moved to this
  follow-up spec.
- The ops-dashboard work blocks on `ops-runner-tier2` Phase 2,
  which hasn't shipped yet. Keeping it in the parent spec would
  have stalled the parent's "DONE" status.
- The parent spec is fully consumable today via CLI + JSON
  output. Ops-dashboard is enhancement, not core.
- Different review surface: parent spec was Python-only;
  ops-dashboard touches HTML/JS/SSE plumbing that the
  ops-runner-tier2 author is the right reviewer for.

---

## 2. Reuse ops-runner-tier2's SSE stream (not build a new one)

**Decision:** Per-source telemetry events publish onto the
existing `/events` SSE stream that ops-runner-tier2 ships.

**Reasoning:** Building a parallel stream for one workflow is
overhead with no benefit. The ops-runner-tier2 spec deliberately
ships SSE as a shared primitive for exactly this kind of consumer.
Consequence: this spec blocks on that one.

---

## 3. Latest-only storage, no history (v1)

**Decision:** `~/.attune/ops/sweep-results/<scope-hash>.json`
holds only the most recent sweep per scope. History is post-v1.

**Reasoning:**

- v1 use case is "show me my current state" — latest-only
  suffices.
- History adds storage management (size cap, eviction policy,
  retention period) that's a separate design problem.
- Users who want trend tracking can persist via cron + a
  separate storage layer; the JSON files are already structured.

---

## 4. `event_sink=None` default keeps CLI behavior identical

**Decision:** The engine's new `event_sink` kwarg defaults to
`None`. CLI invocations get exactly today's behavior with no
event-emission overhead.

**Reasoning:**

- The parent spec is on `main` and works today via CLI; this
  follow-up must not regress that surface.
- Daemon callers opt in explicitly by passing a sink.
- Tests assert `event_sink=None` is a no-op (Phase 1.5 of THIS
  spec, task 1.5).

---

## 5. Fire-and-forget event publishing (asyncio.create_task)

**Decision:** Event sink invocations use
`asyncio.create_task(event_sink(event))`, never
`await event_sink(event)`.

**Reasoning:** A slow SSE listener must not stall the sweep
(NFR-2). The sweep's correctness doesn't depend on events
reaching subscribers — events are observability, not coordination.
If a sink raises, the exception lands in the create_task callback
and gets logged by asyncio's default handler; the sweep
continues.

---

## 6. Reuse Phase 3.2 severity color tokens for chip CSS

**Decision:** Bucket-chip CSS variables (`--severity-high`,
`--severity-medium`, `--severity-dim`) carry the same color values
as the parent spec's Phase 3.2 ANSI codes (red, yellow, dim).

**Reasoning:**

- Visual consistency between the CLI markdown output and the
  dashboard reduces cognitive load when users move between the
  two surfaces.
- The mapping is intentional, not coincidental: queue items skew
  high-severity, questions skew medium, rejected skews
  below-threshold.

---

## 7. Per-source events use raw `findings_count`, not bucket counts

**Decision:** The `source_finished` event reports the source's
raw findings count BEFORE verification rules route them to
queue/questions/rejected. Bucket counts only appear after the
sweep completes (in the JSON output).

**Reasoning:**

- Sources don't know their verification fate when they finish;
  verification runs at the engine level after all sources gather.
- Real-time progress is about "is this source done yet," not
  "how triaged are its findings yet." Triage is a sweep-final
  property.
- Saves the dashboard from re-running verification client-side.

---

## 8. Detail view re-uses ops-runner-tier2's run-view page

**Decision:** Clicking a bucket chip navigates to the existing
run-view page with a `?bucket=` query param, not a bespoke
discovery-sweep detail view.

**Reasoning:**

- ops-runner-tier2 ships a generic run-view; adding a workflow-
  specific one fragments the UI.
- Finding rows are generic enough (severity badge + file:line +
  title + evidence collapsed) to render in the shared template.
- If other workflows adopt the structured-emit JSON pattern
  later, the shared run-view extends to them too.

**Revised (Decision #9):** The drill-in view ends up scope-keyed
(`/workflows/discovery-sweep/results/<scope-hash>?bucket=queue`),
not run-keyed. The run-view page shown for a discovery-sweep run
still displays its captured stdout lines (existing
ops-runner-tier2 behavior); the scope-keyed view is a separate
template that surfaces "current state for this scope" regardless
of which run produced it.

---

## 9. Adopt Option A — stdout-emit + sidecar parser (2026-05-13)

**Decision:** After the Phase 0 audit
([`audit-2026-05-13.md`](audit-2026-05-13.md)) revealed that the
shipped ops-runner-tier2 surface is subprocess + per-run SSE
(not the in-process daemon + shared `/events` stream the original
draft assumed), adopt Option A: engine emits `ATTUNE_DS` prefix
lines on stdout; daemon parses its own captured stdout at run
completion; daemon writes scope-keyed JSON the dashboard reads
for chip counts.

**Q1 — Adopt Option A?** Yes (user approval, 2026-05-13).

**Q2 — Refactor `design.md` / `tasks.md`?** Yes, in the Phase 1
implementation PR (where the engine API surface ships and the
shape becomes concrete in code).

**Q3 — Keep `event_sink` in Phase 1?** Yes. Not load-bearing for
the dashboard, but cheap to add and useful for tests + future
in-process callers (a hypothetical wizard runner, an embedded
sweep API for users with their own daemon, etc.).

**Reasoning for Option A over Option B (in-process exec):**

- Preserves the subprocess invariant for the runner. Flipping one
  workflow to in-process would set a precedent every future
  workflow has to argue about.
- Preserves the single-run lock and `run_id` correlation (no
  `sweep_id` needed).
- Daemon-side parsing is one regex per event kind; ~50 LoC.
- The CLI's existing `--json` flag remains the canonical
  machine-readable surface; the stdout-line format is strictly
  additive.

**Consequence:** the engine's `event_sink` callback is not how
the daemon hears about per-source progress. The daemon hears
stdout. `event_sink` is a parallel surface for in-process
callers only.

---

## 10. Gate stdout emission on `ATTUNE_DS_EMIT=1`, not non-TTY (2026-05-13, Phase 1b)

**Decision:** The Phase 1b `ATTUNE_DS` stdout side-channel is
emitted only when the `ATTUNE_DS_EMIT` environment variable is
set to a non-empty value. The daemon sets it when spawning the
subprocess; nobody else does.

**What the original draft said:** "Emit when `sys.stdout.isatty()`
is False (the subprocess parent has captured stdout)." This was
shorthand for "emit when the daemon is parsing us, but not when
a TTY user is reading us."

**Why that shorthand is wrong:** non-TTY also covers the
legitimate user workflow of `attune workflow run discovery-sweep
> out.md`. That redirects stdout to a file (not a TTY), but the
user wants clean markdown in `out.md`, NOT ATTUNE_DS lines
interleaved with the markdown. The TTY check would silently
pollute that output.

**Env-var gate is precise:** only the daemon opts in. CLI users —
whether typing in a terminal, piping to a file, or running under
CI capture — see exactly today's output. The env var is also
forward-compatible: any future runner (cron job, external script)
that wants to consume the structured stream can opt in the same
way without negotiating a new flag.

**Naming:** `ATTUNE_DS_EMIT` (not `ATTUNE_OPS_DAEMON`) so the
toggle name describes what it does, not who flips it. A future
non-ops consumer can use the same env var without semantic
collision.

---

## 11. Split Phase 2 into 2A (storage primitives) + 2B (daemon wiring) (2026-05-13)

**Decision:** Ship Phase 2 in two PRs rather than one. 2A
introduces `src/attune/ops/sweep_results.py` as a pure utility
module (parser + scope_hash + atomic persist + read). 2B wires
the daemon's post-run hook, the HTTP route, and the feature
flag.

**Reasoning:**

- 2A is all-new files — zero risk of regression, independently
  reviewable, can land while the conflict-prone `runner.py` and
  `routes/runner.py` are tied up in [#324](https://github.com/Smart-AI-Memory/attune-ai/pull/324)
  / [#326](https://github.com/Smart-AI-Memory/attune-ai/pull/326)
  / [#328](https://github.com/Smart-AI-Memory/attune-ai/pull/328).
- 2B touches the very files those PRs modify. Attempting both
  in one PR would create avoidable conflicts and force re-merge
  cycles.
- The 2A surface is independently useful today — any script or
  test can compose the primitives without waiting for 2B.
- Atomic persist + read semantics are testable in isolation
  without spinning up the daemon.

**Scope confirmation:** PR [#334](https://github.com/Smart-AI-Memory/attune-ai/pull/334)
is the 2A landing and stays within this spec (not a new spec).
It implements `tasks.md` items 2.2 (parser), 2.3 (atomic write
to `<scope-hash>.json`), and the prerequisite primitives for
2.5 (feature flag exposed via `is_persistence_enabled()`).
Items 2.1 (post-run hook), 2.4 (HTTP route), and 2.6 (end-to-
end tests) move to a Phase 2B PR once the runner-tier2 PRs
land.

**Consequence:** `tasks.md` Phase 2 status: in progress. 2A in
flight; 2B blocked on [#324](https://github.com/Smart-AI-Memory/attune-ai/pull/324)
/ [#326](https://github.com/Smart-AI-Memory/attune-ai/pull/326)
/ [#328](https://github.com/Smart-AI-Memory/attune-ai/pull/328)
landing.
