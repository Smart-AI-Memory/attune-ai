# Spec: CI Test-Matrix Failures (Pre-existing)

**Status**: complete (2026-05-10) — Phase A `68f19b90`, Phase B `28441852`, Phase C `463df6a5`
**Created**: 2026-05-09
**Discovered**: while verifying that the `ignored-tests` spec landing on
`main` (`e872eae9`) didn't break CI. Investigation revealed `main` was
*already* failing CI before the merge (verified back to commit
`5d99da29` and earlier).

---

## Phase 1: Requirements

### Problem statement

The GitHub Actions test matrix (3 OS × 4 Python versions = 12 jobs)
fails on every commit to `main`. Failures predate the most recent
work — `main`'s CI history shows `failure` on `1e7b0170` and back
through `5d99da29`. **It is unclear how long CI has been red.**

The local test signal (`pytest tests/unit/ -n auto`) is green
(14,110 passed as of 2026-05-09). CI fails because the CI environment
differs from local in three ways:

1. **CI installs only the `[dev]` extra** (`pip install -e .[dev]` in
   `.github/workflows/tests.yml:39`). Several optional runtime deps
   referenced by tests are not pulled in.
2. **CI runs the full suite under one process per job** (no xdist
   sharding across machines), so any single import failure cascades.
3. **CI exercises Windows**, which surfaces UTF-8/cp1252 encoding
   bugs and POSIX-vs-NT path-separator bugs that don't appear on
   Unix.

### The failures (by category)

Sampled from CI run `25608603583` (the run for `e872eae9` on `main`).
Counts are per-job; total cross-platform failures are ~16, plus
~6 Windows-only.

| Category | Failing tests | Cross-platform | Root cause |
|---|---|---|---|
| **Missing dep: `redis`** | 11 | yes | `tests/unit/memory/test_pubsub_direct.py` does `from attune.memory.short_term.pubsub import PubSubManager` which imports `redis` unconditionally. CI's `[dev]` extra doesn't include `redis-py`; `[memory]` does, but isn't installed. |
| **Missing dep: `langchain_anthropic`** | 2 | yes | `tests/unit/agent_factory/test_langgraph_adapter.py::test_anthropic_*` imports `langchain_anthropic`. Not in `[dev]` or any other installed extra. |
| **`tiktoken` test/production contract drift** | 3 | yes | `src/attune/models/token_estimator.py` treats `tiktoken` as optional with a try/except + heuristic fallback. But `tests/unit/models/test_token_estimator.py::TestGetEncodingPaths::*` asserts `result is not None`, which only holds when tiktoken IS installed. Two contradictory contracts in one codebase. CI surfaces it because tiktoken isn't installed. |
| **Windows: cp1252 stdout encoding** | 4–5 | Windows only | `plugin/hooks/compact_warning.py:101` calls `sys.stdout.write(...)` with content containing `⚠️` (line 59). Windows console default is cp1252; the warning emoji has no mapping → `UnicodeEncodeError`. Same pattern affects `spec_orient.py`. The hook's try/except swallows the exception, so on Windows the warning silently never displays. |
| **Windows: path separator** | 1 | Windows only | `tests/unit/hooks/test_session_continuity_state.py::TestWorkspaceRoots::test_override_takes_precedence` joins paths with `:` (POSIX `PATH`-style separator). On Windows the separator is `;`; the production parser splits on `:` and matches the drive letter (`C:`), shredding the path. |
| **`auto-approve-dependabot`** | 1 | n/a | Gated on `tests` matrix passing. Will recover when the underlying tests recover. No independent action needed. |

### Why this matters

- **CI signal is broken.** Every PR shows `tests` as failing,
  including dependabot updates (#191, #192). Reviewers can't tell
  whether a PR introduced a regression or just inherited the broken
  state. This is exactly the false-confidence problem the
  `ignored-tests` spec was about, just one layer up.
- **Dependabot PRs back up.** With CI red, even green-after-rebase
  dependabot PRs need manual override to merge. Security patches
  sit instead of landing.
- **The tiktoken contract is internally inconsistent.** Production
  treats it as optional (heuristic fallback exists); tests treat it
  as required (assert non-None). Whichever is right, the other is
  a bug.
- **Windows users are silently unsupported today.** The cp1252
  crash means every `compact_warning` invocation on Windows raises
  an exception (caught by the hook's `try/except`, swallowed
  silently). The warning never displays. Same for `spec_orient`.
  Fix is small and worth doing now.

### Goals

- **G1: Test matrix green on every commit to `main`.**
  All 12 jobs (3 OS × 4 Python) pass without `--maxfail`
  truncation.
- **G2: Each fix is a single, named root cause** — no shotgun
  patches. Expand the `[dev]` extra for dep failures; resolve the
  tiktoken contract architecturally; reconfigure stdout in the
  hook scripts; use `os.pathsep` in the parser.
- **G3: The tiktoken optional/required contradiction is resolved.**
  Either tiktoken is genuinely optional (test both code paths) or
  it's required (declare it a hard dep). One answer, not two.
- **G4: A dependabot PR can land green** without any further
  intervention from this spec, proving the fix.
- **G5: Windows is no longer a silently-broken second-class
  platform.** The hook scripts and the workspace-roots parser
  work correctly on Windows. The test matrix continues to verify
  this on every commit.

### Non-goals

- **Not fixing the 14,110-test suite to add coverage.** The local
  suite is already healthy; this spec only addresses the gap
  between local and CI.
- **Not touching xdist parallelism in CI.** The local-CI parity
  goal from the `test-infrastructure` spec was about having one
  command that works locally; CI's per-job VMs already amortize
  the memory cost.
- **Not refactoring `plugin/hooks/*.py` for cross-platform.** Fix
  the encoding bug and the path-separator bug; don't rewrite the
  architecture.
- **Not setting up dependabot auto-merge.** A reasonable adjacent
  PR (auto-merge `version-update:semver-patch` only), but a
  separate decision (already opened as PR #206). This spec only
  ensures CI is green so that dependabot PRs can land cleanly.

### Success criteria

- `gh run list --workflow=tests --branch=main --limit=5 --json conclusion`
  → all `success`.
- A test PR (e.g. a no-op docstring change) lands green on all 12
  matrix jobs (3 OS × 4 Python).
- Dependabot PRs #191 and #192 — already updated to track current
  `main` — show green CI and are mergeable without override.
- `grep "tiktoken" pyproject.toml tests/unit/models/test_token_estimator.py`
  shows one consistent contract — either tiktoken is in the deps
  list AND the tests assert non-None, or it's gated by
  `pytest.importorskip` and a separate test class covers the
  fallback path.
- `grep -rE "sys\.stdout\.write|^\s*print\(" plugin/hooks/` returns
  no unprotected writes (all wrapped or stdout reconfigured).

### Risks

- **Risk 1 — expanding `[dev]` reveals more failures.** Once
  `redis-py` and `langchain-anthropic` are pulled in, the 13
  previously-skipped tests run and may surface more issues (e.g.
  the redis tests requiring a real Redis server, not just the
  library). Mitigation: stage by category; verify Phase A's CI
  delta before moving on.

- **Risk 2 — `tiktoken` install brings a Rust-compiled wheel.**
  Tiktoken ships pre-built wheels for common platforms, but
  occasionally a runner can fall through to source build (no
  `cargo` available → fail). Mitigation: pin to a version with
  known good wheels, or restrict to `--only-binary=:all:` in the
  CI install.

- **Risk 3 — expanding `[dev]` is a contract change for
  contributors.** Anyone who has `pip install -e .[dev]` cached
  from a stale checkout will have a smaller env than CI until they
  reinstall. Mitigation: low-impact — a fresh `pip install -e .[dev]`
  fixes it. Mention in `CONTRIBUTING.md` if it has install
  instructions.

- **Risk 4 — `sys.stdout.reconfigure(encoding='utf-8',
  errors='replace')` substitutes `?` for non-encodable bytes.**
  For informational hook output that's the right tradeoff (don't
  crash, don't block), but a stray non-ASCII character in a
  user-facing message would silently degrade. Mitigation: keep
  hook output deliberately ASCII-safe where possible; the
  reconfigure is a defense-in-depth, not a license to spew
  arbitrary Unicode.

- **Risk 5 — `os.pathsep` in `workspace_roots()` is a behavior
  change.** Existing users on macOS/Linux who set
  `ATTUNE_AI_WORKSPACE_ROOTS=/foo:/bar` still work (`os.pathsep`
  is `:` on POSIX). Windows users who set the env var with `:`
  break. Mitigation: documented in CLAUDE.md / README wherever
  the env var is mentioned; Windows users this far in are rare.

- **Risk 6 — long uncertainty about how long CI has been red.**
  Without a clear "regressed at commit X" point, can't bisect.
  Have to fix forward. If a fix doesn't move the needle, it
  signals the failure was always there — not a regression we
  caused.
