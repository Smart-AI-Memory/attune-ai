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
| Design option (A/B/C) | _TBD — pre-commit after Phase 0_ | The choice is determined by whether subscription auth is inheritable across a subprocess boundary. |
| Detection default for subscribers | _TBD — pre-commit after Phase 0_ | Lean toward opt-in (`ATTUNE_AUTHOR_AUTH_MODE=auto` not the default initially) to avoid surprising users until the routing is proven stable. Revisit after the first month of real use. |
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

To be filled in during Phase 0 implementation:

- [ ] Phase 0 finding: `claude_agent_sdk.query()` inside Claude Code
      without env key: _TBD_
- [ ] Phase 0 finding: same from a child subprocess of Claude Code:
      _TBD_
- [ ] Phase 0 finding: detection signal Claude Code exposes
      (env var, file, or none): _TBD_
- [ ] Phase 0 finding: total sibling-package count making direct
      API calls (today's known set: attune-author, attune-rag —
      audit may surface more): _TBD_

---

## Decision-change log

> Append entries here when a decision above is revised.
> Reference the PR that revised it.

- 2026-05-16 — Initial decisions captured during spec draft.
  Motivating trigger: polish-fact-check Phase 3 (attune-author
  PR #36) added a second LLM-call path that requires
  `ANTHROPIC_API_KEY`, making the cumulative API-key dependency
  in sibling packages tangible enough to warrant fixing.
