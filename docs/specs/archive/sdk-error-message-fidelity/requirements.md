# Spec: SDK Error Message Fidelity

> When `claude_agent_sdk.query()` fails, surface the real cause
> from the `claude` CLI's stderr instead of a generic
> "Command failed with exit code 1" wrapped in a list of plausible-
> but-wrong remediation suggestions.

**Status:** approved (2026-05-24)
**Created:** 2026-05-17
**Owner:** TBD
**Related:** [`workflow-failure-exit-propagation`](../workflow-failure-exit-propagation/) (sibling — same surface, exit-code side); [`decisions.md`](decisions.md) and [`design.md`](design.md) and [`tasks.md`](tasks.md) (built out 2026-05-24 after firefight reproduction confirmed the requirements as written)

---

## Problem statement

When a workflow's `claude_agent_sdk.query()` call fails, three
distinct layers of error masking collapse the real cause into an
unhelpful message:

1. **SDK layer:** `claude_agent_sdk._internal.query` catches the
   subprocess failure and raises a bare
   `Exception: Command failed with exit code 1 (exit code: 1)
   Error output: Check stderr output for details`. The actual
   stderr (which contains the real cause) is not attached to the
   exception.

2. **Workflow layer:** the workflow's catch wrapper calls a
   shared `sdk_error_message()` helper that presents a fixed
   menu of three plausible-but-often-wrong causes:
   ```
   - `ANTHROPIC_API_KEY` is unset, expired, or invalid
   - The `claude` CLI isn't installed or isn't on PATH
   - `claude-agent-sdk` version is incompatible
   ```
   None of these may be the actual cause.

3. **CLI layer:** `attune workflow run` exits `0` and prints the
   "What Went Wrong" voice-layer block as if the workflow
   completed normally. *(Tracked separately by
   [`workflow-failure-exit-propagation`](../workflow-failure-exit-propagation/);
   this spec focuses on layers 1 and 2.)*

### Concrete trigger (2026-05-17)

The Anthropic account's API usage cap was hit during a workflow
queue. Running `code-review` from the CLI:

- Real error from `claude --json-schema ...` direct call:
  ```
  API Error: 400 ... "You have reached your specified API
  usage limits. You will regain access on 2026-06-01 at
  00:00 UTC."
  ```
- What the user saw in the workflow output:
  ```
  - ANTHROPIC_API_KEY is unset, expired, or invalid
  - The `claude` CLI isn't installed or isn't on PATH
  - claude-agent-sdk version is incompatible
  ```

The diagnostic cost without this fix: ~15 minutes of probing
auth, PATH, and SDK version before someone thought to call
`claude` directly. The fix should make the real cause visible
in the first user-facing error.

### Affected workflows

Any workflow that calls `claude_agent_sdk.query()`. The structured-
output workflows hit this most visibly because they exercise the
`--json-schema` flag the SDK passes to `claude`:

- `code_review` (`src/attune/workflows/code_review.py`)
- `security_audit` (`src/attune/workflows/security_audit.py`)
- All other SDK-backed workflows (`test_audit`, `doc_audit`,
  `refactor_plan`, `perf_audit`, `bug_predict` SDK shells,
  `dependency_check` SDK shells, `document_gen`,
  `discovery_sweep`, plus the deep-review / secure-release
  pipelines).

---

## Scope

### In scope

- Capture the `claude` subprocess stderr inside the SDK
  invocation surface (where we own the call, not the SDK).
- Surface the captured stderr in the workflow's error result,
  visible in:
  - The CLI's "What Went Wrong" voice-layer block
  - The persisted run JSON (`~/.attune/ops/runs/<wf>/<id>.json`)
  - The dashboard's `/runs/<id>/view` page
- Add a small classification helper that recognizes a handful of
  common error shapes and short-labels them in the chip / voice
  output:
  - API quota exceeded → "API quota reached (regains 2026-06-01)"
    or similar
  - Auth missing / 401 → "Anthropic auth invalid or missing"
  - Rate limit (429) → "Rate-limited by Anthropic; retry shortly"
  - Subprocess not found → "claude CLI not on PATH"
  - Schema rejected → "Output schema not accepted by claude CLI"
  - Unknown → fall through to "see stderr below" + full text

### Out of scope

- Changing the SDK itself. We layer on top, not fork.
- Exit-code propagation — covered by
  [`workflow-failure-exit-propagation`](../workflow-failure-exit-propagation/).
- Retry / backoff logic on transient errors. Surface the cause;
  let the user retry.
- Predicting every possible error class. Five-ish known shapes
  + "see stderr" fallback is sufficient.

---

## Approach (sketch — to be refined in `decisions.md`)

The SDK's `subprocess_cli.py` builds the `claude` invocation and
captures the subprocess via `anyio`. We don't own that file.
**Two implementation paths**, both reasonable; pick during design:

### Path A — Wrap the SDK call site

In each workflow's `_run_agent_*` method (or in the shared
`agent_sdk_adapter`), wrap the `async for message in
claude_agent_sdk.query(...)` loop with a try/except that, on the
generic `Exception: Command failed ...`:

1. Re-runs the `claude` CLI with the same flags but in a
   capture-stderr mode (`subprocess.run` with `capture_output=True`)
   to extract the real error.
2. Re-raises as a typed `SdkSubprocessError(message, stderr,
   classified_kind)`.

Pro: contained to our code, no SDK fork.
Con: double-spend on the second invocation (could be expensive
on rate-limited paths; cheap on quota-exhausted paths since the
second call also fails fast).

### Path B — Monkeypatch the SDK transport

Patch `claude_agent_sdk._internal.transport.subprocess_cli` at
import time to capture stderr and stash it on the raised
exception. Workflow catch blocks read it from
`exc.__cause__.stderr` (or similar attr).

Pro: single subprocess call, real stderr available everywhere.
Con: fragile across SDK upgrades, monkey-patch smell, harder to
test.

**Recommendation:** Path A. Cheaper to maintain. The double-call
cost only fires on failure paths and the second call exits in
sub-second.

---

## Acceptance criteria

1. Reproduce today's symptom: cap the account API quota (or use
   an invalid API key, or any other consistent failure). Run
   `attune workflow run code-review --path <some.py>`. The
   workflow output's "What Went Wrong" block names the **actual
   cause** (API quota, invalid auth, etc.), not the three-cause
   menu.
2. The persisted run JSON contains a `sdk_stderr` field (or
   equivalent) with the captured text.
3. The dashboard's `/runs/<id>/view` page renders the captured
   stderr in a collapsible block.
4. Unit test: mock `claude_agent_sdk.query` to raise
   `Exception("Command failed ...")` and ensure the wrapper
   re-invokes capture-mode and surfaces the real error.
5. Integration test: end-to-end with `ANTHROPIC_API_KEY=invalid`,
   the workflow surfaces "Anthropic auth invalid or missing"
   rather than the generic three-cause list.
6. No regression on the happy path — workflows that succeed
   still produce the existing structured output.

---

## Tasks (rough)

| # | Task | Effort |
|---|------|--------|
| 1 | Add `SdkSubprocessError` exception + classifier helper in `agent_sdk_adapter.py` | 1h |
| 2 | Replace `sdk_error_message()` in code-review + security-audit + four other SDK shells with the new classifier output | 1h |
| 3 | Persist `sdk_stderr` in run JSON; thread through `RunnerService` | 30m |
| 4 | Render captured stderr in `/runs/<id>/view` (collapsible) | 30m |
| 5 | Unit tests for each classifier branch + happy-path regression | 1h |
| 6 | Manual verification: 2-3 induced failure modes | 30m |

**Estimated total:** 4–5 hours.

---

## Open questions

1. Should the classifier be table-driven (regex map in a config
   file) or hard-coded? Table-driven adds extensibility; hard-
   coded is one less thing to maintain. Lean hard-coded for v1;
   table-driven if the list grows past ~8 shapes.
2. Should the captured stderr be redacted (per the
   `session_redaction` module's rules) before persisting? It
   could carry API keys in some configurations. Lean yes —
   reuse the existing redactor.
3. Does the chip-classifier defense-in-depth (PR #366) get
   simplified once this lands? It currently scans log text for
   `Traceback` / `What Went Wrong`; with structured stderr
   capture, it could read the typed classification instead.
