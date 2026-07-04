---
paths:
  - "plugin/**"
  - ".agents/**"
  - "src/attune/mcp/**"
---

# Plugin Reference Validation

**Created:** 2026-03-25

---

## Rule

Before creating or modifying any plugin component
(command, skill, or hook) that references Python code,
**verify all outbound references resolve** using the
checks below.

---

## Reference Chain

```
Commands -> Skills -> MCP Tools -> Workflow Classes
```

Each layer references the next by name in markdown.
A broken reference produces a silent failure at runtime.

---

## Verification Checklist

### Adding or Modifying a Command

- If the command uses `Read skill file:///skills/{name}/SKILL.md`,
  verify the directory exists:

```bash
ls plugin/skills/{name}/SKILL.md
```

- If the command references MCP tool names directly
  (like `attune.md` does), verify each tool:

```bash
grep -w "tool_name" src/attune/mcp/tool_schemas.py
```

### Adding or Modifying a Skill

- Verify every MCP tool name mentioned in backticks
  exists in the schema definitions:

```bash
grep -w "tool_name" src/attune/mcp/tool_schemas.py
```

- Verify any Python class names referenced can be
  imported:

```bash
grep -r "class ClassName" src/attune/
```

### Adding a New MCP Tool

1. Add schema to `src/attune/mcp/tool_schemas.py`
   (correct `get_*_tools()` function)
2. Add handler method to server or mixin
3. Add dispatch entry in `_build_dispatch_table()`
4. Update tool count in
   `tests/unit/test_mcp_memory_tools.py`
5. Update any skill that should reference the new tool

---

## Quick Verification Commands

| Reference Type | Command |
|---|---|
| Skill exists | `ls plugin/skills/{name}/SKILL.md` |
| MCP tool exists | `grep -w "tool_name" src/attune/mcp/tool_schemas.py` |
| Python class exists | `grep -r "class ClassName" src/attune/` |
| CLI command exists | `grep -w "command" src/attune/cli_minimal.py` |
| Workflow class | `grep -r "class WorkflowName" src/attune/workflows/` |

---

## Automated Tests

Run reference validation tests:

```bash
pytest tests/unit/plugins/test_plugin_reference_validation.py -v
```

These tests parse all plugin `.md` files, extract
references, and assert they resolve to real code.
