# Decisions: Collaboration Gates

> Records design decisions and deviations. Companion to
> [`requirements.md`](requirements.md) and (later)
> `design.md` / `tasks.md`. Timestamps are the arbiter when a
> later session wants to relitigate.

**Status:** in progress
**Last updated:** 2026-06-05

---

## Phase 1 — Requirements interview (2026-06-05)

### D1 — v1 scope: spend gate enforced, referent gate phased

The A/B enforceability asymmetry routes the scope. v1 ships the
**spend gate (B)** as real enforced product behavior; the
**referent gate (A)** ships as guidance hardening in a later
phase of the same spec, scoped honestly as advisory in the
broader conversational layer with a partial-enforcement foothold
in attune's own interactive surfaces. Chosen over "spend gate
only" (leaves A unaddressed) and "both gates, full treatment"
(speculative on A's enforceability).

### D2 — Gate model: budget envelope, first-run confirm establishes it

The spend gate is a **budget envelope**, not a per-call confirm.
The first paid run of a session surfaces the estimate + the
envelope and requires an explicit go — which both honors the
discipline's explicit-first-spend rule *and* establishes the
envelope. Subsequent runs proceed silently within it; a breach
re-gates.

Chosen over (a) **confirm-per-first-spend** (the literal
memory wording — but naggy, and reads $0 for subscription users
so it doesn't align with Anthropic's usage model) and (b)
**pure budget cap** (most Anthropic-aligned, least naggy — but
drops the explicit-first-spend "go" entirely; a first surprise
charge under the cap never surfaces).

Originated from Patrick's pushback on the surface question:
"should we use [a per-call confirm] OR a budget that aligns and
works well with Anthropic's system." The envelope model is the
synthesis — it absorbs the budget framing while preserving the
discipline's first-spend go.

Reuses the existing `ATTUNE_MAX_BUDGET_USD` + `Budget` dataclass
rather than inventing a new primitive.

### D3 — Meter alignment: gate against the user's actual meter

"Aligns with Anthropic's system" means the gate gates against
**whichever meter the user is on** — dollars for API users,
rate-limit / usage headroom for subscription users — not a
parallel dollar meter. This avoids the misleading $0 a
dollars-only gate would show a subscription user (Patrick's own
case: `feedback_workflow_output` — "cost figures don't apply,
subscription not API"). Subscription-vs-API detection drives
the framing.

### D4 — First surface: CLI

The enforced spend-gate confirm lands on the **CLI**
(`attune workflow run`) first — simplest interactive confirm,
console-first user, fastest to a shippable PR. Dashboard runner
(confirm modal) and the workflow/MCP layer (agent-invoked,
non-interactive — hardest UX) follow in later phases reusing the
v1 estimate-and-gate core. Patrick leaned to this; taken as the
working decision, reversible at requirements approval.

### D5 — Guardrail framing, not automation

Per the discipline article's thesis (this is a *discipline*, not
a tool problem), the spend gate is framed as a **safety net**
like `security_guard.py` — it catches the surprise-spend failure
mode; it does not automate the §2 contract or substitute for
human judgment.

---

## Phase 2 — Design (2026-06-05)

Grounded against the real machinery before writing (per the
"introspect before coding" lesson): `cmd_workflow_run`
(`cli_commands/workflow_commands.py`), `AuthStrategy`/`AuthMode`
(`models/auth_strategy.py`), the `Budget` dataclass
(`ops/session_summarizer.py:120`), `get_max_budget_usd` +
`ATTUNE_MAX_BUDGET_USD` (`workflows/agent_sdk_adapter.py`), and
the `~/.attune/session_stash` state-file pattern
(`memory/file_stash.py:88`).

### D6 — CLI "session" = a TTL'd envelope file aligned to Anthropic's window

Each `attune workflow run` is a fresh process, so R3's
session-durable authorization persists in
`~/.attune/spend_gate/envelope.json`. The "session" is a **TTL
window** defaulting to Anthropic's rolling usage window (5h), so
the gate's notion of "this session" matches the meter it gates
against. Rejected: binding to `CLAUDE_CODE_SESSION_ID` (absent
in bare-terminal runs), pure in-memory (re-gates every run),
per-calendar-day (misaligned with the rolling window).

### D7 — Estimate is a budget *band*, not false precision

Pre-call cost is unknowable, so the estimate is the workflow's
budget band: `get_max_budget_usd(depth)` as the ceiling,
`AuthStrategy.estimate_cost` as the expected band when a target
size is known. Presented as "≈ up to $X," never a fake single
figure. Honest per the §2 honesty-about-limits clause.

### D8 — Meter framing resolves per auth mode

`gates/meter.py` reads `AuthStrategy` → `AuthMode`. API mode →
dollar framing; subscription mode → usage-headroom framing (no
dollar figure, no misleading $0, satisfying R5). The envelope
tracks dollars in API mode and run-count/window in subscription
mode.

### D9 — Gate logic lives in a shared `attune.gates` core

New package `src/attune/gates/` (`spend_gate.py`, `envelope.py`,
`meter.py`). The core returns a `GateDecision`
(`proceed`/`confirm`/`block`); the **surface** owns confirm I/O.
v1 wires the CLI; dashboard + MCP reuse the core later. Rejected:
CLI-local code refactored later (would drift between surfaces).

### D10 — Non-interactive fail-safe = block-by-default + explicit env pre-auth

No TTY + first paid call + no pre-auth → **block** (never spend
silently). `ATTUNE_SPEND_GATE_AUTHORIZED=1` (or a set budget)
opts CI / the ops daemon in explicitly; the existing
`ATTUNE_MAX_BUDGET_USD` cap still bounds any proceeding run. This
translates the discipline's "first paid call gets an explicit
go" into a machine context as an explicit env grant.

---

## Phase 1 — Implementation deviations

### D11 — T4 touches more files than tasks.md listed (machine-caller opt-ins)

`tasks.md` T4 named only `workflow_commands.py` + its test. But the
gated path (`attune workflow run`) is **shared by non-interactive
machine callers** that the D10 fail-safe would otherwise block —
discovered when wiring the CLI (verify-first against the real
callers, not the spec's assumption). T4 therefore also:

- **`src/attune/cli_commands/_exit_codes.py`** — added an optional,
  additive `on_result` hook (best-effort, guarded) so the CLI can
  record actual cost into the envelope (R4) without the runner
  returning the result. Exit-code semantics unchanged
  (workflow-failure-exit-propagation contract preserved).
- **`src/attune/ops/runner.py`** — the dashboard daemon spawns the
  CLI non-interactively, so its subprocess env gets
  `ATTUNE_SPEND_GATE_AUTHORIZED=1` (the D10 machine-context "go").
  The dashboard's *own confirm modal* remains a later phase; this
  just keeps today's dashboard runs working rather than blocking.
- **`.github/workflows/security-scan.yml`** — the one CI workflow
  that actually runs `attune workflow run` (security-audit) gets the
  same explicit opt-in. (`scorecard.yml` / `windows-debug.yml` only
  mention "workflow run" in prose — they don't invoke the CLI.)
- **Test opt-out** — `ATTUNE_SPEND_GATE=off` autouse fixtures in the
  three pre-gate test files that exercise `cmd_workflow_run`
  (`test_workflow_commands.py`, `test_workflow_exit_codes.py`,
  `test_voice_wiring.py`) so they test dispatch/exit-codes/voice, not
  the gate. New `test_workflow_spend_gate.py` covers the CLI surface.

Approved 2026-06-05 (Patrick: "Full T4 with opt-ins"). The MCP-layer
gating for agent-invoked runs remains deferred to a later phase.
