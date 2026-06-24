---
name: security-audit
source: content/features/security-audit.md
tags:
- security
- audit
- owasp
- scanning
- cve
type: task
---

# Audit code for vulnerabilities with four Agent SDK subagents

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
