---
name: cross-review
description: "One-shot second-opinion review of a real diff by a DIFFERENT model (Claude, Codex or Antigravity) — advisory only, board-recorded. Triggers on: cross review, second opinion, ask another model to review, pre-merge check from codex."
argument-hint: "[staged] [seat=claude|codex|antigravity]"
---

# Cross Review (project shim)

This is the in-repo projection of the plugin skill so
`/cross-review` works in attune-ai sessions before the next plugin
release ships it. The canonical skill body is the plugin copy —
Read
[plugin/skills/cross-review/SKILL.md](../../../plugin/skills/cross-review/SKILL.md)
now and follow it exactly. Do not duplicate its content here; if
this shim and the plugin copy ever disagree, the plugin copy wins.
