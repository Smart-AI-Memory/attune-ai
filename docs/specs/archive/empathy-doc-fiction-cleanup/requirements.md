# Requirements — empathy-doc-fiction-cleanup

**Status:** complete (2026-06-26) — executed in PR #1109; D7 correction #1115; reconciled at 2026-07-14 triage (was: approved)
**Owner:** Patrick + agent
**Origin:** documentation trailing edge of PR #1073
(`feat!: remove legacy Empathy framework (EmpathyOS + 5-level model)`,
9.0.0), which removed two things the docs still present as live.

---

## Problem

PR #1073 removed:

- **`EmpathyOS`** — the god-object entry point (`from attune import
  EmpathyOS`), documented as "main entry point for workflow execution".
- **The 5-level empathy model** — the "Empathy Level 1-5" framing.

The docs never followed. **~21 user-facing docs** still
`from attune import EmpathyOS` (verified `EmpathyOS` is gone from `src`;
it was real, added in `d92035dd8`, removed in `#1073` `8b753f494`), and
several are framed entirely on "Empathy Level N". Readers copy code that
ImportErrors, and clinical/healthcare docs sell features that don't
exist.

Two fiction layers, two dispositions (see `decisions.md`):

- **Generic docs** that merely *use* `EmpathyOS` (as a workflow runner,
  memory accessor, or LLM caller) → **repoint** to the live API.
- **Docs whose premise IS the dead fiction** (clinical/healthcare, or
  the empathy-level model) → **delete**.

---

## What is alive (preserve / repoint to) — code-verified 2026-06-26

`EmpathyOS` is gone, but everything it was bundled with survives:

- Memory/pattern API (`from attune import …`): `get_redis_memory`,
  `AccessTier`, `PatternLibrary`, `Pattern`, `StagedPattern`,
  `AttuneConfig`.
- Workflow execution (the EmpathyOS-as-runner successor):
  `from attune.workflows import <Workflow>` →
  `await <Workflow>().execute(...)`.
- LLM sub-island (name collides with the dead framework but is LIVE):
  `attune.llm.EmpathyLLM`, `attune.memory.PIIScrubber`,
  `attune.memory.SecretsDetector`, `attune.memory.security.AuditLogger`.

Also dead (remove, no successor): `AgentCoordinator`, `encrypt_phi`,
and HIPAA/GDPR/SOC2 "compliance feature" claims.

> **CORRECTION (2026-06-26, decisions-deadness-audit):**
> `EmpathyLLMExecutor` was originally listed here (and in G1 + the
> Deferred note + `tasks.md`) as dead. **It is ALIVE** — a real class at
> `attune.models.empathy_executor`, re-exported as
> `attune.models.EmpathyLLMExecutor`; both import paths resolve. No
> served doc lost content (`llm-toolkit.md` never documented it), and the
> orphaned doc that imports it was never broken. See decisions.md D7.

---

## Goals

- G1. No user-facing doc presents `EmpathyOS` (or `AgentCoordinator` /
  `encrypt_phi`) as a live API. (`EmpathyLLMExecutor` was struck from
  this list — it is alive; see the correction above.)
- G2. No user-facing doc is framed on the removed "Empathy Level N"
  model.
- G3. Every surviving code fence imports against `origin/main`
  (spot-checked by import).
- G4. Live symbols (`get_redis_memory`, `PatternLibrary`, `EmpathyLLM`,
  `PIIScrubber`, …) are preserved where docs legitimately use them.
- G5. Append-only history (`docs/specs/**`, bug logs) untouched.

---

## Out of scope

- The README/site "what is attune now" identity rewrite (deferred to
  Patrick — separate from removing dead symbols).
- Building any replacement for the empathy framework or HIPAA features.
- Non-`EmpathyOS` doc fiction not surfaced by this cleanup.

---

## Acceptance criteria (Done when)

- `git grep -nE 'import EmpathyOS|EmpathyOS\(|EmpathyOS\.|AgentCoordinator|
  encrypt_phi' -- docs/` returns only matches inside append-only history
  (`docs/specs/**`) — zero `EmpathyOS` god-object in user-facing docs.
- No "Empathy Level 1-5" *model framing* (the Reactive→Generative ladder)
  remains in surviving docs. **NOTE:** `target_level` is a LIVE parameter
  on `attune.llm.EmpathyLLM` (default 3); `EmpathyLLM(provider=,
  target_level=)` imports + constructs — it is NOT fiction and is
  preserved. Only the removed model/framework exposition is excised.
- Every code fence in the touched docs imports against `origin/main`.
- mkdocs nav/cross-links to deleted files pruned; `mkdocs build
  --strict` green.
- One PR, docs-only, CI green.

**~~Deferred to a follow-up (decisions.md D6): `EmpathyLLMExecutor`~~ —
WITHDRAWN (2026-06-26 audit).** `EmpathyLLMExecutor` is NOT dead — it is
a live class at `attune.models.empathy_executor`. The references in
`enhanced_escalation_architecture.md` and the social/generated files
import it correctly and were never broken. The "deferred cleanup" was
based on a false premise; its chip is moot. See decisions.md D7.

---

## See also

- `tasks.md` — per-file decision table + phased execution.
- `decisions.md` — D1-D5.
- `docs/specs/orchestration-doc-fiction-cleanup/` — prior art (same
  class, ran 2026-06-26, merged #1107).
- `.claude/rules/attune/removing-dead-code.md` — delete-vs-rewrite rule.
