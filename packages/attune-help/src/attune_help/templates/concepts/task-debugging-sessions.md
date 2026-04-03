---
type: concept
name: task-debugging-sessions
tags: [debugging, python, tools]
source: developer-guidance
---

# Debugging Sessions

Debugging is more than sprinkling `print()` statements and
hoping for the best. Effective debugging follows the
scientific method: observe the symptom, form a hypothesis,
design an experiment, and draw a conclusion. Each technique
in your toolbox has a sweet spot -- knowing when to reach
for each one is what separates a quick fix from an hour of
frustration.

## The scientific method for debugging

Every debugging session follows the same loop, whether you
realize it or not:

1. **Observe** -- what exactly is wrong? Collect the error
   message, stack trace, unexpected output, or missing
   behavior.
2. **Hypothesize** -- based on the evidence, what could
   cause this? Narrow to one testable theory at a time.
3. **Test** -- design the smallest experiment that confirms
   or disproves your hypothesis. Change one thing only.
4. **Conclude** -- did the test confirm your theory? If yes,
   fix and verify. If no, form a new hypothesis from the
   new evidence.

Skipping steps is the most common debugging mistake. Jumping
straight from "observe" to "fix" without a hypothesis leads
to shotgun debugging -- changing things at random hoping
something works.

## Debugging techniques

| Technique | What it does | When to use | Effort |
|-----------|-------------|-------------|--------|
| **Print / log** | Outputs values at specific points | Quick sanity checks, verifying flow | Low |
| **Breakpoint** | Pauses execution, lets you inspect state | Complex state, need to explore interactively | Low |
| **Binary search** | Bisect code or commits to isolate the change | "It used to work" -- finding which change broke it | Medium |
| **Tracing** | Follows execution path through function calls | Understanding unfamiliar code, call-order bugs | Medium |
| **Profiling** | Measures time and memory per function | Performance bugs, "why is this slow?" | Medium |
| **Rubber duck** | Explain the problem out loud, step by step | When you're stuck and nothing makes sense | Free |

## Choosing the right approach

Start with the **cheapest technique that fits the
symptom**:

- **You know where the bug is** -- use a breakpoint or
  print statement right there.
- **You don't know where the bug is** -- use binary search
  (bisect commits with `git bisect`, or comment out code
  halves).
- **The bug is intermittent** -- add logging so you can
  catch it next time it happens without being at the
  keyboard.
- **The code is unfamiliar** -- use tracing or step through
  with a debugger to build a mental model before
  hypothesizing.
- **The bug is performance** -- profile first. Never guess
  where the bottleneck is.
- **Nothing is making sense** -- rubber duck. Explain the
  problem to someone (or something) from scratch.

## Want to learn more?

- Say **"how do I debug a problem step by step?"** for the
  hands-on walkthrough
- Say **"show me all debugging tools"** for the complete
  reference with commands and setup
- Say **"something is broken and I don't know why"** for
  the quick triage guide
- Try **/fix-test** to auto-diagnose failing tests
- Try **/bug-predict** to find code likely to have bugs
- Try **/code-quality** to catch code smells that cause
  bugs
