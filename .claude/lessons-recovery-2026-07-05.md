# Lessons recovered from pruned worktrees (2026-07-05)

Six worktrees (all with MERGED PRs) carried .claude/lessons.md entries
that never landed on main. Extracted verbatim before worktree removal
during the 2026-07-05 housekeeping run. Triage into .claude/lessons.md
(dedupe against current corpus) and delete this file.

## From charming-cohen-432e5c

- **`/attune-gui` from inside the attune-ai worktree — the
  command's literal `.`/`./attune-gui` path checks both miss, but
  the real project is the sibling at `~/attune-gui` (don't report
  "not found")**: the `/attune-gui` slash command resolves the
  project by grepping `pyproject.toml` for `name = "attune-gui"`
  in `.` then checking `./attune-gui/`. Run from the attune-ai
  worktree, `.` is attune-ai's pyproject (no match) and
  `./attune-gui/` doesn't exist, so the literal flow says "not
  found and stop." But the actual project lives at
  `/Users/patrickroebuck/attune-gui` (verify:
  `grep 'name = "attune-gui"' ~/attune-gui/pyproject.toml`; binary
  at `~/.pyenv/shims/attune-gui`). Resolve to that sibling and set
  the launch.json `runtimeArgs` to
  `["run","--directory","/Users/patrickroebuck/attune-gui","attune-gui","--port","<p>"]`.
  Two more gotchas: (1) **port 8000 is normally occupied by the
  Redis Agent Memory Server** (`agent-memory api --port 8000`) —
  load-bearing for the memory backend, never kill it; pin attune-gui
  to a free port (`attune-gui` auto-picks a free port if `--port`
  is omitted, but the preview harness needs a KNOWN port, so pass
  `--port <free>` explicitly and match the launch.json `port`
  field). (2) attune-gui's `/` 307-redirects to `/dashboard` —
  confirm liveness with `curl -sL` and expect a final HTTP 200 on
  `/dashboard`, not on `/`. macOS has no `timeout` binary — don't
  reach for it to bound a `--help` probe.

## From compassionate-bardeen-4e27e7

  CANCELLED noise (separate, low-priority) is quietable with
  `cancel-in-progress: false` in the scan workflow.
- **Vendoring attune-ai canonical hooks into the 4 layer repos: use
  `make sync-hooks`, NEVER a manual `cp` — each layer ships a hook-drift
  guard that fails the WHOLE test matrix otherwise**: hit 2026-06-17
  doing spec-status-integrity task 7 (re-vendor `_state.py` +
  `spec_orient.py` + new `spec_audit.py` into attune-rag/gui/help/author
  `.claude/hooks/`). I `cp`'d the files and committed — all 4 layer PRs
  went red across every OS×py lane. Root cause: each layer carries
  `tests/.../test_claude_hooks_drift.py` which reads a manifest
  `.claude/hooks/.canonical-sha256` (one `<sha256>  <name>` line per hook)
  plus a Makefile `HOOK_FILES` list, and asserts (a) the manifest covers
  every on-disk `*.py` hook and (b) each on-disk file's sha matches the
  pinned canonical sha. Manual `cp` updates the FILES but not the
  manifest, so a NEW hook is `missing_from_manifest` and CHANGED hooks
  fail the sha check. The error text literally says "Run `make
  sync-hooks`". **Correct procedure per layer:** (1) add any NEW hook
  filename to `HOOK_FILES` in that layer's `Makefile` (e.g.
  `spec_audit.py`); (2) `make sync-hooks ATTUNE_AI_ROOT=<canonical>` —
  it `cp`s every `HOOK_FILES` entry from `$(ATTUNE_AI_ROOT)/plugin/hooks`
  and regenerates `.canonical-sha256` via `shasum -a 256 $(HOOK_FILES)`.
  Gotchas: (i) `ATTUNE_AI_ROOT` defaults to `../attune-ai` (the MAIN
  checkout, often behind the just-merged canonical) — pass the merged
  worktree path explicitly. (ii) A far-behind layer re-syncs MORE than
  your target hooks: attune-rag was missing `_sdk_gate.py` (a transitive
  import of the updated `spec_orient.py` → `ModuleNotFoundError` at hook
  runtime, caught by `test_claude_hooks_behavior.py`) AND behind on
  `compact_warning.py`/`format_on_save.py`/`security_guard.py` — so its
  `HOOK_FILES` needed `_sdk_gate.py` added too and its PR diff is larger;
  frame the commit as a full re-sync, not just the feature. (iii)
  `_on_disk_hooks()` scans ALL `.claude/hooks/*.py` not starting with
  `__`, so any on-disk hook absent from `HOOK_FILES` trips the manifest
  test — keep the two in lockstep. Detection: a hooks-only layer PR that
  reds the entire test matrix while the layer's `main` is green is almost
  always this. Pairs with `project_hooks_canonical_drift` (the canonical
  is attune-ai `plugin/hooks/`; layers vendor to `.claude/hooks/`).

## From flamboyant-fermi-26562a

  CANCELLED noise (separate, low-priority) is quietable with
  `cancel-in-progress: false` in the scan workflow.
- **`runpy.run_path(file, run_name="__main__")` does NOT add the
  script's dir to `sys.path` — so a script whose `__main__` block has
  a sibling-relative import (`from _sdk_gate import ...`) fails
  `ModuleNotFoundError` when its test runs in ISOLATION, yet passes in
  the full suite (an earlier test polluted `sys.path`)**: hit
  2026-06-13 on `tests/unit/hooks/test_worktree_path_guard.py`
  (`TestScriptMainEntry`, 3 tests). The hook scripts under
  `src/attune/hooks/scripts/` import their `_sdk_gate` sibling inside
  `if __name__ == "__main__":`. `runpy.run_path` on a FILE PATH runs
  that block but (unlike `python script.py`, which sets
  `sys.path[0]=script dir`, and unlike a real `subprocess.run`) leaves
  `sys.path` untouched — so the import only resolves when some earlier
  test already inserted `src/attune/hooks/scripts`. Run the file alone
  and it fails; CI was green only by accident of ordering. Latent
  since PR #521 (c1b4cf33). **Fix** (PR #853): a
  `tests/unit/hooks/conftest.py` that inserts the absolute scripts dir
  at the front of `sys.path`, so the sibling import resolves
  regardless of order. **Diagnostic**: any "passes in suite, fails
  alone" with `ModuleNotFoundError` on a sibling module → check for
  `runpy.run_path` driving a `__main__` block with a bare
  `from <sibling> import`. **Scope check before assuming it's
  isolated**: `grep -rl runpy.run_path tests/` finds every file with
  the trap; other ways of exercising the same scripts (`importlib`
  spec-from-file-location loading the module directly, plain `import`
  that never runs `__main__`, real `subprocess.run`) do NOT hit it —
  only file-path `runpy.run_path(..., run_name="__main__")` does.
  Pairs with the "stale coverage data" / test-isolation family.

## From objective-nash-a979ce

- **`memory_lint.py --check-all` with no directory argument silently
  defaults to the GLOBAL `~/.claude/memory/` dir, not the per-project
  one — "0 violations" from the bare command gives false confidence
  about a corpus it never actually scanned**: 2026-07-01, while
  designing an eval experiment against the real 78-file per-project
  memory corpus (`~/.claude/projects/<repo>/memory/`), a bare
  `memory_lint.py --check-all` reported "0 violation(s) across 61
  files" — but 61 is the GLOBAL corpus's file count, not this
  project's 78. Passing the per-project directory explicitly
  (`--check-all <project-memory-dir>`) surfaced **134 real
  violations**: bad `name:` fields (R1), schema drift — top-level
  `type:` instead of nested `metadata.type`, undocumented
  `originSessionId` keys (R2) — and dangling `[[link]]` cross-
  references where hyphens were used instead of the target file's
  underscore stem (R4). The mandatory format had been silently
  unenforced for this project's memory the whole time the bare
  command was trusted. **Rule:** when auditing a per-project memory
  directory's format compliance, always pass the directory
  explicitly — never trust the bare `--check-all`'s "clean" result
  as evidence about anything other than the global dir. Separately:
  when WRITING a memory file that discusses the `[[link]]` syntax
  itself (as this lesson's own source material did), the lint hook's
  link-resolution regex will flag literal `[[link]]`-shaped example
  text as a dangling reference (R4) even when it's prose, not a real
  cross-reference — describe the syntax without literal double
  brackets (e.g. "double-bracket reference") to avoid a false
  positive blocking the Write/Edit.


## From recursing-turing-a1c54b

  CANCELLED noise (separate, low-priority) is quietable with
  `cancel-in-progress: false` in the scan workflow.
- **Diagnosing a `workflow_run`/`check_run`-triggered automation (e.g.
  the auto-merge-safe class) — three traps that make a working trigger
  look dead, and one that makes a dead trigger look reasonable**: hit
  2026-06-14 re-testing the auto-merge-safe merge job on PR #884.
  - **`check_run` events from a `GITHUB_TOKEN`-produced check do NOT
    trigger workflows** (GitHub anti-recursion: events originated by the
    repo's own `GITHUB_TOKEN` don't start new runs). So a merge job
    wired to `on: check_run: [completed]` filtering for the `coverage`
    check going green NEVER fires — `coverage` is a job in the Tests
    workflow, produced under `GITHUB_TOKEN`. Symptom: check completes
    success, zero downstream runs, PR stays open. Fix: trigger on
    `workflow_run` (delivered for `GITHUB_TOKEN` workflows). This was
    PR #883's fix.
  - **`workflow_run` fires only when the WHOLE workflow completes (all
    matrix lanes), not when one job/check goes green.** A "merge the
    instant coverage is green" handler keyed on `workflow_run` actually
    waits for the slowest lane (windows ~13 min) and, worse, for a HUNG
    lane until its timeout. Don't conclude "didn't fire" while sibling
    lanes are still running — check the triggering workflow's overall
    status, not the one job you care about.
  - **`gh run list` shows the EXECUTING branch for `workflow_run`-
    triggered runs, NOT the triggering run's branch.** Every
    workflow_run-triggered run of a default-branch workflow shows
    `headBranch=main`/`headSha=<main sha>` regardless of which PR's
    Tests triggered it. I wrongly concluded "the trigger only fires for
    main." To tell which run triggered it, read the run LOGS /
    `github.event.workflow_run.head_sha`, never the list's branch/sha
    columns.
  - **`repos/{repo}/commits/{sha}/pulls` can return EMPTY for a real
    open PR** (eventual-consistency lag, or a fine-grained-PAT
    visibility quirk). The merge job used this to map the triggering
    `head_sha` → PR number, got nothing, and logged "No open PR against
    main" while #884 was plainly open with that head (the same call
    returned the PR fine ~17 min later from a normal token). Durable
    fixes for sha→PR mapping in automation: prefer
    `github.event.workflow_run.pull_requests[]` (populated for same-repo
    PRs), fall back to the REST call, and/or retry with backoff. Never
    trust a single `commits/{sha}/pulls` read as authoritative.

## From youthful-haslett-3bcf39

  CANCELLED noise (separate, low-priority) is quietable with
  `cancel-in-progress: false` in the scan workflow.
- **`status` is a read-only special variable in zsh — a CI-poll loop
  that does `status=$(...)` dies with `(eval):5: read-only variable:
  status`**: hit 2026-06-24 writing a background `gh pr checks` poll
  loop. zsh aliases `$status` to `$?` (the last exit code) and marks it
  read-only, so the common idiom `status=$(some_cmd)` fails the whole
  script (exit 1) the moment it assigns. The Bash tool runs under zsh
  here (user's login shell), so this bites any captured-result loop.
  Fix: name the variable anything else (`st`, `result`, `chk`). Other
  zsh read-only/special names to avoid as plain locals: `path`
  (tied to `$PATH` as an array!), `cdpath`, `fignore`, `prompt`,
  `pipestatus`. Diagnostic: the error line number points INTO the
  `python -c`/here-doc `eval` body, which misleads — read the
  `read-only variable: <name>` clause, not the line number.
- **A `cd <main-checkout> && python <reads-relative-file>` from a
  worktree session can silently read a DIFFERENT branch's copy of that
  file and produce a misleading "invariant failed" result**: hit
  2026-06-24 verifying the help-docs single-source "remaining set is
  empty" check. The Bash tool reset the shell cwd (the prefixed `cd`
  to the main checkout took effect, or partially), and the main
  checkout was on an unrelated branch (`docs/plugin-quickstart`) whose
  `.help/features.yaml` still listed features as non-manual — so the
  query reported a long "remaining" list and I briefly concluded the
  worktree was stale. It wasn't: the worktree was exactly at
  `origin/main` HEAD; the read had just hit the wrong tree. Confirm
  the surprising "regression" against the RIGHT tree before reacting:
  `git -C <path> rev-parse HEAD` vs `git rev-parse origin/main`, and
  re-run the relative-path read with the cwd pinned to the worktree
  (`cd <worktree> && ...`, never a bare `cd <main>` whose branch you
  haven't checked). Extends the editable-MAPPING / worktree-vs-main
  family to the *config-file read* surface (prior instances were
  code-execution and write-side).

## From elegant-pasteur-da6dcb (round 2, added post-#1260)

  CANCELLED noise (separate, low-priority) is quietable with
  `cancel-in-progress: false` in the scan workflow.
- **The #910 retry harness emits a `failure` (not `cancelled`) with
  near-full runtime when it gives up on a hang — don't misread it as
  a real test/coverage failure.** When the bounded auto-retry wrapper
  exhausts its attempts it deliberately `exit 1`s with
  `::error::<lane> pytest hung on every attempt (runner-hang) —
  failing the job after bounded auto-retry`, so the job conclusion is
  `failure` (NOT `cancelled` like a raw step-timeout). The ~28-29 min
  runtime is the hang signature itself (≈2× the 14m step timeout +
  retries), NOT evidence that real work ran and failed — so "ran the
  full duration ⇒ real failure" is exactly backwards for this harness.
  Hit 2026-06-15 triaging PR #912: I first called its `coverage` +
  `test (ubuntu-3.11)` fails "real" from the long runtime, but the
  logs had ZERO `FAILED` test lines and ZERO "Required test coverage …
  not reached" lines — only the `::error:: …runner-hang` marker and a
  trailing `Terminate orphan process: pid (…) (python)` cleanup tail.
  Diagnostic before assuming a code fix is needed: `gh run view --job
  <id> --log | grep -E "FAILED |Required test coverage|hung on every
  attempt|Terminate orphan"`. Only the runner-hang marker + orphan
  cleanup (no `FAILED`/coverage-shortfall lines) ⇒ it's the hang;
  rerun the failed lanes, don't fix code. Contrast: a fast (~2 min)
  `pre-commit` `failure` on a dependabot PR IS real (lint/lock) — the
  hang signature is specifically long runtime + orphan-python tail.
  Two rerun gotchas: (a) `gh run rerun <id> --failed` rejects "cannot
  be retried" if `<id>` is a SIBLING workflow's run (Auto Approve,
  Security Scan, Dependabot auto-merge) — resolve the *Tests* run id
  from the failing check's `link` field, never `gh run list --limit
  1`; (b) the resolved Tests run reruns cleanly. Extends the existing
  CI-hang retry-harness lessons with the consumer/reading side.

## From compassionate-matsumoto-c31293 (round 2, added post-#1260; full snapshot also on origin/claude/compassionate-matsumoto-c31293)

  CANCELLED noise (separate, low-priority) is quietable with
  `cancel-in-progress: false` in the scan workflow.
  **AUDIT RESULT (2026-06-24, the predicted systemic sweep):** running
  the "grep the handler's kwargs inside the workflow module" check
  across ALL 18 `_run_*` handlers found FOUR broken by this class, not
  two. Hard-broken (every call returns `"path argument is required"`):
  `_run_doc_gen` (passed `source_code`/`doc_type`/`audience`),
  `_run_doc_audit` (passed `project_root`; workflow reads only `path`),
  `_run_research_synthesis` (passed `sources`/`question`; workflow was
  rewritten to read source docs from a `path` on disk — a SEMANTIC
  drift, not just a rename, so the fix changed the tool's input schema
  too), plus `_run_test_generation` (passed `module_path`; fixed under
  its own task). Silently-DEGRADED (no error, wrong scope):
  `_run_doc_orchestrator` buried the path in `context={"project_root":
  …}` while the orchestrator resolves scope from the TOP-LEVEL `path`/
  `project_root` kwargs → scope fell back to cwd. Working-but-via-
  DEPRECATED-alias (migrated to canonical `path=` opportunistically):
  `_run_test_audit` (`src_path=`), `_run_health_check` (`project_root=`).
  All the plain path-passers (security_audit, bug_predict, code_review,
  perf_audit, release_prep, refactor_plan, dependency_check,
  deep_review, simplify_code, secure_release, test_gen_parallel) were
  already correct. Takeaways that generalize: (a) the degraded case is
  nastier than the hard-broken one — no error to grep for, you only
  catch it by checking the workflow READS the kwarg you pass at the
  level you pass it (top-level vs nested in a dict); (b) when the
  workflow was rewritten (not just renamed), aligning handler→workflow
  means changing the `tool_schemas.py` input contract too, and updating
  every mocked test that PINNED the old kwargs (they're the reason the
  drift survived); (c) the non-mocked receipt that catches all four:
  drive the real handler→`execute` with only `claude_agent_sdk.query`
  (the subprocess) stubbed, and assert `success is True` — a stale
  kwarg yields `success False` + `"path argument is required"`.

## From pensive-newton-b374a4 (round 2; full branch on origin/feat/authoring-staleness)


- **A `subprocess.run(..., check=False)` consumer that parses stdout
  turns a SUBPROCESS CRASH into a false "clean/empty" result — verify
  the exit code (or that the CLI is even importable) before trusting
  parsed-empty output**: 2026-07-01, absorbing attune-author's staleness
  machinery, dogfooding the live consumer
  (`attune.ops.help_data._attune_author_stale_features`) revealed it
  shells `attune-author status` via `subprocess.run(check=False)` and
  feeds `result.stdout` to a markdown parser. On this machine the
  `attune-author` PATH shim points at a Python without `attune_author`
  installed → the subprocess dies with `ModuleNotFoundError`, exits
  non-zero, stdout empty. `_parse_status_output("")` returns
  `frozenset()`, so a **crash reads as "nothing stale"** — and because
  the function returns an empty set (not `None`), callers never reach
  their age-based fallback. The graceful-degradation shape
  (`check=False` + parse-whatever-came-back) silently converts "the tool
  is broken" into "the tool says everything's fine." Rules: (1) a
  subprocess whose EMPTY output is a valid answer MUST check
  `returncode` (or `check=True` + catch) — treat non-zero as *unknown*,
  not as the empty answer; (2) map *unknown* to the real fallback
  (here: `None` → age-based), never to the same value as a genuine empty
  result; (3) when a consumer "returns nothing wrong," confirm the
  underlying tool actually RAN — `which <tool>` finding a shim is not
  proof it's importable/runnable. Pairs with "registered ≠ working —
  dogfood the live loop" (a broken dependency masquerading as success)
  and the workflow-failure-exit-propagation family (swallowed non-zero
  exits). Recorded in attune-author-consolidation decisions.md D8.

# Recovered from stash triage (2026-07-05, 22 stashes cleared)

## Patrick's inline curator comments (stash: patrick curator inline comments, bulletin-curator/design.md, absent from archived spec)


**Status:** draft
## System prompt --would we get better performance if you use a XML-enhanced prompt...?
### Template: `curator.html`--I really like this way of showing what to expect. I also will like the report.
## Cost + safety --can this be done using my max subscription?
   to suppress lives in a follow-up spec. -- a needed item please prioritize
   natural scope. -- I wonder. Will I have the ability to have agents from multiple projects report? If not in V1 then in V23
    curator's intermediate tokens stay inside the SDK session -- what I'm hearing is a bit confusing. DO I have to use the API for this?

## CLAUDE.md additions from stash@{1} (On fix/sdk-error-capture-fallback: session-2026-06-06-lessons+help-reg)


- **Subscription `claude` CLI is structurally broken for
  `claude_agent_sdk.query()` in this repo — SessionStart hooks
  pollute the stream-json channel**: hit 2026-06-06 trying to run
  bug-predict through the ops dashboard while logged in to Claude
  Max (no `ANTHROPIC_API_KEY` exported). The SDK spawns `claude
  --output-format stream-json --verbose --input-format stream-json
  …`; the subscription CLI loads the FULL session context on every
  invocation (CLAUDE.md ~348k chars, the spec-status starter, the
  `.help` freshness reminder, in-flight specs) and responds with
  conversational prose (`"I see the session orientation. Ready for
  your next instruction — let me know what you'd like to work on."`)
  instead of stream-json. The SDK's `receive_messages` reader hits
  the non-JSON line, raises `Command failed with exit code 1`, and
  the workflow dies after ~6 min of CLI churn. **The #650
  `ATTUNE_SDK_ERROR_PROBE` health probe paid off exactly as
  designed** — its captured `sdk_stderr` in the on-disk run record
  contained the literal "session orientation" prose, making the
  cause unambiguous (without it: opaque exit 1). Workarounds:
  (a) **API mode** — `set -a && source ~/.attune/anthropic.env &&
  set +a && export ATTUNE_MAX_BUDGET_USD=10` before launching the
  dashboard; bug-predict on `src/attune/gates/` then ran clean in
  ~6 min, returning real findings. (b) Real fix (small follow-up
  spec, not done): gate SessionStart hooks on a marker like
  `CLAUDE_CODE_SDK_SUBPROCESS=1` and set it in `runner.py`'s
  `proc_env` alongside the existing `ATTUNE_SDK_ERROR_PROBE=1`.
  Pairs with the existing "MCP server process doesn't inherit .env"
  and "SDK error fidelity" lessons — same family (process-environment
  boundaries shape SDK subprocess behavior), new specific surface
  (SessionStart-hook output poisoning the stream-json channel that
  the SDK reader requires).

- **Ops dashboard `_SESSION_TOKEN` regenerates on every server
  restart, and the Cowork preview pane caches the page across
  restarts — every restart costs a Cmd+R on the pane or every
  mutating click 403s**: hit 2026-06-06 multiple times. The
  `attune.ops.security._SESSION_TOKEN = secrets.token_urlsafe(32)`
  is per-process, injected into each rendered page as
  `<meta name="attune-client-token">`. After `preview_stop` +
  `preview_start` (or any backend restart), the live server mints
  a fresh token, but the Cowork preview proxy serves the previous
  process's cached HTML — so the open page holds a dead token and
  every mutating POST returns 403 invalid_client. Three distinct
  tokens were observed on port 8765 in one diagnosis pass (page
  meta `aZxrk4`, live `curl` `7fNWqG`, next-restart `_2keAk`).
  **Cache-busted URL navigation (`?cb=Date.now()`) does NOT fix
  it** — the preview proxy's cache ignores the query string.
  Cmd+R / Cmd+Shift+R on the pane DOES. **Diagnostic playbook**
  when the dashboard 403s after a restart: (1) `curl -s
  http://127.0.0.1:8765/workflows | grep attune-client-token` —
  the live server-injected token; (2) `preview_eval` reading
  `document.querySelector('meta[name="attune-client-token"]')
  .content` — the page's token; (3) if they differ → stale-page,
  Cmd+R is the only reliable fix; if they match → validate against
  a cheap protected endpoint (`POST /api/telemetry/interaction
  {"event":"test"}` returns 204 with token, 403 without) before
  suspecting a dual-module problem. Three-token confusion is the
  single biggest source of "403 invalid_client" UX time-sink
  during dashboard development.

- **bug-predict on small recently-touched leaf modules produces
  real, actionable findings — validated by running it on
  just-shipped code**: 2026-06-06 ran `bug-predict
  src/attune/gates/` (the collaboration-gates T1 code shipped
  24 h earlier in #637, ~150 LOC) in API mode after subscription
  failed (see above). ~6 min, returned TWO real findings, both
  verified against the actual code: (1) `envelope.py:151` —
  deterministic `.tmp` filename (`path.name + ".tmp"`) →
  last-writer-wins race under concurrent processes (fix: append
  `.{os.getpid()}-{secrets.token_hex(4)}.tmp`); (2)
  `envelope.py:170-178` — `load_or_new(ttl_seconds=, cap_usd=,
  meter=)` silently discards those kwargs when an existing live
  envelope is found, but the function name implies they're
  effective. Pattern: bug-predict's value-per-dollar is highest
  on **recently-touched, small, leaf modules** where the
  workflow's full attention fits the scope. ~6 min runtime on
  ~150 LOC is the normal/healthy duration for a real
  multi-subagent run; pairs with the existing "duration <5s on
  any LLM-backed workflow = startup failure" lesson as the
  positive-direction companion.

## CLAUDE.md additions from stash@{7} (On fix/bulletin-route-coverage-gap: wip)


- **`concurrency: cancel-in-progress: true` on a required-
  status-check workflow blocks every PR that gets a follow-up
  commit during CI**: hit on three PRs in one session (#477,
  #478, #480). `.github/workflows/security.yml` has
  `concurrency: cancel-in-progress: true`, so any subsequent
  push during a run cancels the in-flight one and leaves the
  required `security` check stuck at CANCELLED. Branch
  protection treats CANCELLED as not-passing, so the PR is
  BLOCKED until someone manually reruns the job
  (`gh run rerun <run-id> --job <job-id>`). The fix-by-rerun
  works because the rerun creates a fresh run unaffected by
  the prior concurrency cancellation. Three response options:
  (1) drop `security` from `required_status_checks` (cheapest;
  the workflow's actual scan job `Run Security Scanner`
  already runs and tracks SUCCESS separately); (2) remove
  `cancel-in-progress: true` from the workflow so concurrent
  runs queue instead of cancelling; (3) accept the per-PR
  manual rerun friction. Diagnostic shape: when a PR shows
  `security: CANCELLED` with no obvious cause, look at the
  workflow's `concurrency:` block before assuming the job's
  own logic failed. Pairs with the existing
  "`gh pr checks --watch --fail-fast` exits prematurely on
  cancelled-but-tagged-fail guard jobs" lesson — that one
  covers the WATCHER side of the same shape; this one covers
  the BRANCH-PROTECTION side.

## CLAUDE.md additions from stash@{8} (On feat/expanded-subagent-haiku-routing: wip: pre-telemetry-fix snapsh)


- **`monkeypatch.delenv` doesn't track SUT-side env writes
  — pair with `try/finally` `os.environ.pop` cleanup**:
  pytest's `monkeypatch.delenv("FOO", raising=False)`
  tracks the *deletion* (if FOO was originally set, teardown
  restores it; if not, teardown is a no-op). It does NOT
  track subsequent writes to `os.environ["FOO"] = ...` done
  by the code-under-test. If the SUT does a raw env write
  during the test, the var lingers on the xdist worker and
  poisons sibling tests that assert it's unset. Local
  single-test runs pass; matrix CI on slower Pythons (3.12,
  3.13) hits the leak because xdist puts the polluting test
  and the assertion test on the same worker in leak-then-read
  order — the same shape as the existing structlog-config
  leak lesson, different mechanism. Hit on PR #437 where
  `cmd_workflow_run` does
  `os.environ["ATTUNE_AGENT_MODEL_DEFAULT"] = "haiku"` for
  the `--cheap` flag and `get_subagent_model("perf-reviewer")
  is None` sibling tests then saw `"haiku"` instead. Fix:
  wrap the body in `try/finally` with
  `os.environ.pop("FOO", None)` as cleanup. Apply to BOTH
  positive (sets the var) and negative (asserts unset) tests
  as defense in depth — a future refactor that accidentally
  introduces a write in the negative case won't reintroduce
  the leak. Generalizes to ANY test for code that writes
  process env vars directly (signal handlers, locale config,
  logging setup, feature-flag toggles).

- **Explore subagent inventories can mislabel resolver-
  routed columns — verify by running names through the real
  algorithm**: when delegating an inventory task whose output
  includes "currently resolves to X" or any column derived
  from a runtime algorithm (keyword routing, regex matching,
  dispatch tables), the Explore agent often guesses by
  *intent* ("this looks like a haiku-friendly job, so it
  must resolve to haiku") rather than by *mechanism* (run
  the actual keyword-substring matcher). The names and
  descriptions in the inventory are typically correct; the
  routing column is the part that drifts. Defensive fix: ask
  for "exact subagent names from source" without the routing
  column, then resolve the routing yourself with a short
  Python script that imports the real resolver. Hit on the
  2026-05-19 model-override audit — the explorer's table had
  6+ wrong "resolves to" entries (e.g. claimed
  `pattern-scanner → haiku` when it actually resolved to
  `inherit` because no map keyword matches "pattern" or
  "scanner" yet). Generalizes beyond agent-resolver mapping:
  any subagent task whose output is a table where one column
  is "what the runtime would do" benefits from a final
  verification pass against the real runtime.

## CLAUDE.md additions from stash@{9} (On feat/anthropic-cost-phase1: session-state-during-pr-420-fix)


- **Anthropic admin cost-report API: shape +
  semantics worth remembering**: `GET
  https://api.anthropic.com/v1/organizations/cost_report`
  is the canonical "what did the org spend"
  endpoint. Auth header is `X-Api-Key:
  <ANTHROPIC_ADMIN_API_KEY>` — an admin key, NOT
  the regular `sk-ant-api03-...` key (admin keys
  have org-wide read scope; regular keys are
  workspace-scoped). The `amount` field in each
  result row is a **decimal string in lowest
  currency units** (cents-as-string), so
  `float(amount) / 100.0` lands in USD — easy to
  mishandle as "already in dollars" and end up
  100x off. Useful params: `bucket_width=1d`,
  `group_by[]=description` (returns `cost_type` +
  `model` rows for free without a second call),
  `starting_at` / `ending_at` (RFC 3339,
  inclusive/exclusive). 30 daily buckets with
  `has_more: false` at the daily granularity, no
  pagination needed for typical dashboard views.
  `cost_type` enum: `tokens` / `web_search` /
  `code_execution` / `session_usage`. Probe
  reference: `scripts/probe_anthropic_cost.py`
  in attune-ai (added in PR #431). Phase 1 client
  implementation: `src/attune/ops/anthropic_cost.py`
  (PR #432).

- **Anthropic's subscription seat fee and API
  meter spend are on two separate ledgers; the
  Console only shows the API one**: critical for
  any dashboard that surfaces "what am I
  spending." A Claude Pro/Max subscriber's
  recurring fee ($20/$100/$200/month) is billed
  via Anthropic's subscription ledger (visible
  at `claude.ai/settings/billing` or the user's
  credit card statement). The admin `cost_report`
  API endpoint sees only the API ledger
  (`cost_type=tokens` etc.). For a subscriber
  whose Claude Code is authenticated via
  `ANTHROPIC_API_KEY` rather than OAuth, EVERY
  Claude Code conversation hits the API meter
  instead of consuming subscription quota — so
  they're effectively paying for the subscription
  seat AND paying per-token on top. Discovered
  with Patrick's account 2026-05-18: $400 of
  `cost_type=tokens` MTD on top of an unused
  Max subscription. Dashboard integrations that
  source from `cost_report` should call out this
  asymmetry explicitly so users don't think the
  figure is their TOTAL spend.

- **Claude Code authentication mode determined by
  `ANTHROPIC_API_KEY` presence; precedence is
  env-var-first, then cached OAuth**: the Claude
  Agent SDK / `claude` CLI checks
  `ANTHROPIC_API_KEY` first. If set → API meter,
  per-token billing. If unset and a prior `claude
  login` cached OAuth credentials → subscription
  quota, no per-token charge. If neither →
  authentication fails. For subscribers who want
  attune workflows on subscription pricing: unset
  `ANTHROPIC_API_KEY` globally, run `claude login`
  once interactively to cache the token, and set
  the key inline (`ANTHROPIC_API_KEY=$(...) python
  script.py`) only when a script needs direct API
  access (e.g. batch jobs, `anthropic` SDK calls).
  Caveat: the `claude` CLI is a separate install
  from the VSCode extension / macOS desktop app /
  claude.ai web — having a Claude Code
  subscription doesn't imply the `claude` binary
  is on PATH. Install via
  `curl -fsSL https://claude.ai/install.sh | sh`
  if `which claude` returns nothing.

- **`git checkout -b <new-branch> origin/main`
  bypasses the "main is already used by worktree"
  error**: when working in a worktree and main is
  owned by the parent worktree, `git checkout
  main` fails with `fatal: 'main' is already used
  by worktree at <path>`. The fix is to base the
  new branch directly on the remote ref:
  `git checkout -b feat/foo origin/main` — git
  creates the new branch from origin/main and
  switches the current worktree to it without
  ever checking out the `main` ref. Pairs with the
  existing "Launching `attune.ops` from a worktree"
  lesson — both are about navigating the
  multi-worktree layout without fighting git's
  per-ref ownership model. Hit while opening
  Phase 1 of the cost-integration spec (PR #432).

- **Bash classifier blocks even sanitized reads
  of credential files**: tried to probe
  `~/.attune/anthropic.env`'s first 12 chars per
  line with `head -c 12` to verify file shape
  without exposing the full key — classifier
  blocked it with "leaks credential prefix bytes"
  even though 12 chars is far too short to be a
  useful key. The classifier reads the *intent*
  of the command (probing a credential file), not
  just the byte count exposed. Right move when
  blocked is to ASK the user where the file is
  rather than try to engineer around the
  classifier. Designing credential loaders to be
  tolerant of multiple file formats (NAME=VALUE
  AND bare-key) removes the need to probe in the
  first place.

## CLAUDE.md additions from stash@{10} (On main: CLAUDE.md unrelated lessons)


- **Edit/Write target paths don't follow the Bash `cwd`
  into a worktree — file-content tools take ABSOLUTE
  paths and write wherever those point, ignoring git
  worktree boundaries**: hit 2026-05-17 during Feature
  A (ops-suggestion-chips). Bash `pwd` showed the
  worktree directory, but my Read commands used the
  absolute path
  `/Users/patrickroebuck/attune-ai/src/attune/ops/static/js/run_view.js`
  (pointing at MAIN, not the worktree). Subsequent
  Edits inherited that absolute path and silently
  wrote into main's working tree. Symptoms: `git
  status` from the worktree showed no changes; main's
  checkout had unexpected `M` rows + an untracked
  test file. Recovery: `cp` modified files into the
  worktree, `git checkout --` them in main, `rm` the
  untracked test in main. Pattern: when working in a
  worktree, always (a) `cd` into it via Bash AND (b)
  anchor every file path on the worktree prefix
  explicitly —
  `/Users/patrickroebuck/attune-ai/.claude/worktrees/<slug>/src/...`.
  Don't trust the Bash `cwd` to redirect absolute
  paths the way relative-`pwd`-based commands do.
  Edit/Write/Read resolve absolute paths literally;
  they don't introspect git worktree state. Diagnostic
  after any Edit during worktree work: run `git
  status` from BOTH the worktree AND main — files
  appearing on the wrong side is the tell. Pairs with
  the existing "`PYTHONPATH=$(pwd)/src` in a launch
  one-liner" lesson — both are forms of "absolute
  paths win over wherever you think you are."

- **Source-grep test boundaries fail silently when the
  next `function ` / `def ` keyword is a nested
  callable**: hit 2026-05-17 writing tests for the
  suggestion-chip JS handler. Intuitive boundary
  `text.find("function ", start_idx + 1)` returns the
  start of a NESTED `function () { ... }` fetch
  callback inside the outer function, not the next
  top-level definition. The bounded "body" ends up
  empty — the substring you want is past the false
  boundary. Two fixes:
  (a) anchor on indentation —
  `text.find("
  function ", start_idx + 1)` for
  top-level functions inside a 2-space-indented IIFE,
  or `text.find("
def ", start_idx + 1)` for module-
  level Python def;
  (b) when the assertion's tokens are file-unique,
  drop body scoping entirely and grep globally
  (`assert "resp.status === 409" in text`).
  Generalizes: any test that bounds a function body
  by searching for the next definition keyword needs
  to account for nested callables — anchor on
  indentation, or skip body scoping when tokens are
  unique enough. Cost of the wrong boundary: cryptic
  "substring not found" failures where the substring
  IS in the file but not in the bogus-bounded slice.

## CLAUDE.md additions from stash@{12} (On chore/deprecation-marker-enforcement: CLAUDE.md lessons leftover)

  `used in tests`. Three gotchas: (a) `dismissed_comment` has a
  hard **280-character limit** — the API returns `422 Only 280
  characters are allowed` if you overshoot. Trim mercilessly;
  the reason field carries the categorical signal, the comment
  is just terse rationale. (b) The single-alert read endpoint
  (`/code-scanning/alerts/{id}`) returns `state: null` for any
  alert that exists only in a PR-ref instance (never on main).
  To check the truthful "is this still blocking my PR" state,
  query the PR-filtered list endpoint instead:
  `gh api "repos/X/code-scanning/alerts?pr=<N>" --jq '.[] |
  "#\(.number) state=\(.state)"'`. The list endpoint returns
  `most_recent_instance.state`, which is what you actually
  want. (c) Even after dismissal, the CodeQL **check** stays
  `fail` on the PR until the next scan runs. Push a no-op
  commit (e.g. a coverage-fix commit, which we did for #411)
  to trigger a fresh scan, then the check flips green.

- **Sequencing-plan audits go stale within days —
  grep main for the symbols before believing a phase
  is "not started"**: hit 2026-05-16 on step-4 Phase 2
  (ops-scope-picker-ia). The plan doc shipped 2 days
  prior ([#408](https://github.com/Smart-AI-Memory/attune-ai/pull/408))
  said the spec was "draft — production implementation
  not started" and that the worktree should ship ~5
  files / ~100 LOC + ~50–60 tests. Reality: 5 of 6
  acceptance criteria had already landed via #344
  (initial), #363 (scope-textbox), #365 (per-workflow
  defaults), with 41 passing tests in
  `tests/unit/ops/test_scope_picker.py`. The audit
  was point-in-time; specs ship in multiple PRs
  during the window between "plan written" and "you
  start the work." Operational rule: before
  committing to implement a sequencing-plan phase,
  grep `main` for the symbols, files, and tests the
  spec promises to add. If they exist, the spec
  already shipped — re-scope to the genuine gap (in
  this case, AC-6 alone). Spec status fields and
  audit doc claims are hypotheses; the codebase is
  the ground truth. The cost of the 60-second grep
  is strictly cheaper than building infrastructure
  that's already there. Pattern generalizes to any
  multi-PR spec where a plan doc summarizes the
  state at one moment — those summaries don't auto-
  update as PRs land.

## CLAUDE.md additions from stash@{14} (On claude/recursing-montalcini-0d26be: recursing-montalcini-2026-05-16)

### Spec / pipeline discipline (the three gates)

Rationale + spec:
[docs/specs/spec-pipeline-discipline/proposal.md](../docs/specs/spec-pipeline-discipline/proposal.md).
Apply on every multi-phase spec execution:

- **Patch coverage exit gate.** No phase claims "done" until
  new code lines/branches hit >=90% patch coverage (or the
  uncovered lines are explicitly documented defensive
  paths). Run `pytest --cov=<paths> --cov-report=term-missing`
  and report at phase close.
- **Defer requires explicit override.** Any proposal to skip,
  defer, or shrink a spec-named deliverable surfaces as a
  flagged question to the user, not a soft option. The
  default answer is "do it"; defer is the exception.
- **Audit-doc fidelity on phase close.** If execution
  revealed an error in the audit doc or prior-phase
  artifacts, fix it before closing the current phase. Audit
  drift breaks downstream phase planning.

These exist as standing rules here AND as the system of
record in the spec because both are needed: CLAUDE.md
ensures visibility every session start, the spec tracks
rationale + acceptance criteria. Visibility ≠ enforcement
— apply the gates actively, don't just read them.

### Phase numbering convention

Phases in any spec start at 1, not 0. "Phase 0" is not a
convention in this project. If a phase looks like it should
be Phase 0 (audit / setup before "real work"), call it
Phase 1 and shift the rest up.


- **Ops dashboard: two routing/ID gotchas that fail
  silently in fixtures**: hit 2026-05-15 while
  pre-seeding a demo run for the run-view panel. Both
  worth capturing because the failure modes are quiet
  enough to waste minutes on first encounter. (1)
  `_RUN_ID_RE = ^[a-f0-9]{1,64}$` in
  `src/attune/ops/runner.py` — only lowercase hex
  chars. A "human-readable" demo id like
  "demo123abc" with the letter 'm' fails the regex,
  and `_load_run_record` returns None **with no log
  message**. The disk-fallback route then 404s
  identically to "file truly missing." When seeding
  fixtures: use `uuid.uuid4().hex[:N]` for run_ids,
  not human-readable strings. (2) `/api/runs/{workflow}`
  (the workflow-list endpoint in `routes/runs_history.py`)
  ≠ `/runs/{run_id}` (single-run JSON endpoint in
  `routes/runner.py`). JS code fetching single-run data
  must hit `/runs/<id>`, NOT `/api/runs/<id>` — the
  latter matches the workflow-list pattern and returns
  a list payload (or 404) keyed on `<id>` interpreted
  as a workflow name. The `/api/` namespace prefix is
  reserved for workflow-keyed history endpoints in
  this codebase; single-run JSON intentionally lives
  on the un-prefixed path. Pattern when writing JS
  that consumes the dashboard API: read
  `src/attune/ops/routes/` first to confirm the path
  rather than guessing from convention.

## CLAUDE.md additions from stash@{20} (On ci-add-pytest-timeout: WIP: pre-commit-retry)


- **GitHub Actions `run:` blocks default to PowerShell
  on `windows-latest`, not bash — bash syntax fails
  with `ParserError` ~30s in**: a `run: |` step using
  `if [ "${{ runner.os }}" = "Linux" ]; then ... fi`
  (plus `awk`, `trap`, `&` backgrounding) runs fine on
  ubuntu/macos but on windows-latest the runner picks
  `C:\Program Files\PowerShell\7\pwsh.EXE`, which can't
  parse the bash `if`/test-bracket grammar. Fails fast
  with `Missing '(' after 'if' in if statement` and the
  whole job is red despite zero tests having run. Fix
  is one line: add `shell: bash` to the offending step
  (`shell: bash` resolves to Git Bash on Windows
  runners, native bash on linux/macos — universal).
  Apply whenever a multi-OS workflow step uses any of:
  `[ ... ]`, `$()`, `&&`, backgrounded processes with
  `&`/`trap`, or `awk`/`free`/POSIX utilities. The
  PowerShell default only bites Windows steps, but the
  fix is harmless on the other OSes, so prefer setting
  it explicitly rather than hoping the syntax happens
  to be PowerShell-compatible.

- **`gh pr checks` failures categorized by latency
  pattern reveal class without reading logs**: when a
  PR's matrix shows mixed durations, the buckets are
  diagnostic. ~30s-2m failures on a specific OS only
  are usually configuration/parse errors (wrong shell,
  missing dep) — investigate that one OS first. Tests
  that run 9-15min then fail are typically test-suite
  failures or OOM/shutdown. 1-5s "failures" with no
  step output are almost always concurrency-group
  cancellations, not real failures — re-run will pass.
  Saves time vs reading every log: bucket the failure
  durations first, pick the cheapest-to-diagnose
  bucket, and tackle that. On attune-ai PR #212 this
  split into (a) 1s cancelled Security Scanner —
  ignore, (b) ~30s Windows test parse errors — shell
  fix, (c) 9-15min Linux/macOS — the actual bug being
  investigated.

- **`pip-audit --strict --skip-editable` started
  failing on editable root packages around 2026-04-27
  even though pip-audit version is unchanged
  (2.10.0)** — error is `ERROR:pip_audit._cli:<pkg>:
  distribution marked as editable`. `--skip-editable`
  was supposed to skip the editable root but in strict
  mode the error fires BEFORE the skip applies. Cause
  is upstream in pip/setuptools editable metadata
  handling. Workaround that's robust to whatever
  changed: generate a requirements file from
  `pip freeze --exclude-editable`, then run
  `pip-audit -r <file>` instead of scanning the
  installed env. The dependency closure audited is
  identical but pip-audit never sees the editable
  install. Verified locally: 75 entries audited,
  zero attune-ai entries in the reqs file. See
  attune-ai PR #218. Applies to any project whose CI
  installs itself editable and runs pip-audit in
  strict mode.

- **`gh api -X PUT repos/<o>/<r>/pulls/<n>/update-branch
  -F expected_head_sha=<sha>` is the fast cascade-
  rebase tool when main moves forward and you want to
  bring N stacked PRs up to date**: faster and safer
  than checking each branch out, rebasing, force-
  pushing. Triggers GitHub's "Update branch" merge-
  with-main on each PR in turn (creates a merge
  commit, but squash-merge at PR-merge collapses it,
  so cosmetic only). `expected_head_sha` is a safety
  check — pass the current PR head OID via
  `gh pr view N --json headRefOid --jq .headRefOid`.
  Used on attune-ai to update-branch #213, #215, #216,
  #209 in a loop after #218 merged. Each call returns
  in under a second; CI re-fires on each PR
  automatically. The trade-off: merge-with-main not
  rebase, so commit history of stacked PRs gains a
  merge commit. Acceptable when the final merge
  strategy is squash anyway.

- **pytest-cov + branch coverage + xdist + 14k+ tests
  exceeds 16 GB on GitHub Linux runners — the
  `[~92-98%] PASSED → worker crashed/shutdown` pattern
  is the kernel OOM killer harvesting workers**:
  attune-ai Probe B (PR #212) instrumented mem with
  `free -m` ticks every 30s during pytest. Run
  25643234935 ubuntu-3.11 showed monotonic growth
  from 1 GB baseline to 15.7 GB used / 251 MB
  available, then a worker was killed and 14 GB was
  reclaimed in a single tick. The "FAILED" test in
  the log is the casualty (the test running on the
  killed worker), not the cause. The growth is
  gradual across thousands of tests, not
  spike-from-one-bad-test. Half-fixes that DO NOT
  work in isolation:
  - `-n 2` (halve xdist workers from `-n auto`):
    second iteration still OOM'd at 15.5 GB. Two
    workers shared 14.5 GB of growth, so per-worker
    memory was ~7 GB, not the ~3-4 GB you'd estimate.
    Coverage data structures are the bulk, not per-
    worker import state. `-n 2` alone is insufficient.
  Levers that actually reduce memory significantly:
  - `branch = false` in `[tool.coverage.run]` — and
    setting it ONLY at CLI via dropping `--cov-branch`
    does nothing because pyproject `branch = true` is
    the authoritative source of truth. The CLI flag
    can turn branch ON if config didn't, but cannot
    turn it OFF. Must change config to disable.
  - `parallel = true` + `concurrency =
    ["multiprocessing", "thread"]` in
    `[tool.coverage.run]` — without these xdist
    workers accumulate ALL coverage data in memory
    until end-of-suite. With them, workers write to
    per-worker `.coverage.<host>.<pid>` files
    incrementally; peak resident memory drops
    significantly. pytest-cov auto-combines at suite
    end. These should be on by default for any
    xdist + coverage setup.
  - Last-resort: remove coverage from matrix
    entirely, add one dedicated coverage job with
    reduced `--cov=` scope. Splits OOM risk to a
    single job that can be tuned without affecting
    the test correctness gate.

- **OOM crashes can mask real test failures —
  fix-the-infra-first ordering matters**: pytest with
  `-n auto` + `--maxfail=20` on a CI runner that OOMs
  at 92% completion does NOT report the failing tests
  that ran in the first 92%. Dropping to `-n 1`
  (sequential) eliminated the OOM but immediately
  exposed 20 pre-existing failures in
  `test_langgraph_adapter.py` (asyncio event-loop
  errors). The failures were always there; OOM killed
  the suite before maxfail's counter tripped. Lesson:
  when chasing CI flakes/crashes, FIX THE
  INFRASTRUCTURE ISSUE FIRST so the real signal can
  surface. The crash that "covers up" your bug is
  doing you a disservice. Corollary: anytime you
  drastically change pytest runner config (`-n auto`
  → `-n 1`, removing parallelism, etc.) expect to see
  new failures you've never seen before. They're not
  caused by the config change — they were always
  there, masked by the previous setup.

- **`pytest --maxfail=N` × xdist worker count is
  per-worker, not global — clustered failures hide
  more in parallel**: with `-n 4`, maxfail=20 means
  the suite stops only when ONE worker accumulates 20
  failures. 20 failures distributed evenly across 4
  workers (5 per worker) never trips maxfail and the
  suite continues. With `-n 1`, all failures count
  against the same 20-counter and the suite stops
  faster. This interacts subtly with the "OOM masks
  failures" lesson: clustered failures in one file
  (like the 20 in `test_langgraph_adapter.py`)
  distribute across xdist workers and stay below the
  per-worker cap, then OOM crashes the suite before
  any worker individually tripped maxfail. Going
  sequential surfaces both: failures concentrate
  against one counter AND the runtime ordering puts
  the clustered file together. If you want maxfail to
  catch failures in a parallel-friendly way, set it
  intentionally low per-worker (knowing it
  multiplies), or use `--maxfail=0` in CI to run the
  whole suite and report total counts, then triage
  separately.

- **`asyncio.get_event_loop().run_until_complete(coro)`
  is dead in Python 3.12+ — must migrate to
  `asyncio.run(coro)`**: `get_event_loop()` was
  deprecated in 3.10 when no loop exists (used to
  auto-create one). In 3.12+ it RAISES
  `RuntimeError: There is no current event loop in
  thread 'MainThread'`. Modern replacement is
  `asyncio.run(coro)` — creates a new loop, runs the
  coroutine, cleans up. 1:1 substitution in most test
  code. Failures surface as the exact error above and
  may show up only in CI Python 3.12/3.13 entries if
  local dev is on 3.10/3.11. Grep test suites for
  `asyncio.get_event_loop().run_until_complete` when
  bumping the CI Python matrix or before tagging a
  release that touches async surfaces.

- **`pytest --cov-fail-under` failure presents as
  "worker 'gwX' crashed" — the test name is just
  whatever was running when pytest killed workers**:
  the FAILED line says
  `FAILED tests/.../test_foo - worker 'gw0' crashed
  while running tests/.../test_foo` which looks like
  a test bug. The actual failure is one line up:
  `ERROR: Coverage failure: total of 81.66 is less
  than fail-under=85.00`. When pytest decides to exit
  on coverage-gate failure, it kills running xdist
  workers, and the worker shutdown gets reported as
  a "crash" with whatever test was unlucky enough to
  be running at the time. Three jobs may each "crash"
  in a different test — that pattern (different
  tests each run) is the tell that it's not a real
  test bug. Search the log for "Coverage failure"
  before treating worker-crash output as a test
  failure to investigate.

- **Disabling `branch = true` in `[tool.coverage.run]`
  drops total coverage ~5-6 percentage points and can
  trip a `--cov-fail-under` gate**: not just a memory
  optimization. Branch coverage contributes to the
  reported total, so flipping the config off
  uniformly lowers the percentage even if no source
  line lost coverage. attune-ai's `--cov-fail-under=85`
  passed at 87.70% with branch coverage on; without
  it, total reported as 81.66% and the gate failed.
  If you disable branch coverage to reduce memory or
  speed, lower the `fail_under` threshold in the same
  change or you'll get a false-looking failure that
  hides under whatever else you're debugging.

- **Diagnostic anchoring bias: when a narrative
  explains 3+ iterations of data, re-examine the data
  before iteration 4**: PR #212 spent 3 commits
  tuning xdist worker count + coverage config to
  "fix the OOM". Iter 4 finally got mem-tick data
  showing peak memory was 1.5 GB / 16 GB — there was
  no OOM. The real blocker had been `--cov-fail-under`
  failing all along, masked by the OOM narrative
  (and earlier by the OOM itself, when the OOM
  happened before coverage was computed). The
  lesson: once you have a story that explains the
  failure, every subsequent iteration tends to be
  framed as evidence for the story rather than
  evidence to test it. Force a re-read of the raw
  logs before iteration N+1, looking for what the
  story DOESN'T explain. In this case, the
  `ERROR: Coverage failure` line was in the
  iter-3 log too — but the narrative said "OOM" so
  the reader (and I) skimmed past it.

## CLAUDE.md additions from stash@{21} (On ci-add-pytest-timeout: WIP: pre-langgraph-fix-extract)


- **GitHub Actions `run:` blocks default to PowerShell
  on `windows-latest`, not bash — bash syntax fails
  with `ParserError` ~30s in**: a `run: |` step using
  `if [ "${{ runner.os }}" = "Linux" ]; then ... fi`
  (plus `awk`, `trap`, `&` backgrounding) runs fine on
  ubuntu/macos but on windows-latest the runner picks
  `C:\Program Files\PowerShell\7\pwsh.EXE`, which can't
  parse the bash `if`/test-bracket grammar. Fails fast
  with `Missing '(' after 'if' in if statement` and the
  whole job is red despite zero tests having run. Fix
  is one line: add `shell: bash` to the offending step
  (`shell: bash` resolves to Git Bash on Windows
  runners, native bash on linux/macos — universal).
  Apply whenever a multi-OS workflow step uses any of:
  `[ ... ]`, `$()`, `&&`, backgrounded processes with
  `&`/`trap`, or `awk`/`free`/POSIX utilities. The
  PowerShell default only bites Windows steps, but the
  fix is harmless on the other OSes, so prefer setting
  it explicitly rather than hoping the syntax happens
  to be PowerShell-compatible.

- **`gh pr checks` failures categorized by latency
  pattern reveal class without reading logs**: when a
  PR's matrix shows mixed durations, the buckets are
  diagnostic. ~30s-2m failures on a specific OS only
  are usually configuration/parse errors (wrong shell,
  missing dep) — investigate that one OS first. Tests
  that run 9-15min then fail are typically test-suite
  failures or OOM/shutdown. 1-5s "failures" with no
  step output are almost always concurrency-group
  cancellations, not real failures — re-run will pass.
  Saves time vs reading every log: bucket the failure
  durations first, pick the cheapest-to-diagnose
  bucket, and tackle that. On attune-ai PR #212 this
  split into (a) 1s cancelled Security Scanner —
  ignore, (b) ~30s Windows test parse errors — shell
  fix, (c) 9-15min Linux/macOS — the actual bug being
  investigated.

- **`pip-audit --strict --skip-editable` started
  failing on editable root packages around 2026-04-27
  even though pip-audit version is unchanged
  (2.10.0)** — error is `ERROR:pip_audit._cli:<pkg>:
  distribution marked as editable`. `--skip-editable`
  was supposed to skip the editable root but in strict
  mode the error fires BEFORE the skip applies. Cause
  is upstream in pip/setuptools editable metadata
  handling. Workaround that's robust to whatever
  changed: generate a requirements file from
  `pip freeze --exclude-editable`, then run
  `pip-audit -r <file>` instead of scanning the
  installed env. The dependency closure audited is
  identical but pip-audit never sees the editable
  install. Verified locally: 75 entries audited,
  zero attune-ai entries in the reqs file. See
  attune-ai PR #218. Applies to any project whose CI
  installs itself editable and runs pip-audit in
  strict mode.

- **`gh api -X PUT repos/<o>/<r>/pulls/<n>/update-branch
  -F expected_head_sha=<sha>` is the fast cascade-
  rebase tool when main moves forward and you want to
  bring N stacked PRs up to date**: faster and safer
  than checking each branch out, rebasing, force-
  pushing. Triggers GitHub's "Update branch" merge-
  with-main on each PR in turn (creates a merge
  commit, but squash-merge at PR-merge collapses it,
  so cosmetic only). `expected_head_sha` is a safety
  check — pass the current PR head OID via
  `gh pr view N --json headRefOid --jq .headRefOid`.
  Used on attune-ai to update-branch #213, #215, #216,
  #209 in a loop after #218 merged. Each call returns
  in under a second; CI re-fires on each PR
  automatically. The trade-off: merge-with-main not
  rebase, so commit history of stacked PRs gains a
  merge commit. Acceptable when the final merge
  strategy is squash anyway.

- **pytest-cov + branch coverage + xdist + 14k+ tests
  exceeds 16 GB on GitHub Linux runners — the
  `[~92-98%] PASSED → worker crashed/shutdown` pattern
  is the kernel OOM killer harvesting workers**:
  attune-ai Probe B (PR #212) instrumented mem with
  `free -m` ticks every 30s during pytest. Run
  25643234935 ubuntu-3.11 showed monotonic growth
  from 1 GB baseline to 15.7 GB used / 251 MB
  available, then a worker was killed and 14 GB was
  reclaimed in a single tick. The "FAILED" test in
  the log is the casualty (the test running on the
  killed worker), not the cause. The growth is
  gradual across thousands of tests, not
  spike-from-one-bad-test. Half-fixes that DO NOT
  work in isolation:
  - `-n 2` (halve xdist workers from `-n auto`):
    second iteration still OOM'd at 15.5 GB. Two
    workers shared 14.5 GB of growth, so per-worker
    memory was ~7 GB, not the ~3-4 GB you'd estimate.
    Coverage data structures are the bulk, not per-
    worker import state. `-n 2` alone is insufficient.
  Levers that actually reduce memory significantly:
  - `branch = false` in `[tool.coverage.run]` — and
    setting it ONLY at CLI via dropping `--cov-branch`
    does nothing because pyproject `branch = true` is
    the authoritative source of truth. The CLI flag
    can turn branch ON if config didn't, but cannot
    turn it OFF. Must change config to disable.
  - `parallel = true` + `concurrency =
    ["multiprocessing", "thread"]` in
    `[tool.coverage.run]` — without these xdist
    workers accumulate ALL coverage data in memory
    until end-of-suite. With them, workers write to
    per-worker `.coverage.<host>.<pid>` files
    incrementally; peak resident memory drops
    significantly. pytest-cov auto-combines at suite
    end. These should be on by default for any
    xdist + coverage setup.
  - Last-resort: remove coverage from matrix
    entirely, add one dedicated coverage job with
    reduced `--cov=` scope. Splits OOM risk to a
    single job that can be tuned without affecting
    the test correctness gate.
