# Coverage `omit` list audit (QA #6, 2026-06-14)

**Question:** are the modules in `pyproject.toml`'s
`[tool.coverage.run] omit` genuinely untestable, or just untested?

**Method:** for each entry whose comment claims a testability-blocking
reason ("Requires LLM API calls", "Interactive", "Requires Redis",
server), probe (a) does it import cleanly **keyless**
(`ANTHROPIC_API_KEY=""`) — i.e. is the external dep needed at import or
only at call time? and (b) its nature (dataclass / parsing / CLI /
server / shim). Obvious excludes (`__init__.py`, `__main__.py`,
`*_example.py`, deprecated `agent_factory` adapters, the `config.py`
shadow) were not re-litigated.

**Headline:** nearly every "untestable" module imports fine keyless —
the external dependency is used at **call** time, so it is mockable.
The omit comments describe *why a naive test would hit the network*,
not an actual testability barrier. Several entries are mislabeled
(dataclasses/shims tagged "Requires LLM API calls") and two are stale.

---

## Tier 1 — Stale / ineffective omits (remove; no testing needed)

| Entry | Finding |
|-------|---------|
| `*/cache/hybrid.py` | `src/attune/cache/` does not exist — file deleted. Dead entry. |
| `*/memory/cross_session.py` | Real file is `memory/short_term/cross_session.py`; the glob `*/memory/cross_session.py` does **not** match it, so the omit is a no-op (the file is measured normally or not at all). Fix the path or drop it. |

---

## Tier 2 — Mislabeled / wrongly omitted, high-ROI (convert)

All import keyless; the "LLM/Redis" reason is an optional `try/except`
import or a call-time dependency, not an import barrier.

| Entry | loc | Real nature | Note |
|-------|-----|-------------|------|
| `agents/release/release_models.py` | 206 | Enums + `@dataclass` + config constants | "Requires LLM API calls" is wrong — pure data types. Trivially testable. |
| `agents/release/release_parsing.py` | 60 | Pure parsing functions | Testable with literal inputs; no LLM. |
| `agents/release/release_agents.py` | 27 | Re-export shim | One import test ≈ 100%. |
| `agents/release/release_prep_team.py` | 420 | Orchestration (redis + llm at call time) | Mockable like `base_agent` (#896) — larger effort. |
| `memory/claude_memory.py` | 309 | dataclasses + Claude at call time | Mock the client (cf. research_synthesis #892). |
| `monitoring/otel_backend.py` | 268 | plain logic | Mock the otel SDK. |
| `orchestration/_strategies/base.py` | 203 | plain logic / abstract base | Testable directly. |
| `orchestration/execution_strategies.py` | 109 | plain logic | "Requires live agents" → inject mock agents. |
| `core_modules/short_term_memory.py` | 222 | redis at call time | Mock redis. |
| `meta_workflows/cli_commands/memory_commands.py` | 137 | plain logic | cf. existing `cli_commands` tests. |
| `meta_workflows/cli_commands/analytics_commands.py` | 323 | plain logic | "" |
| `meta_workflows/cli_commands/agent_commands.py` | 248 | plain logic | "" |
| `meta_workflows/cli_commands/template_commands.py` | 268 | logic | "" |
| `meta_workflows/cli_commands/config_commands.py` | 170 | logic | "" |

---

## Tier 3 — Testable, lower ROI (more harness effort)

| Entry | loc | Why harder |
|-------|-----|-----------|
| `models/auth_cli.py` | 343 | `input()`-driven; mock stdin/Prompt. |
| `monitoring/alerts_cli.py` | 344 | interactive CLI. |
| `core_modules/interaction.py` | 164 | interactive prompts. |
| `memory/control_panel_api.py` | 328 | FastAPI — coverable via `TestClient`. |
| `memory/short_term/sessions.py` | 191 | redis-mockable (partly addressed in QA #5). |
| `socratic/collaboration*.py` | ~500 | external collab service; verify not deprecated before investing. |

---

## Tier 4 — Keep omitted (genuinely not unit-testable)

`mcp/server.py` (live protocol server),
`project_index/scanner_parallel.py` (multiprocessing),
`project_index/index.py` (integration-tested), all `__init__.py` /
`__main__.py` package/entry stubs, `*_example.py`, deprecated
`agent_factory/*` adapters, and `config.py` (import-shadowed).
(`workflows/progress_server.py` was DELETED 2026-07-30 — zero
importers, gated on `websockets` which was never a declared dep,
so it could not even instantiate in the shipped package; its omit
entry went with it.)

**Second pass done (2026-07-16):** hook scripts and `config.py` ARE
well-covered — the reason they read 0% in whole-repo baselines is a
measurement artifact, not an absence of tests. Both are loaded via
`importlib.util.spec_from_file_location` under a synthetic module
name (bypassing normal package import, by design — `config.py` for
legacy re-export, hook scripts so they run standalone without the
full `attune` package). `--cov=<dotted.module>` requires that exact
import to happen and never sees them; a path-scoped `--cov=<dir>`
does. Real numbers: `config.py` 98%, `worktree_path_guard.py` 93%,
`starter_reconciler.py` 95%. The one genuine gap in this class:
`hooks/scripts/_bootstrap.py` (24 lines, confirmed 0% under both
measurement methods). See `.claude/lessons.md` "coverage baseline
misreports spec_from_file_location-loaded modules" and the fix in
`scripts/qa_coverage_baseline.sh`.

---

## Recommendations

1. **Quick win:** delete the two Tier-1 stale entries.
2. **Backlog:** convert Tier-2 one module per PR, cheapest first —
   `release_models.py`, `release_parsing.py`, `release_agents.py` are
   near-free. Each conversion = remove its `omit` line **and** add a
   net-new test (the `omit`-line removal makes the PR out-of-class →
   needs human merge; pure test additions without removing `omit`
   would not count toward measured coverage).
3. **Hygiene:** the `omit` comments should state the *real* reason.
   "Requires LLM API calls" on a dataclasses file is how this debt
   accumulated — a module gets parked in `omit` once and the label is
   never revisited. Consider a periodic re-audit (this doc) and/or a
   check that flags `omit` entries whose files import cleanly keyless.

**Caveat:** this audit covers the "claims-untestable" entries, not the
hook scripts or every `__init__`. Tier-2 alone is ~2,000 statements of
currently-unmeasured, testable code.

---

## Pass 2 — 2026-07-29 (#1569, chair-directed)

**Method:** one scoped coverage run over each candidate's own test
files (subset lower bound — a module clearing the bar in subset is
proven; more tests only raise it). 1027 tests, keyless, serial.

**Converted (removed from omit — measured, labels were false):**

| Entry | Claimed reason | Measured |
|-------|----------------|----------|
| `agents/release/release_prep_team.py` | "Requires LLM API calls" | 100% (#1740/#1741 suites) |
| `monitoring/otel_backend.py` | "Requires OpenTelemetry SDK" | 100% (3 dedicated suites) |
| `orchestration/execution_strategies.py` | "Requires live agents" | 94% (unit consumers) |
| `meta_workflows/cli_commands/config_commands.py` | "Interactive" | 100% |
| `meta_workflows/cli_commands/memory_commands.py` | "Interactive" | 100% |
| `meta_workflows/cli_commands/template_commands.py` | "Interactive" | 100% |
| `meta_workflows/cli_commands/analytics_commands.py` | "Interactive" | 99% |
| `meta_workflows/cli_commands/agent_commands.py` | "Interactive... live Claude agent loop" | 99% |

**Removed as dead:** `*/memory/cross_session.py` — the glob matches
no file on disk (real module: `memory/short_term/cross_session.py`).

**Kept omitted with honest state (measured low — need tests first):**

| Entry | Measured | Note |
|-------|----------|------|
| `orchestration/_strategies/base.py` | 46% | Label corrected to justified-other; QA-pass candidate |
| `project_index/index.py` | 18% | Comment's "(integration-tested)" claim stands; unit gap real |
| `project_index/scanner_parallel.py` | 17% | Same |

Not probed this pass (bounded scope): `core_modules/short_term_memory.py`
(integration-only evidence), `memory/short_term/sessions.py`,
`memory/control_panel_api.py`, the hook scripts, and the init/entry
excludes. Net effect: ~930 statements of ~99%-covered production code
re-enter the measured denominator — the project total RISES.
