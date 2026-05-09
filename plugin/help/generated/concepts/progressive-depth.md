---
type: concept
name: progressive-depth
tags: [help-system, ux]
source: src/attune/help/engine.py
---

# Concept: Progressive depth

## What

Templates adapt their verbosity based on repeated access. First view shows a compact summary; asking again shows normal detail; asking a third time shows everything.

## Why

Respects the user's attention. Most of the time, a one-line answer is enough. When it's not, the user drills deeper without switching tools or commands.

## How

The engine tracks session state (last template ID + depth level). populate_progressive() increments depth on repeated access to the same template. Depth maps to verbosity: 0=compact, 1=normal, 2=detailed. New template resets to 0.

## Example

Call `populate_progressive('err-shadow-dirs')` three times to see escalation.

## Related Topics

_No related topics yet._
