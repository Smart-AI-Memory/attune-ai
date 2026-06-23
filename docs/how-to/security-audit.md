# Security Audit

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

<!-- attune-generated: source_hash=e6418a3912ca1198d747373f96c129051dd6130394ad9f787b25fd12acf68e4a feature=security-audit kind=how-to generated_at=2026-06-23 -->
