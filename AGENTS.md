# AGENTS.md — Attune AI

Project instructions for AI coding agents that do not read
`.claude/` (Codex, etc.). Claude Code loads `.claude/CLAUDE.md`
instead; the rules below are the shared, agent-agnostic core. If
you change a rule here, check whether `.claude/CLAUDE.md` needs
the same change.

## Overview

Attune AI — AI-powered developer workflows with cost optimization
and multi-agent orchestration. Python 3.10+, published on PyPI as
`attune-ai`. Stack: pydantic, anthropic SDK / claude-agent-sdk,
structlog, rich, typer.

```text
src/attune/
├── agents/            # Release agents, state persistence, recovery
├── workflows/         # AI-powered workflows (all SDK-native)
├── models/            # Auth strategy and LLM providers
├── meta_workflows/    # Intent detection, NL routing
├── orchestration/     # Dynamic teams, workflow composition
├── plugins/           # BasePlugin + register_mcp_tools() hook
├── telemetry/         # FeedbackLoop, UsageTracker
└── cli_router.py      # NL command routing
attune_redis/          # Redis plugin — bundled in the attune-ai wheel
```

## Commands

```bash
uv sync --extra dev --extra developer   # environment
uv run pytest tests/unit -q             # unit tests (fast lanes)
uv run ruff check src/ tests/           # lint
uv run --with pre-commit pre-commit run black --files <f>  # pinned format
attune <command>                        # CLI (canonical entry)
```

## Critical rules

- NEVER use `eval()` or `exec()`.
- ALWAYS validate file paths with `_validate_file_path()` in file
  operations; security tests required for file-op code.
- NEVER use bare `except:` — catch specific exceptions and log them
  before handling.
- Type hints and docstrings required on all public APIs (PEP 8).
- Minimum 80% test coverage on changed code.
- Simpler is better: flatten nested conditionals, inline one-use
  helpers, prefer stdlib over custom abstractions. Three clear
  lines beat one clever abstraction.

## Git and pre-commit

- Commits are GPG-signed; `git pull` rebases.
- Pre-commit auto-fix hooks (black, ruff, detect-secrets) modify
  staged files mid-commit. Pre-flight the PINNED tools on your
  files BEFORE `git add` (command above) so hooks see clean files.
- After every `git commit`, verify it landed: `git log --oneline
  -1` + `git status --short`. Hooks can leave the commit skipped
  with exit 0 and files re-staged.
- If a hook reformats staged files, the fixes land UNSTAGED —
  `git add` again and retry the commit.
- A PreToolUse/pre-commit guard blocks commit messages containing
  literal `eval(` / `exec(` — write the message to a file and use
  `git commit -F <file>`.
- `--no-verify` is forbidden. To skip ONE misbehaving hook:
  `SKIP=<hook-id> git commit …` (runs all others).
- detect-secrets flags placeholder-looking strings; annotate false
  positives with `# pragma: allowlist secret`.

## Branch and worktree discipline

Multiple agents work this repo in parallel (Claude Code sessions
use worktrees under `.claude/worktrees/<slug>/`).

- One branch per agent per task. Never commit to a branch another
  agent has in flight.
- Before every commit: `git branch --show-current` — confirm the
  checkout you edited is on the branch you mean to ship.
- Don't touch other worktrees under `.claude/worktrees/` — they
  may hold live sessions.

## Single-source projections (don't hand-edit generated files)

- `plugin/skills/*/SKILL.md` is the SOURCE for
  `.agents/skills/<name>/SKILL.md`. After editing a skill, run
  `python scripts/sync_agents_skills.py` and commit BOTH sides —
  a drift-guard test fails CI otherwise.
- `.help/` and docs feature pages are projector-owned
  (`status: manual` pages excepted). Don't rewrite generated help
  content by hand; edit the source and re-project.

## CI notes

- Per-push/PR workflows run with `ANTHROPIC_API_KEY: ""` (empty,
  keyless) by design — never wire the real secret into them.
- To reproduce keyless CI locally: `ANTHROPIC_API_KEY="" pytest …`
  (empty string, not unset — dotenv re-injects unset vars).
- The Windows matrix lanes are slow (~13 min) but real — path
  handling, subprocess, and encoding changes must wait for them.

## Where agent-specific state lives

- `.claude/` — Claude Code's rules, lessons corpus, skills,
  worktrees. Not loaded by other agents; don't edit ad hoc.
- `.codex/` — Codex local config (gitignored).
- `AGENTS.md` (this file) — tracked, shared rules for non-Claude
  agents.
