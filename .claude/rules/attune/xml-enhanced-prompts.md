# XML-Enhanced Implementation Prompts

**Created:** 2026-02-06
**Source:** Claude Code integration planning sessions

---

## When to Use

This section owns eligibility for the XML-task tier; the
[shared contract](../../../content/collaboration/contract.md#artifact-selection)
owns the tiers and shared communication requirements. The
[decision routine](decision-routine.md#decision-tree) routes work by reference.

Use an XML-task contract when execution needs any of these:

- A cold handoff to another agent or session, with context and completion
  checks that cannot depend on the current conversation.
- Explicit ordering of dependent changes or coordinated task outputs.
- Material risk to authorization, retained data or compatibility that requires
  explicit action boundaries, mitigations and verification, even for one file.
- A consumer that parses XML task blocks, including the spec reader.

File count and the label "bug fix" do not determine eligibility. A routine
multi-file rename may fit a structured one-shot; a one-file authorization
fix may need an XML task. Ordinary validation alone does not require XML.
Check the contract's spec tier first; its executable tasks can use this schema.

When a tool parses the artifact, preserve its supported XML schema.
The [spec reader](../../../src/attune/pipeline/spec_reader.py) extracts XML
task blocks; its [tests](../../../tests/unit/pipeline/test_spec_reader.py)
exercise that input contract. Prose is not interchangeable on this route.
For human/agent-only prompts with no XML consumer, equivalent structured
text may carry the same task contract. The information requirements remain;
format flexibility does not permit skipping handoff or risk details.

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

1. **Self-contained** -- Include necessary context and precise source references. For handoffs, pin the baseline revision and required context; recipients check for changes before relying on it.
2. **Specific paths** -- Always use exact file paths, not "the config file"
3. **BEFORE/AFTER** -- Use for a verified, settled edit; otherwise state the required behavior and constraints without inventing an implementation
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

- [Shared contract](../../../content/collaboration/contract.md#artifact-selection) — tiers and communication requirements
- [Spec reader](../../../src/attune/pipeline/spec_reader.py) — XML-consuming execution path
- [Task parser](../../../src/attune/wizards/decomposer.py) — supported task fields
- [OpenAI reasoning guidance](https://developers.openai.com/api/docs/guides/reasoning-best-practices) — direct goals, constraints and useful delimiters
- [Anthropic prompting guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) — XML for separating mixed prompt content

Provider guidance checked 2026-09-07 UTC. These are formatting recommendations,
not evidence of a universal XML performance advantage. Examples, reasoning
instructions and effort settings should follow the selected model's guidance;
acceptance criteria and observable verification remain explicit.
