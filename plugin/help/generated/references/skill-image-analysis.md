---
type: reference
subtype: procedural
name: skill-image-analysis
category: skill
tags: [skill, plugin]
source: plugin/skills/image-analysis/SKILL.md
---

# Reference: Skill: image-analysis

Analyze an image — screenshot, diagram, UI mockup, or chart — with Claude's vision. Triggers on: analyze this image, look at this screenshot, what's in this diagram, read this mockup, describe this picture, analyze image.

**Usage:** `/image-analysis <path to image file>`

## Scoping

Before running, ask:

1. **Image path**: "Which image file should I analyze?"
2. **Focus** (optional): "Anything specific to look for, or a general
   description?"

## Execution

Call the `analyze_image` MCP tool:

**Parameters:**

- **image_path** (required): Path to the image file (PNG, JPEG, GIF,
  or WebP).
- **prompt** (optional): A specific question or instruction. Omit for
  a general description.

```python
analyze_image(image_path="docs/architecture.png")

analyze_image(
    image_path="screenshot.png",
    prompt="What error is shown in this dialog?",
)
```

## Output

Present the model's analysis as readable prose. When the user asked a
specific question, lead with the direct answer, then supporting
detail.

## When to Use

- Reading text or errors out of a screenshot.
- Describing or critiquing a UI mockup or diagram.
- Extracting structure from a chart or whiteboard photo.

## Anti-Patterns

- DO NOT use for non-image files — this is vision-only (PNG/JPEG/
  GIF/WebP).
- DO NOT pass a URL — the tool reads a local file path.

## Related Topics
- **Reference**: Tool: Analyze Image (`analyze_image`)
