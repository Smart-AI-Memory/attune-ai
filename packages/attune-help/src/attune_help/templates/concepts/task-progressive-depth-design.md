---
type: concept
name: task-progressive-depth-design
tags: [progressive-depth, help-system, authoring, ux]
source: developer-guidance
---

# Progressive Depth Design

When a user asks "what is X?", they get one document.
When they say "tell me more", they get a different
document -- not a longer version of the first one.
Progressive depth is the practice of writing three
distinct documents per topic, each designed for a
different need state.

## Three levels, three purposes

| Level | Document type | The user's question | Purpose | Typical length |
|-------|--------------|---------------------|---------|----------------|
| **Concept** | What is it? | "What is dependency management?" | Orient -- build a mental model, explain why it matters | 20-30 lines |
| **Task** | How do I do it? | "How do I add a dependency?" | Instruct -- step-by-step with examples and expected output | 40-80 lines |
| **Reference** | Show me everything | "What are all the version specifiers?" | Document -- every option, edge case, configuration detail | 100+ lines |

The key insight: each level serves a genuinely different
audience state. A concept reader doesn't know what the
thing is yet. A task reader knows what it is but not how
to do it. A reference reader knows how to do it but needs
a specific detail. Writing the same content at three
lengths misses the point entirely.

## How it works at runtime

The help engine tracks session state per topic. When a
user first asks about "dependency management", they see
the concept. If they say "tell me more" within the same
session, the engine increments the depth counter and
serves the task document. A third request serves the
reference. Switching to a different topic resets depth
to zero.

Session state expires after 4 hours of inactivity.
After that, the next request for any topic starts back
at the concept level.

## What makes each level different

| Aspect | Concept | Task | Reference |
|--------|---------|------|-----------|
| **Contains code?** | Rarely -- only to illustrate a point | Yes -- runnable examples with output | Yes -- exhaustive syntax and options |
| **Has steps?** | No | Yes -- numbered, actionable | No -- organized by category |
| **Uses tables?** | For comparisons | For decision-making | For parameter lists and flags |
| **Mentions tools?** | By name only | With commands to run | With every flag and config option |
| **Answers "why?"** | Yes -- this is the primary job | Briefly, in context | No -- assumes motivation is known |
| **Assumes prior knowledge?** | None about this topic | Knows what it is, not how | Knows what and how, needs specifics |

## Why not just write one long document?

Because people stop reading. A concept reader who sees
80 lines of step-by-step instructions bounces. A
reference reader who has to scroll past "what is this?"
and "step 1, step 2" to find a flag name gets
frustrated. Different documents for different needs
means every reader finds what they need immediately.

## Want to learn more?

- Say **"how do I write progressive depth content?"** for
  the step-by-step authoring guide
- Say **"show me the content guidelines"** for length
  targets, section patterns, and cross-linking rules
- Say **"quickstart for writing depth levels"** to jump
  straight to the 5-step workflow
