---
type: task
name: use-image-analysis
tags: [skill, task]
source: plugin/skills/image-analysis/SKILL.md
---

# Task: Use the image-analysis skill

Analyze an image — screenshot, diagram, UI mockup, or chart — with Claude's vision. Triggers on: analyze this image, look at this screenshot, what's in this diagram, read this mockup, describe this picture, analyze image.

Invoke with: `/image-analysis <path to image file>`

## Steps

1. **Define image path**
   "Which image file should I analyze?"

2. **Define focus**
   (optional): "Anything specific to look for, or a general description?"

3. **Run the tool**
   Call the `analyze_image` MCP tool: **Parameters:** - **image_path** (required): Path to the image file (PNG, JPEG, GIF,
  or WebP).
- **prompt** (optional): A specific question or instruction. Omit for
  a general description.

   ```
   analyze_image(image_path="docs/architecture.png")

analyze_image(
    image_path="screenshot.png",
    prompt="What error is shown in this dialog?",
)
   ```


## Related Topics
- **Reference**: Skill: image-analysis — full reference
