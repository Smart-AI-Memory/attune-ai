# Phase 0 Findings

**Run date**: 2026-05-16
**Run context**: inside a Claude Code session (CLI v2.1.117)
**Probe**: `scripts/probe_subscription_routing.py`
**Raw artifacts**: `/tmp/probe_full.json`, `/tmp/probe_minimal.json`
(not committed — re-run the probe to regenerate)

---

## Summary

`claude_agent_sdk.query()` is the subscription-routing mechanism.
When invoked from a process running under Claude Code, it
succeeds against the user's Claude subscription without an
`ANTHROPIC_API_KEY` in the environment. The direct
`anthropic.AsyncAnthropic` SDK requires the key and has no
subscription-aware path. Detection is one env var:
**`CLAUDECODE=1`**.

This validates Option A from `design.md` (per-sibling Agent-SDK
shim) and dismisses the more elaborate Options B and C as
unnecessary for the v1 implementation.

---

## Answers to the four open design questions

### Q1: Does `claude_agent_sdk.query()` work inside Claude Code without `ANTHROPIC_API_KEY`?

**Yes.** The probe ran with `ANTHROPIC_API_KEY` present but
empty (`len=0`). `claude_agent_sdk.query(prompt="say hi")`
returned a complete response — addressed me by name, even
referenced the existing CLAUDE.md session-start protocol. The
direct Anthropic SDK call in the same process failed with
"ANTHROPIC_API_KEY not set" (the empty-string fallthrough), so
the Agent SDK is clearly NOT consuming the env var to make this
call.

### Q2: Does the same call work from a child subprocess of Claude Code?

**Yes** — the probe itself runs as a subprocess (the Bash tool
spawns `python scripts/probe_subscription_routing.py`) and
succeeds. So a sibling like `attune-author generate` invoked
either as a CLI from a Claude Code shell OR via the Bash tool
inside a Claude Code session inherits the subscription auth via
`claude_agent_sdk`.

This is the critical result. Pre-probe, the assumption was that
session auth might be tied to the Claude Code process itself and
not crossable. It crosses cleanly.

### Q3: What env var / config signal advertises Claude Code's presence?

**`CLAUDECODE=1`** is the cleanest signal — a boolean string set
by Claude Code in every subprocess it spawns.

Secondary signal: **`CLAUDE_CODE_SESSION_ID=<uuid>`** is also
set and matches the on-disk JSONL filename at
`~/.claude/projects/<encoded>/<session-id>.jsonl`. This is more
specific than just "running under Claude Code" — it identifies
*which* session. Not needed for the routing decision, but useful
for telemetry attribution.

Additional environment signals observed:

- `ANTHROPIC_BASE_URL=https://api.anthropic.com` — default;
  Claude Code does NOT proxy through a different host.
- `ANTHROPIC_API_KEY=""` — set to an empty string. This explains
  the earlier session's "invalid x-api-key 401" error when a
  literal placeholder was exported: an empty key fails fast at
  the API. Code that probes `if os.environ.get(...)` correctly
  treats this as "no key".
- `~/.claude/` exists and contains `projects/`. No `auth.json`
  or `credentials.json` was found — Claude Code stores auth in
  macOS Keychain (not visible to the probe), and the on-disk
  state is only session metadata.

### Q4: Does the judge's async API need to change?

**No.** `claude_agent_sdk.query` is an async generator —
identical async shape to `FaithfulnessJudge.score`. The
adapter is a straight swap of the SDK call inside the existing
`async def score(...)`; no caller changes.

The shape difference to absorb: `anthropic.AsyncAnthropic`
returns a `Message` object whose `.content` is a list of
content blocks; `claude_agent_sdk.query` yields a stream of
`AssistantMessage`/`ResultMessage` objects whose `.content`
list contains `TextBlock`s. The judge collects text from
both — the existing
[`collect_agent_output` helper in `attune-ai`](https://github.com/Smart-AI-Memory/attune-ai/blob/main/src/attune/workflows/agent_sdk_adapter.py)
already handles this idiom and is the pattern siblings can mirror.

---

## Sibling-package audit (task 0.4)

Direct Anthropic API call sites found:

| Package | Call site | Pattern |
|---|---|---|
| `attune-author` | `src/attune_author/doc_gen/_anthropic.py` (polish-pass) | `anthropic.Anthropic(api_key=...)` sync |
| `attune-rag` | `src/attune_rag/eval/faithfulness.py` (judge) | `anthropic.AsyncAnthropic(api_key=...)` |
| `attune-rag` | `src/attune_rag/providers/claude.py` (`ClaudeProvider`, RAG answer-generation) | `anthropic.AsyncAnthropic` — outside this spec's scope unless we also want to subscription-route generation |
| `attune-help` | _none observed_ | reader-only package; no LLM calls |
| `attune-lite` | _none observed_ | minimal install variant |

The polish + faithfulness-judge calls are the priority. RAG
answer-generation is a follow-up if the same UX seam appears.

---

## Recommendation for Phase 1

Implement **Option A** from `design.md` — a small per-sibling
adapter that:

1. Reads `CLAUDECODE` from the environment.
2. When set (and `claude_agent_sdk` is importable), routes
   through `claude_agent_sdk.query()`.
3. Otherwise, falls back to the existing direct-SDK path (which
   requires `ANTHROPIC_API_KEY`).
4. Exposes an explicit override via `--auth-mode={auto,api,sub}`
   CLI flag and `ATTUNE_AUTHOR_AUTH_MODE` env var.

Estimated per-sibling adapter size: ~50–80 LOC. Mostly the
shape-coercion code that maps Agent-SDK message blocks into
something the existing call site expects.

**Don't extract to a shared package yet.** Two adapters with the
same shape isn't enough duplication to justify Phase 3 of the
spec. Revisit after attune-author and attune-rag each ship their
adapter.

---

## Caveats / known unknowns

1. **Subscription rate limits.** This probe made one tiny call.
   We haven't measured whether a full `attune-author regenerate`
   (potentially dozens of LLM calls in 30 seconds) would hit a
   subscription-level rate limit that the API path wouldn't. If
   it does, the auto-mode could still degrade by falling back to
   the API path on rate-limit errors — but it's worth measuring
   in Phase 1.
2. **Token accounting visibility.** Subscription-routed calls
   probably won't appear in the Anthropic billing dashboard
   under the user's API account — they're billed against the
   subscription. The Phase 3 telemetry log "(subscription)"
   annotation needs to be the user's *only* source of truth for
   "did this go through my subscription?". Acceptable trade-off.
3. **Non-Claude-Code shells.** A subscriber running a sibling
   from a plain terminal (no `CLAUDECODE=1`) will fall back to
   the API path. That's expected, but documenting it as a known
   case is necessary — otherwise users will see "I have a
   subscription, why am I being charged?" surprises.
4. **Probe didn't test the in-shell-no-key case.** The probe
   ran inside a Claude Code session; we haven't verified the
   "plain terminal, no key" path produces the expected
   `NoCredentialsError`. Phase 1 implementation should add this
   to the auth-status command tests.

---

## Re-running

```bash
# Inside Claude Code session
python scripts/probe_subscription_routing.py
# or, for signature-only without LLM calls:
python scripts/probe_subscription_routing.py --probe minimal
```

If the routing mechanism changes upstream (Claude Code CLI
bumps, Agent SDK version skew, env-var rename), re-running this
probe gives a quick diff against the recorded findings here.
