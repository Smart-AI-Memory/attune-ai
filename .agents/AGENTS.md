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

### Principles

Every principle below names its enforcer — the ratchet, gate, hook,
or drift-guard test that makes it true without anyone remembering
it. A principle marked **aspirational** has no mechanical enforcer
yet: treat it as binding discipline, and treat adding its enforcer
as pickable work.

1. **The receipt beats the promise.** "Configured", "registered",
   and "exited 0" are claims; evidence of the user-visible behavior
   is the receipt. Delegated lanes declare their receipt type at
   launch and the lead re-runs receipts centrally.
   *Enforcer: **aspirational** (ruled discipline —
   `.claude/rules/attune/decision-routine.md` delegation receipts
   + this contract's Verification receipts section; no mechanical
   gate).*

2. **The code is the contract; spec text is a hypothesis.** Before
   executing any spec-named scope, grep the code for the property
   the phase targets and execute against THAT set.
   *Enforcer: **aspirational** (lessons-core rule; no gate can
   check intent — partially backstopped by drift guards below).*

3. **One source, projected — never hand-edited twins.** Skills,
   the collaboration contract, help pages, and docs feature pages
   are projections; edit the master and re-project.
   *Enforcers: `tests/unit/plugins/test_sync_agents_skills.py`
   (skills mirror), `tests/unit/scripts/
   test_project_collaboration_contract.py` (contract blocks),
   `tests/unit/lessons/test_core_mirror.py` (lessons core),
   `tests/unit/authoring/test_projection_drift.py` (authored
   projections) — all fail CI on drift.*

4. **Dangerous constructs are blocked, not discouraged.** No
   `eval`/`exec`, no unvalidated file paths, no bare `except`.
   *Enforcers: `src/attune/hooks/scripts/security_guard.py`
   (PreToolUse block on eval/exec), pre-commit detect-secrets,
   `tests/unit/gates/test_path_validation_gate.py` (AST scan —
   modules with write-capable file ops must reference a
   path-validation helper or hold an allowlist entry; seeded
   2026-07-29 with 35 vetted modules, ratchets shrink-only).*

5. **Coverage is a floor, not a goal.** Changed code carries
   ≥80% coverage; the local bar is 85%.
   *Enforcers: `codecov.yml` project+patch gates (80%),
   `tests/unit/ci/test_workflow_yaml.py::
   test_coverage_threshold_is_at_least_80` (the threshold itself
   is drift-guarded).*

6. **CI spends attention, never money.** Per-push/PR workflows run
   keyless (`ANTHROPIC_API_KEY: ""`); the real secret lives only in
   allowlisted, manually-dispatched or budget-capped jobs.
   *Enforcers: `tests/unit/ci/test_ci_spend_guard.py` (secret refs
   allowlisted, non-allowlisted assignments must be `""`),
   `tests/unit/ci/test_workflow_yaml.py`
   (timeouts/pinning/concurrency).*

7. **A failed gatekeeper fails the gate.** A security auditor that
   errors or goes missing fails the Security gate — absence is not
   a pass.
   *Enforcer: sentinel semantics pinned by
   `tests/unit/agents/test_release_prep_team_orchestration.py`
   (chair-ruled 2026-07-29).*

8. **Docs may not cite fiction.** A doc that names a symbol which
   no longer imports fails CI.
   *Enforcers: `doc-import-audit` CI job +
   `tests/unit/test_generated_doc_import_drift.py`; wiring claims
   checked by the `wiring-audit` job.*

9. **Identity and brand drift are ratcheted.** Legacy identifiers
   and retired framing cannot re-enter the tree.
   *Enforcers: G5 brand-drift pre-commit gate +
   `tests/unit/gates/test_brand_drift.py`,
   `tests/unit/gates/test_claim_drift.py`.*

10. **Context is budgeted.** Always-loaded rule bodies fit a
    byte budget; everything else is JIT-recalled via the index.
    *Enforcer: `tests/unit/rules/test_rules_residency_budget.py`.*

11. **Seats advise; the chair promotes; the lead integrates.**
    Cross-provider seats are advisory, the integrating lead owns
    synthesis and central receipt re-runs below the chair, and only
    the chair promotes (R8).
    *Enforcer: **aspirational** (governance ruling, D8/D9 +
    R8 — carried by this contract's text on all provider surfaces;
    inherently procedural).*

12. **Memory is derived, never authored in the serving layer.**
    Durable findings land in the tracked corpus (lessons, spec
    decisions, handoffs); Redis indexes are hydrated projections.
    *Enforcer: **aspirational** (contract text; hydration
    overwrites hand-written keys on the next run, which is a
    ratchet-by-reconstruction, but nothing blocks the direct
    write).*

13. **Simpler is better.** Three clear lines beat one clever
    abstraction: flatten nested conditionals, inline one-use
    helpers, prefer stdlib over custom abstractions, and review
    every change for complexity it didn't need.
    *Enforcer: **aspirational** (ratified design philosophy,
    carried in every provider surface's instructions; simplicity
    is judged in review, not gated).*

14. **A handoff is context, not authority.** The receiving agent
    verifies a handoff against the current Git state and tests
    before continuing; the current worktree, Git state, and test
    results are the shared truth, never hidden chat context.
    *Enforcer: **aspirational** (contract text — Shared truth +
    Handoffs sections; inherently procedural, since the check IS
    the receiving agent's first action).*

15. **Degrade gracefully around the memory layer.** When Redis or
    the memory index is unreachable, skip recall and proceed —
    work is never blocked on the memory layer, and recalled
    results are context to verify, not authority.
    *Enforcers: `tests/unit/memory/test_session_stash.py` (backend
    resolution failure degrades to None, never raises),
    `tests/unit/test_mcp_memory_tools.py` (memory tools degrade
    gracefully when the layer is absent),
    `tests/unit/memory/test_session_hydrate_fail_open.py` (the
    SessionStart hydrate hook exits 0 with a skip notice when the
    backend is unreachable — machine-local by design: the hook is
    personal infra outside this repo, so the test runs the real
    script where `~/.attune/memory/` exists and skips elsewhere,
    including CI).*

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

### Lead programmer and delegation

- The project has a **lead programmer: Claude**, global by default.
  A per-feature lead may be set via the feature-lead-governance
  spec's mechanism; where one is set, it overrides the global
  default for that feature only (feature lead, not permanent model
  owner — its D1).
- The lead owns integration, synthesis, central receipt re-runs,
  and the final recommendation below the chair. Other seats work
  ADVISORY: their findings and drafts route through the lead, and
  they should expect the lead to integrate, amend, or decline with
  a recorded reason. Only the chair promotes (R8).
- **Single-provider fallback:** when the lead's provider is absent
  from a session, lead duties devolve to the CHAIR (integration and
  final recommendation), the active provider works
  advisory-to-the-chair, and receipt re-runs fall to whatever
  provider is present. The contract stays executable with one
  provider; the lead role resumes when its provider returns.
- **Receipt-declared delegation is binding for cross-provider
  lanes**: every delegated lane names its receipt type(s) at
  launch (suite / behavioral / live-fire / metric /
  evidence-chain), and the lead re-runs the receipts centrally
  before work reaches the chair. A seat's self-report is never
  the receipt.
- Delegated runs are recorded in the cross-review R5 dogfood
  ledger (`docs/specs/cross-review/receipts.md`). P1 FULL
  ACTIVATION was ruled at the D8 bar (chair, 2026-07-30, 11
  fully-triaged runs): the lead/delegation model is the standing
  operating mode, no longer pilot-scoped; per-feature leads are
  set via the feature-lead-governance spec's mechanism, and the
  ledger keeps accruing as the standing evidence surface.
- **The lead is reviewed too (D11, 2026-07-29):** a lead-authored
  diff touching a risk class — authored contract/spec/rule text
  (named explicit 2026-07-30 as the R5 ledger's highest-yield
  class), security, persistence, release, governance/enforcement
  surfaces (gates, guards, ledgers, this contract), external
  boundaries, or a disputed finding — requires a different-model
  review lane BEFORE the chair reads the recommendation; the chair
  may override in either direction.
  When the lead REJECTS a seat's finding, the ledger row carries
  the seat's claim verbatim plus the lead's reason
  (`tests/unit/gates/test_ledger_rejection_format.py` enforces the
  format). RULED (chair, 2026-07-30, at the D8 bar with 10
  fully-triaged runs): risk-triggered lanes are the PERMANENT
  default — the lane is not expanded to all lead diffs (5 clean
  lanes on well-tested code and release diffs showed cost without
  yield there). Yield stays measured in the R5 ledger; a future
  chair ruling can revisit either direction.

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
