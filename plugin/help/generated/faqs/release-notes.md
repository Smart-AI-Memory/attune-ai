---
name: release-notes
source: content/features/release-notes.md
tags:
- release
- changelog
- advisory
type: faq
---

# Release Notes FAQ

## What is release-notes?

Release-notes is the **advisory** half of the release pair. It drafts
a changelog and an overall go/no-go readiness recommendation for a
codebase about to ship, using four Claude Agent SDK subagents — a
health checker, a security scanner, a changelog generator, and a
release assessor. It predicts and drafts; it does not block.

## What's the difference between release-notes and release-prep?

Release-notes is advisory — it drafts a changelog and an LLM go/no-go,
and never blocks. Release-prep is the deterministic gate: it runs real
`bandit` / `ruff` / `pytest` and a docstring check against hard
thresholds and returns an APPROVED or BLOCKED verdict. Run the gate
with `attune workflow run release-gate`.

## Does release-notes block my release if the score is low?

No. It only recommends. The readiness score and go/no-go come from an
LLM assessor reading the codebase, not from measured thresholds. For
an enforced gate, use release-prep.

## How much does a run cost?

It is subscription-billed with a per-depth budget cap — $2 / $10 / $25
for `quick` / `standard` / `deep`. Subscription users pay no
per-request cost. Set `ATTUNE_MAX_BUDGET_USD=0` to lift the cap for a
pre-release run that needs to finish.

## Which calls are async?

`ReleasePreparationWorkflow.execute` is a coroutine — `await` it or
drive it with `asyncio.run`. Calling it without awaiting is the most
common mistake.

## Where does the changelog come from?

The `changelog-generator` subagent reads `git log` since the last
release tag and drafts a CHANGELOG section in Keep a Changelog format.

## How do I run it?

- **CLI:** `attune workflow run release-notes --path .`
- **Python:** `await ReleasePreparationWorkflow().execute(path=".")`
  (importable from `attune.workflows`)
- **Conversation:** the `release_notes` MCP tool, via the `/release`
  skill.

## How do I keep a run cheap?

Use a shallower `depth` — `quick` uses the smallest agent-turn budget
(10 turns) and the lowest cap ($2).

**Tags:** `release`, `changelog`, `advisory`
