# Agent work handoff

## Goal

redis-config-truth rct-5 (final rung): a non-mocked requirepass
round trip that PROVISIONS its own ephemeral
`redis-server --requirepass` — random password, scratch port,
auto-teardown — so the R4 incident AC is verified on any host with
the binary, never depending on a pre-configured hardened instance.

## Acceptance criteria

- Lane RUNS (not skips) whenever redis-server is on PATH; skip ONLY
  on binary absence, pinned by a meta-test.
- Incident shape authenticates against the provisioned server
  through the resolver AND migrated consumers.
- Wrong password → live degraded_auth; missing password → live
  AuthenticationError (the pre-fix incident reproduced).

## Scope and assumptions

- Branch/worktree: `claude/rct-5-requirepass-lane`, built atop
  `claude/rct-4-consumer-migration`; rebase onto origin/main once
  PR #1993's squash lands, then open its own PR.
- Provider/session: Claude lead, 2026-08-08 starter session (cont.).
- Assumptions: no CI workflow changes (GH runners lack redis-server
  → lane skips there legitimately; it runs on dev machines, which
  is where the incident class lives).

## Current state

- Status: implemented + 8/8 live-green (serial AND xdist); awaiting
  #1993 merge to rebase + open PR + D11 lane.
- Changed files: tests/integration/test_requirepass_provisioned_lane.py
  (provisioning fixture + 5 live behavior tests + 3 contract tests).
- Decisions: meta-contract pinned two ways — provisioning-must-work
  when binary exists, plus a source-scan asserting exactly ONE
  pytest.skip guarded by binary absence (self-count avoided via
  literal split); non-default port proves no reliance on a
  pre-configured instance.
- Risks or open questions: none open.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Provisioned auth round trip | test_resolver_url_authenticates (live PING) | pass |
| Migrated consumer live | test_recall_reader_authenticates | pass |
| Live degraded_auth | test_wrong_password_classifies_degraded_auth_live | pass |
| Pre-fix incident reproduced | test_missing_password_fails_auth_live | pass |
| Skip contract | test_skip_guard_is_binary_absence_only + meta run test | pass |
| xdist-safe | lane green under -n 2 | pass |

## Next action

After #1993 merges: rebase onto origin/main, flip tasks.md (rct-4
MERGED, rct-5 in review → ladder COMPLETE on merge), open the PR,
run the D11 lane. Delete this file when the branch merges.
