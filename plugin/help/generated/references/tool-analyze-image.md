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

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `image_path` | string | Path to the image file to analyze |  | required |
| `prompt` | string | Analysis prompt (default: describe what you see, focusing on errors or notable elements) |  |  |

## Usage

`analyze_image(image_path="...")`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
