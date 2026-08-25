"""Back-compat shim — the SDK error taxonomy lives in ``attune.models``.

#2239 slice 1 moved the defining module to
:mod:`attune.models.sdk_errors` (the adapter core in the models layer
needs it, and models must never import workflows). This shim keeps
historical ``attune.workflows.sdk_errors`` imports working.

Tests that monkeypatch MUST target ``attune.models.sdk_errors`` (the
defining namespace) — patching these re-bindings leaves the defining
module's own reads untouched (the #2162 vacuous-test class).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

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
