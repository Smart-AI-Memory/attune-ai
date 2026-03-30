---
type: reference
subtype: tabular
name: tool-analyze-image
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Analyze Image

Analyze an image (screenshot, diagram, UI mockup) using Claude's vision capabilities. Supports PNG, JPEG, GIF, and WebP.

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `image_path` | string | Path to the image file to analyze | required |
| `prompt` | string | Analysis prompt (default: describe what you see, focusing on errors or notable elements) |  |

## Related Topics
- Reference: Related workflow tools: security_audit, bug_predict, code_review
