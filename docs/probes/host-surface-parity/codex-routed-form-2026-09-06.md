# Codex routed-form trials — 2026-09-06

These are exploratory live-host receipts for the bounded D14 milestone,
not a complete host-parity or latency claim.

## Setup

The existing isolated `attune-ai-preview` exposes `elicitation_route_form`.
Its installation is recorded in `docs/handoffs/codex-codex-form-interaction.md`.
The current session called that connected tool; no caller supplied capabilities,
session identity, evidence, or receipt bindings. The serving process's build
was not independently re-attested during these trials.

## Explicit integration trial

A planning form asked for scope, minutes and outcome. The server returned:

- `selected_route`: `mcp-native:surface-native-elicitation`.
- Accepted, validated `server_observed_completion`.
- `response_id`: `resp-20260906-140704-26a75087`.
- One render, two presentations, `context_reason: missing_receipt`.
- Selection elapsed: 0.7815000135451555 ms (not display latency).

Patrick subsequently confirmed the controls: **“they worked”**. The specific
first-attempt validation problem was not captured. The final response exposes
the attempt count, not its discarded answers; no retry defect is inferred.

## Ordinary-request trial

After reading the updated elicit guidance, the active assistant received:
**“plan a website for a band”**. The prompt named no form or tool. This was an
announced trial in the existing session, not a blinded or fresh-session test
of automatic skill discovery.

The assistant selected the routed endpoint and asked three independent
dimensions: band identity/style, primary site purpose and launch scope.
The validated answers described a punk band, bookings from venues/promoters,
and a full site including a merchandise store. The assistant continued with a
website plan in the same task, without recollecting the response.

- `response_id`: `resp-20260906-141154-5b90134f`.
- `selected_route`: `mcp-native:surface-native-elicitation`.
- Outer success and nested completion success; action `accept`.
- Provenance: `server_observed_completion`.
- One render, one presentation, `context_reason: missing_receipt`.
- Selection elapsed: 0.7705839816480875 ms (not display latency).

This verifies one guidance-following continuation with genuine host answers.
It does not establish universal automatic selection or exactly-once application
side effects; lifecycle regressions supply separate evidence for their tested
boundaries. The second trial has no separate user paint attestation or recording.

## Checks and remaining evidence

Central reruns from the feature worktree using the isolated-credential,
disposable-Redis harness:

- Runtime, policy and bootstrap suites: 92 passed.
- Skill projection suite: 38 passed.
- Final combined projection/configuration/help checks: 72 passed after
  shortening the description to the supported limit and regenerating help.
- Final whole configured tree: 26,056 passed, 242 skipped, 3 xfailed;
  `/private/tmp/form-guidance-whole-final.log`.
- `scripts/sync_agents_skills.py --check`: 45 sources in sync.
- Different-model advisory review: no concrete guidance defects; reviewed
  ordinary/settled input, preferences, accept/abort and unavailable-route cases
  against the code and D10/D14. This was source review, not a live host probe.

Neither trial has request-to-visible video timing. Do not subtract selection
or tool duration from perceived waiting time. A completed native interaction
has no policy-warm successor; process reuse cannot fill that missing stratum.
Repeated measured display trials and a fresh-session discovery trial remain
open. Other hosts and richer widget layouts remain outside these receipts.
