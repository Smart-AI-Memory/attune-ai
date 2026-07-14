# Decisions — empathy-doc-fiction-cleanup

**Status:** complete (2026-06-26) — executed in PR #1109; D7 correction #1115; reconciled at 2026-07-14 triage (was: approved)

---

## D1 — Delete on *premise*, not on keyword count (Patrick, 2026-06-26)

A naive "delete every doc that mentions a clinical word" was rejected:
the healthcare-keyword count (`hc`) is a *theme* signal, not a binary.
Real, accurate docs (`unified-memory-system`, `redis-setup`,
`smart-router`, `simple-chatbot`, …) mention "patient"/"compliance" once
in an example but are legitimate infrastructure/usage docs — deleting
them would discard true content over an incidental keyword. The line is
**does the doc's PREMISE depend on the dead fiction?**

- Premise IS the dead clinical/empathy-framework feature → **delete**.
- Real doc that merely *uses* `EmpathyOS` → **repoint**, keep the doc.

Patrick's calls: "SBAR can be deleted" and "[healthcare-premise docs]
can be deleted" — applied as premise-based, not count-based.

---

## D2 — `EmpathyOS` repoints to the live API; it is not revived

`EmpathyOS` (the removed god-object) had three documented roles, each
with a live successor (all code-verified 2026-06-26):

- **Workflow runner** → `from attune.workflows import <Workflow>` then
  `await <Workflow>().execute(...)`.
- **Memory / pattern accessor** → the still-exported companions
  `get_redis_memory`, `AccessTier`, `PatternLibrary`, `Pattern`,
  `StagedPattern`, `AttuneConfig` (all `from attune import …`).
- **LLM caller** → `attune.llm.EmpathyLLM` (ALIVE — see D3).

A fence whose `EmpathyOS` use relied on a method with NO successor is
deleted with its prose, not faked onto a replacement.

---

## D3 — The `EmpathyLLM` sub-island is LIVE — do not delete on the name

`attune.llm.EmpathyLLM`, `attune.memory.PIIScrubber`,
`attune.memory.SecretsDetector`, and `attune.memory.security.AuditLogger`
are alive and are real workflow infra. The "Empathy" name collides with
the dead framework but the code is current. `reference/llm-toolkit.md`
is therefore **repoint/excise, NOT delete**: keep the `EmpathyLLM` /
`PIIScrubber` / `SecretsDetector` / `AuditLogger` content; remove the
dead `EmpathyOS` integration, the fictional `encrypt_phi`, and the
unsupported HIPAA/GDPR/SOC2 "compliance feature" claims. (This line
originally also listed `EmpathyLLMExecutor` as dead — it is NOT; see
D7. llm-toolkit.md never documented it, so nothing changed in practice.)

---

## D4 — Empathy-level-framed docs are deleted

Docs built on the removed "Empathy Level 1-5" model
(`adaptive-learning-system.md`, both `examples/` and
`tutorials/examples/` copies — `el=12`/`11`) document a framework that
no longer exists. Per `removing-dead-code.md` they are deleted, not
rewritten (no successor for "empathy levels").

---

## D5 — Append-only history is left untouched

`docs/specs/**` (incl. this spec and the archived `doc-fiction-cleanup`)
and bug logs legitimately name the removed symbols as history. Excluded
from the acceptance grep.

---

## D6 — scope corrected at execution: `target_level` is LIVE; `EmpathyLLMExecutor` deferred (2026-06-26)

Two execution-time corrections, both from grepping the FULL dead-symbol
set instead of the initial `import EmpathyOS` inventory:

1. **`target_level` is NOT fiction — it is a live param.** The initial
   plan flagged `target_level=N` / `EmpathyLLM(provider=…)` as dead
   (empathy-level model). Verifying the signature corrected this:
   `attune.llm.EmpathyLLM.__init__(provider='anthropic',
   target_level: int = 3, …)` — `EmpathyLLM(provider='anthropic',
   target_level=4)` imports and constructs (a no-API-key ValueError is a
   runtime gate, not an import error). The 5-level *model framing* (the
   Reactive→Generative ladder prose) was removed; the surviving
   `target_level` param and `EmpathyLLM(...)` usages are PRESERVED.
   `docs/reference/TROUBLESHOOTING.md`, `llm-toolkit.md:33`, and
   `persistence.md:372` were nearly mass-rewritten on the bad grep —
   verifying the signature first avoided breaking valid docs.

2. **`EmpathyLLMExecutor` is a DISTINCT dead symbol — deferred.** The
   `import EmpathyOS` inventory undercounted: `EmpathyLLMExecutor`
   (gone from `attune.models`) still appears in
   `architecture/enhanced_escalation_architecture.md`, two
   `blog/social/*_claude_costs.md` drafts, and the generated
   `plugin/help/generated/faqs/models.md`. It is a separate symbol on
   social + generated surfaces (the generated one needs a help-source
   fix + regen), so it is tracked as its own follow-up rather than
   sprawling this PR. Lesson: inventory with the FULL acceptance grep,
   not one symbol (pairs with "spec scope drifts from code reality").

---

## D7 — CORRECTION of D6: `EmpathyLLMExecutor` is ALIVE, not dead (decisions-deadness-audit, 2026-06-26)

D6 (and requirements.md G1 + the Deferred note + tasks.md) asserted
`EmpathyLLMExecutor` is a "distinct dead symbol ... gone from
`attune.models`." **That is wrong.** Verified:

```text
from attune.models import EmpathyLLMExecutor            # works
from attune.models.empathy_executor import EmpathyLLMExecutor  # works
type(EmpathyLLMExecutor) is type  # a real class, module attune.models.empathy_executor
```

Consequences, all benign:

- **No content was lost.** `reference/llm-toolkit.md` never documented
  `EmpathyLLMExecutor` (checked the pre-#1109 revision — zero mentions),
  so the cleanup removed nothing real. Its `EmpathyLLM` / `PIIScrubber`
  / `SecretsDetector` / `AuditLogger` content is intact and correct.
- **The orphaned doc was never broken.**
  `enhanced_escalation_architecture.md:365`'s
  `from attune.models.empathy_executor import EmpathyLLMExecutor`
  imports fine; the social/generated references likewise.
- **The deferred chip (`task_673b87a1`) is moot** — there is no dead
  `EmpathyLLMExecutor` to clean.

Root cause: deadness was INFERRED from the empathy-framework removal +
the shared "Empathy" name, not verified by import — the exact trap D6
itself warned about for `target_level`, repeated one symbol over. This
is why the doc-fiction triage now requires locating the symbol in `src/`
(`grep "class <Sym>"` + probe submodule paths) before ANY "dead" label.
