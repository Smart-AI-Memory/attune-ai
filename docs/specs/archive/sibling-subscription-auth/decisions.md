# Spec: Subscription-First Auth for Sibling Packages — Decisions

> Pre-committed decisions per the existing lesson "Pre-committed
> decision matrices survive contact with data." Phase 0's
> findings populate the empty rows before Phase 1 starts;
> Phase 1+ rows get filled as implementation progresses.

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Phase 0 deliverable shape | A single `findings.md` doc plus a runnable probe script committed to `scripts/probe_subscription_routing.py` | The probe is reusable: if the routing mechanism changes upstream, re-running tells us so. A doc alone goes stale. |
| Phase 0 success criterion | The four open design questions in `design.md` have explicit yes/no answers (or "not yet determined, follow-up needed") | Soft "we learned a lot" deliverables are how investigation phases die. |
| Design option (A/B/C) | **Option A** — per-sibling Agent-SDK shim | Phase 0 confirmed `claude_agent_sdk.query()` succeeds in a subprocess of Claude Code without `ANTHROPIC_API_KEY`. Two adapters across two siblings isn't enough duplication to justify Option B (cycle risk) or Option C (new package). Revisit after a 4th consumer needs the same plumbing. |
| Detection signal | **`CLAUDECODE=1` env var** | Phase 0 surfaced this as a clean boolean string set by Claude Code in every subprocess it spawns. `CLAUDE_CODE_SESSION_ID` is a secondary, session-specific signal — not needed for routing. |
| Detection default for subscribers | **Opt-out** (auto-mode is default; users opt out via env var or CLI flag) | Phase 0 showed routing works seamlessly via one env-var check. Opt-in would force every subscriber to flip a flag to get the obviously-better behavior. Solo-dev / first-run UX wins. |
| CLI flag name | `--auth-mode={auto,api,sub}` on `attune-author generate`, `regenerate`, `attune-rag eval` | Three discrete values map clean to argparse `choices=`; matches existing `--fact-check={off,soft,strict}` style. |
| Env var names | `ATTUNE_AUTHOR_AUTH_MODE` (attune-author scope) and `ATTUNE_RAG_AUTH_MODE` (attune-rag scope) | Per-package env vars; users with both packages can override independently. Avoids a single global `ATTUNE_AUTH_MODE` that overrides everything at once. |
| Status command | `attune-author auth status` (and matching `attune-rag auth status`) | Mirrors `attune-ai`'s existing `attune auth status`. Output format intentionally parallel so users get the same diagnostic surface across packages. |
| Telemetry cost annotation format | `estimated cost $0.0000 (subscription)` and `$0.0150 (API)` | One line, no schema change for existing telemetry consumers. The parenthetical tag is grep-able. |
| Fallback order when both auths are available | Subscription, then API key | A subscriber paying $200/mo for Max should be the first beneficiary; API-key takes over only when subscription explicitly fails or is forced off. |
| Behavior when neither auth is available | Raise a clear error pointing the user at both setup paths | No silent fallback to a "no auth" mode that just emits Jinja drafts. Polish failures already have that lenient path; auth failures should not pile onto it. |
| Cycle prevention if Option B chosen | Place the public auth helper in `attune-ai`'s top-level package surface (`attune.auth.get_authenticated_completer`) with **no transitive attune-ai dependencies** | Siblings can then import a minimal shim without dragging in attune-ai's workflow/MCP/wizard surface. |
| Cross-package release coordination | Land Phase 1 (attune-author) and Phase 2 (attune-rag) in separate PRs; coordinate release in same week if both ship | Independent shipping reduces risk; coordinated release date keeps the user-facing story consistent. |

---

## Calibration record

Phase 0 findings (see `findings.md` for full detail and the raw
probe artifacts):

- [x] **`claude_agent_sdk.query()` inside Claude Code without env key:** ✅ works. Returned a complete response addressed to me by name even though `ANTHROPIC_API_KEY` was empty (`len=0`).
- [x] **Same from a child subprocess of Claude Code:** ✅ works. The probe ran via the Bash tool's `python` subprocess and successfully made the call without an API key.
- [x] **Detection signal Claude Code exposes:** `CLAUDECODE=1` (boolean). Secondary signal `CLAUDE_CODE_SESSION_ID=<uuid>` identifies which session.
- [x] **Sibling-package audit:** today's set is **attune-author** (polish-pass) + **attune-rag** (faithfulness judge + RAG answer-generation). `attune-help` and `attune-lite` have no direct LLM call sites. The RAG answer-generation path is out of scope for v1 unless a UX seam appears.

---

## Decision-change log

> Append entries here when a decision above is revised.
> Reference the PR that revised it.

- 2026-05-16 — Initial decisions captured during spec draft.
  Motivating trigger: polish-fact-check Phase 3 (attune-author
  PR #36) added a second LLM-call path that requires
  `ANTHROPIC_API_KEY`, making the cumulative API-key dependency
  in sibling packages tangible enough to warrant fixing.
- 2026-05-16 — Phase 0 shipped. Decisions revised from "TBD" to
  concrete:
  - **Design option = Option A** (Phase 0 ruled out B and C).
  - **Detection signal = `CLAUDECODE=1`** (one env var, no
    filesystem probes needed).
  - **Detection default = opt-out** (auto-mode is the default).
  Spec status moves from `draft` to `approved`. Phase 1 unblocked.
- 2026-06-10 — Phase 1 shipped (attune-author PR #55). Three
  decisions made at implementation time:
  - **Forced `sub` never falls back to the API key** — the
    auto-mode fallback (sub failure → API when a key exists)
    applies only to `auto`; an explicit `--auth-mode=sub` that
    fails raises rather than silently billing the API. The
    "fall through to API-key if available" failure-mode design
    is thereby scoped to auto mode.
  - **Subscription subprocess runs with `setting_sources=[]`** —
    carried over from attune-ai's sdk-subprocess-isolation spec
    (D2–D5): without it, SessionStart hooks and CLAUDE.md
    injection from the user's settings pollute the stream-json
    channel and break the call for subscription users.
  - **Task 1.6 telemetry shape** — the polish path has no
    per-call cost estimate, so the annotation shipped as a route
    counter line (`Polish LLM calls: N (subscription), M (API)`)
    rather than a `$X (subscription)` cost line; the cost-line
    format in the decision matrix still applies to the Phase 2
    faithfulness-judge line, which does estimate cost.
  Also: `claude-agent-sdk` added to attune-author's `[ai]` extra
  (subscribers get the routing on a plain `[ai]` install), and
  the test-suite conftest pins `ATTUNE_AUTHOR_AUTH_MODE=api` +
  clears `CLAUDECODE` so running tests inside Claude Code can't
  auto-route un-mocked polish calls to real subscription calls.
  Known unknown carried forward: subscription rate limits at
  full-regen volume (Phase 0 caveat #1) — the first real `.help`
  regen doubles as the measurement.
