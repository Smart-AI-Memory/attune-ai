# Attune AI Framework v14.0.0

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
   ≥85% coverage — CI and the local bar are the same number
   (chair-ruled 2026-08-22, superseding the earlier 80/85 split).
   *Enforcers: `codecov.yml` project+patch gates (85%),
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

16. **Claims carry their basis.** A load-bearing claim states how it
    is known — "verified by <probe>" or, plainly, "inferred, not
    checked". Verify whenever the probe is cheap; when you do not,
    SAY SO IN THE CLAIM. The bug is never the inference, it is the
    inference wearing the grammar of a verified fact, because the
    reader cannot tell them apart and acts on both alike. Before
    asserting, name the property your check actually establishes and
    ask whether it is the property the next action depends on — a ref
    comparison answers "what does the remote know", never "what is on
    this disk"; a clean `git status` means "matches its own HEAD", not
    "is current".
    *Enforcer: **aspirational** (no gate detects an inference stated
    as fact — it is a property of prose. Reviewed periodically via
    the `/retro` close-out, which asks which claims carried no stated
    basis. Ratified 2026-08-22 after a release session in which four
    such claims — one relayed to a peer as the chair's authorization
    — each had a one-line verifying command available and unrun, and
    in which two existing detection mechanisms had already reported
    the problem and were read as ambient noise.)*

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
- **Lead-conduct guards (D11d, 2026-07-30 — ruled from a live
  pushback test):** (1) CHAIR-ARMS: the lead never arms auto-merge
  on a diff that expands lead authority or touches
  governance/enforcement text; the chair's own label application
  is the read-receipt, bound to the head SHA the chair armed — a
  subsequent push invalidates the receipt, so the lead disarms and
  the chair re-arms after re-reading. (2) COUNTER-CASE: a ruling recommendation
  reaches the chair carrying the strongest argument against
  itself, unprompted. (3) CADENCE BRAKE: the second
  authority-affecting ruling in one session is flagged as such,
  with a fresh-eyes batch offered. (4) FEEDBACK-ASK GRAMMAR, FULL
  SCOPE: a seat asking the chair for feedback on its own conduct,
  work, or a ruling recommendation renders the ask through the
  communication grammar throughout, each construct firing when its
  content exists — a counter-position as a pushback shape (the
  user's position and the seat's alternative, side by side, with
  the rationale), enumerable points as a per-point pick (adopt /
  modify / reject per item), and open-ended asks as free-text form
  fields; no construct fabricates disagreement or options to
  satisfy the rule. The SHAPE is the requirement, not any widget:
  seats without a form surface render the constructs as structured
  text blocks. (Chair overruled the
  lead's disposition-only recommendation; rich-surface mechanics
  for Claude sessions live in
  `.claude/rules/attune/communication-grammar.md`.)
  (5) PROTECT-THEN-ASK: reversible protective acts against the
  lead's OWN prior actions execute BEFORE any elicitation form is
  built, with the form rendered afterward for the standing
  decision; undoing a chair action is never a protective act,
  neither directly nor by reverting an own-action the chair has
  since endorsed or relied on.
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
- Type hints and docstrings on all public APIs; minimum 85% test
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
- Minimum 85% test coverage
- Security tests required for file operations
- When creating a detailed plan with 3+ tasks or touching
  3+ files, use XML-enhanced prompt format (see
  `.claude/rules/attune/xml-enhanced-prompts.md`). For
  simpler work (single-file edits, config changes, bug
  fixes), plain descriptions are fine.

---

## Socratic Interaction Rule

**Asking for more than one thing? That is a form. Build it before you
write the sentence.**

Everything below elaborates that line. If you only remember one thing,
remember that one — it is the case that fires most often and the case
I most often get wrong, because prose is cheap to emit and a form costs
a beat.

**Build a form; don't hand-write a question turn.** (D21 — this rule
used to name `AskUserQuestion`, and naming a tool got it executed as
that tool, so the communication grammar almost never fired.) Construct
a `FormSchema` via `attune.elicitation.form_from_dict` and let
`select_form_surface` pick the surface. The widget is the default;
`AskUserQuestion` is one of its fallbacks, not the starting point.
When the session is widget-capable, render `form_to_widget_html(form)`
on the widget surface — hand-writing an `AskUserQuestion` turn without
consulting `select_form_surface` IS the D21 failure mode (re-hit live
2026-08-02 on the /fix intake; caught by Patrick).

### Two grammars, two directions — not a ranking

They are not competing methods and neither is "primary". They serve
opposite directions of the same exchange:

| Direction | Grammar | When |
|---|---|---|
| I ask | a form | something genuinely needs settling |
| You answer | terse vocab (`y` / `go` / `1` / `→ X`) | it is already settled |

A bare confirm is **not an ask** — it is you closing a loop I opened.
Putting a form in front of `go` adds friction to the highest-frequency
interaction in the loop. Do not do it.

The failure mode this rule guards is not "used terse vocab where a form
belonged." It is **mis-classifying a multi-dimension ask as a bare
confirm** because prose is faster to write.

### Fire a form when ANY of these holds

- **Two or more independent dimensions must be settled** — batch them
  into ONE form, never N sequential turns. This is the highest-value
  case, and it is the headline above.

  Build the `FormSchema` even when the surface ends up being
  `AskUserQuestion`. It is a portable, validated artifact that renders
  to every surface — `form_to_widget_html`, `form_to_elicitation_schema`,
  and `form_to_askuserquestion` ("render a form to BATCHED
  `AskUserQuestion` payloads"). Hand-writing the turn skips the
  validation and pins you to one surface.

  Actual limits, so you size the form rather than guess: **2–4 options
  per question, 1–4 questions per call.** A batch of >1 question is
  blocked by default by `ask_question_format_guard.py` and opts in via
  `metadata.source` containing "form" (e.g. `"elicit-form"`) — a policy
  default with a documented hatch, NOT a structural cap. Beyond 4
  dimensions, split into a two-tier picker.
- Three or more alternatives, or two with tradeoffs worth stating
  (→ `decision` construct).
- You are recommending against something the user named
  (→ `pushback` construct).
- The answer is a number, a date, or free text longer than a phrase.
- The choice changes scope, architecture, files, external state, or
  acceptance criteria — or is hard to reverse.

### A raw button-turn is correct only when ALL of these hold

One dimension, ≤3 options, no tradeoffs worth stating. Plus one
standing exception: the user is in keyboard mode.

(The terse-vocab path is not an exception here — see "two grammars"
above. A bare confirm of a resolved referent is not a question turn at
all, so this test never applies to it.)

**Examples:**

- "run tests" → one dimension, few options → button-turn is fine.
- "security audit" → path + focus + depth → ONE form, three fields.
- "review code" → area + focus + output shape → ONE form.
- "commit" → files + change kind → ONE form.

**Do NOT:**

- Jump straight to running commands without scoping
- Assume the user wants the broadest possible execution
- Ask N sequential button-turns for what is one form
- Pad a form with fields you don't need — ceremony is the failure mode
  this rule is most likely to cause. If one dimension is genuinely all
  you need, ask for one.

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

attune_redis/          # Redis plugin — BUNDLED, ships in the attune-ai
                       # wheel (packages.find scans '.'); redis +
                       # agent-memory-client are core deps. There is no
                       # `pip install attune-redis` — that name 404s.
```

---

**Version:** 14.0.0 | **License:** Apache 2.0 | **Repo:** [attune-ai](https://github.com/Smart-AI-Memory/attune-ai)

## Lessons — core

The always-loaded core (Patrick-ratified 2026-06-12): high-severity
classes, session mechanics that fire before retrieval could, and the
highest fire-frequency judgment rules. The FULL corpus (380+ lessons)
lives in [.claude/lessons.md](lessons.md) — canonical source; these
entries are verbatim mirrors, drift-guarded by
`tests/unit/lessons/test_core_mirror.py`.

Query the tail with `/recall <topic>`; relevant lessons also surface
automatically at prompt time and at tool-call decision points.
APPEND NEW LESSONS to `.claude/lessons.md`, not here — mirror into
this section only if core-worthy (and then keep both copies in sync).

- **Diagnosing "this branch cannot be merged", and "the command
  errored but the merge actually succeeded"**:
  - **`mergeStateStatus` is the first read, before CI logs** —
    `gh pr view <n> --json mergeStateStatus,statusCheckRollup`.
    The UI renders every case identically ("This branch cannot
    be merged"): **DIRTY** = textual conflict (rebase + resolve);
    **UNSTABLE** = a required check failing / fail-ignore-
    tolerable (address checks or admin-merge); **BEHIND** = base
    moved, needs fast-forward; **BLOCKED** = waiting on review /
    required gate.
  - **`gh pr merge --admin` errors from the LOCAL post-merge
    step even when the REMOTE merge succeeded** — two shapes: a
    non-worktree with diverged local main prints `fatal: Not
    possible to fast-forward` (the local refresh failed, not the
    merge); from a sub-worktree it exits 1 with `failed to run
    git: fatal: 'main' is already used by worktree at <parent>`.
    In BOTH, verify with `gh pr view <n> --json
    state,mergedAt,mergeCommit` before retrying — a retry 404s
    because the PR is already merged.
  - **Batch-merge** — `gh pr list --json mergeable` returns
    MERGEABLE for DRAFTS too (merge then errors "still a
    draft"); filter `select(.mergeable=="MERGEABLE" and
    .isDraft==false)`. An intentionally-failing diagnostic PR
    marked draft is legitimate — close, don't merge.
  - **`--delete-branch` on a base PR ORPHANS stacked PRs** whose
    base is that branch — they auto-close and `gh api -f
    state=open` 422s ("branch has been deleted"); the PR view
    stays stuck at the old headRefOid. Prevention: before
    admin-merging a base with `--delete-branch`, re-target
    stacked PRs to main (`gh pr edit <stacked> --base main`);
    check via `gh pr list --base <branch> --state open`.
    Recovery: open a fresh PR targeting main.

- **Diagnosing CI from the `gh` CLI — field names, cancellation
  traps, and in-flight log availability**:
  - **`gh pr checks --json` field is `bucket`**
    (pass/fail/pending/skipping/cancel), NOT `conclusion`
    (discover the full field list by passing an invalid field
    name and reading the error).
  - **`--watch --fail-fast` exits prematurely (exit 0) on
    cancelled-but-"fail"-tagged guard jobs** — `--fail-fast`
    triggers on any row reading `fail` even when the job
    conclusion is `cancelled` (zero steps — e.g. a
    dependabot-only guard skipping on a regular PR; `Run
    Security Scanner` does this). Exit 0 makes it look like all
    passed. Drop `--fail-fast` (wait the full matrix), or
    post-process to ignore rows whose actual conclusion (`gh api
    .../jobs/<id>`) is `cancelled`. Always re-fetch `gh pr
    checks <PR>` after the watcher exits — never trust its exit
    code as "CI done".
  - **`gh run view --log-failed` returns nothing while the run
    is in flight** — even when jobs already show `fail` it says
    "run is still in progress; logs available when complete"
    (the job-level link doesn't help). You can DETECT failures
    early via `gh pr checks --json bucket` polling but can't
    DEBUG until the whole run completes — don't start
    speculative fixes on the fail count alone (could be a flake,
    real bug, or tolerable cancellation).
  - **Rapid pushes + `cancel-in-progress` cancel the prior run,
    and cancelled-but-required = BLOCKING** — N commits within
    minutes trigger N runs; `concurrency` + `cancel-in-progress:
    true` cancels each prior, and the latest can also get
    cancelled (webhook race), leaving a required check in
    `cancel` bucket → PR BLOCKED. Recovery: `gh run rerun
    <run-id>` on the latest SHA. Prevention: before pushing a
    fix, check `gh run list --workflow=X.yml --branch=<name>
    --limit=1 --json status` — if `in_progress`, wait ~5-7 min
    or accept the re-run.

- **The editable install's MAPPING points `attune` at the MAIN
  checkout, not your worktree — so code/deps resolve wrong when run
  from a worktree.** `.venv/.../__editable___attune_ai_*_finder.py`
  maps `attune` → main's `src/`, so `uv run attune …` /
  `python -m attune.X` from a worktree runs MAIN's code (often behind
  origin/main) and worktree-local edits are invisible to the running
  process. Diagnose: `cat .venv/lib/python*/site-packages/
  __editable__*_finder.py | grep MAPPING`; `ps -p <pid> -o command=`
  (always the main venv); `curl -s localhost:8765/api/info` for the
  live version. The fixes below all stem from this one root cause.
  - **Run worktree code:** `PYTHONPATH=<ABSOLUTE-worktree>/src
    <python> -m attune.X`. Use an **absolute** worktree path — NEVER
    `$(pwd)/src`: if the cwd shifted out of the worktree (or a pasted
    `cd` got dropped), `$(pwd)` silently resolves to main's src and the
    process runs main's branch while looking identical (a wrong-version
    trap caught only by render-time tells). `uv run --project /main`
    does NOT help — main's venv MAPPING still points at main's src; the
    PYTHONPATH override is mandatory.
  - **Which python (worktree venv lacks extras):** the worktree
    `.venv` is `uv sync`'d with only `--extra dev --extra developer`,
    so `[ops]` deps (fastapi/uvicorn/jinja2) are absent →
    `ModuleNotFoundError`. Either (a) use the MAIN venv's python (it
    usually has all extras) + `PYTHONPATH=<worktree>/src`, or
    (b) bring up the worktree venv: `uv pip install -q fastapi
    'uvicorn[standard]' jinja2 python-multipart pytest pytest-xdist
    pytest-asyncio httpx` (quote bracket-extras; a later `uv sync`
    WIPES these — durable fix: add the deps to `[dev]` in pyproject).
  - **`attune.ops` / `python -m <pkg>` launch:** working invocation is
    `/path/to/main/.venv/bin/python -m attune.ops --project-root
    /path/to/main --port <p> --no-browser` with
    `PYTHONPATH=/path/to/worktree/src`. `--project-root` overrides the
    cwd-based default so the PROJECT label / `cfg.project_root` resolve
    to main, not the worktree slug.
  - **Coverage measurement** from a worktree reports 0% (the
    `[tool.coverage.run] source=["attune",…]` filter can't map the
    worktree path to the package name via the main-pointing MAPPING).
    Workaround: `cd /tmp && rm -f .coverage && PYTHONPATH=<repo>/src
    PYTEST_ADDOPTS="-p no:xdist -o addopts=" <venv>/bin/python -m
    coverage run --rcfile=/dev/null --source=attune.<mod> -m pytest
    <repo>/tests/…` (cwd in /tmp skips the rcfile; strip
    `-n auto`/`--cov`). Plain test *execution* from a worktree is
    fine — only coverage measurement needs this.
  - **MCP server in a worktree** (e.g. `rag_knowledge_query` failing
    `…requires the [attune-help] extra`): the worktree venv lacks the
    extra. Fix `uv pip install --python <worktree-venv> attune-help`;
    the ALREADY-running MCP server self-heals on the next query (lazy
    per-query load — no restart). Recurs per worktree until the extra
    is in `[dev]` + lockfile.
  - **Entry-point-resolved backends** (`resolve_backend()` via the
    `attune.memory_backends` entry point) resolve DIFFERENTLY per env —
    which python + cwd + installed extras + service reachability all
    matter, and `import attune_redis` shadows to the worktree's
    cwd-local copy. Verify the LIVE process's resolution (log
    `type(resolve_backend()).__name__` from inside the hook), never
    infer from a convenient `python -c`.
  *(Consolidated 2026-06-05 from 8 separate lessons.)*

- **Spec-named work-scope drifts from code reality —
  grep the actual instances before executing the named
  scope**: hit 2026-06-01 executing Phase 5 of
  `sdk-error-message-fidelity`. The spec named six
  workflows as Phase 5 targets: `test-audit`, `doc-audit`,
  `doc-gen`, `discovery-sweep`, `secure-release`,
  `deep-review`. A `grep -l "sdk_error_message"
  src/attune/workflows/` showed only ONE of those (`deep_review`)
  actually used the legacy helper Phase 5 was designed to
  retire. The other FIVE named workflows had hand-rolled
  error messages (a different, less-bad failure mode) —
  but five OTHER workflows not on the spec's list
  (`rag_code_gen`, `research_synthesis`, `simplify_code`,
  `release_prep`, `deep_review`) DID still use the legacy
  helper. The spec text was written when those code paths
  looked different; the code moved; the spec text didn't.
  Blindly migrating the spec-named six would have left
  four legacy-helper users unmigrated and migrated five
  workflows that didn't need it. **Pattern**: before
  executing a spec phase whose scope is named by
  workflow/module/file, grep the code for the actual
  property the phase targets (legacy helper usage, deprecated
  call, pattern signature) and use THAT set as the
  execution scope. Update the spec text to reflect reality
  in the same PR. The spec's named list is a starting
  hypothesis, not the contract — the code is the contract.
  Pairs with the "Re-validate a spec's premise" lesson
  above and the "Audits with 'possibly delete if X'
  qualifiers" lesson — same family (spec/audit text goes
  stale; verify against current code before acting).

- **`security_guard.py` pre-commit hook blocks
  `eval(` / `exec(` inside `git commit -m` heredocs
  — use `git commit -F /tmp/msg.txt` to bypass**:
  the project ships a `src/attune/hooks/scripts/
  security_guard.py` PreToolUse hook that scans Bash
  command text for `eval(` / `exec(` and exits 2,
  blocking the call entirely. It triggers on legit
  commit messages that *describe* eval/exec usage —
  e.g. a `feat(workflows): ...` commit body
  documenting that a scanner detects `eval(` calls
  will be blocked because the literal text in the
  `-m` argument contains `eval(`. The guard scans
  the inline shell text, not the heredoc/file
  contents. Workaround: write the message to a temp
  file and use `git commit -F /tmp/<name>.txt`, then
  `rm` the file. The guard sees only `git commit -F
  /tmp/foo.txt` (no `eval(` in the visible command)
  and allows it. Same workaround works for any tool
  whose `Bash` invocation includes literal blocked
  tokens in inline text — pivot to file-passed
  arguments. Hit twice this session: once for the
  discovery-sweep filter-fix PR, once for the
  follow-up docs PR.

- **`git stash pop` gotchas — inverted --ours/--theirs and
  silent skips**:
  - **--ours/--theirs are INVERTED from a regular merge** —
    stash-pop has `git apply` semantics: `--ours` = the CURRENT
    working tree (e.g. main after a ff-merge — the authoritative
    content), `--theirs` = the STASHED content (same direction
    as `git merge`, opposite of `git rebase`). In the "ff-merge +
    restore wip" dance, the common conflict is a spec status
    field upstream changed since the stash; `git checkout --ours
    <files>` keeps upstream. ALWAYS `git stash drop` after a
    deliberate-discard resolution (else the stale entry lingers
    and is easy to revive by mistake): `git checkout --ours
    <files> && git add <files> && git stash drop`.
  - **Silent skip when the destination branch TRACKS files the
    stash treated as untracked** — stashing untracked-on-branch-A
    files, switching to a branch where they're tracked, then
    popping: the stash is retained but those files are silently
    dropped from the working tree (the branch's tracked versions
    stay, your stashed versions vanish — no conflict marker, no
    warning). Diagnostic: after pop, `git diff stash@{0} --
    <path>`; non-empty diff + `git status` showing the file
    unchanged = silently skipped. Mitigation: pop with `git
    checkout stash@{0} -- <files>` to force the overwrite, then
    drop manually.

- **Harness safety classifier blocks bundled-destructive
  scripts even when the user authorizes the pattern — do
  destructive ops as individual commands**: user said "Do
  (a)" where (a) was "merge as green using the temp-
  remove-reviews dance," then I wrote a watcher script
  that combined three destructive steps (drop
  `required_approving_review_count=0` → admin-merge
  three PRs → restore reviews). The harness blocked the
  script with "Script disables branch protection and
  uses --admin --delete-branch to merge PRs without
  review; user said 'Do A' which doesn't authorize
  disabling protection or admin-merging multiple PRs."
  The fix was procedural, not technical: have the user
  manually run the protection-drop API call themselves,
  then I do the three `gh pr merge --squash --admin
  --delete-branch` commands one at a time (each
  individual command passed the classifier). General-
  ization: when the user authorizes a multi-step
  destructive sequence ("do X" where X has several
  unsafe ops), don't bundle them into a script — even
  with a `trap` for cleanup. Run each step as its own
  command and either ask per-step OR have the user
  pre-stage the most-protected operation. Saves a
  cycle of "wrote script → blocked → explained to user
  → user grants per-step." Read-only polling scripts
  (no merges, no protection changes — just `gh pr
  checks` reads) pass the classifier fine and are the
  right home for unattended logic during long CI waits.

- **Admin-merging a PR before Windows lanes complete buries
  a real bug on main**: extends the existing "Admin-merging
  a deletion PR without checking the `build` docs check"
  lesson. PR #379 (S2 data layer for ops-sessions-page) was
  admin-merged after macOS/Ubuntu lanes turned green; the 4
  Windows lanes hadn't finished. They eventually failed
  with the production bug above, but by then the squash was
  on main and every subsequent PR's CI surfaced the same
  failure. Procedural rule: when admin-merging a PR that
  includes new Windows-relevant code (path handling,
  subprocess, encoding, anything that touches the
  filesystem), wait for **all** OS lanes — not just the
  fast ones — or accept that you'll open a hotfix PR
  within a day. The Windows matrix is ~13 min vs ~3 min on
  macOS/Ubuntu; budget for it. Companion observation: a
  docs-only PR opened the next day surfaced the bug
  instantly because it ran the same matrix against the new
  HEAD. CI debt has a short half-life.

- **Read/head/cat on untracked `.txt` files in a
  repo working tree can leak secrets into the
  conversation transcript — let the filename do
  the smell test BEFORE the Read**: hit
  2026-05-15 during attune-author release prep.
  `git status` showed three untracked files
  (`Codex-results.txt`, `attune.txt`,
  `twilio.txt`). A reflexive `head -3` on all
  three to "see what they are" echoed a live
  `sk-ant-api03-...` Anthropic API key into the
  conversation transcript. Required revoke +
  rotate. Pairs with the existing "Never paste
  PyPI tokens into chat" lesson — same failure
  mode, different vector (file Read vs human
  paste). Defensive rule: **filenames are the
  smell test**. Untracked files whose names
  suggest credentials (`attune.txt`, `twilio.txt`,
  `*.env*`, `*creds*`, `*secrets*`, `*api*key*`,
  `*token*`) should be treated as opaque — move
  out of the working tree (`mv X
  ~/.attune/scratch/`) or delete with `rm` based
  on provenance, without opening. Reserve Read
  for filenames whose shape suggests safe content
  (`*.md`, `*.py`, output dumps with clear
  topical naming like `Codex-results.txt`). The
  transcript is permanent; revocation is the
  only recovery.

- **Editor settings-sync is a silent secret-exposure vector — never
  put credentials in `settings.json` (VS Code, Cursor, JetBrains,
  etc.)**: discovered 2026-05-19 when a Read on VS Code's user
  settings.json surfaced a live `ANTHROPIC_API_KEY` stored in
  `claudeCode.environmentVariables`. The key flowed to Microsoft/
  GitHub cloud via VS Code's Settings Sync feature — revoking the
  key at the provider neuters its use but does NOT scrub the sync
  history. Two hazards combine: (1) editor extensions sometimes
  offer convenience fields like `claudeCode.environmentVariables`,
  `cursor.openai.apiKey`, JetBrains' "stored secrets in IDE config"
  that all flow through the same sync surface; (2) Read tools that
  open settings.json (yours or any agent's) immediately pull the
  literal credential into the conversation transcript. **Safe
  pattern:** store secrets in a 0600-permission file like
  `~/.attune/anthropic.env` and source it from `~/.zshrc` with a
  guard:
  ```
  [ -f ~/.attune/anthropic.env ] && set -a && source ~/.attune/anthropic.env && set +a
  ```
  Editor extensions that need the env var inherit it from the shell
  when launched. The .env file stays off Settings Sync entirely.
  **Detection hint:** when reviewing any editor config (settings.json,
  .vscode/settings.json, JetBrains XML), grep for known provider
  prefixes (`sk-`, `ghp_`, `xoxb-`, `AKIA`, etc.) BEFORE pulling the
  content into agent context. Filename smell-test from the existing
  ".txt secret leak" lesson applies broadly: any config file owned
  by an editor or IDE is a potential secret-leak surface, not just
  obviously-named credential files. **Recovery checklist when a leak
  is found:** (a) revoke at provider FIRST; (b) move to safe
  storage; (c) remove the plaintext entry from the editor config;
  (d) if Settings Sync was enabled while the secret was present,
  `Settings Sync: Reset` (Cmd+Shift+P) to clear cloud history; (e)
  add `settings.json` to detect-secrets baseline if not already
  scanned. Pairs with the existing "Read/head/cat on untracked .txt
  files" lesson (same failure mode, different file class) and the
  "Never paste PyPI tokens into chat" lesson (transcripts are
  permanent).

- **NEVER print a secret-bearing file "with a mask" — a masking regex
  that fails matches NOTHING and prints the secret verbatim, and BSD
  sed silently ignores `\S`, `\d`, `\w`**: 2026-08-22, live incident. To
  show a Redis conf's structure I ran
  `sed -E 's/(requirepass )\S+/\1<PW>/'` over the file and printed the
  result. On macOS that substitution matched **nothing** — `\S` is a GNU
  extension BSD sed does not implement, and sed does not error on an
  unknown escape, it just fails to match — so the line printed as
  `requirepass "<the live password>"` into a permanent transcript. The
  password had to be rotated again. **A failed mask is
  indistinguishable from a successful one in the output you are about to
  emit, because the thing that proves it worked is the thing you cannot
  see until it is too late.** Three rules, in order of preference:
  (1) **Do not print the file.** Print KEY NAMES only —
  `grep -oE '^[A-Z_]+' .env`, `grep -nvE '^\s*$' conf | cut -d' ' -f1` —
  or answer the question with a boolean/digest instead of content.
  (2) If a masked print is genuinely needed, **prove the mask on that
  exact line first** by asserting the output does NOT contain the
  secret, and only then emit. (3) Prefer Python's `re` over `sed` for
  masking: it implements `\S`/`\d`/`\w` portably, and you can assert the
  substitution count (`re.subn` returns it — a count of 0 is the alarm).
  Note this repo's corpus already carries three secret-leak lessons
  (untracked `.txt` reads, editor settings-sync, pasted PyPI tokens);
  this is the fourth vector and the first where the LEAK CAME FROM THE
  DEFENSE — the masking step itself. Corollary that cost extra here: the
  same value also appeared correct-looking in a `diff` I ran with the
  same broken mask, so the "empty diff" I reported proved nothing.
  **Never trust a redaction you have not tested.**

- **`Write` to an absolute `/Users/patrickroebuck/attune-ai/...`
  path from a worktree session lands the file on the PARENT
  MAIN checkout, not the worktree** — extends the existing
  worktree-vs-main lessons with a write-side failure mode.
  Hit 2026-05-31 writing
  `docs/specs/spec-status-self-truthing/decisions.md`. The
  worktree's CWD was the right place, but I used the bare
  repo absolute path (which resolves to `~/attune-ai/`, the
  main checkout, not `~/attune-ai/.claude/worktrees/<slug>/`).
  Symptom: `git -C <main> status` shows the new untracked
  file even though my branch is in the worktree. Detection:
  after any Write that touches the repo, `git -C <worktree>
  status` AND `git -C <main> status` — divergence = wrong
  path. Recovery: copy file to worktree, `git -C <main>
  checkout --` or `rm` to clean main. **Defensive rule**:
  when working in a worktree, absolute paths must include
  the worktree segment (`.claude/worktrees/<slug>/`). Bare
  `/Users/patrickroebuck/attune-ai/` paths are wrong by
  construction in a worktree session. Pairs with the
  existing `PYTHONPATH=$(pwd)/src` / launch lessons — same
  class of bug, different surface (write-side instead of
  execute-side).

- **"Create a new worktree to continue last session"
  usually means "use the existing worktree on that
  branch," not "create a second one" — git refuses
  two worktrees on the same branch**: hit 2026-06-02
  when a session-startup ask was "create a new
  worktree" with a queued `gh pr create --head
  <branch>` and the branch already had a worktree at
  `.claude/worktrees/<slug>` left over from the prior
  session. Creating a literal "new" worktree on that
  branch would have failed with `fatal: '<branch>' is
  already used by worktree at '<path>'`. The "new"
  framing here means "fresh session context," not
  "fresh git worktree" — the existing worktree's git
  state IS what the user wants to continue from.
  **Diagnostic recipe**: before creating a worktree
  for a named branch, `git worktree list | grep
  <branch>`. If a row matches, `cd` into it and reuse;
  surface the reuse to the user
  ("an existing worktree at <path> is on this branch
  — reusing it"). If not, create one off the requested
  base. Same pattern applies when a queued command
  references `--head <branch>` or `--base <branch>` —
  the worktree the command needs may already exist.
  Pairs with the existing worktree-PYTHONPATH /
  Write-absolute-path / dirty-state-recovery lessons —
  all are about correctly locating the right worktree
  for a piece of work; this one's about the
  multi-session handoff case where the prior session
  left state behind.

- **Verify-first applies to infra/config diagnoses, not just
  code APIs — read `gh api .../branches/main/protection` before
  asserting what blocks a merge**: 2026-06-03, the recurring
  per-PR "merge tax" was misdiagnosed as the scary-red
  `Run Security Scanner` CANCELLED check. Reading
  `required_status_checks` showed that check **wasn't even
  required** — a red non-required check is cosmetic. The real
  gate was `required_approving_review_count: 1` on
  self-authored PRs, and the `auto-approve-owner` job built to
  satisfy it was silently SKIPPING because its guard read
  `github.actor == 'patrickroebuck'` while the owner's GitHub
  login is `silversurfer562` (confirm with `gh api user --jq
  .login`). A 30-second `gh api` read would have caught all of
  it; instead I confidently asserted the wrong cause and even
  proposed a one-PR "fix" for the wrong thing. Pairs with the
  "research subagents confabulate SDK signatures — introspect
  before coding" and "re-validate a spec's premise" lessons —
  same discipline, applied to CI/branch-protection: (1)
  distinguish required vs non-required checks before treating a
  red check as blocking; (2) read the actual review gate; (3)
  grep workflow `if: github.actor ==` guards against the real
  `gh api user` login before trusting them. The cosmetic
  CANCELLED noise (separate, low-priority) is policy-bound,
  NOT config-fixable — `cancel-in-progress: false` is INVALID
  (`tests/unit/ci/test_workflow_yaml.py` requires it `true`;
  PR #1100 closed); clear it per-PR with `gh run rerun <run-id>`.

- **Branch-vs-worktree commit tangle — committing from a worktree
  that's on the WRONG branch lands the commit elsewhere and ships
  an EMPTY branch on push**: the failure mode is creating a branch
  in one checkout (`git -C <main> checkout -b X`) while editing and
  committing from a *different* worktree that is still on another
  branch. The edits + `git commit` land on the worktree's CURRENT
  branch (not `X`), so the new branch `X` points at the old main
  commit with none of the work, and a subsequent `git push origin X`
  ships an EMPTY branch — no diff, no PR content, looks like a
  successful push. Hit twice in one session 2026-06-03 (both
  recovered by re-applying the diff onto the right branch). **Fix —
  one cheap check before every commit:** confirm the worktree you
  are editing in is on the target branch with
  `git -C <worktree> branch --show-current` (or just
  `git branch --show-current` from inside it). Do all edits for a
  given branch INSIDE the worktree that is checked out on that
  branch; don't create the branch in checkout A and commit from
  worktree B. When a session spans multiple worktrees, the safest
  pattern is to keep all work for one branch in a single worktree
  and switch that worktree's branch between tasks, rather than
  juggling `git -C` across checkouts. Pairs with the existing
  worktree-PYTHONPATH / Write-absolute-path / dirty-state-recovery
  / "create a new worktree to continue last session" lessons —
  same family (correctly locating the right worktree+branch for a
  piece of work), this one is the commit-destination surface.

- **"Registered ≠ working" — dogfood the live loop; a non-mocked
  round-trip test is the receipt**: the P2 memory hooks were registered
  in the live plugin AND 1665 mocked unit tests were green, yet the
  live Stop→stash→recall loop did not round-trip on first real contact
  (caught only because Patrick demanded the receipt instead of accepting
  "hooks registered = done"). The mocked tests passed precisely because
  they mocked Ollama + the backend. Two durable takeaways: (1) for any
  hook/pipeline with external deps (LLM, backend, network), ship at
  least one **non-mocked round-trip** test (real input → real sanitize →
  real write → real recall) — it both proves the persistence logic AND,
  when the live system still fails, distinguishes a code bug from an
  environmental one (here the non-mocked round-trip PASSED, reframing
  the live "0 stashed" as environment, not code); (2) "wired up" /
  "registered" / "smoke-exits-0" are necessary-not-sufficient — dogfood
  the actual end-to-end before declaring done. The receipt beats the
  promise (§7).

- **Keyless-CI-faithful local runs need `ANTHROPIC_API_KEY=""`
  (EMPTY), not `env -u` (UNSET) — unset lets `load_dotenv` inject the
  real key from `~/.attune/anthropic.env` and the "keyless" run spends
  real money**: `env -u ANTHROPIC_API_KEY pytest tests/integration`
  ran 6 real SDK workflows (~$3, 8m46s) because dotenv only skips
  variables that EXIST; CI sets the secret to the empty string, which
  both blocks dotenv's injection AND makes `skipif(not
  os.environ.get(...))` gates fire. The empty-string run matched CI
  exactly (295 passed / 41 skipped, 5.8 s). Rule for any
  provider-key-gated suite: simulate CI-keyless with `KEY="" pytest`,
  never by unsetting.

- **A repo CI secret becoming VALID is a spend event — tests.yml passed
  `secrets.ANTHROPIC_API_KEY` to every push/PR × 12 matrix lanes and
  burned ~$1200 in ~6 hours the night the dead key was replaced with a
  live one (2026-06-10 02:52 UTC)**: tests that change behavior when a
  key is present (mismarked `HAS_API_KEY`-gated tests, real-SDK
  spawners of the #728 class, keyed Haiku-summary paths) made real API
  calls at CI scale the moment the secret went live — for weeks prior
  the key was invalid so the same workflow config burned nothing.
  Diagnostic chain that pinned it: (1) sum LOCAL telemetry
  (`~/.attune/telemetry/usage.jsonl` by day — showed only ~$126/month,
  so the burn wasn't local); (2) `grep -l ANTHROPIC_API_KEY
  .github/workflows/*.yml` + read HOW each uses it
  (`integration-tests.yml` sets it to `""` keyless-by-design;
  `tests.yml` passed the real secret); (3) `gh api .../actions/secrets`
  `updated_at` correlates the spend window. Rule: per-push/PR test
  workflows get `ANTHROPIC_API_KEY: ""` ALWAYS; the real secret
  belongs only to deliberately-scheduled, budget-capped jobs
  (`integration-auth.yml` with `ATTUNE_MAX_BUDGET_USD`). Pairs with
  the "keyless-CI-faithful local runs need EMPTY not unset" lesson —
  same empty-string discipline, opposite direction (CI side).

- **An interrupted/rejected compound Bash command may have PARTIALLY
  executed — re-establish actual git state before continuing, or you
  build on phantom assumptions**: hit on the 8.2.0 release (2026-06-10,
  the #737/#738 take-2). A multi-step command (commit prep → switch
  branch → edit → commit → push → PR) was user-interrupted; the
  rejection message implies nothing ran, but the branch existed, one
  commit existed, and the push had landed. Subsequent commands then
  compounded the misread: `git branch -D release/8.2.0` printed
  `(was bf88edb1)` — that SHA was the REAL release-prep commit, deleted
  with its branch; a later "release prep" commit was actually
  lessons-only (the bumps were already committed away); PR #737's
  squash merged WITHOUT the version bumps. The release-execute step-10
  gate (verify content IN the merge SHA before tagging) caught it
  pre-tag; recovery was cherry-picking the dangling commit. Durable
  rules: (1) after ANY interrupted/denied compound command, run
  `git log --oneline -3` + `git status --short` + `git ls-remote
  --heads origin <branch>` and reconcile EVERY step's expected effect
  before the next command; (2) `git branch -D` output `(was <sha>)`
  names a commit — before treating it as disposable, `git show --stat
  <sha>` to check for unmerged content; (3) verify merge-SHA content
  via the GitHub API (`gh api repos/<o>/<r>/contents/<file>?ref=<sha>`)
  — authoritative and immune to the local stale-object trap that
  muddied diagnosis; (4) when archaeology spirals, stop theorizing and
  fact-check trees directly (`git diff <ref-a> <ref-b> --stat` — an
  empty diff settles arguments instantly); (5) the SAME reconciliation
  applies to a rejected or interrupted **Edit** — `grep` the exact
  target line before re-applying, because the rejection message is not
  proof that nothing was written (an append that reported "NOT
  written" was already on disk, and re-applying duplicated the
  suffix); (6) prefer an `old_string` that is NOT a strict prefix of
  the intended `new_string`, so an accidental double-apply fails
  loudly instead of silently duplicating. Pairs with the "harness
  safety classifier blocks bundled-destructive scripts" lesson — same
  root cause family (compound commands + interruption), this one is
  the state-reconciliation half.

- **Teaching a scanner a new safe idiom can make its gate go BLIND —
  and a shrink-only allowlist ratchet then demands you delete the
  entries that were still load-bearing**: 2026-08-21, closing
  library-review class G1. The sweep-fix replaced ten `path.write_text()`
  atomic-publish sites with `tempfile.mkstemp` + `os.fdopen` + `replace`.
  The path-validation gate's scanner knew `.write_text` / `.write_bytes` /
  `.open(mode="w")` / `shutil.*` / `os.remove|unlink|rename|replace` — it
  did **not** know `os.fdopen` or `tempfile.mkstemp`. So six modules
  dropped OFF its offender list the moment they adopted the SAFER idiom,
  while still writing files exactly as before. Then
  `test_allowlist_entries_are_still_needed` (correctly, by its own logic)
  failed demanding those six ALLOWLIST entries be removed as stale —
  which would have made the gate assert something untrue: "these modules
  have no unvalidated file ops." The gate would have gone quiet on six
  real writers and looked *healthier* for it. **The tell is an allowlist
  ratchet firing "no longer needed" on modules you did not make safer —
  if a shrink-only list suddenly wants to shrink right after a
  refactor, suspect the SCANNER lost sight of the code, not that the
  code improved.** Fix: teach the scanner the new idiom in the SAME PR
  as the migration (`tempfile.{mkstemp,mkdtemp,NamedTemporaryFile,
  TemporaryFile}` + `os.fdopen`-for-write), with unit tests pinning both
  directions (write mode detected, read mode ignored). The widening then
  surfaced **two pre-existing writers the scanner had NEVER seen**
  (`authoring/fact_check/tutorial_static_check.py`,
  `ops/session_summary_cache.py`) — one of which interpolates an
  unvalidated id into a path; allowlisted with the traversal question
  recorded in the comment and chipped separately rather than waved
  through. Generalizes beyond this gate: **any AST scanner encodes a
  vocabulary of the idioms in use when it was written, so every idiom
  migration is a silent recall regression for every gate that scans for
  the old one.** Pairs with the existing "reviewing gate allowlist
  entries — the escape hatch is the actual attack surface" prior.
- **State the BASIS with every load-bearing claim — an inference in
  the grammar of a verified fact is the bug, and the verifying command
  is usually one line you already have**: ratified 2026-08-22 after a
  release session where four such claims each had a cheap probe
  available and unrun. **The rule: verify when the probe is cheap; when
  you do not, SAY SO IN THE CLAIM** ("verified by X" / "inferred, not
  checked"). An unmarked confident assertion is indistinguishable from
  a checked one, so the reader acts on both alike — and Patrick's
  framing is that guessing without flagging it is itself the issue, the
  same posture that produces sloppy code. **The diagnostic: name the
  property your check actually establishes, then ask whether it is the
  property your next action depends on.** `git rev-parse origin/main:src`
  matching a tag establishes something about a REMOTE-TRACKING REF; a
  scan that reads the WORKING TREE is unaffected by it (that checkout
  was 17 commits behind, and the review would have been filed as the
  release receipt). `git status --porcelain` clean means "matches its
  own HEAD", NOT "is current" — pair it with
  `git rev-list --count HEAD..origin/main`. "The runner spawns a
  subprocess" establishes a code path, not process independence — read
  `ps -o ppid=,command=`. Which code will execute is answered by the
  filesystem that will be read (`pyproject.toml` on disk, an imported
  `__version__`, `__file__`), never by a ref. Relaying a third party's
  approval ("X approved this") is the same error in social form: the
  recipient cannot verify it through you. **Why this sits in core
  rather than the tail: recall cannot save you from it.** The corpus
  already held adjacent lessons and none fired, because the failure
  happens when a CONCLUSION IS FORMED — earlier than any tool call that
  would trigger retrieval — and on that session the SessionStart hook
  had already printed `STALE SOURCE … 17 commits behind` and it was
  read as ambient noise. Verification also keeps OLD lessons honest:
  the same session found a core lesson's premise ("Windows lanes are
  NOT required") had gone stale, so acting on it unverified would have
  added pointless friction.
- **`os.geteuid()` inside a `pytest.mark.skipif` condition errors the
  WHOLE MODULE at collection time on Windows — skipif conditions are
  evaluated eagerly, so a second `skipif(os.name == "nt")` above it
  never gets a chance**: 2026-08-21, all five Windows lanes on PR #2147
  went red on a tests-only change. The decorator stack read:
  ```python
  @pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits")
  @pytest.mark.skipif(os.geteuid() == 0, reason="root ignores the write bit")
  ```
  which looks defensive and is not: `os.geteuid` **does not exist** on
  Windows, so the condition expression raises `AttributeError: module
  'os' has no attribute 'geteuid'` while pytest is COLLECTING the file —
  before any skip logic runs, taking every test in the module with it
  (`ERROR tests/unit/curator/test_cache.py`). The nt-skip is dead code:
  a decorator cannot protect an expression that is evaluated to build
  the decorator below it. Fix: collapse to one module-level constant
  computed with a safe accessor —
  `_CANNOT_REFUSE_WRITES = os.name == "nt" or getattr(os, "geteuid", lambda: 1)() == 0`
  — then a single `skipif(_CANNOT_REFUSE_WRITES, ...)`. The repo's three
  pre-existing uses already short-circuit correctly
  (`os.name == "posix" and os.geteuid() != 0` in
  `tests/unit/memory/test_file_stash.py`; `hasattr(os, "geteuid") and ...`
  in `tests/unit/telemetry/test_form_events.py` and
  `tests/unit/workflows/discovery_sweep/test_pattern_scan_source.py`) —
  **grep for an existing safe spelling before writing a new
  platform-gated skip**. Generalizes to any POSIX-only `os` member in a
  skipif condition (`geteuid`, `getuid`, `setuid`, `fork`, `getpriority`)
  and to `pytest.mark.parametrize` argument expressions, which are also
  evaluated at collection. Diagnostic tell: a tests-only diff that fails
  EVERY Windows lane as `ERROR` (collection) rather than `FAILED`.
- **Calibrate a new gate rule on the real tree BEFORE writing it, and
  report the precision — a first-draft rule is routinely 60-70% precise,
  and the discriminator that fixes it must be pinned as a fixture**:
  2026-08-21, across four library-review gates. Every rule was probed as
  a throwaway script first, and every one moved after seeing its hits.
  G2's naive form ("any `int()`/`float()` after a per-record skip
  guard") found 6 sites, 4 real: the lookalikes were
  `int(elapsed * 1000)` on floats and `int(m.group(1))` on a `(\d+)`
  capture, neither of which can raise. Requiring the coerced value to
  come from a parsed record (a `.get(...)` or a subscript) took it to
  4/4/0. I-4's naive form found 12, narrowed to 3. H1's FIRST form was
  worse than imprecise — it was **wrong**: keyed on literal `host=`/
  `port=` arguments, it found one site and MISSED the live user-facing
  bug entirely, because `redis.Redis(socket_connect_timeout=2)` has no
  endpoint argument at all and defaults to localhost:6379 implicitly.
  A rule that finds one already-defensible hit is evidence the QUESTION
  is wrong, not that the tree is clean. Three durable practices: (1)
  **probe first, in a scratch script, and look at every hit by hand** —
  the triage is where the rule gets designed; (2) **state the precision
  in the PR** (hits / real / false positives) so a reviewer can judge
  whether the gate will cry wolf, since a noisy gate gets allowlisted
  into uselessness; (3) **pin each false positive you eliminated as a
  passing test fixture** — the discriminator is the most fragile part of
  the rule and the easiest thing for a later "simplification" to drop.
  Matches the class register's own pipeline (confirm -> mechanize ->
  CALIBRATE -> gate -> sweep-fix -> close) and its standing line that
  "uncalibrated rules do not gate anything".
- **A required check failing on a PR that cannot possibly affect it means
  MAIN is red — check main's last run BEFORE debugging the PR; and
  `strict: false` does NOT mean "no rebase needed"**: 2026-08-21. A
  docs-only PR (#2153, one markdown file in an archived spec) failed the
  required `coverage` check. Nothing in that diff can move coverage, and
  that impossibility is the diagnostic: one `gh run list --branch main
  --limit 6 --workflow=tests.yml` showed main itself failing since
  `ced39888a`. The PR was inheriting main's breakage, so debugging the
  PR would have found nothing. **Order of operations: a check that the
  diff cannot influence is a signal about the BASE, not the branch.**
  Root cause was `scripts/check_badge_freshness.py` (it runs inside the
  coverage job, so its failure is reported as "coverage"): the README
  carries a manually-maintained round FLOOR for the tests badge and
  `MARGIN = 5000`, so it trips once actual exceeds floor + 5,000. The
  floor had drifted ~4,970 stale on its own; four gate PRs merged that
  afternoon added the tests that crossed it. Fix was a one-line bump to
  the next round number — which the README's own maintenance comment had
  already named ("bump once the suite clears 25,000"), so **read the
  maintenance comment before inventing a value**.
  **The correction worth carrying:** I first reasoned the follow-up PR
  needed no rebase, because branch protection has `strict: false` and
  the two PRs touched different files. Wrong in effect — `strict`
  governs merge ELIGIBILITY (may a behind-branch merge), not whether a
  check PASSES. The follow-up branched before the fix, so its own tree
  still held the stale floor and `coverage` genuinely failed on its own
  content. It needed the rebase regardless of strictness. **Ask "does
  this branch's TREE contain the fix?", never "is this branch allowed to
  merge behind?"** (rebase re-signed cleanly; verify `%G?` before
  force-pushing, per the existing GPG lesson.)
  Rider on the same episode: merging four PRs inside ~15 minutes made
  `cancel-in-progress` kill an earlier main run's `test (ubuntu-latest,
  3.13)`, and cancelled-but-required also blocks — the known
  rapid-PUSH lesson applies identically to rapid MERGES. No code fixes
  that half; it clears on the next full main run, so verify the two
  previously-red JOB conclusions directly rather than trusting the
  run-level green (a cancelled-but-required check that stays cancelled
  looks the same from a distance and needs `gh run rerun`).

- **A transport migration silently converts every emptiness-asserting
  test into a vacuous one — and the suite CANNOT report it, because the
  failure mode satisfies the assertion**: 2026-08-22, the telemetry
  scan-then-`get()` -> `MGET` migration (#2162). Tests that stubbed only
  `client.get` then handed the listing a bare `Mock` for `mget`, which is
  not iterable; the `TypeError` was swallowed by each listing's
  function-wide `except Exception` and the call returned `[]` / `0` /
  `None`. Any `assert x == []` therefore passed **for the wrong reason**:
  the payload the test set up was never read (`get()` call count 0) and
  the logic under test never ran. The cost, measured: disabling
  `get_pending_approvals`' "only pending" status filter ENTIRELY left the
  whole telemetry suite green (646 passed) — that filter's only guard was
  one of the vacuous tests. **The selection effect is the point, and it
  was perfectly clean across the 13 tests touching those listings:
  POSITIVE-assertion tests (`assert len(x) == 1`) go red instantly and
  get fixed during the migration — 3/3 were wired; emptiness-asserting
  tests are satisfied by the very failure they should catch — 0/10 were.**
  Nobody was careless; the suite emitted no signal, so no amount of care
  would have caught it. Generalizes to ANY mock-stubbed transport swap
  (sync->async, single->batch, REST->GraphQL, one client method ->
  another) wherever the caller has a broad `except` that degrades to an
  empty result. **Diagnostics**: (1) mutation-test the logic the tests
  claim to guard — if breaking a filter leaves the suite green, its
  coverage is fiction; (2) count `get()` calls — a stubbed payload that
  is never read is the tell; (3) grep for tests that stub the OLD method
  and assert emptiness. **Fix**: define the new method in terms of the
  old (`client.mget.side_effect = lambda ks: [client.get(k) for k in ks]`
  — literally the Redis contract), so each test keeps configuring
  payloads the way it already does. **Gate it**: a static check that any
  test feeding a non-empty scan must also serve the batched read
  (`tests/unit/gates/test_listing_mock_transport_gate.py`), since this
  class is invisible by construction and vigilance cannot cover it.
