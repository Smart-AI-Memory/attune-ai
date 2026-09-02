---
name: roundtable
description: "Convene the multi-LLM round table — Claude, Antigravity, and Codex deliberate a question; the user chairs promotion. Triggers on: roundtable, round table, convene the table, ask the table, what do the other models think, deliberate."
argument-hint: "<question | read <thread> | promote <thread> | routine <name>>"
---

# Round Table (project shim)

This is the in-repo projection of the plugin skill so `/roundtable`
works in attune-ai sessions before the next plugin release ships
it. The canonical skill body is the plugin copy — Read
[plugin/skills/roundtable/SKILL.md](../../../plugin/skills/roundtable/SKILL.md)
now and follow it exactly. Do not duplicate its content here; if
this shim and the plugin copy ever disagree, the plugin copy wins.
The canonical workflow uses the shared command-workspace tools when
available, including atomic promotion batches of at most three candidates and
the one-candidate compatibility fallback.
