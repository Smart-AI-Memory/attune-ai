# Decisions — Discovery Sweep

**Status:** approved

Context, motivation, and load-bearing design decisions for a meta-workflow that fans out across the audit-family workflows and triages their findings into act-on-now / drop / ask-human buckets.

See `requirements.md` for user stories, `design.md` for the technical shape, `tasks.md` for the phased plan.

> **DECIDE callouts** mark choices made on partial information. Resolve each before the implementation phase that depends on it. Search the spec for `**DECIDE:**` to find them.

---

## Why this exists

The audit-family workflows (`bug-predict`, `security-audit`, `dependency-check`, `perf-audit`, `doc-audit`, `test-audit`) each:

- Run an independent agent loop with its own subagents
- Emit findings in narrative text via `WorkflowResult.final_output`
- Are invoked one at a time by a developer who has to remember which one to run when
- Charge a separate budget per invocation

Two problems flow from this:

1. **Discovery is unevenly applied.** A change to `src/attune/security/` realistically wants `security-audit` AND `bug-predict` AND `dependency-check`. Most users run one and stop.
2. **Triage is the user's job.** Each workflow returns prose. The user reads it, decides which findings are real, which are noise, and which need a second opinion. Across six workflows this is unsustainable.

`discovery-sweep` is the umbrella: one CLI call, one budget, fan out to every applicable audit, aggregate findings, and split them into three triage buckets the user can act on without re-reading prose.

---

## Output contract — three buckets

Every sweep emits findings into exactly one of:

| Bucket | Meaning | User action |
|---|---|---|
| `queue` | High confidence, structured location, severity ≥ threshold. The verification rules pass. | Act on — open file at line, fix or file an issue |
| `rejected` | Low confidence, duplicate, false-positive pattern, or below severity threshold | None — visible in `--verbose` for debugging the rules |
| `questions` | Real-looking finding but the engine can't auto-classify (missing location, conflicting evidence between sources, novel pattern) | Read the question, answer, re-run or escalate |

The `questions` bucket is the load-bearing piece. It's what lets the engine ship aggressively into `queue` without false positives — anything ambiguous routes to `questions` instead of either accept-or-drop.

**Resolved 2026-05-13:** Severity threshold for queue is `medium+`. `low` and `info` route to `rejected` (noise tier). Findings missing a location route to `questions` regardless of severity — even a `critical` finding can't be acted on without a file:line. Tunable in v2 if dogfood reveals the threshold is wrong.

---

## Why a meta-workflow, not a CLI wrapper

A pure CLI wrapper that shells out to each audit workflow would:

- Pay the full budget for each, regardless of overlap
- Have no way to dedupe findings across workflows (same file:line flagged by both bug-predict and security-audit)
- Have to parse six different prose formats to compare findings
- Make the verification rules unimplementable — they need typed access to findings, not strings

A meta-workflow that wraps each audit as a `FindingSource` adapter:

- Allocates `budget_usd` across sources (default: equal split, override per source)
- Receives findings as typed `Finding` objects from each adapter
- Runs verification rules on the merged finding set
- Returns structured output that the CLI can present, the ops dashboard can render as chips, and the surface evaluation (P2.7) can compare against single-workflow outputs

---

## Why structured-emit, not prose-parsing

Adapters wrap LLM-driven workflows whose final_output is prose. Two options to extract findings:

1. **Prose parsing** — regex / heuristics over `final_output`. Cheap, brittle, every workflow drifts independently.
2. **Structured emit** — augment each wrapped workflow's prompt to also emit a JSON block (e.g. ```json``` fenced) containing a typed findings list alongside its prose. Adapter parses the JSON.

Choose **structured emit**. Costs: one extra paragraph in each wrapped workflow's system prompt, a parser per adapter (≈30 lines), and a fallback path when the JSON block is missing or malformed (degrade gracefully to "one low-confidence text-only finding"). Benefit: every adapter parses the same way, drift is caught by a single parse-failure test, and we don't depend on the LLM's prose stability.

**Resolved 2026-05-13 (deferred):** Sketch in `design.md` accepted. Finalize the exact schema when implementing the first adapter (P2.1), based on what the wrapped workflow actually emits.

---

## Why a Protocol, not a base class

The adapter contract is one method: `discover(paths: list[str], budget_usd: float) -> list[Finding]`. There's no shared state, no lifecycle, no template-method override pattern. A `typing.Protocol` is the right shape:

- Adapters don't need to inherit anything — `PatternScanSource` (non-LLM, wraps a regex scanner) and `BugPredictSource` (LLM, wraps a SDK-native workflow) implement the same Protocol without sharing an ancestor.
- Tests can use trivial fake sources (`@dataclass class FakeSource: name: str; ... def discover(...)`)
- The engine doesn't need to know whether an adapter is LLM-backed.

The Protocol lives in `src/attune/workflows/discovery_sweep/workflow.py` alongside the engine.
good
---

## Why this isn't `code-review` or `deep-review`

`code-review` and `deep-review` are user-driven: "review this code, tell me what's wrong." They take a path and return prose for the user to read. They don't fan out across distinct concerns (security/perf/deps/bugs) — they make one pass with one persona.

`discovery-sweep` is system-driven: "find everything worth flagging across all my analysis lenses, hand me back a triaged queue." It fans out, it dedupes, it triages, it surfaces questions. Different shape, different output contract.

Existing workflows that share `discovery-sweep`'s "find issues" intent: `bug-predict`, `security-audit`, `dependency-check`, `perf-audit`, `doc-audit`, `test-audit`. **All six** are wrapped as adapters (P2.1–P2.3, P2.5–P2.7) and contribute to the default source set.

**Resolved 2026-05-13:** Wrap all six. Each lens is genuinely distinct — test-audit's test-quality scoring is not subsumed by bug-predict's pattern matching, dependency-check's CVE feed is not subsumed by security-audit's prompt analysis, etc. Trying to thin the set on a "redundancy" theory is the wrong question; the right question is whether the sweep's UX supersedes running each standalone (see "Why surface evaluation is a phase" below).

---

## Why surface evaluation is a phase, not an open question

When `discovery-sweep` ships, individual audit workflows still exist. They have CLI entries (`attune workflow run bug-predict ...`), MCP tool exposure, ops-dashboard rows, and docs. Two failure modes if we don't evaluate the surface area:

1. **Surface bloat** — users see seven discovery-style workflows where one entry point would do, and pick wrong.
2. **Stale wrappers** — bug fixes in the underlying workflow have to be made twice (in the workflow + in any adapter-specific quirks).

P2.4 is an empirical evaluation: run both the sweep and each underlying workflow on a real scope, compare outputs, recommend per workflow:

- **DEPRECATE CLI** — the standalone CLI invocation is now redundant; deprecate it but keep the workflow class (the sweep still uses it as an adapter)
- **KEEP CLI** — the workflow has a use case the sweep doesn't serve (e.g., interactive depth tuning, single-source debugging) and the CLI stays
- **DEFER** — not enough data, re-evaluate after more dogfood

Output is a markdown doc with recommendations, not code changes. Actual deprecation lands in Phase 4 under separate PRs.

---

## Cost discipline

`budget_usd` is hard-capped at the sweep level. The engine allocates per-source proportionally to each source's `budget_multiplier` and **does not exceed the total** even if some sources come in under their share. The adapter for each LLM workflow passes its allocated budget through to the wrapped workflow's `max_budget_usd` knob.

**Per-source budget multipliers.** Sources vary in real cost — `security-audit` fans out across 4–5 subagents and needs ~$10 alone at standard depth (per the CLAUDE.md lesson on silent budget-cap termination), while `bug-predict` and `dependency-check` are cheaper. Each `FindingSource` declares a `budget_multiplier: float` (default `1.0`); the engine sums the multipliers across LLM sources and allocates `budget_usd × multiplier / sum_multipliers` to each. Initial values:

| Source | multiplier | Rationale |
|---|---|---|
| `BugPredictSource` | 1.0 | Single agent loop |
| `SecurityAuditSource` | 4.0 | 4–5 subagents, expensive synthesis |
| `DependencyCheckSource` | 0.5 | Mostly deterministic CVE feed + thin LLM layer |
| `PerfAuditSource` | 1.5 | 2–3 subagents |
| `DocAuditSource` | 1.0 | Single agent loop |
| `TestAuditSource` | 1.5 | 2 subagents (scoring + recommendation) |

Sum = 9.5. At default `$10` budget: security gets ~$4.21, perf/test get ~$1.58, bug/doc get ~$1.05, deps gets ~$0.53. Tune after dogfood.

For the pattern adapter (PatternScanSource, no LLM), `budget_usd` is ignored — pattern scanning is effectively free. Engine logs this for telemetry but doesn't redistribute the freed budget to LLM sources (would require a second pass; not worth it for v1).

**Resolved 2026-05-13:** Default total budget is **$10.00** — enough for a meaningful sweep at standard depth across the LLM adapters (~$1–$2 each), well above the bad-default $2.00 ceiling that surfaced in the existing CLAUDE.md lesson about silent budget-cap termination.

---

## Non-goals

- **Real-time / continuous sweep.** This is on-demand. Watching the filesystem and re-sweeping on change is a future concern.
- **Cross-repo sweep.** One repo, one `--path`. Multi-root is out of scope.
- **Auto-fix / agentic remediation.** Sweep finds; it does not fix. A `discovery-fix` follow-on spec could be a thing later.
- **Replacing `code-review` or `deep-review`.** Different intent (see above).
- **MCP tool exposure in v1.** CLI entry only. MCP exposure is a follow-up once the output shape is stable.

---

## Alternatives considered

### Alt A — Run audits in parallel via shell

```bash
attune workflow run bug-predict --path X &
attune workflow run security-audit --path X &
...
```

Rejected: no dedup, no triage, six budgets, six prose blobs to read.

### Alt B — Add a `--all` flag to one of the existing audit workflows

Rejected: arbitrary which workflow gets it, blurs each workflow's single-purpose contract, doesn't solve the triage problem.

### Alt C — Wrap each audit in a subagent inside a single agent loop

Rejected: budget accounting becomes opaque (the SDK doesn't surface per-subagent cost cleanly), no clean retire path (subagents are baked into the prompt, not pluggable), and we lose the ability to run the sweep without LLM access (pattern adapter still works in budgetless mode).

---

## Open questions to revisit

1. Should `questions` findings re-route into a single LLM call that tries to resolve them, before being surfaced? (v1: no, keep the engine LLM-free for cost predictability.) ok
2. Should the sweep cache findings keyed by `path` + git SHA so re-running on unchanged code is instant? (v1: no, premature; add only if dogfood reveals frequent re-runs on the same SHA.)ok
3. Should `default_sources()` be a static list or configurable via `.help/features.yaml`? (v1: static; configurability is a follow-up.)ok
