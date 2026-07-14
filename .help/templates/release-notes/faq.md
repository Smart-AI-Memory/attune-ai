---
type: faq
name: release-notes-faq
feature: release-notes
depth: faq
generated_at: 2026-07-14T15:58:59.190518+00:00
source_hash: 3bee45ea7e9bedc48f6fdc7744f2c05ff0fd177419dba9606233f53b10818ab6
status: generated
---

# Release Notes FAQ

## What's the difference between release-notes and release-prep?

Release-notes is advisory — it drafts a changelog and an LLM
go/no-go, and never blocks. Release-prep is the deterministic gate:
it runs real bandit/ruff/pytest against hard thresholds and returns
APPROVED or BLOCKED. Run the gate with `attune workflow run
release-gate`.

## Does release-notes block my release if the score is low?

No. It only recommends. For an enforced gate, use
release-prep.

## How much does a run cost?

It's subscription-billed with a per-depth budget cap ($2 /
$10 / $25 for quick / standard / deep). Subscription users pay no
per-request cost; set `ATTUNE_MAX_BUDGET_USD=0` to lift the cap.

## Which calls are async?

`execute` is a coroutine — `await` it or use `asyncio.run`.

## Where does the changelog come from?

The `changelog-generator` subagent reads `git log` since the
last release tag and drafts a Keep a Changelog section.
