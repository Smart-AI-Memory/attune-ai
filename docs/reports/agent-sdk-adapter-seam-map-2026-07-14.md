# Seam map — `workflows/agent_sdk_adapter.py` split (health-plan item 4)

Prep artifact for decomposing the largest file in src (1,749 LOC,
19 changes/90d). Produced by a read-only analysis pass 2026-07-14;
verified against the file and its importers. The split is NOT yet
executed — this document is the plan.

## Candidate modules (cohesion-derived, all under `src/attune/workflows/`)

| Module | Symbols | Notes |
|--------|---------|-------|
| `sdk_streaming.py` | `AgentRunResult`, `_maybe_dump_message`, `collect_agent_output`, `_is_benign_teardown_exit`, `iter_agent_messages`, `build_result_text` | operates on the raw `query()` message stream |
| `sdk_subagent_transcripts.py` | `collect_subagent_transcripts`, `format_subagent_transcripts_markdown`, `_extract_assistant_texts` | fully self-contained |
| `sdk_budget.py` | `_DEFAULT_BUDGET_USD`, `_DEFAULT_TASK_BUDGET_TOKENS`, `_cli_supports_task_budget` (+cache), `get_task_budget`, `get_thinking_config`, `get_max_budget_usd` | one shared process-cache global, confined |
| `sdk_error_fidelity.py` | `sdk_error_message`, `SdkErrorKind`, `SdkSubprocessError`, `_stderr_carries_no_signal`, `_CLASSIFIERS`, `classify_subprocess_failure`, `_sdk_error_probe_enabled`, `_claude_health_probe_argv`, `capture_subprocess_failure`, `_last_subprocess_argv` | the churn-heaviest region (4 of last 15 commits) |
| `sdk_isolation.py` | `SDK_SUBPROCESS_ENV_VAR`, `_guard_bash_tool`, `sdk_isolation_kwargs`, `resolve_cwd_for_path` | preserve the DEFERRED `security_guard` import (cycle avoidance) |
| `sdk_subagent_models.py` | `_SUBAGENT_MODEL_MAP`, `get_subagent_model` | flat routing table |
| `sdk_result_adapter.py` | `_CATEGORY_PATTERNS`, `AgentSDKResultAdapter` (~470 LOC) | biggest single unit |

`agent_sdk_adapter.py` becomes a thin re-export shim (explicit name
list) plus its own top-level `import claude_agent_sdk` — zero call
sites change.

## Hard constraints

- The shim must keep exporting every externally-imported name,
  INCLUDING underscore-prefixed ones (`_last_subprocess_argv` — used
  by `gates/spend_gate.py` and every workflow file; `_guard_bash_tool`,
  `_stderr_carries_no_signal`, `_claude_health_probe_argv` — imported
  or patched by tests).
- `agent_sdk_adapter.claude_agent_sdk` must stay importable —
  `test_subagent_transcripts.py` patches
  `patch.object(agent_sdk_adapter.claude_agent_sdk, ...)`. Safe as
  long as both the shim and the extracted modules use plain
  `import claude_agent_sdk` (module singletons in `sys.modules`).
- `TestOptionsIsolationDriftGuard._workflow_files()` excludes the file
  BY NAME (`p.name != "agent_sdk_adapter.py"`) and asserts exactly 15
  `ClaudeAgentOptions(` construction sites — the new modules must not
  construct `ClaudeAgentOptions(` and the shim must not gain the
  literal string; re-verify the count after each extraction.
- No import-cycle risk found from the result-adapter split (`base.py`,
  `output.py`, `data_classes.py` do not import back).

## Extraction order (mechanical-risk ascending)

1. `sdk_subagent_transcripts.py` (2 callers, proves the shim pattern)
2. `sdk_subagent_models.py`
3. `sdk_result_adapter.py` (biggest LOC win, one name crosses)
4. `sdk_budget.py` (watch `gates/spend_gate.py`'s import)
5. `sdk_streaming.py` (`AgentRunResult` is widely referenced)
6. `sdk_isolation.py` (deferred import + drift-guard recheck)
7. `sdk_error_fidelity.py` (highest fan-in; the actual churn-isolation
   goal — do last, on a proven pattern)

## Dead code found during mapping (handle per removing-dead-code gate)

- `sdk_error_message` — zero production callers (tests only).
- `_SUGGESTION_RE` — defined, never referenced anywhere.

Both need the should-this-exist gate before deletion, in their own
commit, not silently during the split.
