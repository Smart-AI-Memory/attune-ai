# Doc Gen

## Reference

Doc-gen's public surface is the `DocumentGenerationWorkflow` class,
re-exported from `attune.workflows`. `WorkflowResult` comes from
`attune.workflows` as well.

### `DocumentGenerationWorkflow` — `attune.workflows.document_gen`

| Symbol | Purpose |
|--------|---------|
| `DocumentGenerationWorkflow()` | Construct the workflow. Takes no special constructor arguments. |
| `DocumentGenerationWorkflow.execute(**kwargs)` | **Async.** Generate docs. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). No `focus`. Returns a `WorkflowResult`. |
| `DocumentGenerationWorkflow.default_context(xml_config=None)` | Classmethod returning a `WorkflowContext` pre-configured with prompt and parsing services, for composition. |
| `DocumentGenerationWorkflow.name` | The registered slug, `"doc-gen"`. |
| `DocumentGenerationWorkflow.stages` | `["agent-gen"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a single module. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | The fullest treatment of a large or public-facing area. |

### The three passes

| Subagent | Role |
|----------|------|
| `outline-planner` | Plans the doc structure: modules, APIs, example sections. |
| `content-writer` | Writes the content with code examples and API references. |
| `polish-reviewer` | Refines for clarity and consistency. |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the run completed. |
| `final_output` | `Any` | The generated document — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short overview of the documented codebase. |
| `suggestions` | `list[NextAction]` | Recommendations for improving coverage. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"`). |
| `metadata` | `dict` | Echoes `path`, `depth`, and `max_turns`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/doc-gen` in a Claude Code conversation — routes to `doc_gen` (generate), `doc_audit` (stale/missing), or `doc_orchestrator` (pipeline). |
| CLI | `attune workflow run doc-gen --path <p> [--depth quick\|standard\|deep] [--json]`. |
| Python | `await DocumentGenerationWorkflow().execute(path=<p>, depth=<d>)`. |

<!-- attune-generated: source_hash=bcc987b14e370273da9042e975c82dcf5af466e245d407e9ce45d5250d354384 feature=doc-gen kind=reference generated_at=2026-06-23 -->
