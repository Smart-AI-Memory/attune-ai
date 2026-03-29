# Attune AI Framework v5.1.2

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

| Command | Description |
| ------- | ----------- |
| `/spec` | Spec-driven development with approval loop |
| `/attune` | Socratic discovery — routes to any workflow |
| `/security` | Security audit |
| `/smart-test` | Find test gaps, generate tests |
| `/release` | Release preparation and publishing |
| `/help` | Quick reference for all commands |

**More commands** (type `/help` for full list):

`/dev` `/plan` `/brainstorm` `/code-quality`
`/doc-gen` `/fix-test` `/refactor` `/deep-review`
`/agent` `/wizard` `/bulk` `/remember`

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
├── agents/            # Release agents, state persistence, recovery
│   ├── release/       # ReleaseAgent, ReleasePrepTeam
│   └── state/         # AgentStateStore, AgentRecoveryManager
├── workflows/         # AI-powered workflows (all SDK-native)
├── models/            # Authentication strategy and LLM providers
├── meta_workflows/    # Intent detection and natural language routing
├── orchestration/     # Dynamic teams, workflow composition, agent models
├── plugins/           # BasePlugin + register_mcp_tools() hook
├── telemetry/         # FeedbackLoop, UsageTracker (MemoryBackend protocol)
└── cli_router.py      # Natural language command routing

attune_redis/          # attune-redis plugin (pip install attune-redis)
```

---

**Version:** 5.0.0 | **License:** Apache 2.0 | **Repo:** [attune-ai](https://github.com/Smart-AI-Memory/attune-ai)

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

- **Patch the source module for `from ..X import Y` in function
  bodies**: When a function does `from ..real_tools import
  RealSecurityAuditor`, patching
  `_strategies.base.RealSecurityAuditor` fails (not at module
  scope). Instead patch `real_tools.RealSecurityAuditor` — the
  source module where the name IS at module scope. The deferred
  import resolves from the (now-patched) source at call time.
  This is cleaner than moving imports or using
  `patch.dict("sys.modules")`.

- **Mock a lazy `import X` with `types.ModuleType` +
  `patch.dict("sys.modules")`**: When a function body does
  `import attune` (bare module, not `from X import Y`),
  `patch("module.attune")` fails (not at module scope) and
  source-module patching doesn't apply. Fix: create
  `mock = types.ModuleType("attune")`, set attributes like
  `mock.__version__ = "1.0.0"`, then use
  `patch.dict("sys.modules", {"attune": mock})`. The lazy
  import inside the function resolves from `sys.modules`.

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

- **`claude-agent-sdk` is now a core dependency of attune-ai**:
  As of v4.2.0, the Agent SDK is included in core dependencies.
  No need for `pip install 'attune-ai[agent-sdk]'` — a plain
  `pip install attune-ai` includes it. The `[agent-sdk]` extra
  is kept as an empty placeholder for backward compatibility.

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

- **Replacing a mixin-based class scatters test failures across many
  files**: When merging `CodeReviewWorkflow` from 5 mixins into an
  SDK-native class, tests for old internal methods (`_classify`,
  `_scan`, `_gather_project_context`, `should_skip_stage`) were spread
  across 6+ test files (unit, workflow, integration, coverage batches).
  Grep for ALL method names being removed across the entire test tree
  before considering the migration done — `pytest -k "code_review"`
  catches failures that file-specific runs miss.

- **Registry count assertions are scattered across test files**: When
  merging SDK workflow variants (reducing `_SDK_WORKFLOW_MAP` from
  12→9 entries), hardcoded count assertions like
  `assert len(_SDK_WORKFLOW_MAP) == 12` and expected-set assertions
  exist in routing behavioral tests, validation framework tests, and
  coverage batch tests. Always grep for the old count and old class
  names (e.g. `SecurityAuditAgentSDKWorkflow`) across all test files
  when changing registry size.

- **SDK-native workflows validate in `execute()`, not `input_schema`**:
  After merging to SDK-native, workflows no longer declare
  `input_schema` as a class attribute — path validation happens inside
  `execute()`. Tests asserting `Workflow.input_schema is not None`
  must be removed or updated.

- **Hardcoded strings in method bodies survive class attribute
  renames**: Changing `name = "deep-review-sdk"` to `"deep-review"`
  on the class didn't fix a hardcoded `"workflow": "deep-review-sdk"`
  string inside `execute()`. After renaming a class attribute, always
  grep for the old value across the entire source file to catch
  hardcoded duplicates in method bodies and metadata dicts.

- **GPG signing fails in non-interactive terminals (VSCode
  extension, Claude Code)**: `gpg` tries to open `/dev/tty` for
  passphrase input, which doesn't exist in spawned subprocesses.
  Fix: install `pinentry-mac` (`brew install pinentry-mac`), set
  `pinentry-program /opt/homebrew/bin/pinentry-mac` in
  `~/.gnupg/gpg-agent.conf` (remove any earlier `pinentry-tty`
  lines — GPG uses the first match), then `gpgconf --kill
  gpg-agent`. The passphrase must still be cached first by
  running `echo "unlock" | gpg --clearsign` in a real terminal.

- **Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins**: GPG uses the first `pinentry-program` directive it
  finds. Appending a new line doesn't override earlier ones.
  Always replace, don't append.

- **`pip-audit` fails on unpublished versions**: `pip-audit --strict`
  with a local editable install (`pip install -e .`) fails if the
  version in `pyproject.toml` doesn't exist on PyPI yet. The error
  is `Dependency not found on PyPI and could not be audited:
  attune-ai (5.0.0)`. This self-resolves after publishing. Not a
  blocking CI failure for version bump PRs.

- **`bg-[var(--primary)] bg-opacity-10` is invisible in dark mode**:
  A 10% opacity tint of dark blue (`#1E40AF`) on a dark background
  (`#0F172A`) produces near-zero contrast. Use `bg-[var(--background)]`
  with a colored border instead, or switch to `gradient-accent`
  (purple) which is brighter. This affected callout boxes and hero
  sections on the attune-lite page.

- **Claude Code plugins expect `plugin.json` inside `.claude-plugin/`**:
  The correct location is `<plugin-root>/.claude-plugin/plugin.json`.
  Skills, commands, agents, and hooks directories go at the plugin
  root level alongside `.claude-plugin/`. Use `claude --plugin-dir
  ./plugin` to test local plugins during development.

- **`_validate_file_path` needed on reads too, not just writes**:
  `load_state(user_id)` and `delete_state(user_id)` built paths
  from user input without validation. Even though the existing
  `save_state()` validated, the read and delete paths did not.
  When adding path validation to a module, grep for ALL `open()`,
  `.unlink()`, and `.read_text()` calls in the same file — not
  just write operations.

- **`importlib.import_module()` is an arbitrary code execution
  vector**: The hook executor's `_execute_python()` fell through
  to `importlib.import_module(module_path)` for any module not
  in `_python_handlers`. This allowed importing `os`, `subprocess`,
  or any installed package. Fix: allowlist module prefixes (e.g.,
  `("attune.",)`) before the import call. Security boundaries
  should not be user-configurable.

- **Hardcoded `user_id` defeats ownership checks**: Adding
  ownership validation to memory handlers is pointless if the
  MCP server uses `user_id="mcp-session"` for everyone. Fix the
  identity layer (Fix 5) before or alongside the authorization
  layer (Fix 4). Use `os.getlogin()` with fallback for
  non-interactive environments.

- **Pre-commit black + unstaged files: re-stage after failure**:
  When `git commit` fails because black reformatted staged files,
  the reformatted files are in the working tree but unstaged. Run
  `git add <files>` again before retrying the commit. This is
  distinct from the stash conflict issue — here the hook succeeds
  at formatting but the commit is rejected because files changed.

- **New security features need dedicated tests before release**:
  v5.0.1 shipped with 4 new security controls (rate limiter,
  ownership checks, module prefix restriction, workspace
  isolation) — all with zero effective test coverage despite
  15,555 tests passing. The deep review caught this after
  publishing to PyPI. Run `/deep-review` on changed files
  BEFORE `/release prep`, not after.

- **SSRF in webhook handlers is easy to miss**: The
  `_execute_webhook()` method in `executor.py` accepts
  arbitrary URLs without IP blocklist, scheme validation, or
  DNS resolution checks (CWE-918). Webhook endpoints need the
  same validation rigor as file paths — add
  `_validate_webhook_url()` alongside `_validate_file_path()`.

- **`ResultMessage.result` is often `None` — capture
  `AssistantMessage` text too**: All 15 SDK-native workflows
  only checked `ResultMessage.result` for the agent's output.
  But `ResultMessage` is a metadata-only final message; its
  `result` field is `str | None` and frequently `None`. The
  actual analysis text lives in `AssistantMessage.content`
  `TextBlock` entries emitted throughout the conversation.
  Fix: `collect_agent_output()` and `build_result_text()` in
  `agent_sdk_adapter.py` now collect from both message types,
  preferring `ResultMessage.result` when present and falling
  back to `AssistantMessage` text. Filter with
  `parent_tool_use_id is None` to skip subagent tool-call
  messages.

- **Exploration agents fabricate names — verify against
  source**: When generating docs, the Explore agent fabricated
  10 of 14 agent template names (e.g. "bug_predictor" instead
  of actual "test_coverage_analyzer"). Always `grep` source
  files for IDs, class names, and counts before trusting
  agent-generated inventories. This applies to any generated
  content that enumerates codebase entities.

- **Skill frontmatter has a strict allowlist**: Claude Code
  skills only support these YAML frontmatter fields:
  `name`, `description`, `argument-hint`,
  `disable-model-invocation`, `user-invocable`,
  `compatibility`, `license`, `metadata`. Fields like
  `allowed-tools`, `model`, `context`, `agent`, and `hooks`
  are NOT valid for skills (they may apply to agents or
  commands). The IDE linter catches these — always check
  diagnostics after editing SKILL.md frontmatter.

- **Commands are NOT namespaced in plugins, skills ARE**:
  A command named `attune` in `commands/attune.md` is
  invoked as `/attune` directly. A skill named
  `workflow-orchestration` is invoked as
  `/attune-ai:workflow-orchestration`. Keep a command as
  the short entry point when UX matters. Check Claude
  Code built-ins (`/batch`, `/compact`, `/config`,
  `/cost`, `/help`, `/init`, `/login`, `/logout`,
  `/memory`, `/permissions`, `/review`, `/status`,
  `/vim`) before naming commands to avoid collisions.

- **MCP tool renames propagate to skill docs**: The empathy
  tools were renamed from `empathy_get_level`/`empathy_set_level`
  to `attune_get_level`/`attune_set_level` in the MCP server,
  but skill docs and command routing still referenced the old
  names. Always grep plugin/ for old tool names after renaming
  MCP handlers.

- **Broad gitignore patterns match nested directories**: A
  root `.gitignore` entry `planning/` (without leading `/`)
  matches `plugin/skills/planning/` too. Scope patterns with
  `/planning/` for root-only, and add `!plugin/skills/planning/`
  exceptions when needed.

- **Verify MCP tool wiring after adding new tools**: After
  adding tools to `server.py`, grep all plugin skills and
  commands for references. 15 tools were registered but
  unreachable from any skill until explicitly wired into
  existing skill documentation.

- **Mixin classes inherit `self._workspace_root` at runtime,
  not at definition time**: `WorkflowHandlersMixin` has no
  `__init__` and no `_workspace_root` attribute, but it works
  because it's mixed into `EmpathyMCPServer` which sets
  `_workspace_root` in its constructor. When adding validation
  to a mixin, use `self._workspace_root` freely — but document
  the expected host attribute in the mixin docstring.

- **`PurePosixPath` strips trailing slashes**: The test fixture
  `_passthrough` returns `PurePosixPath(path)`, which strips
  trailing slashes (`"src/"` → `"src"`). Tests asserting exact
  path strings passed through `_validate_file_path` must account
  for this. Use `in ("src/", "src")` or check `call_args.kwargs`
  instead of `assert_awaited_once_with`.

- **Deep review false positives — verify before acting**: The
  quality pass reported `summary_index.py` at 0% coverage and
  `test_runner_helpers.py` missing docstrings. Both were wrong —
  `summary_index.py` had 25 tests in `tests/memory/`, and all
  helpers had docstrings. Always re-verify agent findings against
  the actual codebase before planning fixes.

- **Ghost command references survive CLI renames**: Renaming
  `empathy` → `attune` left 30+ stale command references in
  discovery tips, workflow output, template definitions, and
  docstrings across 15 files. After any CLI rename, grep the
  entire `src/` for the old name and add a validation test
  that checks user-facing command strings against the actual
  registered CLI subcommands.

- **New MCP handlers must match the validation pattern of
  adjacent handlers**: `_run_test_generation` was the only
  handler (out of 10) missing `_validate_file_path()` — easy
  to miss because the handler worked fine without it. When
  adding a new MCP tool handler, copy the validation block
  from the nearest similar handler, not just the workflow
  call pattern.

- **Silent `pass` blocks in discovery/registry code hide
  import failures**: Workflow discovery had 6 silent `pass`
  blocks that swallowed `ImportError`/`AttributeError`. When
  a workflow disappeared from `attune workflow list`, there
  was no diagnostic output at any log level. Always use
  `logger.warning()` in discovery paths so `--verbose` or
  log inspection can surface the root cause.

- **Semantic cache 70% hit rate claim was unmeasured**:
  Telemetry data (`~/.attune/telemetry/usage.jsonl`, 17,264
  requests) showed 0.2% hit rate and $0.26 saved out of $72.
  The 0.95 similarity threshold and non-repetitive workflow
  prompts (unique file paths, timestamps, code snippets) meant
  near-matches almost never fired. Always verify performance
  claims against actual telemetry before documenting them.

- **Anthropic's built-in prompt caching supersedes custom
  caching**: Since Dec 2024, the Anthropic API provides 90%
  input token discounts via server-side prompt caching. The
  Claude Agent SDK uses this automatically. Custom client-side
  caching with `sentence-transformers` (420MB dep) delivered
  0.4% savings vs Anthropic's automatic server-side caching.
  Removed in favor of the native solution.

- **Dead code modules with full test suites look alive**:
  `socratic/embeddings/` had 240 lines of passing tests, clean
  exports in `__init__.py`, and conftest fixtures — but zero
  imports from any workflow, CLI, or MCP path. Tests passing
  is not evidence of integration. Grep for imports outside the
  module itself before considering a feature "active".

- **Changing user-facing output strings cascades through test
  assertions**: Replacing "Workflow completed" with voice layer
  personality messaging broke 6 assertions across 4 test classes.
  When changing any user-facing output string in a shared path
  (like `_print_workflow_result`), grep the entire test suite for
  the old string before considering the change done. This is
  broader than just error messages — any output text change.

- **Real project files on disk override test mocks**: Tests that
  mock `_get_raw_suggestions()` at the definition site still get
  real suggestions from `_get_spec_suggestions()` which reads
  actual `.claude/plans/` files. Fix: mock at the *import site*
  in the consuming module (`attune.voice.formatter.get_next_steps`
  not `attune.voice.next_steps.get_next_steps`), or use
  `monkeypatch.chdir(tmp_path)` to isolate from the real
  filesystem.

- **MCP `call_tool` wrapper pattern**: When adding a cross-cutting
  concern (like voice layer) to the MCP server, rename the
  original `call_tool()` to `_dispatch_tool()` and create a new
  `call_tool()` that wraps it. This preserves the public API,
  keeps the diff minimal, and lets the wrapper degrade gracefully
  with a try/except around the new layer.

- **macOS `/var` → `/private/var` symlink breaks path assertions**:
  `_validate_file_path()` calls `Path.resolve()`, which follows the
  macOS symlink from `/var/folders/...` to `/private/var/folders/...`.
  Tests using `tempfile.NamedTemporaryFile` get unresolved paths from
  `f.name` but resolved paths from validated code. Fix: assert against
  `str(Path(f.name).resolve())` instead of `f.name`. This is the macOS
  equivalent of the Windows drive-letter lesson.

- **PyPI renders README links relative to its own domain**: Relative
  links like `docs/ARCHITECTURE.md` become
  `https://pypi.org/project/attune-ai/docs/ARCHITECTURE.md` which
  404s. All links in README.md must use absolute GitHub URLs
  (`https://github.com/Smart-AI-Memory/attune-ai/blob/main/...`).
  This applies to LICENSE, SECURITY.md, CONTRIBUTING.md, and any
  docs/ path. Contributor-facing links (coding standards,
  contributing guide) are better removed from the PyPI README
  entirely — they add clutter and broken-link risk for users who
  will never contribute.

- **Plugin `Read skill` references break outside the plugin**: The
  `file:///skills/doc-gen/SKILL.md` path in plugin commands is
  relative to `${CLAUDE_PLUGIN_ROOT}`. When the command is copied
  to `~/.claude/commands/` via `attune setup`, the path doesn't
  resolve. Commands shipped in `src/attune/commands/` (for PyPI)
  must be self-contained — embed the instructions directly instead
  of referencing skill files.

- **Dependency lower bounds trigger Scorecard vulnerability alerts**:
  Even if installed versions are safe, OpenSSF Scorecard flags
  `pyproject.toml` specs that *allow* vulnerable versions (e.g.,
  `pydantic>=2.0.0` permits 2.0–2.3 which have CVEs). Fix: bump
  lower bounds past the patched version, not just the lockfile.

- **`enforce_admins: false` defeats Code-Review Scorecard check**:
  Even with `required_approving_review_count: 1`, admins bypass
  reviews when `enforce_admins` is off. Scorecard sees 0/25
  approved changesets. For solo devs: enable `enforce_admins` and
  add an auto-approve workflow triggered by CI success.

- **YAML `run:` values with colons cause parse errors**: A GitHub
  Actions `run:` like `run: gh pr review --body "Auto-approved:
  update"` fails YAML parsing because the colon after
  "Auto-approved" is interpreted as a mapping. Remove the colon
  or quote the entire value.

- **CodeQL alerts dismissible in bulk via `gh api`**: Use
  `gh api repos/OWNER/REPO/code-scanning/alerts/ID -X PATCH
  -f state=dismissed -f dismissed_reason="false positive"
  -f dismissed_comment="..."` to batch-dismiss with documented
  reasons. Valid reasons: `false positive`, `won't fix`,
  `used in tests`.

- **Repo merge policy may restrict merge strategies**: `gh pr merge
  --merge` failed with "Merge method merge commits are not allowed".
  This repo only allows squash merges. Always use `--squash` for
  `gh pr merge` in this repo.

- **CodeQL `py/clear-text-logging-sensitive-data` traces data flow,
  not literal secrets**: CodeQL flagged `user_id` in a log message
  inside `security.py` even though only the count of secrets was
  logged (not secret values). It traces any variable that flows
  through a security-sensitive method. Fix: use `%s` formatting
  without user identifiers, or move audit correlation to the
  dedicated audit logger which is designed for that purpose.

- **CodeQL `js/stored-xss` flags JSX even though React auto-escapes**:
  CodeQL flagged `{tag}` rendered in `<h1>` as stored XSS despite
  React's automatic text escaping. Defense-in-depth fix:
  `decodeURIComponent` on input + `encodeURIComponent` on `href`
  values. `generateStaticParams` constrains valid values but CodeQL
  can't see that.

- **Dispatch tables hold direct function references — mocks
  must target the table, not the module name**: When
  `_SUBCOMMAND_DISPATCH` or `_SIMPLE_DISPATCH` in
  `cli_minimal.py` captures `cmd_foo` at import time,
  `@patch("attune.cli_minimal.cmd_foo")` replaces the module
  attribute but the dispatch table still calls the original.
  Fix: use `patch.dict("attune.cli_minimal._SUBCOMMAND_DISPATCH",
  {command: {**orig, subcommand: mock_fn}})` to replace the
  entry in the dispatch table itself. This caused 20+
  pre-existing test failures.

- **Pre-commit stash conflicts when any tracked unstaged file
  exists alongside staged files**: Even a single unrelated
  unstaged tracked file (e.g. `memdocs_storage/test_key.json`)
  triggers pre-commit's stash/restore cycle. If auto-fix hooks
  (black, ruff) modify staged files during that cycle, the
  restore conflicts and the commit fails. Fix: `git stash push`
  the unstaged tracked files before committing, then
  `git stash pop` after.

- **`hot_reload/` subsystem was 1,038 lines of dead code**:
  Zero inbound imports from any file outside the package, but
  it had its own test suite (1,409 lines) that all passed —
  making it look alive. Lesson: passing tests are not evidence
  of integration. Always grep for imports outside the module
  itself before considering a feature active. (This echoes the
  existing `socratic/embeddings/` lesson but for a different
  module.)

- **`gh pr merge --admin` is blocked by in-progress required
  checks**: The `--admin` flag only bypasses failed or missing
  checks — it cannot override checks that are still running.
  GitHub returns `Required status check "X" is in progress`.
  You must wait for required checks to complete (or cancel
  them) before even an admin merge is possible. Budget extra
  time when the test matrix is large (12 platform combos ~15
  min).

- **ClusterFuzzLite `--no-deps` misses transitive imports**:
  `.clusterfuzzlite/build.sh` used `pip3 install --no-deps`
  to keep the fuzz image lean, but when `attune.security`
  gained a transitive import chain to `structlog` (via
  `attune.memory.security.secrets_detector`), the fuzz target
  crashed at startup with `ModuleNotFoundError`. PyInstaller
  `--hidden-import` flags tell the bundler about modules but
  don't install missing packages. Fix: explicitly `pip3
  install <dep>` for any dependency reachable from fuzz target
  imports.
- **Required status check names must match GitHub's exact check
  names**: We set `Analyze Python` as a required check, but the
  actual name is `Analyze (python)` (with parentheses). Mismatched
  names silently block merges because the expected check never
  appears. Always run `gh pr checks <PR>` first to see the exact
  check names before adding them to branch protection.

- **`enforce_admins` + required reviews blocks solo-dev merges**:
  With `enforce_admins: true` and `required_approving_review_count:
  1`, the repo owner cannot self-approve PRs (`Review Can not
  approve your own pull request`) and `--admin` merge also fails.
  The auto-approve workflow's `GITHUB_TOKEN` also can't approve
  the PR author's own PRs. For solo-dev repos: temporarily remove
  the review requirement via API, merge, then re-enable. The
  auto-approve workflow works correctly for PRs opened by other
  actors (Dependabot, collaborators).

- **OpenSSF Scorecard alerts (#2 CodeReviewID, #3 SASTID) are
  process metrics, not code bugs**: They measure the ratio of
  approved/analyzed changesets over time. No single PR can fix
  them — they improve incrementally as future PRs flow through
  review and SAST gates. Setting up the gates (required reviews,
  required CodeQL checks) is the fix; the score follows.
- **Scorecard's pip parser ignores `--hash` flags entirely**:
  Even single-line `pip3 install 'pkg==1.0' --hash=sha256:abc...`
  is flagged as "not pinned by hash". Scorecard's `PinnedDependenciesID`
  check does not recognize pip's `--hash` CLI flag — it only
  recognizes `--require-hashes` with a requirements file, or
  possibly other formats. For ClusterFuzzLite `build.sh`, dismiss
  as false positive since the deps ARE hash-pinned. The alerts
  recur on each Scorecard re-scan so expect to re-dismiss.

- **Re-enabling required reviews kills queued auto-merge**: If you
  set `gh pr merge --auto` while reviews are removed, then
  re-enable `required_approving_review_count: 1` before the merge
  fires, auto-merge is blocked (no approval exists). Fix: either
  wait for auto-merge to complete before re-enabling reviews, or
  skip auto-merge entirely and use the remove-reviews → admin-merge
  → re-enable-reviews pattern.
- **Skill descriptions must be under 250 characters**: Anthropic
  truncates skill descriptions longer than 250 chars, which breaks
  auto-triggering from natural language. Always check with
  `len(description)` after editing SKILL.md frontmatter. Our initial
  migration had 7 of 11 skills over the limit.

- **Skill frontmatter allowlist (March 2026)**: Valid fields are
  `name`, `description`, `argument-hint`, `disable-model-invocation`,
  `user-invocable`, `allowed-tools`, `model`, `effort`, `context`,
  `agent`, `hooks`, `paths`, `shell`. Fields `compatibility`,
  `license`, and `metadata` are NOT in the official docs and should
  not be used. The old lesson about a strict 8-field allowlist was
  outdated.

- **`claude plugin install` is marketplace-only**: The `install`
  command does not accept local paths. For local testing use
  `claude --plugin-dir ./plugin`. For distribution, create a
  `.claude-plugin/marketplace.json` at the repo root and have users
  run `claude plugin marketplace add owner/repo` then
  `claude plugin install name@marketplace`.

- **GitHub repos serve as Claude Code marketplaces**: Add
  `.claude-plugin/marketplace.json` at the repo root with a `source`
  field pointing to the plugin subdirectory (e.g., `"./plugin"`).
  Users install with two commands:
  `claude plugin marketplace add Smart-AI-Memory/attune-ai` then
  `claude plugin install attune-ai@attune-ai`. The marketplace clones
  from the default branch — changes must be merged to `main` before
  users see them.

- **Duplicate plugins cause conflicting skill triggers**: Having
  both `attune-lite` and `attune-ai` installed creates duplicate
  skills (`security-audit`, `smart-test`, etc.). Claude sees both
  and must pick one, degrading UX. When consolidating plugins,
  deprecate the old one and uninstall it before installing the
  replacement.
<!-- attune-lessons-end -->
