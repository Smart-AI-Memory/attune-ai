# Spec: CI Test-Matrix Failures

**Status**: approved

---

## Phase 2: Design

### Architecture

Three independent fixes, each one PR. Stage smallest blast radius
first, verify each phase before moving on. Don't bundle.

```
Phase A: DEPS + tiktoken contract     ← pyproject.toml + test split
   │
   ├─ Expand [dev] extra: redis, langchain-anthropic, tiktoken
   ├─ Resolve tiktoken contract: test both paths (with + without)
   └─ Verify: 16 cross-platform failures → 0
   │
   ▼
Phase B: WINDOWS STDOUT ENCODING      ← Python script change
   │
   ├─ Reconfigure stdout to utf-8 in plugin/hooks scripts
   └─ Verify: 4–5 Windows-only failures → 0
   │
   ▼
Phase C: WINDOWS PATH SEPARATOR       ← parser change
   │
   ├─ Use os.pathsep in workspace_roots()
   └─ Verify: 1 Windows-only failure → 0
   │
   ▼
DONE: full 12-job matrix green → unblock dependabot PRs
```

### Phase A — Missing CI deps + tiktoken contract

**Two intertwined root causes**, both addressed in one PR.

**Root cause 1:** CI runs `pip install -e .[dev]`. The `[dev]`
extra (pyproject.toml lines 198–224) doesn't include `redis`,
`langchain-anthropic`, or `tiktoken`. Tests that import them fail
at collection time.

**Root cause 2:** `src/attune/models/token_estimator.py` lines 17–23
treat `tiktoken` as optional with a heuristic fallback:

```python
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
```

But `tests/unit/models/test_token_estimator.py::TestGetEncodingPaths::*`
asserts `result is not None`, which is only true when tiktoken IS
available. Production says "optional," tests say "required" —
contradictory.

**Fix:**

1. **Expand `[dev]` in `pyproject.toml`** to include
   `redis>=5.0.0,<8.0.0`, `langchain-anthropic`, and `tiktoken`.
   This restores local-CI parity: a contributor running
   `pip install -e .[dev]` gets the same environment CI uses.

2. **Resolve the tiktoken contract by testing both paths.**
   Tiktoken stays optional in production (the heuristic fallback
   has real value — works without binary deps). Update tests:

   - **Existing `TestGetEncodingPaths` tests** stay; with tiktoken
     installed they pass as-is.
   - **Add a new `TestGetEncodingPathsNoTiktoken`** test class that
     uses `unittest.mock.patch` to set
     `attune.models.token_estimator.TIKTOKEN_AVAILABLE = False`
     and asserts the expected fallback behavior (returns `None`,
     production code falls back to heuristic).

   Both paths get coverage. The contradiction is resolved by
   acknowledging: tiktoken is optional, and we test both modes.

**Why expand `[dev]` (Option A2) instead of editing the workflow
(Option A1):** local-CI parity. A contributor running
`pip install -e .[dev]` should get the same test-runtime
environment CI uses, so they can reproduce CI failures locally.
Putting test deps in `[dev]` makes that contract explicit.

**Considered alternatives (rejected):**

- *Workflow-level install (Option A1):* `pip install -e .[dev,memory,agents]`
  in CI keeps `[dev]` smaller but breaks the local-CI parity goal.
  Contributors would hit the same dep failures locally that the
  spec just fixed in CI.
- *Make tiktoken a hard dep (remove try/except):* throws away the
  heuristic fallback's value. The fallback is real — people without
  binary deps shouldn't pay a hard install cost for ~5% better
  token counting.
- *`pytest.importorskip("tiktoken")` only:* skipping is strictly
  worse than running. Use it as a fallback if Phase A's tiktoken
  install proves fragile (Risk 2 in requirements.md), not as the
  primary path.

### Phase B — Windows cp1252 stdout

**Root cause:** `plugin/hooks/compact_warning.py` and
`plugin/hooks/spec_orient.py` write Unicode characters (`⚠️`,
arrows, em-dashes) to `sys.stdout`. On Windows, default stdout
encoding is cp1252; non-mappable characters raise
`UnicodeEncodeError`. The hooks have `try/except` wrappers that
swallow the exception, so the user sees nothing — silent breakage.

**Fix:** at the top of each affected script, before any
`sys.stdout.write()` calls, add:

```python
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

`errors="replace"` ensures a stray non-encodable byte substitutes
`?` rather than crashing. For informational hook output, that's
the right tradeoff. Risk #4 in requirements.md notes this is
defense-in-depth, not a license to spew arbitrary Unicode.

**Affected files:** at minimum
`plugin/hooks/compact_warning.py` and `plugin/hooks/spec_orient.py`.
Audit every other `plugin/hooks/*.py` for `sys.stdout.write` /
`print()` calls and apply the reconfigure idiom uniformly. Don't
guess which scripts are safe — apply it everywhere as a defensive
default for hook output.

**Considered alternatives (rejected):**

- *Strip emoji from hook output:* loses information density and
  wouldn't catch the next stray Unicode character (em-dash,
  arrow, etc.). The reconfigure is one-time and permanent.
- *Wrap each `write()` call in try/except:* duplicates the hook's
  outer try/except and still loses the message on failure. The
  reconfigure prevents the failure outright.

### Phase C — Windows path separator

**Root cause:** `tests/unit/hooks/test_session_continuity_state.py`
line 250:

```python
monkeypatch.setenv("ATTUNE_AI_WORKSPACE_ROOTS", f"{tmp_path / 'a'}:{tmp_path / 'b'}")
```

uses `:` as the separator (POSIX `PATH` convention). On Windows,
`tmp_path` looks like `C:\Users\...`, so the resulting env var is
`C:\...\a:C:\...\b`. The production parser splits on `:`,
producing `["C", "\...\a", "C", "\...\b"]` — drive letters torn
off.

**Fix (production parser):** use `os.pathsep` instead of
hardcoded `:`.

```python
roots_env = os.environ.get("ATTUNE_AI_WORKSPACE_ROOTS", "")
roots = [Path(p) for p in roots_env.split(os.pathsep) if p]
```

**Fix (test):** match the parser by using `os.pathsep.join(...)`:

```python
monkeypatch.setenv(
    "ATTUNE_AI_WORKSPACE_ROOTS",
    os.pathsep.join([str(tmp_path / "a"), str(tmp_path / "b")]),
)
```

Both fixes ship together. Locating the production parser is the
first step (likely in `attune.hooks.scripts.session_continuity_state`
or `plugin/hooks/_state.py` — confirm with `git grep
ATTUNE_AI_WORKSPACE_ROOTS`).

**Documentation:** add a one-line note wherever
`ATTUNE_AI_WORKSPACE_ROOTS` is documented (CLAUDE.md, README,
`.help/` templates if present): "uses `os.pathsep` (`:` on POSIX,
`;` on Windows)."

### Verification gates

After each phase:

1. **Push the change to a feature branch.**
2. **Trigger CI** (push triggers it automatically).
3. **Read the matrix result.** Expected delta:
   - After Phase A: ubuntu and macos jobs all green; Windows jobs
     still fail on encoding + path-separator. 8 jobs green / 4
     failing.
   - After Phase B: Windows jobs fail only on the path-separator
     test. 11 jobs green / 1 job failing.
   - After Phase C: all 12 green.
4. **If the delta isn't what's expected**, stop. Either the
   diagnosis is incomplete or another regression has slipped in.
   Investigate before continuing.

### Out-of-scope cross-references

- **`auto-approve-dependabot` job** is gated on the test matrix.
  Recovers automatically when the matrix recovers. No spec work
  needed.
- **PRs #191 and #192** (dependabot) are downstream beneficiaries.
  Once `main`'s CI is green, they'll show green CI and be
  mergeable. No work in this spec touches them directly.
- **PR #206 — dependabot auto-merge for patch updates** is
  already open. Independent of this spec; will only fire
  effectively once CI is green again.

### Failure-to-deliver fallback

If Phase A reveals deeper test-environment issues (e.g. the redis
tests need a running Redis server, not just the `redis-py`
library):

1. **Mark Phase A as partial.** Document which subset of the 11
   redis tests work with library-only install and which need
   server.
2. **For server-requiring tests**, mark with
   `@pytest.mark.skipif(not redis_server_available(), reason=...)`
   or move them to `tests/integration/` (already excluded from
   the unit run).
3. Continue with Phases B and C — they're independent.
4. The spec ends with **partial** status: matrix mostly green,
   N tests skipped on server-less CI. Document the skip count.

This is acceptable because the goal is **a reliable CI signal**,
not "every test must run on every platform." A skip with a
documented reason is honest; a silent failure is not.
