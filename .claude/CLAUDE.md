# Attune AI Framework v3.6.1

AI-powered developer workflows with cost optimization and multi-agent orchestration.

@./python-standards.md

---

## Quick Start

```bash
python -m attune.models.auth_cli setup    # Configure authentication
python examples/dashboard_demo.py         # Agent dashboard at localhost:8000
```

**CLI:** `attune <command>` (canonical) or `python -m attune.cli_minimal` (full). See `docs/reference/cli-reference.md`.

---

## Command Hubs

Use `/hub-name` to access organized workflows:

| Hub | Key Routes | Description |
| --- | ---------- | ----------- |
| `/attune` | Socratic discovery | Natural language routing to all workflows |
| `/dev` | debug, review, commit, pr, refactor, quality, perf-audit | Developer tools |
| `/testing` | run, coverage, generate, benchmark | Test runner and generation |
| `/workflows` | security, bugs, perf, review, list | Automated analysis |
| `/plan` | feature, refactor, architecture | Planning and strategy |
| `/docs` | generate, readme, changelog, explain, audit, overview | Documentation |
| `/release` | prep, security, health, publish | Release preparation |
| `/brainstorm` | "topic", plan | Guided brainstorming and ideation |
| `/agent` | create, list, run, release-prep | Agent management |
| `/batch` | submit, status, results, wait | Batch API processing (50% cost savings) |
| `/wizard` | run, create, list, edit | Guided multi-step wizards |
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
├── dashboard/         # DEPRECATED — soft-deprecated, removal in future major
├── meta_workflows/    # Intent detection and natural language routing
├── orchestration/     # Dynamic teams, workflow composition, pattern learning
├── plugins/           # BasePlugin + register_mcp_tools() hook
├── telemetry/         # FeedbackLoop, UsageTracker (MemoryBackend protocol)
└── cli_router.py      # Natural language command routing

attune_redis/          # attune-redis plugin (pip install attune-redis)
```

---

**Version:** 3.6.3 | **License:** Apache 2.0 | **Repo:** [attune-ai](https://github.com/Smart-AI-Memory/attune-ai)

<!-- attune-lessons-start -->

## Lessons Learned

- **Windows CI encoding**: Always use `encoding="utf-8"` on
  `Path.read_text()` calls. Windows defaults to `cp1252` which
  fails on any file containing non-ASCII bytes.

- **Test mocks must match imports**: When a function changes its
  import (e.g. `run_standalone_dashboard` → `run_simple_dashboard`),
  all test mocks must be updated to match or side effects are silently
  ignored and assertions fail.

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
  `attune dashboard start`, `npm run dev`) survive session end and
  keep running silently. They can open browser tabs, consume ports,
  or interfere with the next session. Always `kill` them explicitly
  when removing a feature, and check `ps aux` if unexpected behavior
  is observed (Chrome tabs opening, ports already in use, etc.).

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

<!-- attune-lessons-end -->
