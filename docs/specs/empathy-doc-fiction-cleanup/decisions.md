# Decisions — empathy-doc-fiction-cleanup

**Status:** approved (2026-06-26)

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
dead `EmpathyOS` integration, the fictional `encrypt_phi`, the dead
`EmpathyLLMExecutor`, and the unsupported HIPAA/GDPR/SOC2 "compliance
feature" claims.

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
