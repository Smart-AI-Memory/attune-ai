# Host Surface Parity — Requirements

**Status:** draft (2026-09-03) — requirements proposed by the Claude
seat; chair rulings D1a–D1c recorded in [decisions.md](decisions.md).
No implementation authority is granted by this document; every task
in [tasks.md](tasks.md) executes only behind its own chair go.
**Slug:** `host-surface-parity`
**Provenance:** Cowork session with the Claude seat, 2026-09-03,
chair Patrick Roebuck. Companion brief: the artifact "Fable 5.1 and
the Attune Surface" (Claude seat opening position, thread slug
`q-fable-51-surface-overlap-001` proposed, not yet opened on the
board). Antigravity and Codex have not deliberated this; the chair
may convene the table before ruling any task.

## Position in the existing stack

This spec sits on four shipped seams and adds no new renderer,
memory store, orchestration layer, or provider registry:

- **Surfaces** — `attune-forms` already negotiates
  `Surface.RICH / PORTABLE / HEADLESS`; the state-bound command
  workspaces of 16.2.0 ([shared-command-workspaces](../shared-command-workspaces/requirements.md))
  render through it with Markdown and terminal-receipt fallbacks.
- **Projection** — the collaboration projector
  ([cross-provider-collaboration-projector](../cross-provider-collaboration-projector/requirements.md))
  owns one master (`content/collaboration/contract.md`) and projects
  it to `AGENTS.md`, `.claude/CLAUDE.md`, and the Antigravity mirror
  `.agents/AGENTS.md`.
- **Memory** — stash → recall → promote, with `resolve_backend()`
  reading `attune.memory_backends`, and cross-provider transport
  shipped in 10.6.x
  ([cross-provider-memory-transport](../cross-provider-memory-transport/requirements.md)).
- **Extensions** — the trust-gated `attune.extensions` system ruled
  in [release-16-manifest](../release-16-manifest/decisions.md)
  D1/D2 (passenger 4), not yet on disk. Chair ruling D1b of this spec
  makes it the seam through which providers, backends and seats
  arrive.

## Problem

The 2026-09-01 host release (Claude Fable 5.1; the Cowork and Claude
Code surfaces around it) ships first-party versions of things Attune
built as portable, verified, multi-provider systems: a structured
question widget (`AskUserQuestion`), desktop-persistent project
memory (`MEMORY.md` + typed topic files), a skill-proposal card, a
multi-agent workflow runner, typed review findings, hosted artifacts
with runtime state, scheduled tasks, and a file monitor.

Two failure modes follow, and they pull in opposite directions:

1. **Ignore the host** and Attune's lowest rendering tier looks worse
   than the native widget sitting next to it; memory reads as a
   duplicate of a feature the host now has by the same name.
2. **Chase the host** and Claude surfaces become privileged: a rich
   Cowork path with a neglected Codex / Antigravity path, which is
   exactly the power-user sacrifice the chair has ruled out.

The requirements below resolve the tension with one rule: **every
host-specific capability ships with its portable twin, receipted,
in the same change** — and the multi-provider roster becomes data
so a vendor change is a config edit, not a PR.

## Hypotheses

- **H1 — tier 0 is a render target, not a rival.** A single-question
  form projected onto the host's native widget returns the same
  validated answer as the widget-HTML and headless tiers. Richer
  constructs (decision, pushback, ranking, triage, assumption
  review, progress) keep their own renderers and are not degraded
  to fit the host.
- **H2 — parity can be mechanical.** "The receipt beats the promise"
  is listed as *aspirational* in the collaboration contract. For
  surfaces it can be an enforcer: a drift guard that fails when a
  RICH-tier renderer or host hook lacks PORTABLE and HEADLESS twins
  with receipts.
- **H3 — the host remembers; Attune recalls.** Projecting the
  promoted-lesson index into each host's native memory surface makes
  a plain host session benefit from the corpus, while recall
  (relevance-ranked, at prompt time) remains the product. Memory
  stays the single source of truth; every projection is
  regenerable and never hand-edited.
- **H4 — local models earn a role before a seat.** Under D1a, a
  local model's first job is the set of low-stakes, high-volume
  roles where cost and privacy dominate — recall re-ranking, lesson
  classification, triage pre-sort, skeptic/countersign at low
  stakes, fact-check probes — not deliberation. Under D1b these
  arrive as extensions under the two ruled capability contracts,
  which makes an Ollama-backed reranker the first real second
  implementer that release-16-manifest D2 named as its falsifier.
- **H5 — roster by role, not vendor.** The three seats are harness
  recipes with role properties (`PLAN_ONLY_SEATS`), not providers.
  Expressing the roster as role slots with a vendor binding keeps
  the fixed three as the default while making "Google changed tiers
  again" or "add a fourth seat" a data change gated by the extension
  system.

## Requirements

**R1 — Host tier 0 renderer** *(seat: proposed; chair: not yet ruled)*
`attune-forms` gains a renderer that projects a single-question form
onto the host's structured question contract: at most four options,
each with label and description, optional multi-select, a
"(Recommended)" suffix on the first option when the form carries a
recommendation, and the host-supplied "Other" free-text escape.
Forms that exceed the contract (more than four options, bounded
numbers, path pickers, multi-question) fall through to the existing
PORTABLE tier — never truncated. The answer is validated on the way
back exactly as on every other tier.

**R2 — Surface parity gate** *(seat: proposed; chair: not yet ruled)*
A drift-guard test enumerates every RICH-tier renderer and every
host-specific hook or template in the tree and fails when any lacks
(a) a PORTABLE twin, (b) a HEADLESS twin, and (c) a receipt entry
naming the three renders of one form with identical validated
output. The gate is mechanical; it implements collaboration-contract
principle 1 for surfaces and is listed there as its enforcer.

**R3 — Memory index projection** *(seat: proposed; chair: not yet ruled)*
The collaboration projector gains a second master — the
promoted-lesson index — and projects it to every host memory
surface: the Cowork project-memory `MEMORY.md` index (one line per
lesson, pointing at the Attune store), the memory block of
`.claude/CLAUDE.md`, `AGENTS.md`, and `.agents/AGENTS.md`. Promotion
triggers regeneration; a line budget is drift-guarded; the projector
refuses hand edits exactly as it does for the contract block.
Recall is unchanged.

**R4 — MCP Apps round-trip receipt** *(seat: proposed; chair: not yet ruled)*
A recorded receipt of the Fix preview workspace rendered by the
Cowork host through the standard `ui://` profile, with
`fix_workspace_collect_action` returning revision, nonce and
contract hash intact, a replayed action failing closed, and — if the
host does not advertise the profile — the Markdown fallback rendering
correctly. No production change unless the receipt fails.

**R5 — Scheduled and monitored delivery, twinned** *(seat: proposed; chair: not yet ruled)*
Templates that run `discovery-sweep`, `bug-predict`, and
`release-prep` as host scheduled tasks and wake on a file monitor,
each shipped with its portable twin (`cron` + `attune` CLI) and
subject to the spend gate. The first monitored path is
`~/.attune/telemetry/context_fit.jsonl`, which also settles the
fit_source budget clock in `TASKS.md`.

**R6 — Local-model roles via extensions** *(chair-ruled D1a, D1b; mechanics proposed)*
Local models (Ollama first) enter as extensions under the two ruled
capability contracts: a **memory-backend** extension advertising an
optional `rerank` capability (Phase A of release-16-manifest D3), and
**workflow** extensions for classification, triage pre-sort,
skeptic/countersign at low stakes, and fact-check probes (Phase B).
A `LOCAL` tier is added to the tier contract for routing these roles;
the mechanics are D2 in decisions.md. No change to `ModelProvider`;
no third capability contract (D3).

**R7 — Roster as data** *(seat: proposed; chair: not yet ruled)*
`CANONICAL_SEATS`, `SEAT_RECIPES` and `PLAN_ONLY_SEATS` become a
roster document of role slots — one plan-only reviewer, one
code-native proposer, one moderator with receipts — each bound to a
harness recipe. The default roster is the current three, byte-for-byte
in behavior. Workspace gates check roster size from the roster, not
the literal three. A fourth slot is legal only when supplied by an
enabled extension.

**R8 — Asks-per-outcome** *(seat: proposed; chair: not yet ruled)*
The session ledger records structured asks per completed outcome
(receipt), so "demanding" is measured as structure per result rather
than interruptions per session. `friction_gate` reads the figure; no
new telemetry store.

## Non-goals

- No fourth round-table seat in this spec. A seat arrives through
  R7 plus an enabled extension, in a later cycle, behind its own
  chair go.
- No general Ollama provider for all workflows. `ModelProvider` stays
  Claude-native; local models serve the roles in R6 only. A
  provider-level capability contract would be a third contract and
  is deferred to the chair (decisions.md D3).
- No change to recall ranking, the promote gate, or the memory
  store's schema. R3 projects; it does not move truth.
- No new renderer. R1 is a projection inside `attune-forms`; R4 is a
  receipt.
- No auto-promotion, no auto-advance. R4 in
  [spec-lifecycle-gates](../spec-lifecycle-gates/requirements.md)
  applies unchanged.

## Public compatibility constraints

- `attune fix` CLI behavior and exit contract are unchanged
  ([outcome-first-fix](../outcome-first-fix/requirements.md)).
- The `attune.memory_backends` entry-point group keeps working
  through the compatibility adapter ruled in release-16-manifest D1.
- The tier enum is duplicated by design in four places
  (`src/attune/models/registry.py`, `src/attune/config/agent_config.py`,
  `src/attune/workflows/compat.py`, `src/attune/workflows/progressive/core.py`)
  and mirrored in `attune-rag`, with
  `tests/unit/test_model_tiers_drift.py` as the alarm. Adding `LOCAL`
  is a change to all copies and to the mirror in the same release;
  the drift guard is the receipt.
- R7 must not change the brief preamble's observable behavior for
  the default roster; the "three-model round table" wording becomes
  templated from the roster.
- The brand-drift gate (G5) applies to every file in this spec.

## Dissent register

- The Claude seat's own earlier candidate (bridge to Cowork
  `MEMORY.md` only) is withdrawn in favor of R3, which projects to
  every host memory surface. Reason: a Claude-only bridge would make
  memory the one place Attune quietly picks a vendor.
- Anticipated pushback to weigh at the table: whether R3 dilutes
  "Attune recalls" positioning by making the host notebook good
  enough. The seat's answer: a corpus with no recall is the demo;
  recall is the product.
- Anticipated pushback: whether `LOCAL` belongs in the tier enum at
  all versus a role-routing label. Recorded as D2 (proposed) with
  both options.

## Open questions for the chair

1. Convene `q-fable-51-surface-overlap-001` before ruling R1–R8, or
   rule from this brief? (Antigravity and Codex have not spoken.)
2. Coverage floor for this initiative: the repository's 85% or the
   90% the chair set for shared-command-workspaces (D4 there)?
3. D2 mechanics for `LOCAL` (enum member vs. routing label).
4. Whether R6's workflow extensions wait for release-16-manifest
   Phase B, or Phase A ships the reranker alone first.
