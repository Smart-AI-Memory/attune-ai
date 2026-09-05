# Form/workspace instance correlation and browser latency

## Goal and acceptance criteria

Pair overlapping displays correctly. Count workspace acceptance only after
canonical successor storage. Compare identical baseline and batched scenarios
in an observable host, separating paint, dwell, and accepted acknowledgment.

## Scope

- attune-ai branch: `codex/form-instance-correlation`, base `1aab6bebe`.
- attune-forms isolated clone: `/private/tmp/attune-forms-instance-correlation`,
  branch `codex/form-instance-correlation`, base `cc94fc2`.
- Codex advisory to Patrick. User approved implementation, workspace acceptance
  instrumentation, final verification and loading an isolated observable host.
- XML task: unique render tokens travel through ordinary form envelopes and
  workspace action envelopes; exact joins use form identity or workspace/revision.
  Test invalid inputs, overlaps, replay, canonical failures and real stdio.
  Then compare seven single rulings with 3+3+1 batches over identical fixtures.

## Current state

Implementation and measurements are complete in both repos. Git history and
the paired PRs record the publishing state.

- Form response envelopes carry a unique display token through MCP Apps and both
  collectors. Legacy events retain counts but do not invent wait samples.
- Workspace tokens are optional validated metadata, outside nonce/HMAC authority.
  The host emits acceptance after storing the canonical successor. Rejections,
  adapter failures and replay attempts do not produce acceptance events.
- Older installed forms wheels retain functional rendering/collection and report
  missing workspace timing explicitly.
- Final reviewed wheels were built and byte-checked against source, installed
  with no dependency resolution into `/private/tmp/latency-host-site`, and run
  through public MCP stdio and an isolated visible in-app browser host.
- No global package install, host restart, model call, real board write or
  promotion was performed.

## Verification receipts

- 994 attune-forms tests and 129 focused attune-ai tests passed.
- Changed executable Python coverage: forms 57/57, ai 19/19. Shipped JavaScript
  has a separate Node transport receipt; both servers have real stdio receipts.
- Pinned Ruff 0.8.4 and Black from the cached 24.10.0 pre-commit checkout pass.
- Different-model review: gpt-5.6-sol closed the first two receipt gaps, then
  reviewed workspace acceptance, backward compatibility and the browser probe
  with no blockers.
- Four visible-browser runs in ABBA order completed with identical terminal
  Markdown. Baseline requires seven accepted submissions; batched requires three.
  The actual server logged 20 accepted actions and 20 exact instance joins.
- Raw observations, wheel hashes, definitions, limitations and reproduction:
  `docs/probes/latency/README.md`, `browser-receipts.json`,
  `workspace-events.jsonl`, and `wheel-manifest.json`.
- Native Codex UI observation remains blocked. The earlier installed-wheel
  receipt `resp-20260904-220004-85d8004d` is successful behavior evidence only.
  The completed measurements describe the isolated browser + real stdio path,
  not native Codex or Claude latency. Human completion speed remains unmeasured.

## CI fix by the Claude lead session (2026-09-04 late, chair: "fix 2421")

- `wiring-audit` failed: `docs/probes/latency/README.md` builds but is
  nav-unreachable. Fixed by allowlisting `docs/probes/` in
  `.audit/orphans.yml` with a reason (repo-only evidence, not site content);
  `scripts/audit_docs_wiring.py --format json` returns no findings locally.
- `changelog-entry` failed: shipped `src/` paths without a CHANGELOG line.
  Added an `[Unreleased]` "Added" entry describing the user-visible receipt
  behaviour and the older-wheel fallback.
- NOT fixed here, and not fixable in this repo: the new tests import
  `attune_forms.form_events.workspace_latency` / `stage_latency` unguarded,
  which public attune-forms 0.12.2 does not provide. attune-forms #76 merged
  2026-09-05T02:23Z but is UNRELEASED (main still `0.12.2`, its
  `[Unreleased]` section empty). The test lanes stay red until a forms
  release ships and this PR bumps the floor + `uv.lock`.
- Written from a detached scratch worktree and pushed by refspec; the Codex
  worktree at `~/.codex/worktrees/c655/attune-ai` was not touched — pull
  before committing again there.

## Next action

Review the paired cross-repository change for shipping. Before release,
choose/version the new attune-forms release and update the consuming dependency
floor as appropriate. No release or push was requested in this task.
