# Spec: Documentation Fiction Cleanup

> A cluster of project docs describe APIs that do not exist —
> dead import paths (`attune_llm`, `coach_wizards`,
> `attune.webhooks`) and feature surfaces that were never built
> as documented. Bring the docs back in line with the real
> source, retiring what describes nothing real and rewriting
> what describes a real feature through a fictional API.

**Status:** complete — cleanup executed (see decisions.md); audit/process doc, not a shippable feature — verified 2026-06-08 spec triage
**Created:** 2026-05-28
**Owner:** TBD
**Related:** [`sdk-error-message-fidelity`](../sdk-error-message-fidelity/)
(why the `doc-audit` workflow couldn't be used for triage — see
below); [`decisions.md`](decisions.md); [`tasks.md`](tasks.md)

---

## Problem statement

Two overlapping problems make a body of documentation actively
misleading — a reader who copy-pastes from these docs hits an
immediate `ModuleNotFoundError` or `AttributeError`.

1. **Dead import paths (mechanical).** 21 docs under `docs/`
   still import from `attune_llm`, the package's old name before
   the `attune_llm` -> `attune` rename. The symbols usually
   still exist; only the package prefix is wrong.

2. **Structural fiction (substantive).** A smaller set of docs
   describe entire APIs that never shipped as written:
   - `attune.webhooks` package with `SlackWebhook` / `JiraWebhook`
     classes (real surface: one hook action, `HookType.WEBHOOK`
     -> `HookExecutor._execute_webhook`).
   - `coach_wizards` with 16 named wizard classes, and an
     industry-wizard taxonomy (Healthcare / Finance / Legal)
     (real surface: 5 config-driven builtin wizards in
     `src/attune/wizards/builtin/`).
   - A wizard-centric plugin model with `BaseWizard` /
     `register_wizards()` (real surface: workflow-centric
     `BasePlugin` / `register_mcp_tools()`).
   - A PII-scrub -> secrets -> audit -> LLM runtime "security
     architecture" (real surface: the SDK-subagent
     `SecurityAuditWorkflow` plus `attune.security` primitives).

### Why this went undetected

The `.help` staleness system only tracks docs listed under a
feature's `doc_paths` in `.help/features.yaml`. Most of the
fiction lives in docs that are NOT listed there (examples,
guides, top-level narratives), so they never appear in
`attune-author status` and never raised a staleness flag. The
tracked surface (30 docs) was triaged this session; the wider
cluster (27 docs total touching the fiction markers) was
discovered only by grepping for the dead package names.

### Why `doc-audit` couldn't do the triage

The intended tool — `attune workflow run doc-audit` — is
currently unrunnable from inside a Claude Code session: the
underlying `claude_agent_sdk.query()` subprocess completes the
turn but exits code 1 on teardown, and the SDK discards the
result. See [`sdk-error-message-fidelity`](../sdk-error-message-fidelity/)
and the memory note `project_sdk_workflows_blocked_nested`. The
30-doc triage was therefore done directly by in-harness
subagents comparing each doc's claims against current source.

---

## Scope

In scope: every doc under `docs/` (excluding `docs/archive/`,
which mkdocs already excludes from the build) that either
references a dead import path or describes a fictional feature
surface.

Out of scope: docs whose only drift is cosmetic (frontmatter
hash, prose) and whose claims still verify against source — the
8 "formatting-only" docs from the triage. They can be picked up
by the normal `.help` regen cycle.

---

## Acceptance criteria

- No doc under `docs/` (outside `docs/archive/`) imports from
  `attune_llm`, `coach_wizards`, or `attune.webhooks`.
- Every retained doc's concrete claims (class names, imports,
  CLI commands, signatures, counts) verify against current
  source.
- `mkdocs build --strict` passes (no broken internal links from
  retired docs).
- `.help/features.yaml` `doc_paths` reference only docs that
  still exist.
- Retired docs are removed from mkdocs nav, `features.yaml`, and
  all inbound links.
