# Spec: Subscription-First Auth for Sibling Packages — Tasks

**Status**: complete (2026-06-11) — Phase 0 shipped (`findings.md`); Phase 1 shipped (attune-author #55, v0.16.0 on PyPI); Phase 2 shipped end-to-end (attune-rag #183 + v0.7.0 on PyPI; 2.5 in attune-author #57). Phase 3 (shared-helper extraction) intentionally not taken — two mirrored adapters, revisit at a third consumer.

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
| 0.1 | Probe: does `claude_agent_sdk.query()` work inside Claude Code without `ANTHROPIC_API_KEY`? | attune-ai | **done** | ✅ Yes. Probe succeeded with empty API key. See `findings.md` Q1. |
| 0.2 | Probe: same as 0.1, but from a child subprocess spawned by Claude Code | attune-ai | **done** | ✅ Yes. Probe runs as a subprocess via the Bash tool; succeeded. Critical result. See `findings.md` Q2. |
| 0.3 | Probe: identify env vars / config files Claude Code sets that advertise its presence | attune-ai | **done** | Found `CLAUDECODE=1` (boolean) + `CLAUDE_CODE_SESSION_ID=<uuid>` (session-specific). See `findings.md` Q3. |
| 0.4 | Audit: list every sibling package that makes direct Anthropic API calls | attune-ai | **done** | attune-author (polish), attune-rag (judge + RAG answer-gen). attune-help and attune-lite have no LLM call sites. See `findings.md`. |
| 0.5 | Write `findings.md` in this spec dir | attune-ai | **done** | Covers all four open design questions + sibling audit + caveats. |
| 0.6 | Pre-commit Phase 1 design decisions in `decisions.md` | attune-ai | **done** | Design option = A; detection signal = `CLAUDECODE=1`; detection default = opt-out. |

### Phase 0 exit checklist

- [x] `scripts/probe_subscription_routing.py` lands and is
      runnable both inside and outside Claude Code
- [x] `findings.md` answers the four open design questions
      from `design.md`
- [x] `decisions.md` has a pre-committed decision row for each
      open question
- [x] Spec status moves from `draft` to `approved`

---

## Phase 1: Shim layer in attune-author (smallest blast radius)

**Target PR scope:** ~300 LOC including tests. Depends on Phase 0.

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1.1 | Pick design option (A/B/C) from Phase 0 findings | attune-author | **done** | Option A, decided in Phase 0 (see decisions.md) |
| 1.2 | Implement the chosen adapter / wrapper in attune-author | attune-author | **done** | `src/attune_author/auth.py` (single module). Subscription subprocess runs `setting_sources=[]` so user/project hooks/CLAUDE.md can't pollute the stream-json channel. PR #55 |
| 1.3 | Wire the adapter into `polish._call_llm` | attune-author | **done** | `auth.call_llm` is the chokepoint; API path byte-identical incl. cache telemetry |
| 1.4 | Add `--auth-mode={auto,api,sub}` to `attune-author generate` and `regenerate` | attune-author | **done** | Bridged via `ATTUNE_AUTHOR_AUTH_MODE` (mirrors the `--fact-check` env-bridge pattern; a pre-set env var wins over the flag) |
| 1.5 | Add `attune-author auth status` CLI command | attune-author | **done** | Reports detection signals + resolved route; exits 1 on forced-sub-unavailable |
| 1.6 | Telemetry: annotate cost as `(subscription)` or `(API)` in the regen summary log | attune-author | **done** | Shipped as `Polish LLM calls: N (subscription), M (API)` — the polish path has no per-call cost estimate to annotate; the `$X (subscription)` format remains for the Phase 2 judge line |
| 1.7 | Tests: routing under each mode (auto-sub, auto-api, forced-sub, forced-api, no-creds) | attune-author | **done** | 30 tests in `tests/test_auth_routing.py`; suite conftest pins `ATTUNE_AUTHOR_AUTH_MODE=api` + clears `CLAUDECODE` so running the suite inside Claude Code can't auto-route un-mocked polish calls to real subscription calls |
| 1.8 | Tests: failure modes (subscription expires mid-run, mixed auth) | attune-author | **done** | Auto falls back to API on sub failure; forced sub never falls back; sub errors get the `sk-ant-` redaction contract |
| 1.9 | Update CHANGELOG + README | attune-author | **done** | New README "Authentication" section; `claude-agent-sdk>=0.1.60` added to the `[ai]` extra |

### Phase 1 exit checklist

- [x] Tasks 1.1–1.9 done (attune-author PR #55, 2026-06-10)
- [x] A subscriber can run `attune-author generate <feat>`
      without `ANTHROPIC_API_KEY` and see "(subscription)"
      cost in the log — live receipt: keyless `polish_template`
      routed sub in 24.3s, telemetry `{sub_calls: 1, api_calls: 0}`,
      real polished output
- [x] An API-key-only user sees no behavior change (API path
      byte-identical; full suite 1031 passed)
- [x] `auth status` correctly reports the active mode (verified
      live in subscription, API-no-key, and forced-sub-unavailable
      states)

**Full-regen receipt at scale (2026-06-11, attune-author v0.16.0
wheel from PyPI):** `attune-author regenerate --auth-mode sub`
against attune-ai's `.help` (4 stale features), keyless
(`ANTHROPIC_API_KEY=""`), `CLAUDECODE=1` — telemetry
`Polish LLM calls: 12 (subscription), 0 (API)`, exit 0.
Rate-limit measurement (Phase 0 caveat #1): 12 calls over 15m16s
(~76 s/call), zero 429/overload/rate-limit events. Per-kind skip
(polish-cost lever 2) held under subscription routing: 12 calls
instead of 44 (3 changed kinds per feature; 8 skipped each).

---

## Phase 2: Same for attune-rag (faithfulness judge)

**Target PR scope:** ~250 LOC. Depends on Phase 1 (reuses the
adapter shape; may extract to a shared helper).

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 2.1 | Mirror Phase 1's adapter inside attune-rag (or import from a shared package per Option B/C) | attune-rag | **done** | `attune_rag.auth` (PR #183) — async-native, Option A (mirror, no shared package yet). Schema guarantee preserved via Agent SDK `output_format` json_schema → `ResultMessage.structured_output`; `max_turns=2` (structured output costs the CLI an extra turn — found live, drift-guarded in tests) |
| 2.2 | Wire into `FaithfulnessJudge.__init__` so callers don't pass api_key when subscription is detected | attune-rag | **done** | `auth_mode=` param; injected client always wins (API route); sub route skips `AsyncAnthropic` construction; auto falls back to API on sub failure, forced sub never falls back |
| 2.3 | Update `attune-rag eval` CLI commands with the same `--auth-mode` flag | attune-rag | **done** | Premise correction: no `attune-rag eval` subcommand exists — the judge's CLI surface is `attune-rag-benchmark`, which got `--auth-mode {auto,api,sub}` (judge route only; answer GENERATION via `ClaudeProvider` stays API-key-only per the Phase-0 scope note, so the `--with-faithfulness` key gate stays) |
| 2.4 | Tests: judge routing under each mode | attune-rag | **done** | 16 tests in `tests/unit/test_auth_routing.py`; suite conftest pins `ATTUNE_RAG_AUTH_MODE=api` + clears `CLAUDECODE` (mirrors attune-author) |
| 2.5 | Telemetry: annotate `subscription` vs `API` cost in attune-author's faithfulness summary log | attune-author | **done** | attune-author #57 (2026-06-11): `Faithfulness judge auth: N call(s) subscription, M API` after the cost line; graceful skip on attune-rag <0.7; `[rag]` cap widened `<0.3`→`<0.8` |
| 2.6 | Update CHANGELOG + README in attune-rag | attune-rag | **done** | New README "Authentication" section; `claude-agent-sdk>=0.1.63` added to `[claude]` extra |

### Phase 2 exit checklist

- [x] Tasks 2.1–2.6 done (2.1–2.4 + 2.6 in attune-rag #183,
      released as v0.7.0; 2.5 in attune-author #57)
- [x] Judge runs against subscription without an API key — live
      receipt (2026-06-11): route=sub, keyless, 14.6 s, judge
      caught a planted fake-flag hallucination (score 0.5,
      2 supported / 2 unsupported), telemetry
      `{sub_calls: 1, api_calls: 0}`. (The polish-fact-check
      Phase 3 wording resolves to this once attune-rag 0.7.0 is
      released and attune-author picks it up.)
- [x] attune-rag's standalone CLI honors the same flags as
      attune-author (`attune-rag-benchmark --auth-mode`; the
      spec's named `attune-rag eval` surface doesn't exist —
      see 2.3 note)

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
