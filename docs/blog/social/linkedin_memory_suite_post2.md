---
description: "LinkedIn Post — memory-suite follow-up: re-ran the published benchmark 24 hours later; every claim held and the ratios read slightly wider, because the budget cap is constant while the corpus grows. Short-form companion to the measured memory-suite Article."
---

# LinkedIn Post — Memory Suite follow-up (the day-after re-run)

*Format: LinkedIn post (short-form, no headers). ~170 words.
ASCII markers only — LinkedIn mangles Unicode arrows on paste.*

---

Yesterday I published measured numbers on what persistent AI
memory saves. Today I re-ran the same benchmark against the live
store. The claims didn't just hold — they read slightly better.

Published -> re-run, 24 hours apart:

-> Token savings at the trap moment: 67x -> 67.3x
-> Warm Redis recall: 0.6 ms -> 0.6 ms (flat)
-> Read-the-corpus-from-disk baseline: 4.4 ms -> 4.63 ms
-> Durable corpus: 751 -> 752 docs

That's not luck — it's the design. The recall budget is capped at
3,000 tokens and the recall path is one warm Redis call, so both
stay constant while the corpus underneath keeps growing. Every
session the store learns from makes the "load everything into
context" alternative more expensive, and the recall slice costs
the same.

Publish a benchmark and it starts aging the moment you post it.
This one ages in the right direction.

Reproducible: benchmarks/memory_savings.py in the attune-ai repo,
run against your own live store.

What's the one number you'd want your AI to remember tomorrow?

#AIDevelopment #DeveloperTools #Python #OpenSource #Claude

---

## Alternative hooks

**Version B (blunt lead):**
The worst time to re-run your own benchmark is the day after you
publish it. I did anyway. It got better.

**Version C (mechanism lead):**
A constant beats a ratio: cap the recall budget at 3,000 tokens
and every doc the corpus gains widens your savings for free.
