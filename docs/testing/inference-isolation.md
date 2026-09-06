# Inference isolation in tests

Ordinary pytest runs install `tests/_inference_guard.py` from
`tests/conftest.py` before application imports or test collection. This applies
to the controller and xdist workers. No API key, pytest marker, or saved login
opts a test into inference. Production imports do not install the guard.

## Why empty keys were insufficient

The suite previously isolated Attune/Redis settings but had no inference
barrier. `SecurityAuditWorkflow._run_agent_audit` calls the Agent SDK, whose
subprocess transport starts Claude with its own environment and authentication.
A missing or empty API key cannot prove that this child lacks a saved login.
An application fallback can also catch an ordinary connection exception and
continue through another provider. Tests must stop at the inference boundary,
independently of the credentials available there.

The September 6 daily usage export does not identify an initiating session.
Matching dates/models do not establish attribution or authorization for paid
inference. The usage estimate
remains unattributed. These changes do not reconstruct that billing history.

## Enforced boundaries

- Real `httpx`, `http.client`, and `urllib3` HTTP requests require a
  fixture-owned endpoint. This also blocks arbitrary local proxies that could
  perform remote inference behind an ordinary-looking URL. External Python socket
  connections, datagrams, and DNS lookups are rejected before network access.
- Claude/Agent SDK inference, the repository's other provider CLIs, and network
  CLI calls are rejected before process creation. Shell/env/node wrappers,
  executable overrides, and the SDK's streaming command shape are checked.
  Exact non-inference checks such as `--version`, `--help`, `auth status`, and
  `plugin list` remain available.
- Every real `Popen` child gets scrubbed provider credentials, an isolated
  `CLAUDE_CONFIG_DIR`, and a Python startup guard, including when the caller
  supplies a replacement environment. Python flags that disable that startup
  guard are rejected. Bootstrap failure exits the child rather than continuing.
- `InferenceBlocked` derives from `BaseException` so normal application
  `except Exception` fallback/degradation handlers cannot turn an attempted
  inference into a passing test. Mock the boundary the test is meant to use;
  do not catch this exception in application code.

All environment changes are local to test processes and restored on teardown.
No normal interactive authentication file, login, or shell configuration is
changed. Dashboard tests also redirect their saved admin-key lookup into the
fixture directory.

## Writing tests

Patch the workflow/SDK boundary or inject `httpx.MockTransport`/ASGI transports.
These continue exercising real application and client behavior without network
inference. Environment-construction tests assert the environment passed to an
intercepted launch; the isolation regressions separately prove real child
credentials are scrubbed.

For a real local HTTP round trip, bind a fixture-owned socket on loopback port
zero, then use `loopback_http_fixture(server.socket)` while it remains open.
Only that bound endpoint is permitted; other model endpoints remain blocked.
For a real connection-refusal receipt, keep a bound socket open without calling
`listen`. Do not assume a fixed local port is empty. Fixture servers must close
and join their threads on teardown.

```bash
.venv/bin/python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
.venv/bin/python -m pytest tests/unit/test_inference_isolation.py -n 0 \
  --cov=tests._inference_guard --cov-config=tests/inference-coverage.ini
.venv/bin/python -m pytest tests
```

The first command prepares static tokenizer vocabulary data outside pytest;
it makes no inference request. CI caches this data in `TIKTOKEN_CACHE_DIR`
and requires preparation to succeed before the matrix, coverage, timezone
and no-auth integration suites. The same cache directory is inherited by
every step in those jobs. A cold test process must not download it through
the inference guard, and a failed setup does not skip tokenizer assertions.

The no-auth integration lane runs separately from the default coverage
selection. Its AMS readback tests use a fixture-owned HTTP service, including
a real 404 for an acknowledged but unpersisted write. MCP stdout tests select
the fixture-local file backend explicitly; dispatch, sanitization and JSON-RPC
frames still run through production code. The invalid-key test exercises the
real SDK's 401 handling through `httpx.MockTransport`. These tests never need
an ambient AMS service or a provider response.

The dedicated coverage configuration includes the test-support implementation,
which the normal production coverage configuration deliberately omits.
Regression probes use fake credentials, inert CLI fixtures, intercepted network
transports, and nested pytest runs. They must fail without making a provider
request even if a guard regresses.

## Limits

This is protection against accidental inference through the suite's Python
transports and recognized CLI launch paths, not an operating-system sandbox for
hostile tests. Arbitrary native programs, opaque shell scripts, direct native
network bindings, or deliberate removal of the guard need an OS-level network
sandbox before they can be treated as untrusted. Python plugins imported before
`tests/conftest.py` are also outside its collection-time installation boundary.
Do not add a new provider/transport without extending the guarded-boundary
regressions. There is no live-inference opt-out in this pytest setup; separately
authorized live-provider work needs a separate runner and spend approval.

The full-tree receipt uses the repository's existing default marker exclusions.
The six existing live AMS tests now carry integration/network markers and defer
availability probing until fixture setup. Their assertions are unchanged;
collection no longer auto-discovers a running model-backed memory service.
Its legacy Redis integration module additionally needs an isolated Redis
instance/database; this inference guard does not make destructive Redis tests
safe against a user's shared database.
