---
feature: security-audit
summary: Audit code for vulnerabilities with four Agent SDK subagents
tags: [security, audit, vulnerabilities]
source_globs:
  - src/attune/workflows/security_audit.py
nav:
  help: security-audit
  mkdocs:
    how-to: how-to/security-audit
    architecture: architecture/security-audit
    reference: reference/security-audit
---

## Overview

Security-audit scans a codebase for vulnerabilities and reports
them by severity with prioritized remediation. It is **SDK-native**:
`SecurityAuditWorkflow` delegates the analysis to four specialized
Claude Agent SDK subagents and synthesizes their findings into one
report — an overall security score, findings grouped CRITICAL /
HIGH / MEDIUM / LOW, and an effort-ranked remediation plan.

Like its sibling bug-predict, it **predicts** rather than proves:
the four subagents apply LLM judgment over the code (via Read /
Glob / Grep), so a finding is a lead to verify, not a confirmed
exploit. Treat a CRITICAL finding as "audit this first," not "this
is definitely exploitable."

You reach security-audit four ways, all of which run the same
workflow:

- the **`/security-audit`** skill, inside a Claude Code
  conversation;
- the CLI — **`attune workflow run security-audit`**;
- the **`security_audit`** MCP tool (one required `path`
  argument);
- the Python API — `await SecurityAuditWorkflow().execute(...)`,
  documented here for wiring an audit into a hook, a CI gate, or a
  custom tool.

The audit workflow is self-contained — it owns scanning and
report synthesis only. Alerting, telemetry storage, and
monitoring live in a **separate** subsystem (`attune.monitoring`)
and are not part of this feature.

## Concepts

### Four subagents, one synthesized report

`SecurityAuditWorkflow.execute` issues a single
`claude_agent_sdk.query` whose options define four subagents, each
scoped to `Read` / `Glob` / `Grep`:

| Subagent | What it looks for |
|----------|-------------------|
| `vuln-scanner` | `eval`/`exec` usage, SQL injection, XSS, path traversal, command injection, and insecure deserialization. Reports file, line, severity, and remediation advice. |
| `secret-detector` | Hardcoded API keys, passwords, tokens, private keys, database credentials, and sensitive environment variables committed to source — plus how to externalize each. |
| `auth-reviewer` | Missing auth checks, broken access control, insecure session management, weak password policies, and privilege-escalation risks. |
| `remediation-planner` | Reviews all findings and builds a prioritized fix plan, grouped by effort (quick wins / medium / major refactors), with time estimates and inter-fix dependencies. |

The orchestrator then synthesizes all four into one report with
three sections — **Summary** (an overall 0–100 security score plus
a 2–3 sentence posture summary), **Security** (consolidated
findings grouped CRITICAL / HIGH / MEDIUM / LOW), and
**Suggestions** (remediation steps ordered by priority, each with
an effort estimate).

### Depth controls the budget — and deep engages extended thinking

`execute` takes a `depth` of `"quick"`, `"standard"` (default),
or `"deep"`. Depth maps to the maximum agent turns and a per-run
cost cap:

| Depth | Max agent turns |
|-------|-----------------|
| `quick` | 10 |
| `standard` | 20 |
| `deep` | 40 |

An unrecognized depth falls back to the standard budget (20
turns). A `deep` audit additionally engages a token-aware task
budget and **extended thinking** (with high reasoning effort), so
the remediation-planner and architecture-level reasoning get more
room — at higher cost.

### Findings survive synthesis

Two mechanisms keep findings from being lost in the
orchestrator's synthesis step:

- the query runs with a structured `output_format`, so findings
  parse into categories reliably rather than depending on prose
  formatting; and
- after the run, the per-subagent transcripts are recovered from
  the session and appended to the report under a
  **"## Subagent findings"** heading — so a finding a subagent
  surfaced is preserved even if the synthesis under-reports it.
  The raw transcripts are also attached to the result's
  `metadata["subagent_transcripts"]`.

### `execute` is async, and honors only `path` and `depth`

`execute` is a coroutine — `await` it (or drive it with
`asyncio.run`). Calling it without awaiting is the most common
mistake.

It reads exactly two keyword arguments: `path` (required) and
`depth` (default `"standard"`). Any other keyword is ignored. An
empty or missing `path` returns a failed `WorkflowResult` rather
than raising.

### The result is a `WorkflowResult`

`execute` returns a `WorkflowResult` (from `attune.workflows`).
The synthesized report lands in `final_output` — a serialized
report when the findings parse, or the raw markdown otherwise —
with a short `summary`, a `suggestions` list, the `cost_report`,
the `provider`, and a `metadata` dict echoing `path`, `depth`,
`max_turns`, and the recovered `subagent_transcripts`. On failure,
`success` is `False` and `error` / `error_type` carry the reason.

## Quickstart

Audit a directory and print the synthesized report.
`SecurityAuditWorkflow.execute` is an async coroutine, so drive it
with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import SecurityAuditWorkflow


async def main() -> None:
    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed audit
    print(result.summary)          # short posture summary
    print(result.final_output)     # the full synthesized report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for a
longer, extended-thinking audit.

## Tasks

### Audit a path from the CLI

**Goal:** run a one-off audit over a directory without writing any
Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run security-audit --path src/

# Deep audit (extended thinking), JSON output for a CI gate:
attune workflow run security-audit --path src/ --depth deep --json

# Cost-saving pass (unpinned subagents run on Haiku):
attune workflow run security-audit --path src/ --cheap
```

**Verify:** `--path` / `-p` defaults to the current directory;
`--depth` accepts `quick`, `standard`, or `deep`; `--json` / `-j`
emits machine-readable output; `--cheap` forces every subagent
without an explicit model onto Haiku for that run. Use
`attune workflow info security-audit` to confirm registration, and
`attune workflow list` to see it alongside the other workflows.

### Call the audit from Python

**Goal:** drive security-audit from a hook or CI gate and act on
the result.

**Steps:**

```python
import asyncio

from attune.workflows import SecurityAuditWorkflow


async def main() -> None:
    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(path="src/api/", depth="deep")

    if not result.success:
        print("audit failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed
audit returns `success=True` with the report in `final_output`;
a failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns` used, plus the recovered `subagent_transcripts`.

### Focus the audit with a prompt suffix

**Goal:** steer the audit toward a concern without replacing the
built-in orchestrator behavior.

**Steps:**

```python
import asyncio

from attune.workflows import SecurityAuditWorkflow


async def main() -> None:
    workflow = SecurityAuditWorkflow(
        system_prompt_suffix=(
            "Prioritize authentication and secret-handling code. "
            "Call out anything touching the login flow."
        ),
    )
    result = await workflow.execute(path="src/auth/")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** `system_prompt_suffix` is a keyword-only constructor
argument appended to the orchestrator's system prompt. The four
subagents still run their normal analysis; the suffix only steers
the orchestrator. The empty-string default leaves behavior
unchanged (this is the hook discovery-sweep's `SecurityAuditSource`
uses to augment the prompt per instance).

## Reference

Security-audit's public surface is the `SecurityAuditWorkflow`
class, re-exported from `attune.workflows`. `WorkflowResult` comes
from `attune.workflows` as well.

### `SecurityAuditWorkflow` — `attune.workflows.security_audit`

| Symbol | Purpose |
|--------|---------|
| `SecurityAuditWorkflow(*, system_prompt_suffix="", **kwargs)` | Construct the workflow. `system_prompt_suffix` (keyword-only) is appended to the orchestrator's system prompt; the empty default preserves stock behavior. Other kwargs pass to `BaseWorkflow`. |
| `SecurityAuditWorkflow.execute(**kwargs)` | **Async.** Run the audit. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`); other kwargs are ignored. Returns a `WorkflowResult`. |
| `SecurityAuditWorkflow.name` | The registered slug, `"security-audit"`. |
| `SecurityAuditWorkflow.stages` | `["agent-audit"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → budget

| Depth | Max turns | Behavior |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | Thorough; additionally engages a token-aware budget and extended thinking. |

### The four subagents

| Subagent | Domain |
|----------|--------|
| `vuln-scanner` | Injection, `eval`/`exec`, XSS, path traversal, command injection, insecure deserialization. |
| `secret-detector` | Hardcoded credentials, API keys, tokens, private keys, sensitive env vars in source. |
| `auth-reviewer` | Missing auth, broken access control, session weaknesses, privilege escalation. |
| `remediation-planner` | Prioritized fix plan grouped by effort, with time estimates and dependencies. |

### `WorkflowResult` fields read after an audit

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the audit completed. |
| `final_output` | `Any` | The synthesized report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short posture summary. |
| `suggestions` | `list[NextAction]` | Prioritized remediation actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run. |
| `metadata` | `dict` | Echoes `path`, `depth`, `max_turns`, and `subagent_transcripts`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/security-audit` in a Claude Code conversation. |
| CLI | `attune workflow run security-audit --path <p> [--depth quick\|standard\|deep] [--json] [--cheap]`. |
| MCP tool | `security_audit` — one required `path` argument; runs at standard depth (the handler does not pass `depth`). |
| Python | `await SecurityAuditWorkflow().execute(path=<p>, depth=<d>)`. |

## Comparison

Security-audit and **bug-predict** are sibling SDK-native
workflows — both scan the same codebase through Agent SDK
subagents, both reached with `attune workflow run <name>`, both
predictive (LLM judgment) — but they answer different questions.

| | `security-audit` | `bug-predict` |
|---|---|---|
| **Question answered** | "Where are the security vulnerabilities?" | "Where are bugs most likely to be?" |
| **Subagents** | Four: vuln-scanner, secret-detector, auth-reviewer, remediation-planner | Three: pattern-scanner, risk-correlator, prevention-advisor |
| **Focus** | Injection, secrets, auth/access control, path traversal | Correctness-risk hotspots: null refs, type mismatches, race conditions, resource leaks |
| **Severity scale** | CRITICAL / HIGH / MEDIUM / LOW | HIGH / MEDIUM / LOW |
| **Slug** | `attune workflow run security-audit` | `attune workflow run bug-predict` |

Reach for **security-audit** when the concern is a vulnerability
surface — secrets, injection, access control; reach for
**bug-predict** for a broad correctness-risk triage. They overlap
on `eval`/`exec` (both flag it) and pair well on a pre-release
sweep.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'SecurityAuditWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `WorkflowResult.success` is `False`, `error` is `"path argument is required"` | `execute` called with empty or missing `path` | Pass a non-empty `path` | high |
| `error` reads `"Agent SDK unavailable: ..."` | `claude_agent_sdk` is not importable | Install the Agent SDK dependency for the environment | high |
| `error` reads `"Agent SDK connection failed: ..."` | A `ConnectionError` / `TimeoutError` reaching the SDK | Check connectivity / retry; `transient` is set when a retry is reasonable | medium |
| Audit stops early / partial report | The depth's agent-turn or budget cap was reached | Use a shallower path or accept a deeper (costlier) run | medium |
| `metadata["subagent_transcripts"]` is empty | The session transcript could not be recovered for this run | The synthesized `final_output` is still authoritative; transcripts are a supplement | low |
| A finding looks like a false positive | Findings are LLM predictions, not verified exploits | Confirm against the cited file/line before acting | medium |

### Risk areas

- **The async call is easy to get wrong.** `execute` is the only
  public method and it is a coroutine. Forgetting to `await` it is
  the single most common mistake.
- **Findings are predictions, not proofs.** The four subagents
  apply LLM judgment; a CRITICAL finding means "audit this first,"
  not "this is a confirmed vulnerability." Verify before acting —
  and never treat a clean report as a security guarantee.
- **Deep audits cost more.** `deep` engages extended thinking and
  a larger budget; reserve it for high-risk areas rather than
  whole-repo sweeps.

### Diagnosis order

1. Confirm you are awaiting: `result = await workflow.execute(
   path="src/")` inside an `async def` or `asyncio.run`.
2. Check `result.success`; if `False`, read `result.error` and
   `result.error_type`.
3. On an SDK error, inspect `result.metadata` for the captured
   `sdk_stderr` / SDK error kind.
4. Confirm the scope: `result.metadata` echoes the `path`,
   `depth`, and `max_turns` actually used.
5. Cross-check findings against `metadata["subagent_transcripts"]`
   to see which subagent surfaced each.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic
> source of truth fed by four channels — unmatched user queries,
> telemetry error-frequency, GitHub issues, and these
> author-curated seeds — merged, deduplicated, and
> frequency-ranked by the FAQ Generator (see doc-stack D3, and the
> help-docs-single-source spec's decisions.md D6). This section is
> **not** projected verbatim as the FAQ; it contributes the
> feature's author-curated seed questions.

- **Q:** Does security-audit fix the vulnerabilities it finds?
  **A:** No. It finds and prioritizes them and proposes a
  remediation plan; applying fixes is a separate step you take.
- **Q:** Is there an `attune security-audit` command?
  **A:** No dedicated subcommand — run it as
  `attune workflow run security-audit`, or use the
  `/security-audit` skill or the `security_audit` MCP tool.
- **Q:** Which calls are async?
  **A:** `execute` is the only public method and it is a
  coroutine — `await` it or use `asyncio.run`.
- **Q:** What does `depth` change?
  **A:** The agent-turn budget (quick 10, standard 20, deep 40)
  and the cost cap; `deep` additionally turns on extended thinking
  for richer remediation reasoning.
- **Q:** Does a clean report mean my code is secure?
  **A:** No. Findings are LLM predictions, not proofs, and a clean
  pass is not a guarantee — use the audit as one input, not a
  certification.

## Notes & tips

- **Depend on the documented public surface.** The supported API
  is `SecurityAuditWorkflow` (its constructor and async `execute`)
  plus the `WorkflowResult` it returns. Names with a leading
  underscore — `_run_agent_audit`, `_SUBAGENT_NAMES` — are
  internal and may change.
- **Use `metadata["subagent_transcripts"]` to attribute findings.**
  The synthesized report is the headline; the recovered transcripts
  show which of the four subagents raised each finding, which helps
  when triaging.
- **Start shallow, then go deep on the hot spots.** Run `standard`
  broadly, and spend a `deep` (extended-thinking) audit only on the
  modules that came back risky.
- **Use `--cheap` for routine CLI runs.** It forces unpinned
  subagents onto Haiku, trading some depth for cost.
- **Monitoring is a separate subsystem.** Alerting and telemetry
  storage live in `attune.monitoring`, not here — this feature is
  the audit workflow only.

## Design & extension

### Design decisions

- **SDK-native, four specialized subagents.** Since v4.2.0,
  security-audit is a single `claude_agent_sdk.query` with four
  subagents — `vuln-scanner`, `secret-detector`, `auth-reviewer`,
  and `remediation-planner`. Splitting the work keeps each
  subagent's context focused; the cost is an extra synthesis step
  in the orchestrator.
- **Findings are recovered, not just synthesized.** The run uses a
  structured `output_format`, and the per-subagent transcripts are
  pulled from the session and appended under "## Subagent
  findings" — so the orchestrator's synthesis is no longer a single
  point of data loss.
- **Prediction, not certification, is the contract.** The workflow
  returns LLM-judged findings; it deliberately trades a scanner's
  precision for breadth and prioritized remediation. This is why
  findings are framed as leads to verify, never a security
  guarantee.
- **The result is data, not print output.** `execute` returns a
  `WorkflowResult` (report in `final_output`, plus `summary`,
  `suggestions`, `cost_report`, and `metadata`); the CLI, MCP, and
  skill surfaces all render that same result.

### Extension points

- **Steer a single run:** pass `system_prompt_suffix` to the
  constructor to append instructions to the orchestrator prompt
  without subclassing — the pattern discovery-sweep's
  `SecurityAuditSource` uses.
- **Change the budget:** choose `depth` (`quick` / `standard` /
  `deep`) to trade coverage against cost; `deep` adds extended
  thinking, and `--cheap` on the CLI forces unpinned subagents
  onto Haiku.
- **Add a scan category:** the four subagent names are a
  module-level constant (`_SUBAGENT_NAMES`) and the task prompt is
  a module template; a new category is a new subagent definition
  plus a synthesis-section update in `security_audit.py`.
