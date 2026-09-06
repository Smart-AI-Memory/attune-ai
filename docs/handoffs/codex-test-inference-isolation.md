# Agent work handoff

## Goal

Make ordinary attune-ai tests fail before real inference, without changing
interactive authentication. Prepare this focused fix for Claude review.

## Acceptance criteria

- Direct API and Agent SDK/Claude CLI inference boundaries fail closed.
- Fake credentials and intercepted calls prove the guard without provider probes.
- Legitimate mocked tests and non-inference CLI diagnostics remain usable.
- At least 90% coverage on the guard; full configured test tree passes under
  isolated credentials before pushing.
- Preserve PR #2444; no auto-merge, no host-surface-parity increment 3.

## Scope and assumptions

- Branch: `codex/test-inference-isolation`, separate worktree created from
  `origin/main` at `db4e9ffb1a0eb1e9f62cbbd3e9dfd5ceb7a06de4`; rebased for the CI repair onto `3ff6b5a2677e47e9631868a4f80c77bcd11fd489` (#2447).
- Local worktree: `/private/tmp/attune-test-inference-isolation-20260906`.
- Provider: Codex executes; Claude requested changes on the original head. The CI repair needs a fresh Claude review.
- Original parity worktree and PR #2444 remain separate and unchanged.
- The September 6 usage estimate remains unattributed. Dates/models are not
  evidence identifying an initiating session.

## Current state

- Read-only preflight and Git/PR inspection preceded edits. Preflight reported
  no failures and warnings about the separate main checkout; that checkout was
  left untouched. #2444 was confirmed open before work and before publication.
- The previous conftest had no inference barrier. The security-audit workflow's
  Agent SDK path can launch Claude with authentication independent of empty
  parent API keys. The new regression exercises that real SDK transport with
  an inert executable and fake saved authentication, and stops before launch.
- The exact historical test node that initiated the reported live audits has
  not been established. The previously fixed MCP path-containment test already
  mocks its workflow correctly; this change does not relabel it as the culprit.
- The guard installs before application imports/collection, checks real HTTP
  transports and external Python sockets, checks subprocess launch paths,
  scrubs credentials and supplies private Claude configuration to children,
  and propagates into ordinary Python children. No production auth code changes.
- Initial validation exposed ambient local AMS access as a gap in endpoint-name
  filtering. Real HTTP now requires a fixture-owned endpoint, including local
  proxies. Six existing live AMS tests are correctly marked integration/network;
  their assertions remain intact and availability probing no longer happens
  during collection. No broad test skip was introduced.
- The Ollama unit test now retains a real HTTP request/parse round trip against
  a deterministic fixture. Saved admin-key lookup is isolated in dashboard tests.
  Environment-construction tests inspect intercepted subprocess arguments.
  Hook and chart tests now inject their memory dependencies; webhook tests
  still assert pinned socket destinations and original TLS SNI with intercepted
  connection factories.
- See `docs/testing/inference-isolation.md` for scope, authoring instructions,
  and limitations. This is a test guard, not a hostile-code OS sandbox; opaque
  native wrappers and plugins imported before conftest remain outside its scope.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Guard behavior, cold collection, controller/workers, SDK and direct HTTP boundaries | `.venv/bin/python -m pytest tests/unit/test_inference_isolation.py -q -n0 --cov=tests._inference_guard --cov-config=tests/inference-coverage.ini` | 74 passed; 99.20% statement/branch coverage |
| Whole configured tree under isolated credentials | `.venv/bin/python /private/tmp/run_parity_suite.py` | 25,618 passed, 242 skipped, 3 xfailed; 78.91s |
| Pinned repository hooks | `uv run --frozen --with pre-commit pre-commit run --files <changed files>` | All pinned hooks passed |

The whole-tree wrapper starts disposable loopback Redis with persistence off,
sets empty provider API keys and a private Claude profile, and invokes
`pytest -p parity_isolated_redis tests -n auto`. Its temporary pytest plugin
restores the disposable Redis URL after the existing env-scrub fixtures only
for `tests/memory/test_redis_integration.py`, with one DB per xdist worker.
The committed inference guard enforces inference isolation independently of
that wrapper. No API-backed workflow or live-provider probe is a validation
step. Earlier diagnostic runs reached the existing local AMS service; no
billing attribution is inferred from those accesses.

## CI repair after Claude review (2026-09-06)

The earlier whole-tree receipt was macOS/Python 3.11 with a warm tokenizer
cache and the default integration exclusion. It did not certify the Windows
matrix or the no-auth integration lane. Downloaded CI logs independently
confirmed the Windows missing-executable crash, cold tokenizer downloads,
unisolated AMS paths, live invalid-key request and orphan documentation.

- Windows Popen audit events check argv when the executable override is
  absent. Quoted Windows command strings still reject inference and Python
  bootstrap bypass flags. No guard exception is swallowed in production.
- Cold pytest children scrub parent PYTEST_ADDOPTS/PYTEST_PLUGINS.
- Test, timezone, coverage and no-auth integration jobs prepare static
  cl100k_base data before pytest. Setup failure fails the step; no test skip
  or HTTP exemption was introduced. The job-wide cache path covers every
  pytest step. The rebase reconciles #2447's tokenizer setup into one strict warm-up
  per job and the shared cache environment, without duplicate setup steps.
- AMS readback tests use real HTTP with a fixture-owned service: successful
  create/readback and an acknowledged-but-unpersisted write returning 404.
  They make no claim to test a deployed AMS server or its embedding model.
- MCP and doctor tests select the fixture-local file backend for unrelated
  memory diagnostics. Redis endpoint tests still use real RESP sockets;
  dispatch/sanitization and stdout JSON-RPC frames remain production paths.
- Invalid-key handling uses the real SDK through MockTransport with a 401,
  asserting status, request count, path and the fake key sent.
- The documentation now has a Contributing navigation entry.

Verified receipts for this repair:

- Focused guard + workflow checks: 423 passed, 1 existing skip; guard
  statement/branch coverage 99.21%. Log: `/private/tmp/2445-round2-focused.log`.
- Exact no-auth integration selection: 234 passed, 41 existing skips in
  6.32s, guarded with disposable Redis and a freshly prepared tokenizer
  cache. Log: `/private/tmp/2445-round2-integration.log`.
- Doctor boundary rerun: 51 passed. The initial post-rebase whole tree
  exposed 16 doctor tests reaching the newly merged AMS diagnostic; the
  fixture-local file preference repairs that dependency without changing
  their assertions. Log: `/private/tmp/2445-round2-doctor.log`.
- Whole configured tree after the doctor repair: 25,685 passed, 242 existing
  skips, 3 xfailed in 75.25s. Log:
  `/private/tmp/2445-round2-whole-tree-final.log`. Inference guard active,
  isolated credentials, freshly prepared tokenizer cache and disposable Redis.
- Documentation wiring audit: no findings. Pinned hooks passed on the repair
  files, including the doctor fixtures; they run again at commit.

## Post-#2447 rebase receipts

Base `3ff6b5a2677e47e9631868a4f80c77bcd11fd489`; the sole conflict was
`.github/workflows/tests.yml`. The resolved file retains one strict warm-up
per job and the job-wide cache environment. The workflow regression also
rejects duplicate cache/warm steps.

- Guard + workflow checks: 423 passed, 1 existing skip, 99.21% guard
  statement/branch coverage. `/private/tmp/2445-post2447-focused.log` and
  `/private/tmp/2445-post2447-coverage.json`.
- Whole configured tree: 25,715 passed, 242 existing skips, 3 xfailed in
  81.69s. `/private/tmp/2445-post2447-whole.log`.
- No-auth integration: 234 passed, 41 existing skips in 6.05s.
  `/private/tmp/2445-post2447-integration.log`.
- Both suite runs used the committed guard, isolated credentials, the prepared
  static tokenizer cache and disposable Redis. No live inference was attempted.

## Next action

Publish the signed repair and verify the fresh CI matrix, including Windows.
Claude reviews the repaired head; the chair merges. Do not auto-merge or
launch a review agent. The parity work is preserved in its separate #2444
worktree and resumes after the required upstream merges. Do not start
increment 3. The September 6 usage estimate remains unattributed.
