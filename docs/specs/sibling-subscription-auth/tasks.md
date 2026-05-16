# Spec: Subscription-First Auth for Sibling Packages — Tasks

**Status**: draft

> Phase 0 is mandatory and lands before any implementation. The
> design rests on assumptions about how `claude_agent_sdk` and
> Claude Code subscriptions interact; the implementation phases
> are gated on those assumptions surviving contact with reality.

---

## Phase 0: Research

**Target PR scope:** ~100 LOC of probe scripts + a written
findings doc. No production code changes.

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 0.1 | Probe: does `claude_agent_sdk.query()` work inside Claude Code without `ANTHROPIC_API_KEY`? | attune-ai | todo | Write the probe as a one-shot script under `scripts/probe_subscription_routing.py`. Run inside Claude Code; capture whether the call succeeds and what auth context it uses. |
| 0.2 | Probe: same as 0.1, but from a child subprocess spawned by Claude Code (mimicking attune-author being invoked from Claude Code) | attune-ai | todo | Critical: confirms whether subscription auth is inherited across a process boundary or only available inside Claude Code's own process. |
| 0.3 | Probe: identify env vars / config files Claude Code sets that advertise its presence | attune-ai | todo | Look for `CLAUDE_CODE_*`, `~/.claude/`, etc. Findings inform the detection step. |
| 0.4 | Audit: list every sibling package that makes direct Anthropic API calls | attune-ai | todo | Grep `attune-author`, `attune-rag`, `attune-help`, `attune-lite`, `attune-software` for `anthropic.Anthropic`, `anthropic.AsyncAnthropic`. Confirm scope. |
| 0.5 | Write `findings.md` in this spec dir | attune-ai | todo | One page; covers what the probes returned + which design option (A/B/C) the data supports. |
| 0.6 | Pre-commit Phase 1 design decisions in `decisions.md` | attune-ai | todo | Detection default (opt-in vs opt-out), CLI/env-var override naming, telemetry message format. |

### Phase 0 exit checklist

- [ ] `scripts/probe_subscription_routing.py` lands and is
      runnable both inside and outside Claude Code
- [ ] `findings.md` answers the four open design questions
      from `design.md`
- [ ] `decisions.md` has a pre-committed decision row for each
      open question
- [ ] Spec status moves from `draft` to `approved` (or `paused`
      if findings invalidate the premise)

---

## Phase 1: Shim layer in attune-author (smallest blast radius)

**Target PR scope:** ~300 LOC including tests. Depends on Phase 0.

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1.1 | Pick design option (A/B/C) from Phase 0 findings | attune-author | todo | Document in this spec's decisions.md |
| 1.2 | Implement the chosen adapter / wrapper in attune-author | attune-author | todo | Lives under `src/attune_author/auth/` or extends `doc_gen/_anthropic.py` |
| 1.3 | Wire the adapter into `polish._call_llm` | attune-author | todo | Drop-in replacement for the current direct `get_client()` call |
| 1.4 | Add `--auth-mode={auto,api,sub}` to `attune-author generate` and `regenerate` | attune-author | todo | Plus `ATTUNE_AUTHOR_AUTH_MODE` env var (explicit override always wins over auto) |
| 1.5 | Add `attune-author auth status` CLI command | attune-author | todo | Report which mode would fire right now; list available credentials |
| 1.6 | Telemetry: annotate cost as `(subscription)` or `(API)` in the regen summary log | attune-author | todo | Matches the Phase 3 telemetry log format |
| 1.7 | Tests: routing under each mode (auto-sub, auto-api, forced-sub, forced-api, no-creds) | attune-author | todo | Mock the SDK at the adapter boundary, not the wire |
| 1.8 | Tests: failure modes (subscription expires mid-run, mixed auth) | attune-author | todo | |
| 1.9 | Update CHANGELOG + README | attune-author | todo | Document zero-config subscriber UX |

### Phase 1 exit checklist

- [ ] Tasks 1.1–1.9 done
- [ ] A subscriber can run `attune-author generate <feat>`
      without `ANTHROPIC_API_KEY` and see "(subscription)"
      cost in the log
- [ ] An API-key-only user sees no behavior change
- [ ] `auth status` correctly reports the active mode

---

## Phase 2: Same for attune-rag (faithfulness judge)

**Target PR scope:** ~250 LOC. Depends on Phase 1 (reuses the
adapter shape; may extract to a shared helper).

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 2.1 | Mirror Phase 1's adapter inside attune-rag (or import from a shared package per Option B/C) | attune-rag | todo | Async-native — `claude_agent_sdk.query()` matches `FaithfulnessJudge.score`'s async shape |
| 2.2 | Wire into `FaithfulnessJudge.__init__` so callers don't pass api_key when subscription is detected | attune-rag | todo | Existing `client: AsyncAnthropic | None` keyword stays for explicit injection |
| 2.3 | Update `attune-rag eval` CLI commands with the same `--auth-mode` flag | attune-rag | todo | Parity with attune-author |
| 2.4 | Tests: judge routing under each mode | attune-rag | todo | |
| 2.5 | Telemetry: annotate `subscription` vs `API` cost in attune-author's faithfulness summary log | attune-author | todo | Cross-package; depends on Phase 2 being merged |
| 2.6 | Update CHANGELOG + README in attune-rag | attune-rag | todo | |

### Phase 2 exit checklist

- [ ] Tasks 2.1–2.6 done
- [ ] Polish-fact-check Phase 3 judge runs against subscription
      without an API key
- [ ] attune-rag's standalone CLI honors the same flags as
      attune-author

---

## Phase 3 (optional): Extract shared helper

**Target PR scope:** ~200 LOC. Only happens if Phase 1 + 2
shake out enough duplication to justify a separate package.

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 3.1 | Decide: ship as `attune-ai.auth` public API (Option B) or new `attune-auth` package (Option C) | spec | todo | Driven by whether a 4th consumer (attune-help, attune-lite) needs it |
| 3.2 | Extract the adapter | varies | todo | |
| 3.3 | Update attune-author and attune-rag to consume the shared helper | attune-author + attune-rag | todo | |
| 3.4 | Deprecate the duplicate adapters in each sibling | varies | todo | Keep the duplicate as a deprecation shim for one release cycle |
| 3.5 | CHANGELOGs + READMEs in all affected packages | all | todo | |

### Phase 3 exit checklist

- [ ] Single source of truth for sibling auth routing
- [ ] Each consumer's `auth/` module has shrunk to a re-export
- [ ] Umbrella spec status moves to `complete`

---

## Cross-phase notes

### Testing strategy

- No mocking of LLM calls in integration tests. Mock at the SDK
  client boundary (`anthropic.Anthropic` and
  `claude_agent_sdk.query`) per the regen-pipeline pattern.
- Each adapter has a test that constructs it in each of the four
  states: subscription-available, api-key-available, both,
  neither. The four states cover every routing decision the
  adapter has to make.

### Rollback strategy

Each phase has its own `--auth-mode=api` opt-out. If
subscription routing causes unexpected breakage in production
regens, the operator can pin `ATTUNE_AUTHOR_AUTH_MODE=api` in
`pyproject.toml` or env without touching code. The behavior
returns to pre-spec semantics.

### Sequencing within the broader spec backlog

This spec is independent of `polish-fact-check` Phase 3 — that
PR ships now with `ANTHROPIC_API_KEY` as the only credential
path. The current spec retroactively makes the key optional for
subscribers; it doesn't gate the Phase 3 ship.
