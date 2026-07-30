---
type: tutorial
name: fix-test
tags: [fix-test, testing, hooks, automation, debugging]
source: plugin/skills/fix-test/SKILL.md
---

# Tutorial: Fix a Failing Test — Then Make It Automatic

In this tutorial you'll fix a real failing test with attune-ai's
`/fix-test` skill, then wire a Claude Code hook so every future edit
runs its matching test immediately — failures get caught (and fixed)
the moment they're created, not at the next full suite run.

**You'll need:** Claude Code with the attune-ai plugin installed
(`pip install attune-ai`), and a Python project with a pytest suite.

**Time:** about 10 minutes.

---

## Part 1 — See the failure

Every fix starts with a reproducible failure. Run the failing test
directly so you know exactly what Claude will see:

```bash
uv run pytest tests/unit/test_pricing.py -v --tb=short
```

```text
FAILED tests/unit/test_pricing.py::test_discount_applies -
AssertionError: assert 90.0 == 85.0
```

If you don't have a failing test handy and want to follow along,
break one on purpose — change an expected value in any assertion.

## Part 2 — Fix it with /fix-test

In Claude Code, run:

```text
/fix-test tests/unit/test_pricing.py
```

The skill scopes before it acts — expect two questions:

1. **Target** — which test is failing (you just gave it), or whether
   it should hunt for failures itself.
2. **Context** — did this start failing after a recent change, or
   has it been broken a while? (This routes the diagnosis: assertion
   drift after a refactor is a different fix than a stale mock.)

Then it loops: run the test, classify the root cause, apply a
targeted fix, re-run — up to **3 attempts** before it stops and
reports honestly. The root-cause classes it recognizes:

| Error pattern | Likely root cause | Typical fix |
| --- | --- | --- |
| `ModuleNotFoundError` | Import path changed | Update the import |
| `AttributeError` on a mock | Mock target wrong | Match the real import path |
| `AssertionError` | Expected value drift | Update the assertion |
| `TypeError: __init__` | Constructor changed | Update the call site |
| `FileNotFoundError` | Fixture path wrong | Use `tmp_path` |

You get a report at the end — tests fixed, attempts used, and
anything still failing with notes. **A fix that changes the
assertion deserves a skeptical read**: if the production behavior
changed *unintentionally*, updating the test buries a bug. The
report names the root cause precisely so you can make that call.

## Part 3 — Make it automatic

The manual loop works, but the best moment to fix a test is the
moment an edit breaks it. Claude Code **hooks** make that happen:
a `PostToolUse` hook runs after every file edit, and anything it
writes to stderr with exit code 2 is fed straight back to Claude —
which then sees the failure *in the same session that caused it*
and fixes it immediately.

### Step 1 — add the hook script

Save this as `.claude/hooks/run_matching_test.py` in your project:

```python
#!/usr/bin/env python3
"""PostToolUse hook: run the test file matching an edited source file.

Reads the hook event JSON on stdin. If the edited file is production
code, finds test files named after it (tests/**/test_<stem>*.py) and
runs them. Exit 0 when they pass (silent); exit 2 with the pytest
tail on stderr when they fail — Claude Code feeds exit-2 stderr back
to Claude, which fixes the failure immediately.
"""
import json
import subprocess
import sys
from pathlib import Path

event = json.load(sys.stdin)
edited = event.get("tool_input", {}).get("file_path", "")
path = Path(edited)

# Only react to production .py edits — never to test edits (that
# would loop) and never to docs/config.
if path.suffix != ".py" or "test" in path.name or "tests" in path.parts:
    sys.exit(0)

project_root = Path.cwd()
matches = sorted(project_root.glob(f"tests/**/test_{path.stem}*.py"))
if not matches:
    sys.exit(0)  # no matching test file — nothing to run

proc = subprocess.run(
    ["uv", "run", "pytest", *map(str, matches), "-x", "-q", "--tb=short"],
    capture_output=True,
    text=True,
    timeout=120,
)
if proc.returncode == 0:
    sys.exit(0)

tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-30:])
print(
    f"Tests for {path.name} FAILED after your edit:\n{tail}\n"
    "Fix the failure before continuing (or run /fix-test).",
    file=sys.stderr,
)
sys.exit(2)
```

### Step 2 — register it

Add this to your project's `.claude/settings.json` (create the file
if it doesn't exist; if you already have a `hooks` block, merge the
`PostToolUse` entry into it):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/run_matching_test.py\""
          }
        ]
      }
    ]
  }
}
```

### Step 3 — watch the loop close

Ask Claude to change something in a file that has tests. The moment
the edit lands, the hook runs the matching tests. If the edit broke
one, Claude sees the failure output immediately and repairs it —
usually before you'd have noticed anything was wrong. If the repair
isn't obvious, `/fix-test` is one command away with the failure
already on screen.

Convention note: the hook maps `src/**/pricing.py` to
`tests/**/test_pricing*.py`. If your suite names tests differently,
adjust the `glob` pattern on the `matches` line — that one line is
the whole mapping.

## What you built

- A diagnosis-first fix loop (`/fix-test`) that classifies root
  causes instead of pattern-matching on error text, and knows when
  to stop.
- A tests-on-edit hook that turns every edit into an immediate
  verification, with failures routed back to the session that
  caused them.

## Where to go next

- `/smart-test` — find test *gaps* and generate tests for uncovered
  code (the complement of fixing existing ones).
- `/quick-test` — run tests affected by recent changes on demand.
- The [fix-test help pages](../features/fix-test.md) cover the
  Python-level `TestMaintenanceWorkflow` API for scripted
  maintenance plans.
