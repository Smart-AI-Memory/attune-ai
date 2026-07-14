# Spec: Subscription-First Auth for Sibling Packages

**Status**: complete — Phases 0–2 shipped end-to-end (attune-author #55, v0.16.0); reconciled at 2026-07-14 triage (was: draft)
**Created**: 2026-05-16
**Sibling spec**: `docs/specs/polish-fact-check/` (motivating
trigger — Phase 3 made attune-author's API-key dependency
visibly tangible by adding a second LLM-call path)

---

## Phase 1: Requirements

### Problem statement

`attune-author` and `attune-rag` both make direct Anthropic API
calls and require `ANTHROPIC_API_KEY` in the environment.

- `attune_author.doc_gen._anthropic.call_anthropic` constructs a
  sync `anthropic.Anthropic(api_key=...)` client.
- `attune_rag.eval.faithfulness.FaithfulnessJudge.__init__`
  constructs `anthropic.AsyncAnthropic(api_key=...)` directly.

`attune-ai` ships an auth strategy
(`attune.models.auth_strategy.AuthStrategy`) that recommends
subscription-vs-API mode based on subscription tier + module
size. Its own workflows route LLM calls through
`claude_agent_sdk.query()` which CAN consume a Claude Code
subscription when run in the appropriate context. But that
routing capability isn't exposed to sibling packages, so users
who have a Claude Code subscription still pay full API cost when
attune-author polishes templates or attune-rag's judge scores
faithfulness.

### Why this matters

1. **Duplicate billing.** A Pro/Max subscriber pays $20–$200/month
   for Claude Code AND pays per-token to Anthropic for the same
   model when attune-author runs polish or attune-rag runs the
   judge. The two paths use different SDKs so the subscription
   discount doesn't apply.
2. **First-run friction.** New attune-ai users today get told
   "install attune-ai, run a command" and it works. The moment
   they try `attune-author generate` or enable the Phase 3
   faithfulness judge, they hit an API-key requirement that the
   rest of attune-ai didn't make them think about. The UX seam
   breaks the zero-config story.
3. **Cost surprise.** Without a subscription path, faithfulness
   scoring at default rates (~$0.03 per 3-kind feature) is
   inexpensive but unbounded: a full regen of 30 features at
   11 kinds each is ~$3 per pass. With subscription routing the
   incremental cost is zero.

### Scope

In scope:

- `attune_author.doc_gen._anthropic` (polish-pass API calls).
- `attune_rag.eval.faithfulness.FaithfulnessJudge` (judge calls).
- Any other sibling package that makes direct Anthropic API
  calls — `attune-help`, `attune-lite` — discovered during
  Phase 0 audit.

Out of scope:

- attune-ai's own workflows (already route through
  `claude_agent_sdk`).
- The recommendation logic in `AuthStrategy` (which mode to
  pick); this spec is about execution, not policy.
- Anthropic's own SDK behavior or pricing.

### What "subscription routing" actually means (open question)

The Phase 0 research task answers this: today's `AuthStrategy`
returns recommendations (`AuthMode.SUBSCRIPTION` vs
`AuthMode.API`) but the code path that converts a "use the
subscription" recommendation into an actual non-billed LLM call
is not obvious from a five-minute read of
`src/attune/models/`. The most likely mechanism is
`claude_agent_sdk.query()` invoked from inside a Claude Code
session, where the SDK inherits the session's authentication
context. If that's the mechanism, sibling packages need either:

1. A way to detect "I'm running under Claude Code" and route
   through `claude_agent_sdk` instead of the direct Anthropic
   SDK, OR
2. A shared auth-routing helper that exposes the choice as a
   library call.

### Success criteria

- A Pro/Max-subscription user can run `attune-author generate`
  and `attune-author regenerate` end-to-end **without setting
  `ANTHROPIC_API_KEY`** (when their Claude Code session has
  valid auth).
- Same for the Phase 3 faithfulness judge: a subscriber-only
  user can flip `[tool.attune-author.fact-check.faithfulness]
  enabled = true` and the judge runs against their subscription.
- API-key-only users (no Claude Code subscription, or running
  outside a Claude Code session) keep working unchanged — the
  fallback to `ANTHROPIC_API_KEY` stays first-class.
- No behavior change for users running attune-ai's existing
  workflows (the change is additive at the sibling-package
  layer).
- A diagnostic command — likely an extension of
  `attune-author auth status` or a new
  `attune-author auth diagnose` — that prints which mode is
  actually being used for a real call, so users can confirm
  routing is working without scraping logs.

### Non-goals

- Modifying the subscription/API recommendation logic.
- Building a separate `attune-auth` PyPI package (considered
  in the design but deferred unless a 4th sibling needs the
  same plumbing).
- Caching, batching, or cost reporting beyond what already
  exists in attune-ai's telemetry.
