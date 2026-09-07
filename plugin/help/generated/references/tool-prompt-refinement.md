---
type: reference
subtype: tabular
name: tool-prompt-refinement
category: tool
tags: [mcp, tool, utility]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Prompt Refinement

Read the current automatic prompt-refinement policy before refining a user message. No prompt text is needed. Enable/disable persists a user-wide preference ONLY on the user's explicit request. skip_this_prompt bypasses refinement once without changing the preference.

**Group:** utility

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `action` | string |  | enum: status|enable|disable | status |
| `skip_this_prompt` | boolean |  |  | False |

## Usage

`prompt_refinement()`

## Related Topics
- **Reference**: Tool: Auth Status — Get authentication strategy status. Shows current configurat...
- **Reference**: Tool: Auth Recommend — Get authentication recommendation for a file. Analyzes LOC a...
- **Reference**: Tool: Telemetry Stats — Get telemetry statistics. Shows cost savings, cache hit rate...
