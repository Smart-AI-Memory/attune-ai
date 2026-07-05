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
