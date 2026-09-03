# Host Surface Parity — Requirements

**Status:** approved (2026-09-02) — round 1 of
`q-fable-51-surface-overlap-001` deliberated R1–R8 (3/3 seats);
the chair promoted the round in decisions.md **D5**: R4 adopted as
written, R1/R2/R3/R5/R7/R8 adopted as amended (binding amendment
text lives in D5), R6 adopted with D2's routing-label mechanics,
R9 (capability-descriptor/conformance layer) adopted as the 16.3
foundation. D6 ruled 2026-09-03 (hybrid locus); D7 coverage floor
90%; D8 grants the 16.3 execution gos — no proposed decision
remains open. Tasks in [tasks.md](tasks.md) execute per D8; each
lands against the 90% floor.
**Slug:** `host-surface-parity`
**Provenance:** Cowork session with the Claude seat, 2026-09-03,
chair Patrick Roebuck. Companion brief: the artifact "Fable 5.1 and
the Attune Surface" (Claude seat opening position, thread slug
`q-fable-51-surface-overlap-001` proposed, not yet opened on the
board). *(Update: the table was convened 2026-09-02 — all three
seats deliberated; the round was promoted in decisions.md D5.)*

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

**R1 — Host tier 0 renderer** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: host-profile record, not a hardcoded vendor shape)*
`attune-forms` gains a renderer that projects a single-question form
onto the host's structured question contract: at most four options,
each with label and description, optional multi-select, a
"(Recommended)" suffix on the first option when the form carries a
recommendation, and the host-supplied "Other" free-text escape.
Forms that exceed the contract (more than four options, bounded
numbers, path pickers, multi-question) fall through to the existing
PORTABLE tier — never truncated. The answer is validated on the way
back exactly as on every other tier.

**R2 — Surface parity gate** *(chair-ruled — ADOPT as amended, D4/D5; locus ruled 2026-09-03, D6: hybrid — registry for renderers, enumeration for in-tree hooks)*
A drift-guard test enumerates every RICH-tier renderer and every
host-specific hook or template in the tree and fails when any lacks
(a) a PORTABLE twin, (b) a HEADLESS twin, and (c) a receipt entry
naming the three renders of one form with identical validated
output. The gate is mechanical; it implements collaboration-contract
principle 1 for surfaces and is listed there as its enforcer.

**R3 — Memory index projection** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: bounded top-K sentinel-bracketed digest, per-host budgets)*
The collaboration projector gains a second master — the
promoted-lesson index — and projects it to every host memory
surface: the Cowork project-memory `MEMORY.md` index (one line per
lesson, pointing at the Attune store), the memory block of
`.claude/CLAUDE.md`, `AGENTS.md`, and `.agents/AGENTS.md`. Promotion
triggers regeneration; a line budget is drift-guarded; the projector
refuses hand edits exactly as it does for the contract block.
Recall is unchanged.

**R4 — MCP Apps round-trip receipt** *(chair-ruled 2026-09-02 — ADOPT as written, first among the eight, D5)*
A recorded receipt of the Fix preview workspace rendered by the
Cowork host through the standard `ui://` profile, with
`fix_workspace_collect_action` returning revision, nonce and
contract hash intact, a replayed action failing closed, and — if the
host does not advertise the profile — the Markdown fallback rendering
correctly. No production change unless the receipt fails.

**R5 — Scheduled and monitored delivery, twinned** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: one master definition, generated bindings, sweep guards)*
Templates that run `discovery-sweep`, `bug-predict`, and
`release-prep` as host scheduled tasks and wake on a file monitor,
each shipped with its portable twin (`cron` + `attune` CLI) and
subject to the spend gate. The first monitored path is
`~/.attune/telemetry/context_fit.jsonl`, which also settles the
fit_source budget clock in `TASKS.md`.

**R6 — Local-model roles via extensions** *(chair-ruled D1a, D1b; D2 mechanics ruled 2026-09-02 — routing label)*
Local models (Ollama first) enter as extensions under the two ruled
capability contracts: a **memory-backend** extension advertising an
optional `rerank` capability (Phase A of release-16-manifest D3), and
**workflow** extensions for classification, triage pre-sort,
skeptic/countersign at low stakes, and fact-check probes (Phase B).
Local routing uses a `placement: local` **routing label** on the
role's routing record — the tier enum stays `CHEAP / CAPABLE /
PREMIUM` and no copy or mirror changes (D2, ruled: the label lets a
role say "CHEAP, prefer local, fall back hosted"). No change to
`ModelProvider`; no third capability contract (D3, ruled with the
second-implementer tripwire).

**R7 — Roster as data** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: typed slots, golden-roster receipt, loader-enforced fourth-slot gate)*
`CANONICAL_SEATS`, `SEAT_RECIPES` and `PLAN_ONLY_SEATS` become a
roster document of role slots — one plan-only reviewer, one
code-native proposer, one moderator with receipts — each bound to a
harness recipe. The default roster is the current three, byte-for-byte
in behavior. Workspace gates check roster size from the roster, not
the literal three. A fourth slot is legal only when supplied by an
enabled extension.

**R8 — Asks-per-outcome** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: terminal outcomes, raw counts, floor)*
The session ledger records structured asks per completed outcome
(receipt), so "demanding" is measured as structure per result rather
than interruptions per session. `friction_gate` reads the figure; no
new telemetry store.

**R9 — Host capability descriptor and conformance layer** *(chair-adopted 2026-09-02 at promotion, D5 — the 16.3 foundation item)*
Every host adapter and extension publishes a machine-readable
**capability descriptor** (structured-question shape, memory
surfaces, `ui://` profiles, scheduling/monitoring support, action
round-trip guarantees, receipt schema versions). An
`attune surfaces doctor` probe records which contracts the current
host actually advertises and writes a capability receipt; from
accumulated receipts a generated, drift-guarded **hosts ×
capabilities matrix** (each cell native / fallback-receipted /
absent) lives in tree, so "no privileged surface" is a visible red
cell rather than a vibe. A shared conformance suite runs canonical
transcripts against each adapter and proves: unsupported
capabilities degrade deliberately; semantic outputs stay
equivalent; receipts keep provenance and replay protection;
removing any host adapter leaves PORTABLE and HEADLESS execution
usable; no workflow silently selects a privileged host. The matrix
must be assertable in CI with **no host present** (all-fallback
column green), or HEADLESS parity is a promise again. Renderers
consult the probe instead of sniffing per call. *(Provenance: all
three seats proposed this layer independently in round 1 — Codex
R9, Claude R9, Antigravity's R1 capability descriptor.)*

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
  `tests/unit/test_model_tiers_drift.py` as the alarm. Under the D2
  ruling the enum does not change: `LOCAL` is a routing label, all
  copies and the mirror stay three-member, and the drift guard
  continues to assert exactly that.
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

1. ~~Convene before ruling R1–R8?~~ Resolved: convened 2026-09-02,
   round 1 promoted (D5).
2. ~~Coverage floor~~ Ruled 2026-09-03: 90% (D7).
3. ~~D2 mechanics~~ Ruled: routing label (D2).
4. ~~Task 7 phasing~~ Ruled: the reranker ships alone on Phase A
   (D5).
5. ~~D6 — R2 enforcement locus~~ Ruled 2026-09-03: hybrid,
   subject-local (D6).
