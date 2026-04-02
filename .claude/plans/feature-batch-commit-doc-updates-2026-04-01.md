# Batch + Commit-Time Documentation Updates

**Created:** 2026-04-01
**Source:** /plan feature
**Route:** feature
**Status:** pending

## Context

The help system has 542 templates generated from just
29 unique source files. The `HelpMaintenanceWorkflow`
detects stale templates and regenerates them, but only
when manually triggered. Two gaps remain:

1. **Cost** — regenerating all templates synchronously
   uses full-price API calls. The Anthropic Batch API
   offers 50% savings for non-urgent work.
2. **Freshness** — source files can change without
   templates being updated. Developers must remember
   to run the maintenance workflow manually.

## Goals

- Batch regeneration of stale templates at 50% cost
  via Anthropic Batch API (must-have)
- Automatic staleness detection on commit (must-have)
- Optional auto-regeneration on commit (nice-to-have)
- Structured JSON output from staleness check for
  programmatic consumption (must-have)

## End State

1. `help_maintain(batch=true)` submits stale template
   regeneration to the Batch API — returns a batch ID,
   results arrive within 24 hours at 50% cost
2. Every git commit that touches a source file
   (CLAUDE.md, SKILL.md, tool_schemas.py, etc.)
   automatically checks for stale docs and either
   warns or regenerates
3. `generate_all.py --stale --json` outputs structured
   data for tooling integration

## Scope

- **Files (modify):** 4
- **Files (create):** 1
- **Type:** feature

## Approach

### A. Structured Staleness Output

**Modify:** `scripts/generate_all.py`

Add `--json` flag to `check_staleness()`:

```python
def check_staleness(generated_dir, json_output=False):
    # ... existing hash comparison logic ...
    if json_output:
        import json as json_mod
        result = {
            "stale_count": len(stale_items),
            "stale": stale_items,  # list of dicts
            "types_affected": list(types),
        }
        print(json_mod.dumps(result))
        return 1 if stale_items else 0
    # ... existing human-readable output ...
```

Where `stale_items` is already built as dicts with
`id`, `reason`, `source` keys in the existing loop.

Also add `--manifest-only` flag that just rebuilds
the manifest without running generators (needed by
the maintenance workflow after regeneration).

### B. Batch Mode for HelpMaintenanceWorkflow

**Modify:** `src/attune/workflows/help_maintenance.py`

Add `batch: bool = False` parameter to `execute()`:

When `batch=True`:

1. MAP phase runs the same way (find stale templates)
2. Instead of subprocess generators, build a
   `BatchRequest` per stale template type:

```python
BatchRequest(
    task_id=f"regen-{type_dir}",
    task_type="regenerate_template",
    input_data={
        "type_dir": type_dir,
        "script": script_name,
        "stale_ids": [ids for this type],
    },
    model_tier="cheap",
)
```

3. Submit via `BatchProcessingWorkflow.execute_batch()`
4. Return immediately with batch ID (don't wait)
5. Skip REBUILD/VALIDATE (deferred until batch
   completes)

When `batch=False`: current synchronous behavior
(unchanged).

**Modify:** `src/attune/mcp/tool_schemas.py`

Add `batch` parameter to `help_maintain` schema:

```python
"batch": {
    "type": "boolean",
    "description": "Submit to Batch API (50% cost, async)",
    "default": False,
}
```

**Modify:** `src/attune/mcp/server.py`

Pass `batch` arg through in `_handle_help_maintain`.

### C. Pre-Commit Staleness Check

**Create:** `scripts/check_docs_freshness.py`

Lightweight script for pre-commit integration:

```python
"""Pre-commit hook: warn if help templates are stale."""
import subprocess, sys

result = subprocess.run(
    ["uv", "run", "python", "scripts/generate_all.py",
     "--stale", "--json"],
    capture_output=True, text=True, timeout=10,
)

if result.returncode == 0:
    sys.exit(0)  # All fresh

# Parse JSON output
import json
data = json.loads(result.stdout)
count = data["stale_count"]
types = data["types_affected"]

print(f"⚠ {count} help templates are stale")
print(f"  Affected types: {', '.join(types)}")
print(f"  Run: /learn maintain")
sys.exit(0)  # Warn but don't block
```

**Modify:** `.pre-commit-config.yaml`

Add local hook:

```yaml
- id: check-docs-freshness
  name: Check help template freshness
  entry: uv run python scripts/check_docs_freshness.py
  language: system
  pass_filenames: false
  files: >-
    ^\.claude/CLAUDE\.md$|
    ^plugin/skills/.*/SKILL\.md$|
    ^src/attune/mcp/tool_schemas\.py$
  stages: [commit]
```

Key design decisions:
- `files:` regex limits hook to the 29 source files
  that actually drive template generation
- `exit(0)` always — warn, don't block commits
- Fast: just reads manifest JSON + hashes a few files
- `stages: [commit]` — runs on every commit, not
  manual

### D. Update /learn Skill

**Modify:** `plugin/skills/learn/SKILL.md`

Add batch mode to the maintenance section:

```markdown
For cost-optimized bulk updates (50% savings):

```
help_maintain(batch=true, dry_run=false)
```

This submits to the Anthropic Batch API. Results
arrive within 24 hours.
```

## Verification

1. `python scripts/generate_all.py --stale --json`
   outputs valid JSON with stale_count and types
2. `help_maintain(batch=true, dry_run=true)` returns
   batch request preview without submitting
3. Pre-commit hook fires when editing CLAUDE.md and
   prints staleness warning
4. Pre-commit hook does NOT fire when editing
   unrelated files (e.g. src/attune/config.py)
5. All 94 existing tests still pass

## Decisions

- **Pre-commit: configurable** — default to warn-only,
  `ATTUNE_DOCS_AUTOREGEN=1` env var enables auto-regen
  (runs generators + stages regenerated files)
- **Batch results**: no auto-PR for now — user runs
  `/learn maintain` to apply when ready
