---
type: faq
name: release-prep-faq
feature: release-prep
depth: faq
generated_at: 2026-07-14T15:58:59.853890+00:00
source_hash: 63942851d2e8b65c33fd9851fa0f4a2706c1389fb5673a4789c74ae3735154c2
status: generated
---

# Release Prep FAQ

## What's the difference between release-prep and release-notes?

Release-prep is the deterministic gate — it runs real
bandit/ruff/pytest against hard thresholds and returns APPROVED or
BLOCKED. Release-notes is advisory — it drafts a changelog and an LLM
go/no-go and never blocks.

## How much does the gate cost?

$0 by default. The agents are rule-based
(`RELEASE_LLM_MODE=simulated`) and make no API calls. LLM enhancement
is opt-in with `RELEASE_LLM_MODE=real` plus a key.

## Why did a BLOCKED run still exit 0?

`success` means the assessment ran; the verdict is in
`metadata["approved"]`. Branch on that, not the exit code.

## How do I change the thresholds?

Pass `quality_gates={...}` to `ReleasePrepTeam` /
`ReleasePrepTeamWorkflow` using the keys `max_critical_issues`,
`min_coverage`, `min_quality_score`, `min_doc_coverage`.

## Is there an MCP tool for the gate?

No. The gate is CLI / Python only — run `attune workflow run
release-gate`. The advisory (`release_notes`) is the MCP surface.

## Which calls are async?

Both `ReleasePrepTeamWorkflow.execute` and
`ReleasePrepTeam.assess_readiness` are coroutines — `await` them.
