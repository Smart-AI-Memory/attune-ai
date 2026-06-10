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
   everything else). — DONE 2026-06-10.
2. Rewrite-or-retire pass over the 6 `*_with_auth` files (one PR).
   — DONE 2026-06-10, verdict: retire all 6 (below).
3. Re-dispatch `integration-auth.yml`; judge discovery_sweep pass
   quality and the known `test_thinking_mode` Opus-4.8 400 with real
   signal. — DONE 2026-06-10 (below).

## Second run — valid key (2026-06-10)

[Run 27249886475](https://github.com/Smart-AI-Memory/attune-ai/actions/runs/27249886475)
(dispatched 02:53 UTC with the fixed secret): **15 failed /
18 passed in 6:06** — real API spend this time, and every failure
carries real signal.

### Finding 1 — RESOLVED

The fixed key works: `test_llm_integration.py`'s real-call tests
went 16-failed → green (the only remaining failure there is
`test_thinking_mode`, the known Opus-4.8 `max_tokens` vs
`thinking.budget_tokens` 400 on the deprecated `use_thinking`
path — exactly as predicted in phase1-triage.md).

### Finding 2 — confirmed; all 6 `*_with_auth` files RETIRED

Same 8 TypeErrors as the first run (pre-API rot). Per-file
verdict from the rewrite-or-retire read:

- 5 of 6 (`bug_predict`, `code_review`, `gen`, `perf_audit`,
  `security_audit`) are print-based demo scripts with ZERO
  assertions — they could never fail on a wrong answer, only on
  crash. Nothing to rewrite; the auth-strategy *workflow
  integration* they demo (`enable_auth_strategy=True` +
  `auth_mode_used` tracking) no longer exists for these workflows
  (it survives only in `document_gen`). RETIRED.
- `test_release_prep_with_auth.py` has real assertions, but they
  assert the dead feature (`enable_auth_strategy` kwarg,
  `_auth_mode_used` attribute, `result.provider`) on the pre-SDK
  workflow shape, and each of its 3 tests runs full release-prep
  on `src/attune` (~100K LOC) — high spend for a dead contract.
  RETIRED.
- `AuthStrategy` itself (recommendation/cost-estimate logic) keeps
  its coverage in `tests/unit/models/test_auth_strategy_coverage_boost.py`
  and `test_auth_cli.py` — retiring the demos loses nothing.

**Production bug the retirement read surfaced (fixed in the same
PR):** `security_wizard._get_or_create_workflow()` passed the same
dead kwargs to `SecurityAuditWorkflow`; the TypeError was swallowed
by the broad `except` → the security wizard silently ALWAYS used
its LLM fallback instead of the real workflow. Fixed (kwarg-free
construction) + a no-mocks regression test on the real
construction path.

### Finding 3 — re-judged: NOT vacuous; the tests caught a REAL bug

With a valid key the 6 discovery_sweep tests went
suspicious-pass → FAIL, all with "structured-emit contract failed
— adapter fell back to text-only path". Local reproduction
(BugPredictionWorkflow + STRUCTURED_EMIT_FOOTER on the test's own
fixture, 131 s real run) confirmed and root-caused it:

- The suffix IS wired (orchestrator system prompt gets the footer).
- The workflow returns `success=True` with real analysis — but
  `AgentSDKResultAdapter.from_agent_output()` REWRITES
  `final_output` whenever its own category parser
  (`_parse_findings`) extracts findings: it replaces the raw
  agent text with `_format_findings_markdown(...)`, silently
  dropping the model's ```json block. `parse_findings_json` then
  finds no block → text-only fallback. (`metadata["findings"]` is
  the category→bullet-strings dict — too weak to substitute for
  the sweep's Finding schema.)
- Why the first (broken-key) run "passed": workflow failure
  produces `source-failure`-tagged findings, and the assertions
  only reject `text-only-fallback` — an assertion hole. The tests
  should reject BOTH non-organic tags.

**Fix (separate PR):** preserve the raw agent text on a channel
the sweep adapter can read (e.g. `metadata["raw_result_text"]` in
`from_agent_output`), point `parse_findings_json` callers at it
with `final_output` as fallback, and tighten the 6 tests to also
reject `source-failure` tags.
