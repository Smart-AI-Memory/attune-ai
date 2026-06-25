---
name: image-analysis
description: "Analyze an image — screenshot, diagram, UI mockup, or chart — with Claude's vision. Triggers on: analyze this image, look at this screenshot, what's in this diagram, read this mockup, describe this picture, analyze image."
argument-hint: "<path to image file>"
---

# Image Analysis

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="image-analysis", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then tell the
user they can say "tell me more" for a step-by-step guide, or answer
the scoping question below to proceed.

If the MCP call fails, fall back to:

> **Image Analysis** — Sends an image (screenshot, diagram, UI
> mockup, chart) to Claude's vision model and returns a description
> or answers a question about it. Supports PNG, JPEG, GIF, and WebP.

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
