# Bug Predict

## Overview

Bug-predict scans a codebase and predicts where bugs are most
likely to hide. It is **SDK-native**: `BugPredictionWorkflow`
delegates the analysis to three specialized Claude Agent SDK
subagents and synthesizes their findings into a single report
with an overall risk score, per-finding file/line locations, and
prioritized prevention advice.

It **predicts** — it does not prove. The three subagents apply
LLM judgment over the code (via Read / Glob / Grep), so findings
are risk hypotheses to triage, not the deterministic output of a
linter. Treat a HIGH finding as "look here first," not "this line
is definitely broken."

You reach bug-predict four ways, all of which run the same
workflow:

- the **`/bug-predict`** skill, inside a Claude Code conversation;
- the CLI — **`attune workflow run bug-predict`**;
- the **`bug_predict`** MCP tool (one required `path` argument);
- the Python API — `await BugPredictionWorkflow().execute(...)`,
  documented here for wiring bug-predict into a hook, a CI step,
  or a custom tool.

A separate set of regex/string pattern helpers also lives in the
module (`bug_predict_patterns.py`). They are an internal,
lower-level utility layer — **not** what the live workflow runs.
The "Notes & tips" and "Design & extension" sections below say
exactly what they do and do not affect.

## Concepts

### Three subagents, one synthesized report

`BugPredictionWorkflow.execute` issues a single
`claude_agent_sdk.query` whose options define three subagents,
each scoped to `Read` / `Glob` / `Grep`:

| Subagent | What it looks for |
|----------|-------------------|
| `pattern-scanner` | Null references, type mismatches, race conditions, `eval`/`exec` usage, broad exception handlers, resource leaks, off-by-one errors. Reports file path, line number, pattern type, and severity. |
| `risk-correlator` | Correlates the scanner's findings with file complexity, change frequency, and historical bug density; assigns a per-file risk score and names the highest-risk modules. |
| `prevention-advisor` | Reviews the correlated risks, ranks them by impact, and proposes specific fixes: refactoring, added tests, type annotations, error-handling, and architectural changes. |

The orchestrator then synthesizes all three into one report with
three sections — **Summary** (an overall 0–100 risk score plus a
2–3 sentence executive summary), **Bugs** (grouped HIGH /
MEDIUM / LOW, each with file, line, pattern, and description), and
**Suggestions** (prioritized prevention strategies).

### Depth controls the agent-turn budget

`execute` takes a `depth` of `"quick"`, `"standard"` (default),
or `"deep"`. Depth maps to the maximum number of agent turns the
SDK query may take, and to a per-run cost cap:

| Depth | Max agent turns |
|-------|-----------------|
| `quick` | 10 |
| `standard` | 20 |
| `deep` | 40 |

An unrecognized depth falls back to the standard budget (20
turns). Deeper scans let the subagents read more files and reason
longer, at higher cost — the run is bounded by a `max_budget_usd`
derived from the depth.

### `execute` is async, and honors only `path` and `depth`

`execute` is a coroutine — `await` it (or drive it with
`asyncio.run`). Calling it without awaiting is the most common
bug-predict mistake.

It reads exactly two keyword arguments from `**kwargs`: `path`
(required) and `depth` (default `"standard"`). Any other keyword
is silently ignored — there is no `file_types`, `exclude`, or
`depth=...` shorthand beyond those two. An empty or missing
`path` returns a failed `WorkflowResult` rather than raising.

### The result is a `WorkflowResult`

`execute` returns a `WorkflowResult` (from
`attune.workflows`). The synthesized report lands in
`final_output` — a serialized `WorkflowReport` when the findings
parse into categories, or the raw markdown text otherwise — with
a short `summary`, a `suggestions` list, the `cost_report`, the
`provider`, and a `metadata` dict echoing back `path`, `depth`,
and `max_turns`. On failure, `success` is `False` and `error` /
`error_type` carry the reason.

## Design & extension

### Design decisions

- **SDK-native, three specialized subagents.** Since v4.2.0,
  bug-predict is a single `claude_agent_sdk.query` with three
  subagents — `pattern-scanner` (detection), `risk-correlator`
  (scoring), and `prevention-advisor` (advice). Splitting the
  work keeps each subagent's context focused and lets one be
  changed without touching the others; the cost is an extra
  synthesis step in the orchestrator.
- **Prediction, not deterministic scanning, is the contract.**
  The workflow returns LLM-judged risk hypotheses, deliberately
  trading a linter's precision for breadth and prioritization.
  This is why findings are framed as hotspots to triage.
- **The result is data, not print output.** `execute` returns a
  `WorkflowResult` (report in `final_output`, plus `summary`,
  `suggestions`, `cost_report`, and `metadata`); callers own
  presentation. The CLI, MCP, and skill surfaces all render that
  same result.

### Extension points

- **Steer a single run:** pass `system_prompt_suffix` to the
  constructor to append instructions to the orchestrator prompt
  without subclassing — the pattern discovery-sweep's
  `BugPredictSource` uses.
- **Change the budget:** choose `depth` (`quick` / `standard` /
  `deep`) to trade coverage against cost; `--cheap` on the CLI
  forces unpinned subagents onto Haiku.
- **The static pattern helpers are a separate layer.**
  `bug_predict_patterns.py` exposes regex/string detectors
  (`_is_dangerous_eval_usage`, `_has_problematic_exception_handlers`,
  …) and `_load_bug_predict_config`, which reads the
  `./attune.config.yml` `bug_predict` block
  (`risk_threshold`, `exclude_files`,
  `acceptable_exception_contexts`). `_should_exclude_file` is
  reused by `workflow_patterns/behavior.py`; the eval/exception
  detectors are not wired into the live SDK workflow. Treat them
  as an internal utility, not a configuration surface for the
  prediction.

<!-- attune-generated: source_hash=6651bf938b845a590d6af44512242264ef0650223553d1e58325a8c0c6b2e208 feature=bug-predict kind=architecture generated_at=2026-07-14 -->
