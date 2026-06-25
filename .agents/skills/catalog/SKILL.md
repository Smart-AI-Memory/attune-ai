---
name: catalog
description: "Enumerate everything attune offers — every workflow, wizard, agent, and tool, read live from the registries. Triggers on: catalog, list capabilities, browse, show all, what can attune do, list workflows, list agents, list tools."
---
# Capability Catalog

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="catalog", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
proceed to enumerate.

If the MCP call fails, fall back to:

> **Catalog** — Lists every workflow, wizard, and tool attune offers, read live from the registries so the list never drifts from the code.

## Scoping

If the user named a category in the argument
(`workflows`, `wizards`, `agents`, or `tools`), show only that
group. Otherwise show all four.

## Execution

Call the `list_capabilities` MCP tool (no arguments):

```
list_capabilities()
```

It returns `{workflows, wizards, agents, tools}` — each a list of
`{name, description}` — plus a `counts` summary, all read from
`list_workflows()`, `list_wizards()`, `get_all_templates()`, and
the live MCP tool registry at call time. **Do not hand-author or
cache these lists** — always render what the tool returns.

## Output

Render each requested group as its own markdown table, using
the live `counts` in the headings:

```
## Workflows (<counts.workflows>)

| Name | Description |
|------|-------------|
| ... | ... |
```

Repeat for **Wizards**, **Agents**, and **Tools**. For each row,
where a dedicated skill exists for that capability, point the user
to it (e.g. "run the `security-audit` skill"). Close by inviting
the user to pick one.

## Relationship to attune-hub

- **catalog** *enumerates* — "show me everything attune can do".
- **attune-hub** *routes* — "take me to the right workflow for
  my goal".

If the user wants help choosing or routing rather than a full
listing, hand off to the attune-hub skill.
