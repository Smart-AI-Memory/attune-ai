# Spec: Collaboration Gates

> Bake the two collaboration gates — the **referent gate**
> ("go" needs one unambiguous referent) and the **spend gate**
> (the first billable call gets an explicit, estimated go) —
> into attune product behavior, so attune's agents *do* them
> rather than only describe them. v1 ships the enforceable
> half (spend gate) as a budget-envelope guardrail; the
> referent gate ships as guidance hardening in a later phase.

**Status:** complete (2026-06-09) — spend gate (R1–R8) shipped #637/#638/#639;
referent gate (R9/R10) shipped as advisory attune-hub guidance #694 (decisions.md
D13). See [`decisions.md`](decisions.md)
**Created:** 2026-06-05
**Owner:** Patrick
**Related:**

- [`feedback_go_referent_and_spend_gates`](~/.claude/memory/feedback_go_referent_and_spend_gates.md)
  — the two gates as private working discipline (the source)
- [`project_collaboration_gates_spec`](~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/project_collaboration_gates_spec.md)
  — the decision to productize them and the A/B asymmetry
- `attune-ai-dev/discipline/COLLABORATION_DISCIPLINE.md` §2 —
  the mutual contract these gates harden into product
- `src/attune/hooks/scripts/security_guard.py` /
  `worktree_path_guard.py` — the guardrail-hook pattern the
  spend gate mirrors
- `ATTUNE_MAX_BUDGET_USD` + the `Budget` dataclass — the
  existing cost-cap primitive the envelope reuses

---

## Problem statement

Two human↔agent failure modes are universal, not specific to
one collaboration:

1. **Surprise spend.** A terse `go` (or any pre-authorized
   work) sends an agent into a *first* billable API call with
   no explicit, estimated confirmation of the spend. A spec
   that budgets a phase authorizes the *work*, not a silent
   first charge.
2. **Ambiguous referent.** A terse `go` / `do it` / `y`
   executes against the wrong target when the prior turn left
   more than one candidate on the table.

These were named on 2026-06-05 as private working discipline
(the `feedback_go_referent_and_spend_gates` memory) after both
fired at once — an ambiguous `go` that resolved to a first Opus
charge. The discipline article (§2) frames them as part of the
**mutual contract**: the spend gate extends the "decision
point" list (scope expansion, version-bump, admin-merge,
irreversible side effects) with a new named point — *the first
billable call*; the referent gate is the *shorthand-as-
vocabulary primitive* plus *one-question-at-a-time*.

Patrick's call: these should become **attune product
behavior**, because they "will help users a lot." They are
universal failure modes, so attune enforcing the enforceable
half is real user value.

The crux is an **A/B enforceability asymmetry**:

- The **spend gate (B)** is genuinely enforceable inside
  attune's own surfaces — the CLI, dashboard runner, and
  workflow layer all control the moment of the first paid call.
  A guardrail (estimate → confirm → session-durable) is
  concrete and buildable, mirroring `security_guard.py`.
- The **referent gate (A)** is mostly advisory — it lives in
  the Claude Code conversational layer, which attune doesn't
  control programmatically. But it has a **partial enforcement
  foothold**: attune's *own* interactive surfaces (wizards, the
  Socratic `AskUserQuestion` flow, the dashboard run button)
  can enforce single-referent resolution within attune's UX.

The guardrail is a **safety net, not a replacement for
judgment** — consistent with the article's thesis that this is
a *discipline*, not a tool problem. attune catches the failure
mode; it does not automate the contract.

---

## Goals

1. **Spend gate as enforced product behavior (v1).** Before
   the first billable call of a session, attune surfaces a cost
   estimate and an explicit confirm; after the confirm, the
   spend is durably authorized for the session within a
   **budget envelope**. Subsequent runs proceed silently within
   the envelope; a run that would breach it re-gates.
2. **Align with Anthropic's own model.** The gate gates against
   *whichever meter the user is actually on* — dollars for API
   users, rate-limit / usage headroom for subscription users —
   not a parallel dollar meter that reads $0 for subscription
   users.
3. **Referent gate as guidance hardening (later phase).**
   Strengthen single-referent resolution in attune's own
   interactive surfaces and via skill/Socratic guidance;
   document it honestly as advisory in the broader conversation.
4. **Honest scoping.** Ship the enforceable half well rather
   than over-claiming enforcement of the advisory half.

---

## Scope

### v1 (this spec, Phase 1 implementation)

- **Spend gate**, enforced, **CLI surface first**
  (`attune workflow run`), budget-envelope model.
- Reuses `ATTUNE_MAX_BUDGET_USD` + the `Budget` dataclass and
  the existing cost-estimation machinery
  (`cost_mixin`, `tier_recommender`).
- Subscription-vs-API detection drives which meter the gate
  reads.

### Later phases (in this spec, deferred)

- Spend gate on the **dashboard runner** (confirm modal) and
  the **workflow/MCP layer** (agent-invoked runs), reusing the
  v1 estimate-and-gate core.
- **Referent gate** guidance hardening + partial enforcement in
  attune's interactive surfaces.

### Out of scope

- Enforcing the referent gate in the Claude Code conversational
  layer (not attune-controllable).
- Replacing or duplicating Anthropic's own account-level usage
  limits — attune gates *before* hitting them, it does not
  re-implement them.
- Per-token live metering UI; the gate is a pre-call envelope,
  not a streaming meter.

---

## Requirements

Spend gate (v1, CLI surface):

- **R1 — First-call confirm.** The first billable workflow call
  of a session surfaces, before the call is made: (a) what will
  run, (b) an estimate against the active meter, (c) the
  session budget envelope, and requires an explicit confirm.
- **R2 — Estimate.** The estimate is derived from existing cost
  machinery (workflow tier × expected calls), presented in the
  unit of the active meter (≈ dollars for API; usage-headroom
  framing for subscription).
- **R3 — Session-durable authorization.** After the confirm,
  further billable runs within the envelope proceed without
  re-prompting for the rest of the session (mirrors the §6
  admin-merge-authorization-durability pattern).
- **R4 — Envelope breach re-gates.** A run that would push
  cumulative session spend past the envelope re-prompts with the
  breach amount, even after R3.
- **R5 — Meter alignment.** The gate detects subscription-vs-API
  mode and gates against the correct meter; it never shows a
  misleading $0 to a subscription user.
- **R6 — Off switch.** A budget of 0 / a documented env var
  disables the gate entirely (heuristic-free path), consistent
  with the existing `ATTUNE_MAX_BUDGET_USD=0` semantics.
- **R7 — Non-interactive safety.** In a non-interactive context
  (no TTY), the gate fails *safe* per a documented policy
  (block-by-default or proceed-within-a-conservative-default —
  resolved in design), never silently launching an unbounded
  paid run.
- **R8 — Free/local actions never trip it.** Reads, tests,
  Ollama/local models, file ops, `gh`, `git` never gate.

Referent gate (later phase — captured now so the spec is
whole):

- **R9 — Single-referent resolution in attune UX.** attune's
  own interactive surfaces resolve a terse confirm to exactly
  one action, or ask which, before executing.
- **R10 — Honest advisory framing.** Documentation states
  plainly that the referent gate is advisory in the broader
  conversational layer and enforced only within attune's UX.

---

## Acceptance criteria

v1 is done when:

- `attune workflow run <paid-workflow>` surfaces an estimate +
  confirm on the first billable call of a session and proceeds
  silently within the envelope thereafter (R1–R4), demonstrated
  by a real CLI run (dogfood, not only unit tests).
- A subscription-mode run shows headroom framing, not $0
  (R5), verified with both auth modes mocked.
- The off switch disables the gate (R6) and free/local actions
  never gate (R8), both covered by tests.
- Non-interactive behavior matches the documented fail-safe
  policy (R7), covered by a test.
- `decisions.md` logs the gate model, surface order, meter
  alignment, and the fail-safe policy.
- A regression guard locks the "first paid call without confirm
  is impossible when the gate is on" invariant.

---

## Open design questions (resolved in design.md)

1. **What is a "session" for the CLI?** Each `attune workflow
   run` is a fresh process. Candidates: a TTL'd state file under
   `~/.attune/`, a session id, or tying the envelope to
   Anthropic's own rolling-window. Determines how R3 persists.
2. **Estimate source of truth.** Which existing function
   produces the pre-call estimate, and its accuracy band.
3. **Subscription-meter framing.** Exactly how usage-headroom is
   surfaced when there is no dollar figure (R5).
4. **Fail-safe policy for R7** — block-by-default vs
   conservative-default-proceed.
5. **Where the gate logic lives** — a shared estimate-and-gate
   core callable by all three future surfaces, vs CLI-local v1
   code refactored later.
