---
name: progressive-depth
source: src/attune/help/engine.py
summary: This developer help template covers a display strategy that automatically
  increases the detail level and verbosity of content each time a user requests the
  same information within a session, progressing from compact summaries through normal
  explanations to fully detailed responses.
tags:
- help-system
- ux
type: concept
---

# Progressive Depth

## Overview

Progressive depth is a display strategy where templates automatically adjust their verbosity based on how many times a user has accessed the same content in a session. The first view returns a compact summary; a second request returns normal detail; a third returns the full, unabridged content.

## Why It Matters

Not every question needs a five-paragraph answer. Progressive depth respects the user's attention by defaulting to brevity — a one-line response is often sufficient. When it isn't, the user can drill deeper simply by asking again, without switching tools, issuing new commands, or navigating elsewhere.

## How It Works

The engine maintains session state by tracking two values: the ID of the most recently accessed template and its current depth level. Each time `populate_progressive()` is called with the same template ID, the depth increments automatically. Depth levels map to verbosity as follows:

| Depth | Verbosity |
|-------|-----------|
| `0` | Compact — a brief summary or single-line answer |
| `1` | Normal — standard explanation with key details |
| `2` | Detailed — full content, including edge cases and examples |

Accessing a different template resets the depth to `0`.

## Example

Call `populate_progressive('err-shadow-dirs')` three times in succession to observe the escalation from compact through to detailed output.

## Related Topics

*No related topics yet.*
