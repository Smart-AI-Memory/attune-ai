# Usage Signals — Requirements

**Status:** approved (2026-06-11) · **Owner:** Patrick + agent
**Born:** discipline-review chat, 2026-06-11 (improvement #6 + #5 —
the strategic item; Patrick: "I would love to know how my users are
using attune-ai and other products").

## Problem

Every feedback loop in the attune ecosystem currently terminates at
Patrick. The discipline is excellent at "did it work" (receipts,
dogfooding, telemetry-ranked migration order) but has NO loop for
"did anyone else use it":

- No visibility into PyPI install trends per package (attune-ai,
  attune-rag, attune-help, attune-author, attune-verify).
- No visibility into Claude Code marketplace installs/updates.
- No signal for which workflows/skills external users actually run —
  `~/.attune/telemetry/usage.jsonl` is local-only by design.
- Releases ship user-facing claims ("workflows work on subscription")
  with no way to observe whether any external user exercised them.

Companion internal gap (improvement #5, "watch the watchers"): the
local telemetry pipeline itself fails silently — the buffered-writer
bug lost ~10 days of data before anyone noticed; the CI key-spend
burned ~$1,200 in a night. Signals about signal-health belong in the
same spec because they share the dashboard surface.

## Outcome

Each release can answer, with evidence: how many installs, which
surfaces external users touch, and whether our own telemetry is
alive — without compromising the privacy stance that makes a
developer tool trustworthy.

## Scope

- **External signals (zero-instrumentation first):** PyPI download
  stats (pypistats / BigQuery public dataset), GitHub
  stars/clones/traffic, marketplace install counts if exposed,
  PyPI per-version adoption curves.
- **External signals (instrumented, opt-in only):** an anonymous,
  documented, default-OFF usage ping (package version + workflow
  name + platform — no paths, no code, no prompts) is a Phase 2
  question, decided only after zero-instrumentation data lands.
- **Internal watchdogs:** telemetry-freshness ("usage.jsonl last
  wrote N hours ago") on the ops dashboard home; anomaly alarm for
  API spend (the z-score/stddev=0 lesson applies — define the
  flat-history case explicitly).

## Requirements

- **R1 — Phase 0 inventories what's free.** Before building anything:
  pull pypistats for all five packages, GitHub traffic API, and
  whatever the marketplace exposes; record a baseline snapshot in
  `decisions.md`. This is hours, not days, and may answer most of
  the question alone.
- **R2 — Privacy stance is explicit and conservative.** Default is
  observe-only public data. Any instrumented ping is opt-in
  (explicit env var or config flag), documented in README +
  SECURITY.md, payload enumerated and frozen, and trivially
  auditable in source. No exceptions; this is a trust product.
- **R3 — One surface.** Signals land on the existing ops dashboard
  (a "Reach" panel or similar), not a new tool. Per-release deltas
  visible (installs before/after a release week).
- **R4 — Release ritual hook.** The release-execute skill gains a
  step: record the baseline reach snapshot at tag time, so every
  release has a before/after pair without manual effort.
- **R5 — Telemetry watchdog.** Dashboard home shows last-write age
  for usage.jsonl and flags > 48h staleness; the buffered-writer
  failure mode (atexit flush) gets a freshness regression test.
- **R6 — Spend alarm.** Daily API spend anomaly check with an
  explicit flat-history rule (multiplier fallback when stddev=0),
  surfacing on the dashboard — the $1,200-night class of event must
  be visible within a day, not a billing cycle.

## Non-goals (this spec)

- Web/product analytics for attune-ai.dev (separate surface; Vercel
  Analytics already exists there).
- Per-user identification of any kind, ever.
- Growth tooling (changelogs-as-marketing, announcement automation).
- Replacing local telemetry — it stays local-first.

## Done when

- Phase 0 baseline snapshot recorded; the "what's free" decision
  (is zero-instrumentation enough?) is made on data.
- Dashboard shows reach + freshness + spend-anomaly panels.
- One release ships with a before/after reach pair attached.
- The opt-in ping question is explicitly decided (build or decline)
  in `decisions.md` — not left ambient.
