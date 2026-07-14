# Spec: Subscription-First Auth for Sibling Packages — Design

**Status**: complete — Phases 0–2 shipped end-to-end (attune-author #55, v0.16.0); reconciled at 2026-07-14 triage (was: draft)

---

## Phase 2: Design

### Open question driving the design

How does a Claude Code subscription actually route an LLM call so
no API token is consumed?

The honest answer at draft time: it appears to be a property of
the Claude Agent SDK when invoked inside a Claude Code session
context. The SDK reads authentication from the session rather
than from `ANTHROPIC_API_KEY`. This needs Phase 0 verification
before any of the options below get implemented.

The three design options assume Phase 0 confirms the
SDK-context-routing model. If Phase 0 surfaces a different
mechanism, the design will be revised before implementation.

---

### Option A: Agent-SDK shim in each sibling

Each sibling package gains a small adapter that prefers
`claude_agent_sdk.query()` over the direct
`anthropic.Anthropic` client when:

1. The Agent SDK is importable, AND
2. A subscription session is detectable (env var or session
   probe), AND
3. The caller hasn't explicitly forced API mode.

Pseudocode:

```python
def get_llm_client():
    if _running_under_subscription():
        return AgentSDKClientAdapter()  # uses claude_agent_sdk.query
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicSDKClient()
    raise NoCredentialsError(...)
```

**Pros:** No new package; each sibling owns its routing.
**Cons:** Duplicate adapters across siblings (DRY violation);
each sibling decides "what counts as subscription" separately;
two LLM SDKs become a coupling surface.

---

### Option B: Publish `attune_ai.auth` as a public helper

`attune-ai` exposes a function siblings can import that returns
an LLM-call callable already wired for the right mode:

```python
# in attune-ai
def get_authenticated_completer(
    *,
    fallback_to_api: bool = True,
) -> Callable[..., str]:
    """Return a `(messages, **kwargs) -> str` callable that uses
    whichever mode AuthStrategy recommends."""
    ...

# in attune-author / attune-rag
from attune_ai.auth import get_authenticated_completer
complete = get_authenticated_completer()
text = complete(messages=[...], model="claude-haiku-4-5", ...)
```

**Pros:** Single source of truth; siblings get
recommendation-driven routing "for free"; matches how
attune-ai's own workflows already work.
**Cons:** `attune-author` and `attune-rag` gain a runtime
dependency on `attune-ai`. Today they're consumed-by-but-not-
dependent-on. Reversing that direction has packaging
implications (cycle risk, install size, version pinning).

---

### Option C: Shared `attune-auth` package

Extract the auth-routing layer into its own tiny PyPI package
that all four consumers depend on:

```
attune-auth/         # ~150 LOC; exposes get_authenticated_completer
├── attune-ai
├── attune-author
└── attune-rag
```

**Pros:** Cleanest dependency graph; no cycle risk; each
consumer pins independently.
**Cons:** New package to maintain, version, publish, release-
cadence-align. Possibly overkill for what may end up being a
50-line adapter.

---

### Recommendation

Defer the decision until Phase 0 finishes. Likely outcome:

- If subscription routing turns out to be a `claude_agent_sdk`
  context inheritance — and that inheritance works from a child
  subprocess of Claude Code — then **Option A** is sufficient.
  Each sibling gets a ~30-line adapter that detects + uses the
  Agent SDK when present, falls back to the Anthropic SDK
  otherwise. Duplication is acceptable at this scale.
- If subscription routing requires nontrivial setup the auth
  strategy already encodes (token estimation, tier-aware mode
  selection, cost reporting), then **Option B** wins: import
  the existing logic instead of reimplementing it. The
  dependency direction concern is solvable by keeping the auth
  helper in a thin `attune-ai.auth` module that has no transitive
  attune-ai deps.
- **Option C** is the right call only if a 4th consumer needs
  the same plumbing — premature today.

---

### User-facing surface (independent of option)

Regardless of mechanism, the siblings need:

1. **Auto-detection.** `attune-author generate` and the Phase 3
   judge should "just work" for subscribers without env vars.
2. **Explicit override.** `--auth-mode=api` / `--auth-mode=sub`
   CLI flags + `ATTUNE_AUTH_MODE` env var, for cases where the
   user wants to force one path (e.g., CI lanes with an API key
   and no subscription, or vice versa).
3. **Status command.** `attune-author auth status` reports
   which mode would fire for a hypothetical call right now,
   including which credentials are available. Eliminates the
   "did it actually route?" debugging.
4. **Telemetry parity.** The existing Phase 3 telemetry log
   (`Faithfulness judge: 3 calls, 0 skipped, estimated cost
   $0.0150`) should annotate whether costs were
   subscription-covered or billed — e.g.
   `estimated cost $0.0000 (subscription)` vs
   `$0.0150 (API)`.

---

### Failure modes to design around

- **Subscription expires mid-run.** Token / session expires
  between calls during a multi-feature regen. Should fall
  through to API-key if available; surface a clear message if
  not.
- **Mixed authentication on the same machine.** Some users
  have BOTH a subscription AND an `ANTHROPIC_API_KEY` set. The
  mode flag (or `AuthStrategy.default_mode`) is the
  tie-breaker; without an explicit setting, prefer subscription.
- **Sibling invoked from non-Claude-Code shell.** A subscriber
  running `attune-author generate` from a plain terminal won't
  have a session-level subscription to inherit. The detection
  must not false-positive in this case; the fallback to
  `ANTHROPIC_API_KEY` (or a graceful "no auth" error) is the
  expected path.

---

### Open design questions (resolve before Phase 1 implementation)

1. **Does `claude_agent_sdk` inherit a Claude Code session's
   auth when run from a subprocess?** Phase 0 task #1.
2. **Is there an env var or file that Claude Code sets to
   advertise its session presence?** Phase 0 task #2.
3. **Should detection be opt-in (`ATTUNE_AUTH_MODE=auto`
   default-off) or opt-out (default-on, env to disable)?**
   Pre-commit a default in `decisions.md` before Phase 1.
4. **For attune-rag, does the judge's async API change at
   all?** The Agent SDK is async-native; the existing
   `FaithfulnessJudge.score` is already async — clean fit.
   But if Option A picks the Agent SDK, the AsyncAnthropic
   construction needs replacing, not just augmenting.
