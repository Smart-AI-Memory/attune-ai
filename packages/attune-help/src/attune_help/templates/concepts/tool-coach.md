---
type: concept
name: tool-coach
tags: [skill, help-system, progressive-depth]
source: plugin/skills/coach/SKILL.md
---

# Coach

Coach is the help system's own help. It explains any
Attune topic using progressive depth -- start with a
short concept overview, then drill into step-by-step
instructions, then get the full reference with every
detail. You never leave your conversation to look
things up.

## How progressive depth works

Every topic in the knowledge base exists at three
levels. When you ask about something, you get the
first level. Say "tell me more" and you get the next.

| Level | Template type | What you get |
|-------|---------------|--------------|
| 0 | **Concept** | What is it? When would I use it? |
| 1 | **Task** | Step-by-step: how to run it right now |
| 2 | **Reference** | Full detail -- every option, edge case, configuration |

This is not just "more words." Each level is a
different kind of document written for a different
need. The concept tells you whether you care. The
task gets you moving. The reference answers the
question you'll have in six months.

## Session state

The engine tracks your current topic and depth level
across your session. Asking about the same topic
again advances to the next level automatically. Asking
about a different topic resets to level 0 (concept).
Sessions expire after 4 hours of inactivity.

## When you'd use it

- You heard someone mention "security audit" and want
  to know what it does -- ask and get the concept
- You're ready to run it -- say "tell me more" for
  the step-by-step
- You need to configure exclusions or understand the
  scoring -- say "tell me more" again for the full
  reference
- You just finished a workflow and want to understand
  the results -- the engine can skip straight to the
  task level

## Example: coaching on security audits

```
You:    what is security audit?
Coach:  [concept] What it finds, when to use it...
        (say "tell me more" for step-by-step)

You:    tell me more
Coach:  [task] Quick start, choosing targets, reading results...
        (say "tell me more" for full reference)

You:    tell me more
Coach:  [reference] All checks, CWE mappings, scoring, config...
        (full detail)
```

## Want to learn more?

- Say **"tell me more"** for a quick-start guide to
  using coach
- Say **"what is progressive depth?"** to understand
  the engine behind it
- Say **"how does the help system work?"** for the
  broader architecture
