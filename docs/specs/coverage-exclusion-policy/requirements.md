# Spec: Coverage Exclusion Policy

**Status**: approved
**Created**: 2026-05-10
**Origin**: Surfaced during reflection on the 100%-coverage workstream
(see COVERAGE_BUG_LOG.md). Reframed the goal from "every module at
100%" to "every module either at 100% or *knowingly excluded with
a documented reason*."

---

## Phase 1: Requirements

### Why

The 100%-coverage workstream has been treating coverage as a
percentage to maximize. That framing breaks down for code that
genuinely shouldn't be covered by the standard CI gate:
infrastructure stubs, interactive CLIs, modules requiring live
external services (Redis, Claude API, FastAPI server), deprecated
shims awaiting removal.

The current convention — `[tool.coverage.run] omit = [...]` in
`pyproject.toml` — is being used informally. Some entries have
inline `#` comments explaining why; some don't. The audit
(2026-05-10) found:

- 64 total omit entries
- 4 obvious meta-excludes (`*/tests/*`, `*/test_*.py`,
  `*/__pycache__/*`, `*/site-packages/*`) — no comment needed
- 57 entries with inline `# reason here` comments — meets the
  policy
- **3 production-code entries with no documented reason**:
  - `*/hooks/scripts/help_freshness_nudge.py`
  - `*/meta_workflows/cli_commands/agent_commands.py`
  - `*/attune/config.py`

### Goals

- **G1.** Every entry in `[tool.coverage.run] omit` for production
  code (i.e. anything under `src/attune/` or `attune_software/`)
  has an inline `#` comment stating *why* it's excluded. The
  reason should fall into one of the named categories below.
- **G2.** Meta-excludes (test discovery patterns, build artifacts,
  third-party paths) do not need a `#` comment — the pattern
  itself is self-explanatory.
- **G3.** A documented exclusion category taxonomy lives alongside
  the omit list, so future contributors know what shape a valid
  reason takes.
- **G4.** The 3 currently-undocumented entries either get a
  documented reason OR get covered by tests. Pure paperwork is not
  the goal — the audit is a forcing function for the question
  "should this actually be covered?"
- **G5.** A lightweight enforcement mechanism (script or
  pre-commit hook) catches new omit additions that lack
  documentation. Optional for Phase A; required for spec close.

### Documented exclusion categories

Each omit entry's reason should fit one of these. Future
additions should pick a category and explain the specific
instance.

1. **Interactive CLI** — requires TTY, user input, or interactive
   prompts. Not unit-testable as-is. Example:
   `auth_cli.py`, `alerts_cli.py`.
2. **Infrastructure server** — long-running HTTP/WebSocket/MCP
   server. Tested via integration suite or end-to-end smoke tests.
   Example: `mcp/server.py`, `progress_server.py`.
3. **Live external service required** — module fundamentally
   requires Redis, Claude API, or another live external service.
   Mocking is unfaithful (see `redis-decoupling` spec for the
   companion cleanup). Example: `redis_short_term/sessions.py`.
4. **Deprecated module pending removal** — code that's deprecated
   and scheduled for retirement. Excluded so coverage isn't
   blocked by code about to be deleted. Example:
   `*/scaffolding/cli.py` until v7.0 retirement.
5. **Optional dependency adapter** — adapter module for an
   optional package that may not be installed in CI (`crewai`,
   `langchain`, etc.). Example:
   `agent_factory/adapters/crewai_adapter.py`.
6. **Standalone script** — runs as a subprocess via Claude Code
   hooks or similar; not importable through pytest's normal
   collection. Example:
   `hooks/scripts/help_freshness_nudge.py`.
7. **Example/demo code** — illustrative, not production. Example:
   `wizards/customer_support_wizard.py`.
8. **Justified-other** — doesn't fit categories 1-7 but has a
   compelling reason. The reason text should be longer than usual
   to justify the category miss.

### Non-goals

- **Not redesigning the coverage tool.** This spec uses
  `[tool.coverage.run] omit` as it is. No move to per-file
  `# pragma: no cover`, no separate exclusion file format.
- **Not lowering the 85% gate.** The CI threshold stays at 85%
  (or higher); this spec is about which files the gate applies
  to, not the gate itself.
- **Not auditing test files.** `tests/` exclusions and ignored
  test files are handled by `docs/specs/ignored-tests/` (closed
  2026-05-09).
- **Not requiring 100% on the *included* set.** That's the
  ongoing 100%-coverage workstream's concern. This spec is the
  *denominator* policy; that workstream is the *numerator* push.

### Public-API impact

None. This is internal policy + tooling. No PyPI consumer sees a
behavior change.
