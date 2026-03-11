# Attune AI Framework v4.1.1

AI-powered developer workflows with cost optimization and multi-agent orchestration.

@./python-standards.md

---

## Quick Start

```bash
pip install attune-ai                     # Install (zero-config, ready to use)
```

Works out of the box: subscription-first routing with automatic
API fallback for large modules when `ANTHROPIC_API_KEY` is set.
Run `python -m attune.models.auth_cli setup` to customize.

**CLI:** `attune <command>` (canonical) or
`python -m attune.cli_minimal` (full).
See `docs/reference/cli-reference.md`.

---

## Command Hubs

Use `/hub-name` to access organized workflows:

| Hub | Key Routes | Description |
| --- | ---------- | ----------- |
| `/attune` | Socratic discovery | Natural language routing to all workflows |
| `/dev` | debug, review, commit, pr, refactor, quality, perf-audit | Developer tools |
| `/testing` | run, coverage, generate, benchmark | Test runner and generation |
| `/workflows` | security, bugs, perf, review, test-gen, refactor, deps, list | Automated analysis |
| `/plan` | feature, refactor, architecture | Planning and strategy |
| `/docs` | generate, readme, changelog, explain, audit, overview | Documentation |
| `/release` | prep, security, health, publish | Release preparation |
| `/brainstorm` | "topic", plan | Guided brainstorming and ideation |
| `/agent` | create, list, run, release-prep | Agent management |
| `/bulk` | submit, status, results, wait | Batch API processing (50% cost savings) |
| `/wizard` | run, create, list, edit | Guided multi-step wizards |
| `/pipeline` | full, dev, eval, release | Spec-driven development lifecycle |
| `/utilities` | auth-setup, auth-status, auth-reset | Auth and provider management |
| `/help` | (navigation) | Help navigating workflows |

---

## Markdown Formatting

All `.md` files should follow these rules:

- Start every `.md` file with a single `#` (h1) heading
- Heading levels must increment by one (don't skip from
  `#` to `###`)
- Put a single space after `#` in headings
- Surround headings with blank lines (one above, one below)
- Surround fenced code blocks (```) with blank lines
- Surround lists with blank lines
- Use `-` (dash) for unordered list markers, not `*` or `+`
- No trailing whitespace on lines
- No hard tabs — use spaces
- No multiple consecutive blank lines
- End files with a single trailing newline
- Keep lines under 80 characters (except tables and URLs)
- Do not manually pad or align table cells with extra
  spaces — tables are exempt from trailing space rules

---

## Code Simplification

After writing or modifying code, review it for unnecessary
complexity. Claude tends to over-engineer — too many
abstractions, unnecessary classes, premature optimization,
over-configurable interfaces. Counteract this by:

- Flattening deeply nested conditionals (use early returns)
- Inlining trivial helper functions used only once
- Removing dead code paths and unused parameters
- Preferring stdlib over custom abstractions
- Reducing class hierarchies when a function suffices

Simpler is better. Three clear lines beat one clever
abstraction.

---

## Critical Rules

- NEVER use eval() or exec()
- ALWAYS validate file paths with _validate_file_path()
- NEVER use bare except: - catch specific exceptions
- ALWAYS log exceptions before handling
- Type hints and docstrings required on all public APIs
- Minimum 80% test coverage
- Security tests required for file operations
- When creating a detailed plan with 3+ tasks or touching
  3+ files, use XML-enhanced prompt format (see
  `.claude/rules/attune/xml-enhanced-prompts.md`). For
  simpler work (single-file edits, config changes, bug
  fixes), plain descriptions are fine.

---

## Socratic Interaction Rule

**ALWAYS use `AskUserQuestion` to guide users through workflow discovery and scoping. NEVER skip straight to execution.**

This is the core design principle of Attune AI's developer experience. When a user invokes `/attune` or any workflow:

1. **Initial discovery**: Use `AskUserQuestion` to understand their goal (what are you trying to accomplish?)
2. **Scoping**: Use `AskUserQuestion` to narrow scope (which files? what test subset? what level of detail?)
3. **Confirmation**: Use `AskUserQuestion` if there are meaningful choices before execution (approach, format, targets)
4. **Then execute**: Only run CLI commands or tools after the user has been guided through the relevant decisions

**Examples of when to ask:**

- User says "run tests" → Ask: which tests? full suite, CLI only, or quick smoke test?
- User says "security audit" → Ask: which path? src/, tests/, or full project?
- User says "review code" → Ask: which files or area? what focus (security, quality, performance)?
- User says "commit" → Ask: which files to stage? what kind of change is this?

**Do NOT:**

- Jump straight to running commands without scoping
- Assume the user wants the broadest possible execution
- Skip questions just because the next step seems obvious

This rule applies to ALL workflow interactions, not just `/attune`.

---

## Project Structure

```text
src/attune/
├── agents/            # Agent SDK, state persistence, recovery
│   ├── sdk/           # SDKAgent, SDKAgentTeam, adapters
│   └── state/         # AgentStateStore, AgentRecoveryManager
├── workflows/         # AI-powered workflows with state & multi-agent mixins
├── models/            # Authentication strategy and LLM providers
├── meta_workflows/    # Intent detection and natural language routing
├── orchestration/     # Dynamic teams, workflow composition, pattern learning
├── plugins/           # BasePlugin + register_mcp_tools() hook
├── telemetry/         # FeedbackLoop, UsageTracker (MemoryBackend protocol)
└── cli_router.py      # Natural language command routing

attune_redis/          # attune-redis plugin (pip install attune-redis)
```

---

**Version:** 4.0.3 | **License:** Apache 2.0 | **Repo:** [attune-ai](https://github.com/Smart-AI-Memory/attune-ai)

<!-- attune-lessons-start -->

## Lessons Learned

- **Windows CI encoding**: Always use `encoding="utf-8"` on
  `Path.read_text()` calls. Windows defaults to `cp1252` which
  fails on any file containing non-ASCII bytes.

- **Test mocks must match imports**: When a function changes its
  import path, all test mocks must be updated to match or side
  effects are silently ignored and assertions fail.

- **Hardcoded `/root/` paths in tests**: Avoid `/root/` in test
  fixtures — CI runners often execute as root, making the path
  accessible and triggering real I/O instead of the mocked error.
  Use `tmp_path` instead.

- **Stop hooks inject stderr, not stdout**: Claude Code's Stop hook
  with exit code 2 surfaces the hook's **stderr** as the feedback
  message. Use `print(..., file=sys.stderr)` — `print()` writes to
  stdout which is silently discarded.

- **Stop hook ordering matters**: When multiple Stop hook groups are
  configured, run state-saving hooks (exit 0) first and blocking
  hooks (exit 2) last. A trailing exit-0 hook may override a
  preceding exit-2 block.

- **Stop hooks loop without a sentinel**: Exit code 2 blocks one
  stop attempt but the next attempt triggers the hook again,
  creating an infinite loop. Use a TTL sentinel file
  (`~/.attune/lessons_reminded`) to fire the reminder only once
  per session.

- **Claude Code plugin is platform-specific**: Skills, hooks, and
  MCP config only work in Claude Code (CLI). They do not function
  in Claude.ai (web). When submitting to Anthropic's marketplace,
  scope the platform to Claude Code only — not "both platforms".

- **LinkedIn paste: use ASCII markers, not Unicode arrows**: Unicode
  characters like `▶`/`◀` used as code-block delimiters get
  misinterpreted by LinkedIn's editor, causing content duplication
  and markers leaking into code blocks. Use plain ASCII like
  `--- CODE START ---` / `--- CODE END ---` instead.

- **Pre-commit stash conflict with auto-fix hooks**: When black/ruff
  auto-fix staged files and there are also unstaged changes, the
  pre-commit stash/restore cycle conflicts with the fixes. Fix: run
  `uv run ruff check --fix <paths>` manually before committing so
  the staged files are already clean when the hook runs.

- **Stop hooks missing `cd` prefix inherit session cwd**: Stop hooks
  without an explicit `cd /abs/path &&` prefix inherit whatever
  directory Claude Code was started from — which may not be the repo
  root. Always prefix Stop (and all) hook commands with
  `cd /Users/patrickroebuck/attune-ai &&` to guarantee the correct
  working directory regardless of where the session was opened.

- **Next.js shared data libs prevent page duplication**: When multiple
  pages need the same data array (e.g. wizard list), extract it to
  `lib/<name>.ts` and import from there. Defining the same array in
  `app/<page>/page.tsx` and a new `app/<page>/[param]/page.tsx`
  creates drift. The shared lib also enables `generateStaticParams()`
  and sitemap generation to stay in sync automatically.

- **Website feature lists can diverge from the Python registry**: The
  `/workflows` page had 14 manually-authored fictional workflows that
  didn't match `list_workflows()`. Always verify website feature claims
  against the live Python code before publishing.

- **Wizards call workflows internally — they are not duplicates**:
  `attune wizard run` = interactive guided UX; `attune workflow run` =
  non-interactive multi-stage pipeline. `WizardInternalWorkflow` is the
  bridge. The website must explain this distinction or users assume
  overlap.

- **Session hooks may be vestigial**: `session_end.py` saves near-empty
  shells (zero tokens, no patterns detected). Verify they are wired to
  collect meaningful data before building on top of them or advertising
  session memory as a feature.

- **ruff parses pytest.ini as Python**: When committing `pytest.ini`
  alongside `.py` files, ruff's pre-commit hook tries to parse it as
  Python and produces syntax errors. Commit `pytest.ini` in a separate
  commit from Python files so the ruff hook only sees valid Python.

- **Read source before writing tests for tricky logic**: The inline-
  comment check in `is_in_docstring_or_comment()` uses a ternary that
  defaults to `True` for any line not containing `eval`. Tests written
  against assumed behavior (expected `False`) failed. Always read the
  actual implementation before asserting expected values for
  non-obvious control flow.

- **Background processes from previous sessions persist across
  restarts**: Long-running processes started by Claude (e.g.
  `npm run dev`) survive session end and keep running silently.
  They can open browser tabs, consume ports, or interfere with the
  next session. Always `kill` them explicitly when removing a
  feature, and check `ps aux` if unexpected behavior is observed
  (Chrome tabs opening, ports already in use, etc.).

- **Twine cannot prompt for tokens in Claude Code's non-interactive
  terminal**: `twine upload` hangs or raises `EOFError` when it tries
  to prompt for a PyPI token. Pass the token via environment variable:
  `TWINE_PASSWORD=pypi-... uv run twine upload dist/* --username __token__`.

- **`pytest.importorskip` triggers ruff E402**: Test files that call
  `pytest.importorskip(...)` before optional imports cause ruff to
  flag those imports as E402 (module level import not at top of file).
  Fix: add `# noqa: E402` to each import line after the `importorskip`
  call. The pattern is intentional and correct — ruff just can't see
  the skip logic.

- **Pre-commit stash conflict when black/ruff fix files with unstaged
  siblings**: When staging a subset of changed files and running
  `git commit`, pre-commit stashes unstaged changes, auto-fixes staged
  files, then tries to restore — causing a conflict if the same file
  has both staged and unstaged changes. Fix: run
  `uv run ruff check --fix <files>` and `uv run black <files>`
  manually before staging, so the hook sees already-clean files.

- **`**kwargs` collides with explicit params of the same name**: If a
  helper like `_result_from_plan(plan, status, **kwargs)` builds a
  dataclass and callers pass `reason_codes=...` in `**kwargs`, it
  silently conflicts with any `reason_codes=...` already set inside
  the function body. Fix: add an explicit `reason_codes: list[str] |
  None = None` parameter so the signature is unambiguous.

- **Module-level optional imports enable clean test patching**: A
  local `import anthropic` inside a function body can't be patched
  with `unittest.mock.patch` because the name isn't bound at module
  scope. Move to module-level with an availability guard
  (`_anthropic = None`; `_ANTHROPIC_AVAILABLE = False`) and patch as
  `module._anthropic`. This is the established pattern in adapters
  (YAML guard) — apply it to any optional SDK dependency.

- **New dataclass fields need both the class AND the parser updated**:
  Adding a field (e.g. `local_python`) to a dataclass only updates
  the in-memory model. If there's a `_parse_*()` helper that builds
  the dataclass from raw YAML/JSON, the field stays silently empty
  at runtime until the parser is also updated. Always grep for the
  parser function when adding a new dataclass field.

- **Verify new dispatch branches with a known fixture, not just
  imports**: When adding a new runtime case (e.g. `local_python`)
  to an existing dispatch table, a clean import doesn't prove the
  branch fires. Run `Executor.run()` directly with a spec whose
  `runtime` matches the new case and assert `result.status ==
  "success"` before considering the feature done.

- **`patch()` requires the target name to exist at module scope at
  patch time**: `unittest.mock.patch("module.Name")` fails with
  `AttributeError` if `Name` is only imported inside a function
  body (lazy/deferred import). The mock library looks up the
  attribute on the module object immediately when the patch context
  is entered. Move any import that needs to be patchable to module
  level — even optional ones, using an availability guard pattern
  if needed.

- **Shadow directories at repo root break imports**: An `attune/`
  directory at the repo root (from prototyping) shadows the installed
  `src/attune/` package, causing `ModuleNotFoundError` on submodules
  that only exist in one copy. Always check for rogue top-level
  directories matching the package name before debugging import errors.

- **BaseWorkflow uses class attributes, not constructor params**: The
  `name`, `description`, `stages`, and `tier_map` fields on
  BaseWorkflow are CLASS ATTRIBUTES, not `__init__()` parameters.
  Passing them to `super().__init__()` raises `TypeError`. Define them
  as class-level assignments on the subclass.

- **Non-BaseWorkflow classes in workflow registry crash the CLI**:
  Classes registered in `_DEFAULT_WORKFLOW_NAMES` that don't inherit
  BaseWorkflow (missing `execute()`, `run_stage()`, or wrong method
  signatures) will crash `attune workflow run`. Only register true
  BaseWorkflow subclasses; keep standalone utilities importable but
  out of the registry.

- **Validate infrastructure against user value before extending**:
  BEP middleware was well-built (93 tests, clean protocol) but had
  zero working skills and no integration with CLI workflows — the
  surface where all user value lives. Always validate that new
  infrastructure serves actual users before investing in production
  hardening.

- **`ModelTier` has two copies — imports must match**: The enum
  `ModelTier` exists in both `attune.models` and
  `attune.workflows.base` as separate classes (`id()` differs).
  Tests comparing `tier_map` values will fail if the import source
  doesn't match the workflow's import. Check which module the
  workflow imports from and use the same one in tests.

- **BaseWorkflow now provides `self.logger`**: Fixed in `c67ad740`.
  `BaseWorkflow.__init__` sets
  `self.logger = logging.getLogger(type(self).__module__)` so all
  subclasses get an instance logger namespaced to their own module.
  No more manual `wf.logger = ...` workarounds in test fixtures.

- **`WorkflowResult` constructor mismatches surface only at
  runtime**: `ParallelTestGenerationWorkflow.execute()` was passing
  non-existent kwargs (`workflow_name`, `stages_executed`). Fixed in
  `c67ad740` — now passes all required fields (`success`, `stages`,
  `started_at`, `completed_at`, `total_duration_ms`). Lesson: always
  exercise `execute()` end-to-end in tests to catch dataclass
  mismatches that lint can't see.

- **RedisShortTermMemory mock injection path**: After the facade
  refactor, `_client` is a read-only property on the facade.
  Tests must inject mocks via `memory._base._client = mock_client`
  (the plain attribute on `BaseOperations`), not
  `memory._client = MagicMock()`. Old tests using the direct
  path were all skipped with "Redis mocking API changed".

- **Lazy imports inside function bodies can't be patched with
  `patch("module.Name")`**: `HookEvent`, `HookRegistry`, and
  similar names imported inside function bodies are never bound
  at module scope. `patch("attune.commands.context.HookEvent")`
  raises `AttributeError`. Use `patch.dict("sys.modules", ...)`
  to simulate `ImportError`, or use the real value for happy-path
  tests.

- **Full coverage runs on 15k+ test suites timeout easily**:
  `pytest --cov=src/attune` with the full test suite takes 10+
  minutes. For development feedback, use targeted coverage:
  `pytest tests/unit/module/ --cov=attune.module --no-cov-on-fail`
  to measure specific modules in seconds.

- **Bandit B108 blocks hardcoded `/tmp` paths**: Using a literal
  `/tmp/...` string in `subprocess.run` or `open()` triggers
  bandit B108 (insecure temp file usage). Fix: use
  `tempfile.TemporaryDirectory(prefix="...")` instead. This came
  up in `doc_audit/workflow.py` which used `/tmp/doc-audit-site`
  for mkdocs builds.

- **Tests for optional-dep code need `pytest.importorskip()`
  guards in CI**: Tests that import `redis`, `jinja2`, or other
  optional dependencies fail with `ModuleNotFoundError` in CI
  where only core deps are installed. Add
  `pytest.importorskip("redis")` at the top of the test module
  or use `@pytest.mark.skipif` to skip gracefully. This caused
  5 failures in PR #98 (3 redis, 1 jinja2, 1 redis auto-detect).

- **CI timeout tests enforce the range you set**: The test
  `test_timeout_values_are_reasonable` in `tests/unit/ci/`
  asserts that all workflow job timeouts fall within an
  allowed range. When bumping `timeout-minutes` in a workflow
  YAML, also update the test's upper bound or it fails on
  every platform.

- **`/sbin` is a symlink to `/usr/sbin` on modern Ubuntu**:
  `Path("/sbin/init").resolve()` does NOT follow the `/sbin`
  symlink when the target file doesn't exist (Python 3.10+
  `strict=False`). Tests asserting that `/sbin/...` is blocked
  by path validation fail on Ubuntu CI because the resolved
  path stays as `/sbin/init` which doesn't match the
  `/usr/sbin` entry in the blocklist. Use `/usr/sbin/...`
  directly in tests.

- **Windows CI runners are ~3x slower than Ubuntu/macOS**: A
  16k+ test suite that finishes in ~15min on macOS and ~17min
  on Ubuntu needs ~45min+ on Windows. Set `timeout-minutes`
  high enough (60) or the Windows matrix will always time out.
  Remember to update `test_timeout_values_are_reasonable` when
  changing the upper bound.

- **mkdocs `--strict` treats broken links as fatal errors**:
  The CI docs build uses `mkdocs build --strict` even though
  `mkdocs.yml` has `strict: false`. When source files are
  deleted but docs still link to them, the CI build fails with
  "Aborted with N warnings in strict mode!" Move stale docs
  to `docs/archive/` (excluded by mkdocs `exclude_docs`
  config) rather than fixing every dead link.

- **dist/ can contain stale artifacts after version bumps**: The
  `dist/` directory is not automatically rebuilt when
  `pyproject.toml` version changes. Always run
  `rm -rf dist/ && uv run python -m build` before publishing
  and verify `ls dist/` shows the correct version. Publishing
  stale artifacts uploads the old version to PyPI.

- **MCP tool count tests are hardcoded**: When adding new MCP
  tools to `server.py`, grep tests for the old tool count
  (e.g., `assert len(tools) == 22`). The assertion in
  `test_mcp_memory_tools.py` is the main one but others may
  exist. Also check workflow description assertions if
  descriptions were changed.

- **`list_wizards()` is a function, not a class method**:
  The wizard registry exposes `from attune.wizards import
  list_wizards` as a module-level function, not
  `WizardRegistry().list_wizards()`. The class
  `WizardRegistry` is not exported from `attune.wizards`.

- **Attune skill names must not collide with Claude Code built-in
  commands**: Claude Code's built-in `/batch` command (parallel code
  changes) shadows any Attune skill named `batch`. The user types
  `/batch submit` expecting Attune's Batch API workflow but gets
  Claude Code's orchestrator instead. Renamed to `/bulk` to avoid
  the collision. When naming new skills, check Claude Code's
  built-in slash commands first: `/batch`, `/compact`, `/config`,
  `/cost`, `/help`, `/init`, `/login`, `/logout`, `/memory`,
  `/permissions`, `/review`, `/status`, `/vim`.

- **`CostReport` is a dataclass, not a dict**: The
  `WorkflowBatchRunner._execute_one()` method used
  `result.cost_report.get("total_cost", cost)` which fails with
  `AttributeError: 'CostReport' object has no attribute 'get'`.
  Fix: use `getattr(result.cost_report, "total_cost", cost)`.
  Always check whether a result attribute is a dataclass or dict
  before choosing `.get()` vs `getattr()`.

- **Bug-predict `dangerous_eval` flags `subprocess_exec`**: The
  scanner's regex matches `create_subprocess_exec` as containing
  `exec`, producing a false positive for `dangerous_eval` in
  `hooks/executor.py`. There is no actual `eval()` or `exec()`
  usage. Always verify HIGH severity scanner findings against
  the source before treating them as real vulnerabilities.

- **`_run_simplify` catches per-file errors internally**: The
  pipeline orchestrator's `_run_simplify()` wraps each file in
  its own try/except, so even if `SimplifyCodeWorkflow()` raises,
  the method returns normally. The outer caller sets
  `result.simplified = True` regardless. Tests must match this
  behavior — the outer try/except only fires if `_run_simplify`
  itself raises, not if individual files fail.

- **Pre-commit auto-fix requires re-stage before retry**: When
  black/ruff auto-fix staged files during `git commit`, the
  commit fails but the fixes are applied to the working tree.
  The files must be `git add`-ed again before retrying the
  commit. This is different from the stash conflict issue —
  here there are no unstaged siblings, just the hook modifying
  staged files.

- **Any unstaged file triggers pre-commit stash conflicts with
  auto-fix**: Even unrelated unstaged files (e.g. `uv.lock`)
  cause pre-commit to stash/restore. If auto-fix hooks modify
  staged files during the stash, the restore conflicts and
  rolls back the fixes — creating an infinite fail loop. Fix:
  before committing, either `git add` all unstaged files or
  `git stash push` them manually. Running `uv run black` and
  `uv run ruff check --fix` on staged files beforehand doesn't
  help if pre-commit still detects unstaged files to stash.

- **`datetime.utcnow()` → `datetime.now(timezone.utc)` cascades
  through the entire codebase**: Replacing `utcnow()` (naive) with
  `now(timezone.utc)` (aware) in source code causes `TypeError:
  can't compare offset-naive and offset-aware datetimes` everywhere
  that stored/parsed timestamps interact with the new aware values.
  This includes `_parse_timestamp()` helpers, `fromisoformat()`
  calls that strip `Z`, and test fixtures that create naive
  datetimes. Plan for a full sweep of both src/ and tests/ — not
  just the files you initially changed.

- **Don't append `+ "Z"` to timezone-aware `.isoformat()`**:
  `datetime.now(timezone.utc).isoformat()` already produces
  `2026-03-08T12:00:00+00:00`. Appending `+ "Z"` creates
  `+00:00Z` which, when passed through `.replace("Z", "+00:00")`,
  becomes the invalid `+00:00+00:00`. After migrating to
  timezone-aware datetimes, grep for `.isoformat() + "Z"` and
  remove the suffix.

- **`PurePosixPath.match()` doesn't support `**` in Python 3.10**:
  `PurePosixPath("a/b/c.py").match("a/**")` returns `False` because
  `match()` treats `*` as single-segment only (no recursive globbing).
  For `**` glob patterns, convert to fnmatch: replace `**` with `*`,
  then use `fnmatch.fnmatch()`. Python 3.13+ adds recursive support
  but 3.10 does not.

- **Adding `logger` before eager imports triggers E402 in
  `__init__.py`**: Placing `logger = logging.getLogger(__name__)`
  between stdlib imports and eager `from .module import ...` lines
  makes ruff flag all subsequent relative imports as E402 (module-level
  import not at top). Move the logger assignment after ALL imports,
  just before the first non-import statement.

- **SDK agent MODEL_CONFIG uses stale model names**: The `MODEL_CONFIG`
  dict in `agents/release/release_models.py` references
  `claude-3-5-haiku-latest` which returns 404. The current Haiku model
  ID is `claude-haiku-4-5-20251001`. Check model IDs against the
  Anthropic API when tier escalation fails at CHEAP.

- **MyPy "437 errors" was stale — actual count was 2**: The
  pre-commit comment said "437 pre-existing errors" but running
  mypy with the configured settings found only 2 unused
  `type: ignore` comments. Always re-run the tool before assuming
  old error counts are still accurate — they may have been fixed
  as a side effect of other refactors.

- **B904 (`raise X from e`) is not auto-fixable by ruff**: Despite
  `ruff check --fix`, B904 violations require manual edits. Use
  `from e` when the exception variable is captured, `from None`
  when suppressing the original. After fixing all violations,
  remove B904 from the ruff ignore list to enforce going forward.

- **`claude-agent-sdk` is a standalone PyPI package, not bundled
  with Claude Code**: The Agent SDK (`pip install claude-agent-sdk`)
  is independently versioned and published on PyPI. It is not part
  of the `anthropic` package or the Claude Code CLI. The optional
  extra `attune-ai[agent-sdk]` installs it. Check availability at
  runtime with `import claude_agent_sdk` and the `_SDK_AVAILABLE`
  module-level guard pattern.

- **`list_workflows()` deduplication must keep base names visible**:
  When hiding SDK duplicates, only skip entries in `_SDK_REVERSE_MAP`
  (the explicit `-sdk` suffixed names). Do NOT also skip base names
  that have an SDK variant — those are the names users see and type.
  The resolver routes base names to SDK implementations transparently.

- **Push specific tags, not `--tags`**: `git push origin main --tags`
  pushes ALL local tags, causing "already exists" rejections for old
  tags. Use `git push origin main v4.0.0` to push only the intended
  tag.

- **Pull `main` before merging `develop` to avoid merge commits**:
  If `origin/main` has commits not in local `main`, merging `develop`
  creates a merge commit. Always `git pull origin main` first, then
  `git merge develop`. This also avoids the GitHub "no merge commits"
  rule violation.

- **GitHub protected tags cannot be force-updated**: Once a tag is
  pushed, `git push --force` fails if repository rules protect tags.
  Tag the correct commit before pushing — there's no easy fix after.

- **Rebuild dist after README changes**: PyPI uses `README.md` as the
  package description. If you update the README after the initial
  build, run `rm -rf dist/ && uv run python -m build` again before
  publishing or PyPI will show the old README.

- **MCP handler: validate paths before importing workflows**: In
  `server.py`, `_validate_file_path()` must run before the lazy
  `from attune.workflows.X import XWorkflow` import. If the import
  fails (wrong class name, missing dep), the path validation never
  fires and the security check is bypassed. Always: validate first,
  import second.

- **`BugPredictionWorkflow` not `BugPredictWorkflow`**: The class in
  `attune.workflows.bug_predict` is `BugPredictionWorkflow`. The
  MCP server had `BugPredictWorkflow` which caused `ImportError`.
  Always verify the actual class name with `grep` before writing
  an import.

- **`is_private` is a superset in Python `ipaddress`**: Loopback
  (`127.0.0.1`), link-local (`169.254.x.x`), and unspecified
  (`0.0.0.0`) all have `is_private=True`. When checking IP safety,
  test specific attributes (`is_loopback`, `is_link_local`, etc.)
  before `is_private` so error messages are precise. The same
  ordering matters in both IP literal checks and DNS resolution
  checks.


- **Changing error messages breaks tests across the codebase**:
  Updating `_validate_file_path()`'s error from `"path must be
  within"` to `"outside allowed directory"` broke 10 test files.
  Before changing any error message in a shared function, grep the
  entire test suite for `match="<old message>"` and update all
  callers in the same commit.

- **Adding DNS resolution to `_validate_webhook_url` breaks tests
  that pass real hostnames**: Any test calling `_validate_webhook_url`
  with a non-IP hostname (e.g. `example.com`) now needs
  `@patch("attune.monitoring.validators.socket.getaddrinfo")` to
  mock DNS resolution. Grep for all callers when adding network
  validation to an existing function.

- **MCP `workspace_root` defaults to `os.getcwd()` — tests with
  `tmp_path` fail**: Tests that create files in `tmp_path` and pass
  them to MCP handlers will get "outside allowed directory" errors
  because the server defaults to the repo root. Fix: pass
  `workspace_root=str(tmp_path)` when constructing the server in
  tests.

- **SSRF: always decode URLs before validating hostnames**:
  `urllib.parse.urlparse` does NOT decode percent-encoded
  characters. `http://%31%32%37%2e%30%2e%30%2e%31/` parses with
  hostname `%31%32%37%2e%30%2e%30%2e%31` which bypasses blocklist
  checks for `127.0.0.1`. Always `urllib.parse.unquote(url)` before
  parsing and validating.

- **SSRF: strip IPv6 zone IDs before IP validation**: IPv6 zone
  IDs (e.g., `fe80::1%25eth0`) can bypass `ipaddress.ip_address()`
  checks because the `%` suffix makes parsing fail or return
  unexpected results. Strip zone IDs with `hostname.split("%")[0]`
  before any IP validation.

- **structlog kwargs vs stdlib Logger**: `logger.info("msg",
  key=value)` is structlog syntax. stdlib `logging.Logger` raises
  `TypeError: info() got an unexpected keyword argument`. Use
  `logger.info("msg: key=%s", value)` instead. When fixing, grep
  the entire module — partial fixes leave runtime crashes in
  untouched calls.

- **Windows `Path.resolve()` prepends the drive letter to Unix
  paths**: `Path("/code").resolve()` on Windows returns
  `D:\code`, not `/code`. Tests that assert exact path strings
  passed through `_validate_file_path` fail on Windows CI. Fix:
  patch `_validate_file_path` in tests that verify handler logic
  (not path validation) so paths pass through unchanged.

- **Stacked `@patch` decorators inject args bottom-up**: When a
  test has `@patch("A") @patch("B") def test(self, mock_b,
  mock_a)`, the innermost (bottom) decorator's mock is the first
  positional arg. Forgetting a decorator while referencing its
  mock variable causes `NameError` at runtime, not import time.
  Always count decorators vs method params.

- **`.gitignore` exclusions break CI tests that read those
  files**: If tests call `read_spec(".claude/plans/foo.md")` but
  `.gitignore` excludes `.claude/plans/`, CI will never have the
  file. Either track the files or skip the tests when absent.

- **Windows `time.time()` can return 0.0 duration for fast
  operations**: On Windows 3.10-3.12, `time.time()` has ~15ms
  resolution. Tests asserting `execution_time > 0` fail when
  the operation completes within one tick. Use
  `time.perf_counter()` for sub-millisecond timing, or assert
  `>= 0` if the operation may be instant.

- **`config.py` alongside `config/` creates a mypy duplicate
  module**: Having both `src/attune/config.py` and
  `src/attune/config/__init__.py` causes mypy to report
  "Duplicate module named attune.config". This blocks mypy in
  pre-commit. Either rename one or exclude the module from mypy.
  We removed mypy from pre-commit entirely for now.

<!-- attune-lessons-end -->
