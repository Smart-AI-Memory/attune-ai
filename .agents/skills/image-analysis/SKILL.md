---
name: image-analysis
description: "Analyze an image — screenshot, diagram, UI mockup, or chart — with Claude's vision. Triggers on: analyze this image, look at this screenshot, what's in this diagram, read this mockup, describe this picture, analyze image."
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

### Shared command workspace (preferred)

Open adapter `image-analysis` with the local image path and optional prompt.
The adapter reads the real file, validates repository containment, the 10MB
limit, magic bytes versus extension, dimensions, MIME type, and SHA-256. The
invocation already authorizes this read-only analysis, so the running workspace
has no synthetic confirmation action.

Call `analyze_image` with the validated path and publish the exact response as
`analysis_result`; include provider progress only as optional `progress`
events. Success requires non-empty analysis and must match the canonical MIME
and file size. Decode/provider failure must say “did not complete,” never
render an empty successful analysis. Present the terminal widget or Markdown,
and preserve the same input fingerprint and truthfulness in text fallback.

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
