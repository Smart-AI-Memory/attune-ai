"""Back-compat facade — the SDK adapter core lives in ``attune.models``.

#2239 slice 1: ``attune.models`` must never import ``attune.workflows``,
and ``models.single_turn`` needs the adapter — so the adapter core moved
to :mod:`attune.models.sdk_adapter` and the error taxonomy to
:mod:`attune.models.sdk_errors`. This module re-exports the historical
surface so workflows-layer importers keep working unchanged.

Tests that monkeypatch MUST target the DEFINING modules
(``attune.models.sdk_adapter`` / ``attune.models.sdk_errors`` /
``.sdk_output_parser``), never these re-bindings — patching a re-export
leaves the defining module's own reads untouched (the #2162
vacuous-test class). The mutable probe cache
``_CLI_SUPPORTS_TASK_BUDGET`` is deliberately NOT re-exported here for
the same reason: a snapshot of it would silently go stale.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from attune.models.sdk_adapter import (  # noqa: F401
    _DEFAULT_TASK_BUDGET_TOKENS,
    _SUBAGENT_MODEL_MAP,
    SDK_SUBPROCESS_ENV_VAR,
    AgentRunResult,
    _guard_bash_tool,
    build_result_text,
    collect_agent_output,
    collect_subagent_transcripts,
    format_subagent_transcripts_markdown,
    get_max_budget_usd,
    get_subagent_model,
    get_task_budget,
    get_thinking_config,
    iter_agent_messages,
    make_edit_scope_guard,
    resolve_cwd_for_path,
    sdk_isolation_kwargs,
)
from attune.models.sdk_errors import (  # noqa: F401
    _CLASSIFIERS,
    _DEFAULT_BUDGET_USD,
    SdkErrorKind,
    SdkSubprocessError,
    _claude_health_probe_argv,
    _last_subprocess_argv,
    _sdk_error_probe_enabled,
    _stderr_carries_no_signal,
    capture_subprocess_failure,
    classify_subprocess_failure,
    sdk_error_from_exception,
    sdk_error_message,
)

from .sdk_output_parser import (  # noqa: F401
    _CATEGORY_PATTERNS,
    _SUGGESTION_RE,
    AgentSDKResultAdapter,
)

# The re-export surface IS this module's purpose — __all__ makes that
# explicit (and keeps scanners from reading the imports as unused).
__all__ = [
    # adapter core (attune.models.sdk_adapter)
    "_DEFAULT_TASK_BUDGET_TOKENS",
    "_SUBAGENT_MODEL_MAP",
    "SDK_SUBPROCESS_ENV_VAR",
    "AgentRunResult",
    "_guard_bash_tool",
    "build_result_text",
    "collect_agent_output",
    "collect_subagent_transcripts",
    "format_subagent_transcripts_markdown",
    "get_max_budget_usd",
    "get_subagent_model",
    "get_task_budget",
    "get_thinking_config",
    "iter_agent_messages",
    "make_edit_scope_guard",
    "resolve_cwd_for_path",
    "sdk_isolation_kwargs",
    # error taxonomy (attune.models.sdk_errors)
    "_CLASSIFIERS",
    "_DEFAULT_BUDGET_USD",
    "SdkErrorKind",
    "SdkSubprocessError",
    "_claude_health_probe_argv",
    "_last_subprocess_argv",
    "_sdk_error_probe_enabled",
    "_stderr_carries_no_signal",
    "capture_subprocess_failure",
    "classify_subprocess_failure",
    "sdk_error_from_exception",
    "sdk_error_message",
    # output parser (.sdk_output_parser)
    "_CATEGORY_PATTERNS",
    "_SUGGESTION_RE",
    "AgentSDKResultAdapter",
]
