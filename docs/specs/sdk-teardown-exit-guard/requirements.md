# Spec: SDK teardown-exit-1 guard

**Status:** EXECUTED (2026-07-20) — design approved as drafted D1–D3
and execution ARMED by the chair 2026-07-20, executed the same day;
see decisions.md execution log (was DRAFT 2026-06-26, recommitted at
2026-07-14 triage, failure class still live)
**Owner:** Patrick + agent
**Prior art (archived):**
`docs/specs/archive/sdk-error-message-fidelity/` — flagged this exact
case ("a teardown-exit-1 AFTER a successful ResultMessage arguably
should not be fatal — the SDK could surface the result") but did not
build the guard.

---

## Problem

`claude_agent_sdk.query()` streams the full message sequence of a
successful run — including a `ResultMessage(subtype="success")` carrying
the result text, cost, and usage — and **then** the underlying `claude`
subprocess can exit non-zero during teardown. The SDK's message reader
(`claude_agent_sdk/_internal/query.py`) treats any non-zero subprocess
exit as fatal and raises `Exception("Command failed with exit code 1")`
on the iteration *after* the `ResultMessage` was already yielded.

Every attune SDK-native workflow consumes the stream the same way
(`code_review`, `security_audit`, `perf_audit`, `dependency_check`,
`bug_predict`, `rag_code_gen`, `research_synthesis`, `simplify_code`):

```python
# src/attune/workflows/code_review.py:396-400 (representative)
async for message in claude_agent_sdk.query(...):
    sdk_result = collect_agent_output(message, assistant_parts, result_parts)
    if sdk_result is not None:
        run_result = sdk_result          # <- success ResultMessage captured here
run_result.result_text = build_result_text(...)   # <- skipped when the
return run_result                                   #    next iter raises
```

When the teardown exit fires, the exception propagates out of the
`async for` **before** `build_result_text` / `return`, so the
already-captured successful `run_result` is **discarded** and the
workflow reports `success=False`, cost `0.0` — a **false negative**.

### Observed impact

- Confirmed this session: a real `code-review` + `security-audit` run
  reported `success=False` / cost `0.0` nested inside a Claude Code
  session, even though (per the May investigation in
  `~/.claude/.../memory/project_sdk_workflows_blocked_nested.md`) the
  full stream including `ResultMessage(subtype="success")` was received
  before the teardown exit.
- A scrub of `ANTHROPIC_BASE_URL` + the OAuth-refresh env vars
  side-steps the teardown exit, but that is an **environment
  workaround** (forces the raw API key → real spend, manual, env-
  specific), not a fix. It quiets the symptom for local dogfooding
  only.

### Why this is subtle (the knife-edge)

The mirror-image failure already exists and must not be reintroduced:
`attune workflow run` **exits 0 even when `WorkflowResult.success` is
False** (the dispatcher swallows SDK exceptions → false **green**). A
naive "swallow Command-failed exceptions" guard would convert our false
**red** into that false **green**, masking genuine startup/runtime
failures. The guard must therefore swallow the teardown exit **only
when a successful `ResultMessage` was already observed** — never
otherwise.

---

## Goals

1. **Recover the captured success.** When the SDK raises a teardown
   "Command failed" exception *after* a successful `ResultMessage` was
   already yielded, surface the captured result instead of discarding
   it — so the workflow reports its real `success`/score/cost.
2. **Centralize the guard.** One shared wrapper in
   `agent_sdk_adapter.py` that all ~8 SDK workflows adopt with a
   one-line change, rather than per-workflow try/except duplication.
3. **Preserve fail-closed semantics.** If the SDK raises *before* any
   successful `ResultMessage` (genuine auth/quota/startup/runtime
   failure), the exception still propagates exactly as today — no
   masking, no false green.

---

## Non-goals

- **Patching `claude_agent_sdk` upstream.** Out of our control; the
  guard lives at our adapter boundary. (An upstream fix would make the
  guard a no-op, which is fine.)
- **Removing the env-scrub dogfooding note.** It stays in memory as a
  dev convenience for running SDK workflows nested in a session; it is
  not part of the product path.
- **Changing the diagnostic capture path** (`capture_subprocess_failure`
  / `ATTUNE_SDK_ERROR_PROBE`). Genuine failures still route there.
- **Re-opening the archived `sdk-error-message-fidelity` spec.** This is
  a fresh, narrowly-scoped spec that finishes that spec's deferred note.

---

## End state (Done when)

- A shared helper (name settled in design.md) wraps the SDK message
  stream and swallows a teardown "Command failed" exit **iff** a
  `subtype="success"` `ResultMessage` was already yielded; otherwise it
  re-raises unchanged.
- The ~8 SDK workflows consume the stream through that helper (one-line
  change each).
- A regression test reproduces the "success ResultMessage, then teardown
  exit-1" sequence (with a fake async stream — no live key) and asserts
  the workflow returns the captured success; a companion test asserts a
  pre-`ResultMessage` failure still raises/fails closed.
- `decisions.md` records the success signal chosen (`subtype` vs
  `is_error`), the central-wrapper location, and the false-green
  constraint.

---

## Acceptance criteria

| # | Criterion | Verify |
|---|-----------|--------|
| R1 | Teardown after success recovers | Fake stream: success `ResultMessage` then a raising teardown → workflow returns `success=True` with the captured text/cost |
| R2 | Pre-success failure still fails closed | Fake stream raising before any `ResultMessage` → exception propagates / `success=False` (no masking) |
| R3 | Genuine error ResultMessage not masked | `ResultMessage(is_error=True / subtype!="success")` then teardown → not treated as success |
| R4 | Central, low-duplication | Guard lives in `agent_sdk_adapter.py`; workflows adopt via a one-line stream wrap |
| R5 | Diagnostics preserved | The pre-success failure path still reaches `capture_subprocess_failure` / error translation unchanged |
| R6 | No collateral | Full suite green; the false-green dispatcher behavior is not worsened |
| R7 | Auditable | decisions.md records success-signal choice, wrapper location, false-green constraint; references the archived spec + the nested-SDK memory |

---

## Open questions (resolve in design.md)

- **OQ1 — Success signal.** Use `ResultMessage.subtype == "success"` or
  `not is_error`? History: SDK 0.2.102 / bundled CLI 2.1.178 emitted
  `is_error=True` *with* `subtype="success"` (fixed in 2.1.183 / SDK
  0.2.105). Which is the trustworthy success marker across pins?
- **OQ2 — Wrapper shape.** An `async def iter_agent_messages(query)`
  generator that yields through and guards the teardown, or a
  higher-order `run_agent_query(...)` that owns the whole loop? The
  former is a one-line adoption; the latter centralizes more but needs
  per-workflow options threading.
- **OQ3 — Teardown-exit matching.** How precisely to identify the benign
  teardown exception (bare `Exception("Command failed...")`) vs other
  exceptions — message substring, type, or rely solely on the
  `saw_success` gate?

---

## Cross-references

- `docs/specs/archive/sdk-error-message-fidelity/` — the spec that
  flagged this case; this spec finishes its deferred note.
- `docs/specs/archive/workflow-failure-exit-propagation/` and
  `docs/specs/pipeline-coordinator-error-fidelity/` — adjacent
  result-fidelity work.
- `~/.claude/projects/.../memory/project_sdk_workflows_blocked_nested.md`
  — the nested-SDK investigation, the env-scrub workaround, and the
  observation that the success `ResultMessage` arrives before teardown.
- Seam: `src/attune/workflows/agent_sdk_adapter.py`
  (`collect_agent_output`, `capture_subprocess_failure`);
  `src/attune/workflows/code_review.py:396-400` (representative loop).
