# Host Surface Parity — Design

**Status:** draft (2026-09-03) — design proposed by the Claude seat
against the verified baseline below; no task is authorized.
**Last updated:** 2026-09-03

## Verified baseline

Every anchor below was read from the tree on 2026-09-03, not carried
from spec text.

- **Roster is literal.** `CANONICAL_SEATS: tuple[str, ...] =
  ("claude", "antigravity", "codex")` at
  [rotation.py:25](../../../src/attune/roundtable/rotation.py);
  `SEAT_RECIPES` (fixed argv: `claude -p`, `agy --mode plan`,
  `codex exec`) and `PLAN_ONLY_SEATS = {"antigravity"}` at
  [routine.py:92–106](../../../src/attune/roundtable/routine.py);
  `workspace.py` refuses `round_complete` unless the roster is
  exactly the fixed three
  ([workspace.py:258, 341](../../../src/attune/roundtable/workspace.py));
  the brief preamble hard-codes "three-model round table".
  `skeptic.py` and `countersign.py` import `CANONICAL_SEATS` for the
  different-model rule.
- **Provider registry is Claude-native.** `ModelProvider` has one
  member, `ANTHROPIC`
  ([registry.py:33](../../../src/attune/models/registry.py)).
  `ModelTier` is `CHEAP / CAPABLE / PREMIUM`
  ([registry.py:20](../../../src/attune/models/registry.py)) with
  duplicates in `config/agent_config.py:25`,
  `workflows/compat.py:50`, `workflows/progressive/core.py:24` and a
  mirror in `attune-rag` guarded by
  `tests/unit/test_model_tiers_drift.py`. Ollama appears only in
  workflow config docstrings and comments; there is no Ollama client.
- **Surfaces are negotiated.** `attune-forms` exposes
  `Surface.RICH / PORTABLE / HEADLESS` and renders workspaces through
  `workspace_to_widget_html()` and `workspace_to_markdown()`; the
  host authority seam is `src/attune/elicitation/command_workspace.py`
  with Fix as the witness
  (`src/attune/elicitation/fix_workspace.py`, `src/attune/mcp/server.py`).
- **Projection has one master and three targets.**
  `MASTER_PATH = content/collaboration/contract.md`,
  `CONTRACT_TARGETS = (AGENTS.md, .claude/CLAUDE.md)`,
  `IDE_MIRROR_TARGET = .agents/AGENTS.md`
  ([scripts/project_collaboration_contract.py:19–29](../../../scripts/project_collaboration_contract.py)).
  The projector rejects symlinked targets and hand edits inside the
  marked block.
- **Memory promotion is a function.** `promote()` at
  [promotion.py:142](../../../src/attune/memory/promotion.py);
  `resolve_backend()` at
  [session_stash.py:120](../../../src/attune/memory/session_stash.py)
  resolves `attune.memory_backends` with two live implementations
  (`file`, `redis`). Recall hooks: `plugin/hooks/jit_recall.py`,
  `lesson_recall.py`, `session_recall.py`.
  `.attune/next_session_starter.md` is already a per-session
  projection of memory.
- **Spend and friction exist.** `src/attune/gates/spend_gate.py`,
  `src/attune/gates/session_ledger.py`, `plugin/hooks/friction_gate.py`.
- **Context-fit telemetry has a writer and no data.**
  [allocator.py:30](../../../src/attune/context/allocator.py) writes
  `~/.attune/telemetry/context_fit.jsonl`; the file does not exist on
  the chair's machine (TASKS.md, 2026-08-28).
- **Host contracts observed 2026-09-03** (Cowork session tool
  surface, described from the tool contracts):
  `AskUserQuestion` — 1–4 questions, each 2–4 options with `label`
  and `description`, `multiSelect`, an automatic "Other", and the
  convention of putting the recommended option first with a
  "(Recommended)" suffix. Project memory — `MEMORY.md` as an index of
  one-line links (about 150 characters each) to topic files carrying
  `name / description / type` frontmatter with `type` in
  `user | feedback | project | reference`. Scheduled tasks — cron or
  one-shot, each firing a fresh session with a standalone prompt.
  Monitor — wake on file or process change.

## Layer boundary

```text
host (Cowork / Claude Code / Codex / Antigravity / headless)
          |
          v
attune-forms  Surface negotiation: RICH | PORTABLE | HEADLESS
          |     + tier 0: host-native question projection   (R1)
          |
          v
attune-ai   CommandWorkspaceHost + adapters        (unchanged)
          | roster.yaml -> role slots -> harness recipes   (R7)
          | projector: contract master + lesson-index master (R3)
          | ledger: asks-per-outcome                       (R8)
          |
          v
attune.extensions (release-16-manifest D3)
          | Phase A  memory-backend contract  -> local reranker   (R6a)
          | Phase B  workflow contract        -> local role workflows (R6b)
          | later    roster slot supplier     -> fourth seat (non-goal here)
          |
          v
parity gate (R2): every RICH renderer / host hook / host template
has PORTABLE + HEADLESS twins and a three-render receipt
```

The gate sits under everything on purpose: it is the enforcer that
lets the layers above adopt host features without the host becoming
privileged.

## R1 — Host tier 0 renderer

`attune-forms` adds `render_host_question(form) -> HostQuestion |
None`. It returns a payload only when the form is a single question
whose control is a choice with 2–4 options; otherwise `None`, and the
caller falls through to PORTABLE. Mapping:

| Form construct        | Host field                                      |
| --------------------- | ----------------------------------------------- |
| question text         | `question`                                      |
| short heading         | `header` (≤ 12 characters, truncated at a word) |
| option label / detail | `options[].label` / `options[].description`     |
| multi-select control  | `multiSelect: true`                             |
| recommendation        | first option, label suffixed " (Recommended)"   |
| free-text escape      | host-provided "Other" (no mapping needed)       |

The response path reuses the existing validator: the host returns
the chosen label(s) or free text; the renderer maps labels back to
option ids and hands the answer to the same validation the widget and
headless tiers use. A malformed answer is re-asked on the PORTABLE
tier, never silently accepted.

Decision, pushback, ranking, triage, assumption-review and progress
constructs never project to tier 0; they are the vocabulary the host
lacks and they stay on their own renderers.

## R2 — Surface parity gate

`tests/unit/gates/test_surface_parity.py` walks two inventories:

1. **Renderers** — every function in `attune-forms` and
   `src/attune/elicitation/` registered for `Surface.RICH` (including
   R1's tier 0).
2. **Host artifacts** — every file under `plugin/hooks/`,
   `plugin/commands/`, and the templates R5 adds, tagged
   host-specific by a header marker.

For each item the gate requires a PORTABLE twin, a HEADLESS twin, and
a receipt line in `docs/specs/host-surface-parity/receipts.md` naming
one form, its three renders, and the identical validated output.
Missing any of the three fails the test with the exact shortfall.
The gate is added to the collaboration contract as the enforcer of
principle 1 for surfaces, so the master's "aspirational" label comes
off for this case. This is the Discipline article's §7 rule applied
to surfaces — "if a property matters, something must fail when it
stops being true" (attune-ai.dev/discipline).

## R3 — Memory index projection

The projector gains a second master, generated rather than authored:
`content/collaboration/lesson-index.md`, produced by
`scripts/project_lesson_index.py` from the promoted store. Each line
is `- [<lesson name>](<store path>) — <one-line hook>` and the file
carries a budget the projector drift-guards. The budget is in
**bytes, not lines**, because every target is an always-loaded
surface: the Discipline article's §9 sets a 20,000-byte ceiling on
the eager-loaded rules corpus, and the projected lesson block counts
against that ceiling wherever it lands. Default: 4,000 bytes
(about 40 lines), adjustable per target, never above the residual
headroom under the §9 ceiling.

Targets, each inside a marked block the projector owns:

- Cowork project memory: `MEMORY.md` (the host reads it at session
  start; the line shape matches the host's index convention).
- `.claude/CLAUDE.md` — a `<!-- attune:lessons:start -->` block next
  to the existing contract block.
- `AGENTS.md` and `.agents/AGENTS.md` — the same block, so Codex and
  Antigravity read the same index.

`promote()` calls the regenerator after a successful promotion;
`attune memory project` regenerates on demand. Nothing in recall
changes: recall still ranks from the store; the index is a courtesy
to hosts that cannot call recall.

## R4 — MCP Apps round-trip receipt

A scripted run: open the Fix preview workspace in a Cowork session,
capture (a) whether the host advertised the Attune UI MIME profile,
(b) the widget or Markdown that rendered, (c) the
`fix_workspace_collect_action` response with revision, nonce and
contract hash, (d) a deliberate replay of the same action and its
fail-closed refusal. The receipt goes in `receipts.md` under R4. If
(a) is false, the receipt records the Markdown fallback and the task
closes as "portable path verified; RICH path pending host support".

## R5 — Scheduled and monitored delivery, twinned

A new `plugin/templates/scheduled/` directory holds three task prompts (sweep,
bug-predict, release-prep) written as standalone instructions for a
fresh session, plus one monitor template for
`~/.attune/telemetry/context_fit.jsonl`. Beside each host template
sits its twin: a `cron` line and the `attune` CLI invocation that
produces the same receipt in `.attune/workflow_runs.jsonl` with an
`origin: scheduled` field. Both paths pass through the spend gate;
the host template states the cap in its prompt.

## R6 — Local-model roles via extensions

**R6a — reranker (Phase A).** An in-repo example extension
`extensions/attune-ext-local-rerank/` implements the memory-backend
contract's optional `rerank(candidates, query) -> ranked` capability
against an Ollama endpoint, falling back to the store's own ranking
when Ollama is unreachable. It is the "minimal example extension"
Phase A already requires — so it costs the extension work nothing
extra and satisfies D2's demand for a real second implementer.
Recall eval ([memory-recall-eval](../memory-recall-eval/requirements.md))
runs with and without the reranker; the receipt is P@3 on the frozen
benchmark, not a feeling.

**R6b — role workflows (Phase B).** Extensions implementing the
workflow contract for: lesson classification, triage pre-sort,
low-stakes skeptic/countersign, fact-check probes. Each declares
`tier: local` and is routed by role; each has a `PREMIUM`-tier
fallback for stakes above a chair-set threshold.

**Tier.** `LOCAL` is added below `CHEAP` in every tier copy and the
`attune-rag` mirror in one release; the existing drift guard is the
receipt. Pricing metadata is zero; the spend gate records tokens for
volume, not cost. (Mechanics alternatives in decisions.md D2.)

## R7 — Roster as data

`src/attune/roundtable/roster.py` loads `roster.yaml` (default
embedded, overridable in `.attune/`):

```yaml
slots:
  - role: moderator        # receipts, board I/O, synthesis
    seat: claude
    recipe: ["claude", "-p", "{brief}"]
  - role: plan_reviewer     # plan-only; cannot emit code
    seat: antigravity
    recipe: ["agy", "--add-dir", ".", "-p", "{brief}", "--mode", "plan"]
    plan_only: true
  - role: code_proposer     # code-native
    seat: codex
    recipe: ["codex", "exec", "--skip-git-repo-check", "-"]
```

`CANONICAL_SEATS`, `SEAT_RECIPES` and `PLAN_ONLY_SEATS` become
derived views of the roster so every current import keeps working.
Workspace gates compare against `len(roster.slots)`. The brief
preamble is templated from the slot count and seat names. A slot
whose `seat` is not one of the built-in three must name an enabled
extension providing the recipe; otherwise the roster fails to load
with the exact shortfall.

## R8 — Asks-per-outcome

The session ledger already records spend per seat invocation. It
gains two counters: structured asks issued (any form rendered on any
tier) and outcomes receipted (Fix receipts, workflow run receipts,
promotions). `friction_gate` surfaces the ratio at session end. No
new store; the ledger's existing JSONL carries the fields.

## Sequencing

| Increment | Depends on                          | Target                     |
| --------- | ----------------------------------- | -------------------------- |
| R2 gate   | nothing (test-first)                | next minor                 |
| R1, R3    | R2 green                            | next minor                 |
| R4, R5    | R2 green; host access               | next minor                 |
| R7        | R2 green                            | next minor                 |
| R8        | session-spend-ledger fields         | next minor                 |
| R6a       | release-16-manifest Phase A shipped | the minor that ships A     |
| R6b       | Phase B shipped                     | the minor that ships B     |

Nothing here blocks passenger 4; R6a is the example extension Phase A
already owes.

## Receipts

Each task in [tasks.md](tasks.md) names its receipt. The initiative's
overall receipt is a single demo form rendered on five surfaces —
Cowork tier 0, Claude Code widget, Codex Markdown, Antigravity
Markdown, headless text — returning one identical validated answer,
recorded in `receipts.md` and regenerable by
`scripts/render_demo_forms.py`.
