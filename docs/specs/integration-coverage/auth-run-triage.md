# Auth bucket — first-run triage (2026-06-09)

First dispatch of `integration-auth.yml`
([run 27249292521](https://github.com/Smart-AI-Memory/attune-ai/actions/runs/27249292521)),
fired manually right after #723 merged as the dogfood proof
("registered ≠ working"). Result: **24 failed / 9 passed in 18 s, zero
API spend** — the job did exactly what it exists for: it surfaced two
infrastructure problems and one suspicious-pass smell before the first
scheduled nightly.

## Finding 1 — the repo `ANTHROPIC_API_KEY` secret is not a valid key

Every real API call failed with `anthropic.APIConnectionError:
Connection error`, and the provider logged:

> API key does not start with 'sk-ant-'. Anthropic API keys typically
> start with 'sk-ant-api03-'.

So the secret exists but holds something that isn't an Anthropic API
key (placeholder, truncated value, or a different credential).
**Owner-only fix:** set a real key at repo Settings → Secrets →
Actions → `ANTHROPIC_API_KEY`. Until then every nightly run fails the
same way at zero cost.

Affected: all of `test_llm_integration.py`'s real-call tests
(16 failures).

## Finding 2 — all 6 `*_with_auth` files are rot (pre-API failures)

Every `*_with_auth` file fails at workflow construction, before any
API call:

| File | TypeError kwarg |
|------|-----------------|
| test_bug_predict_with_auth.py | `enable_auth_strategy` |
| test_code_review_with_auth.py | `file_threshold` |
| test_gen_with_auth.py | `enable_auth_strategy` |
| test_perf_audit_with_auth.py | `enable_auth_strategy` |
| test_release_prep_with_auth.py | `skip_approve_if_clean` (×3 tests) |
| test_security_audit_with_auth.py | `enable_auth_strategy` |

`BaseWorkflow.__init__()` no longer accepts these kwargs — the files
predate the SDK migration and were never exercised (same rot class as
the Phase 1 no-auth backlog, which deliberately excluded the auth
bucket). They also look script-shaped (print-based, demo-style
bodies), so the triage question per file is **rewrite as a real
assertion-bearing integration test vs retire** — apply the Phase 1
playbook in [phase1-triage.md](phase1-triage.md).

## Finding 3 — the 6 discovery_sweep tests "passed" in 18 s (suspicious)

With the broken key set, the env-gate (`skipif` on
`ANTHROPIC_API_KEY`) let the 6 discovery_sweep tests run — and they
passed within an 18-second total run. A real `depth="quick"` SDK run
takes minutes, so these almost certainly passed **for the wrong
reason** (the wrapped workflow degrades a connection failure into an
empty/error result the assertions tolerate). Re-judge them on the
first run with a valid key; if they still pass in seconds, tighten
their assertions to require a successful workflow result.

## Sequencing

1. Patrick sets a valid `ANTHROPIC_API_KEY` secret (blocker for
   everything else).
2. Rewrite-or-retire pass over the 6 `*_with_auth` files (one PR).
3. Re-dispatch `integration-auth.yml`; judge discovery_sweep pass
   quality and the known `test_thinking_mode` Opus-4.8 400 with real
   signal.
