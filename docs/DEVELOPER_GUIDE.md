---
description: Developer Guide — retired and redirected. The plugin-authoring content has been replaced by the current docs against real source.
---

# Developer Guide — retired

This guide has been retired as part of the
[`doc-fiction-cleanup`](specs/doc-fiction-cleanup/) Phase 2 sweep
(2026-05-30). The previous version's "Plugin Development" chapter
documented a `BaseWizard`-centric plugin model that is fiction; the
real plugin system is `BasePlugin`-centric.

## Read these instead

- **Plugin authoring:** [Plugin System](architecture/plugin-system.md)
  — the real `BasePlugin` / `register_mcp_tools()` contract, with
  reference subclass `RedisPlugin`.
- **Wizards:** [Wizards](reference/wizards.md) — the `attune.wizards`
  runtime and the 5 builtins (`debug`, `test-gen`, `refactor`,
  `security`, `release-prep`).
- **Security:** [Security Architecture](how-to/security-architecture.md)
  — `attune.security` primitives + the `SecurityAuditWorkflow`.

A more comprehensive Developer Guide may be authored in a future
spec; for now, the documents above cover contributor and
plugin-author surfaces against current source.
