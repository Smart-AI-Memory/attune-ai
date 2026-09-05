# Agent work handoff

> **Landed by Claude on 2026-09-05** (branch
> `claude/land-codex-merged-build-latency-receipts`) in Codex's absence, on
> the chair's word ("take the ball and run with it"). The receipt files were
> copied read-only from Codex's worktree `~/.codex/worktrees/30be/attune-ai`
> (branch `codex/merged-build-latency-receipts` @ `e0d88bc50`, a descendant
> of the #2421 merge `c2138be2d`); every copied file is byte-identical to
> its source and the manifest's three SHA-256 entries verify. Codex's
> worktree was not modified. The text below is Codex's, unchanged.

## Goal

Repeat the baseline/batched timing comparison on merged code with forms 0.12.3.

## Acceptance criteria

Comparable visibility and canonical-acceptance receipts for identical scenarios.

## Scope and assumptions

- Branch: codex/merged-build-latency-receipts; worktree: Codex 30be/attune-ai.
- Provider/session: Codex, advisory to Patrick; structured measurement task.
- Fresh observable browser host is the scope; native chat-host latency is unmeasured.

## Current state

- Completed four ABBA runs: seven synthetic declines versus 3+3+1 batches.
- Added docs/probes/latency/merged-2026-09-05/ receipts and this handoff.
- Source and fixture match merged integration c2138be2d; runtime Forms is 0.12.3.
- Batching reduces cumulative acceptance waits; no renderer optimization justified.
- Files are uncommitted. Existing host processes and original receipts preserved.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Merged source | gh pr view 2421; ancestry and scoped git diff | MERGED; ancestor; no source/fixture differences |
| Correct runtime | Explicit-PYTHONPATH import/version probe | Checkout MCP code; installed Forms 0.12.3 |
| Comparable scenarios | Real browser controls and public MCP stdio | Four complete ABBA runs; identical terminal Markdown |
| Accepted actions | Parse logs and join render/accept workspace, revision, instance | 20/20; unique browser interval pairings |

## Next action

Review the receipt README and retain the artifacts. The follow-up native-host
investigation is recorded in `docs/probes/latency/merged-2026-09-05/native-host-blocker.md`
and `native-host-preflight.json`: native app observation was refused, the active
AI workspace lacks the expected instance marker, and exact loaded versions are
unverified. No native ABBA run was made. Obtain process-local provenance and a
supported native host event trace before attempting that comparison. No renderer
optimization was performed.

Runtime follow-up: `runtime-alignment.md` and `.json` in the same receipt directory
record the completed launcher pin and fresh stdio verification. Active Codex MCP
still requires a host reload; its post-config-change live call lacked the token.
After reload, verify the live workspace instance and canonical acceptance join.
