---
name: lookup-topic
description: "Look up a help topic with progressive depth. First call returns concept, repeat calls escalate to task then reference. Triggers on: look up topic, open template, tell me more, go deeper, start over."
argument-hint: "<topic slug>"
---

# Lookup Topic

Progressive depth lookup for a single topic. Uses the
`lookup_topic` MCP tool. Each repeat call on the same topic
escalates from concept (what is it, when to use) to task
(step-by-step) to reference (full detail).

## When to use

- User asks "what is X" or "look up X"
- User says "tell me more" after a previous lookup — advances depth
- User says "start over" or "reset X" — resets session then looks up
- User wants to explore a specific topic without browsing a full list

## Scoping

If no topic is provided, use `AskUserQuestion`:

```yaml
question: "Which topic do you want to look up?"
header: "lookup-topic"
options:
  - label: "I know the topic slug"
    description: "I'll provide it directly (e.g. progressive-depth, security)"
  - label: "Show me what's available"
    description: "Route to lookup-list first, then pick"
```

If the user picks the second option, route to `lookup-list`.

## Execution

1. Call the MCP tool `lookup_topic` with:
   - `topic` — the slug from the user
   - `template_dir` — `.help/templates` if the project has one,
     otherwise omit (uses bundled templates)
   - `user_id` — default `mcp-session`
2. If the result's `success` is `false`, surface the error
   and suggest `lookup-list` to find valid slugs.
3. Print the `rendered` field as-is.
4. Append a hint based on `depth_level`:
   - `0` (concept): "Say 'tell me more' for step-by-step instructions"
   - `1` (task): "Say 'tell me more' for the full reference"
   - `2` (reference): "That's the full reference — say 'reset' to start over"

## Reset behavior

If the user says "start over" or "reset":

1. Call `lookup_reset` with the same `user_id`
2. Then call `lookup_topic` with the topic — will return concept again

## Output Format

```markdown
## <topic>

<rendered content from the MCP tool>

*(concept view — say 'tell me more' for next depth level)*

**Tags:** help-system, ux
```

Keep it minimal. The rendered content usually includes its
own heading and structure.
