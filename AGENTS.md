# AGENTS.md — Attune AI

Project instructions for AI coding agents that do not read
`.claude/` (Codex, etc.). Claude Code loads `.claude/CLAUDE.md`
instead. The shared, agent-agnostic core lives in
`content/collaboration/contract.md` and is projected into the
marked block below (and into `.claude/CLAUDE.md`) — edit the
master and re-run `scripts/project_collaboration_contract.py`,
never the block. Content outside the block is Codex-facing
orientation only.

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

<!-- attune:collaboration:start -->

<!-- generated from content/collaboration/contract.md - edit the master, then run scripts/project_collaboration_contract.py -->

## Cross-provider collaboration

### Shared truth

- Treat the current worktree, Git state, and relevant test results as
  authoritative. Do not rely on hidden chat context for a handoff.
- Preserve unrelated working-tree changes and do not touch another
  agent's worktree.
- Discover capabilities from the available tools, MCP server, and
  tracked skills; do not rely on hard-coded capability counts.

### Session protocol

- Before non-trivial work, run
  `python scripts/collaboration_preflight.py`. It is read-only, uses
  cached Git refs, and does not fetch, pull, switch branches, invoke
  `uv`, or create an environment.
- State the goal, acceptance criteria, assumptions, and intended
  verification before non-trivial implementation.
- Prefer existing repository conventions and public interfaces before
  adding a parallel mechanism.
- Keep provider-specific setup in adapters. The shared contract must
  still work when only one provider is available.

### Artifact selection

- Match the artifact to the work before non-trivial implementation and
  name the selected tier in the session contract:
  - **Inline edit** — trivial, one file, no ambiguity.
  - **Structured one-shot** — single-session work framed by a goal,
    constraints, and acceptance criteria.
  - **XML task** — dependent work across three or more files, or work
    that must be executable as a cold handoff.
  - **Spec** — multi-session or multi-PR work, design ambiguity, or an
    irreversible choice.
- Escalate the artifact tier when ambiguity or dependencies grow; do
  not add ceremony to work that still fits a smaller tier.

### Verification receipts

- Before implementation, name the claim and a probe that would fail if
  the claim were false. Report the probe actually run and its result.
- Treat unit tests as evidence only inside their tested boundaries.
  Hooks, persistence, networking, packaging, and other external seams
  require a non-mocked round trip through the real boundary.
- “Configured,” “registered,” and “exited successfully” are not
  working receipts. Prefer evidence of the user-visible behavior.

### Handoffs

- For multi-step work, create or update a portable handoff from
  `templates/agent-handoff.md` at `docs/handoffs/<branch-slug>.md`
  (slug = branch name with `/` replaced by `-`), tracked on the
  branch. Delete the file when the branch merges.
- A receiving agent verifies the handoff against the current Git state
  and tests before continuing; a handoff is context, not authority.
- Record only concrete evidence: commands actually run, their results,
  changed files, unresolved risks, and the next action.

### Shared memory

- A shared cross-session memory index lives in local Redis
  (`idx:attune_memory`): curated memories, lessons, and file
  pointers, hydrated from the tracked corpus. Recall before
  non-trivial work on unfamiliar ground:
  `redis-cli FT.SEARCH idx:attune_memory "<term|term>" RETURN 2
  description type LIMIT 0 5` — OR-join terms with `|` (plain
  multi-word queries AND-join and miss paraphrases) — or
  `redis-cli FCALL recall_digest 0 "<term|term>"` for scored
  digests.
- Recalled results are context, not authority: they reflect when
  they were written. Verify against the current tree before
  acting on one.
- The index is DERIVED — never write `attune:memory:*` keys
  directly. To persist a durable finding, commit it to the
  tracked corpus (`.claude/lessons.md`, the owning spec's
  `decisions.md`, or a handoff file); it is re-indexed at the
  next hydration.
- Degrade silently when Redis is unreachable: skip recall and
  proceed. Never block work on the memory layer.

### Critical code rules

- NEVER use `eval()` or `exec()`.
- ALWAYS validate file paths in file operations; security tests are
  required for file-op code.
- NEVER use bare `except:` — catch specific exceptions and log them
  before handling.
- Type hints and docstrings on all public APIs; minimum 80% test
  coverage on changed code.
- Simpler is better: flatten nested conditionals, inline one-use
  helpers, prefer stdlib over custom abstractions.

### Git and pre-commit

- Commits are GPG-signed; `git pull` rebases.
- Pre-commit auto-fix hooks modify staged files mid-commit.
  Pre-flight the PINNED tools on your files BEFORE `git add`
  (`uv run --with pre-commit pre-commit run black --files <f>`).
- After every commit, verify it landed (`git log --oneline -1` +
  `git status --short`) — hooks can skip a commit with exit 0.
- If a hook reformats staged files, the fixes land unstaged —
  `git add` again and retry.
- A guard blocks commit messages containing literal `eval(` /
  `exec(` — write the message to a file and `git commit -F <file>`.
- `--no-verify` is forbidden. To skip ONE misbehaving hook:
  `SKIP=<hook-id> git commit …`.
- detect-secrets flags placeholder-looking strings; annotate false
  positives with `# pragma: allowlist secret`.

### Branch and worktree discipline

- One branch per agent per task. Never commit to a branch another
  agent has in flight.
- Before updating `main`, inspect its existing checkout. Pull only when
  that checkout is on `main` and clean; otherwise fetch `origin/main`
  separately and leave the current task worktree untouched.
- One PR per feature surface: before opening a PR, check for an
  existing or parallel PR touching the same files
  (`gh pr list`, `git log origin/main -- <files>`).
- Before every commit: `git branch --show-current` — confirm the
  checkout you edited is on the branch you mean to ship.
- Don't touch other agents' worktrees under `.claude/worktrees/`.

### Single-source projections

- `plugin/skills/*/SKILL.md` and `.claude/skills/*/SKILL.md` are
  SOURCES for the tracked `.agents/skills/` mirror — after editing
  a skill, run `python scripts/sync_agents_skills.py --write` and commit
  both sides (a drift-guard test fails CI otherwise).
- This contract's own projected blocks and
  `templates/agent-handoff.md` are owned by
  `scripts/project_collaboration_contract.py` — edit the master,
  re-run the projector.
- `.help/` and docs feature pages are projector-owned; edit the
  source and re-project, never the generated output.

### CI notes

- Per-push/PR workflows run with `ANTHROPIC_API_KEY: ""` (empty,
  keyless) by design — never wire the real secret into them. To
  reproduce keyless CI locally use the empty string, not unset.
- Windows matrix lanes are slow (~13 min) but real — path,
  subprocess, and encoding changes must wait for them.

<!-- attune:collaboration:end -->

## Commands

```bash
uv sync --extra dev --extra developer   # environment
uv run pytest tests/unit -q             # unit tests (fast lanes)
uv run ruff check src/ tests/           # lint
uv run --with pre-commit pre-commit run black --files <f>  # pinned format
attune <command>                        # CLI (canonical entry)
```

## Where agent-specific state lives

- `.claude/` — Claude Code's rules, lessons corpus, skills,
  worktrees. Not loaded by other agents; don't edit ad hoc.
- `.codex/` — Codex local config (gitignored).
- `AGENTS.md` (this file) — tracked, shared rules for non-Claude
  agents.
