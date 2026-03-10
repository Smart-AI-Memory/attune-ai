# XML-Enhanced Implementation Prompts

**Created:** 2026-02-06
**Source:** Claude Code integration planning sessions

---

## When to Use

Use XML-enhanced prompts when decomposing complex implementation tasks into self-contained, executable specifications. This applies to:

- Multi-file implementation tasks (3+ files)
- Tasks with dependencies, validation steps, or risk factors
- Subagent and workflow definitions
- Any task given to another agent or future session to execute

Do NOT use for single-file edits, bug fixes, or trivial changes.

---

## Core Schema

```xml
<task id="unique-id" name="short-name">
  <objective>What this task accomplishes (1-2 sentences)</objective>

  <context>
    <existing-code path="src/module.py">
      Relevant existing patterns, interfaces, or constraints
    </existing-code>
  </context>

  <files-to-create>
    <file path="path/to/new/file.py">
      Structure, key functions, and content specification
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="path/to/existing.py">
      <change location="function or line range">
        BEFORE: existing code
        AFTER: new code
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Specific assertion or test to verify correctness</check>
    <check>Another verification step</check>
  </validation>

  <risks>
    <risk severity="medium">Description and mitigation</risk>
  </risks>
</task>
```

---

## Key Principles

1. **Self-contained** -- Each task prompt includes all context needed to execute without reading other docs
2. **Specific paths** -- Always use exact file paths, not "the config file"
3. **BEFORE/AFTER** -- Show existing code alongside changes for clarity
4. **Validation-first** -- Define how to verify success before describing the implementation
5. **Severity-tagged risks** -- Flag potential issues so the implementer can plan accordingly

---

## Quick Example

```xml
<task id="2.1" name="security-guard-hook">
  <objective>
    Create a PreToolUse hook that blocks eval/exec in Bash commands
    and validates file paths in Edit/Write operations.
  </objective>
  <context>
    <protocol>stdin JSON with tool_name and tool_input; exit 0=allow, 2=block</protocol>
  </context>
  <files-to-create>
    <file path="attune_llm/hooks/scripts/security_guard.py">
      validate_bash_command() and validate_file_path() functions
    </file>
  </files-to-create>
  <validation>
    <check>echo '{"tool_name":"Bash","tool_input":{"command":"eval(x)"}}' | python script.py exits 2</check>
    <check>echo '{"tool_name":"Write","tool_input":{"file_path":"src/ok.py"}}' | python script.py exits 0</check>
  </validation>
</task>
```

---

## References

- [Full XML Prompts Guide](../../../docs/guides/xml-enhanced-prompts.md) -- Schema v1.0 spec with performance metrics
- [Real Task Prompts](../../../docs/implementation/TASK_PROMPTS.md) -- 10 executed examples
