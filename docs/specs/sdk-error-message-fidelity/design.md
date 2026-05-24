# Spec: SDK Error Message Fidelity — Design

**Status:** draft (2026-05-24)

---

## Module layout

All new code lands in two existing modules + one new test surface:

| File | Change |
|---|---|
| `src/attune/workflows/agent_sdk_adapter.py` | New `SdkSubprocessError`, new `classify_subprocess_failure(stderr)`, new `capture_subprocess_failure(args, env)` helper, modified `collect_agent_output()` / call-site decorators |
| `src/attune/workflows/dependency_check.py` (+ 5 siblings) | Replace `sdk_error_message(exc, ...)` calls in the broad-except branch with `SdkSubprocessError.format_user_message()` |
| `src/attune/ops/data.py` (runs JSON read path) + `src/attune/ops/templates/run_view.html` | New `sdk_stderr` / `sdk_error_kind` fields on the run record; collapsible `<details>` block in the run-view template |
| `tests/unit/workflows/test_sdk_error_fidelity.py` | New file — unit tests for the exception, classifier, and capture helper |
| `tests/unit/workflows/test_*` (each affected workflow) | New test per workflow: `test_<wf>_surfaces_real_cause_on_subprocess_failure` |

---

## `SdkSubprocessError` shape

```python
# agent_sdk_adapter.py
from dataclasses import dataclass
from typing import Literal

SdkErrorKind = Literal[
    "api_quota",
    "auth",
    "rate_limit",
    "not_found",
    "schema_rejected",
    "unknown",
]

@dataclass
class SdkSubprocessError(Exception):
    """Typed wrapper around the SDK's bare 'Command failed' Exception.

    Captures the underlying ``claude`` CLI's stderr (via a second
    direct-subprocess call) and classifies it into one of the known
    failure-kind labels for user-facing messaging.

    Attributes:
        message: User-facing one-line summary (e.g. "API quota
            reached (regains 2026-06-01)").
        stderr: Raw captured stderr from the second ``subprocess.run``
            call, redacted through ``session_redaction.redact()``.
        kind: Classified failure category (see ``SdkErrorKind``).
        original_exc: The SDK's wrapped exception, preserved so
            callers / tests can ``raise X from err.original_exc``.
    """

    message: str
    stderr: str
    kind: SdkErrorKind
    original_exc: BaseException | None = None

    def __str__(self) -> str:
        return self.message

    def format_user_message(self) -> str:
        """Voice-layer-ready user-facing block."""
        if self.kind == "unknown":
            return (
                f"{self.message}\n\n"
                "Underlying error (raw stderr from the claude CLI):\n"
                f"{self.stderr.strip()}"
            )
        return f"{self.message}\n\nFull stderr is available on /runs/<id>/view."
```

---

## Classifier

```python
# agent_sdk_adapter.py
import re

# (compiled_re, kind, message_template) tuples. Ordered: most-specific
# first so a more-precise label wins over a generic one.
_CLASSIFIERS: list[tuple[re.Pattern[str], SdkErrorKind, str]] = [
    (re.compile(r"specified API usage limits", re.I),
     "api_quota",
     "Anthropic API quota reached for this account."),
    (re.compile(r"\b(401|invalid[_\s-]?api[_\s-]?key|unauthorized)\b", re.I),
     "auth",
     "Anthropic auth invalid or missing."),
    (re.compile(r"\b(429|rate[_\s-]?limit|too many requests)\b", re.I),
     "rate_limit",
     "Rate-limited by Anthropic; retry shortly."),
    (re.compile(r"FileNotFoundError|claude.*not.*(found|on.*PATH)", re.I),
     "not_found",
     "The bundled claude CLI was not found at the expected path."),
    (re.compile(r"json[_\s-]?schema|--?json-?schema", re.I),
     "schema_rejected",
     "The output schema was rejected by the claude CLI."),
]

def classify_subprocess_failure(stderr: str) -> tuple[SdkErrorKind, str]:
    """Classify a captured stderr blob into (kind, user-message)."""
    for pattern, kind, message in _CLASSIFIERS:
        if pattern.search(stderr):
            return kind, message
    return "unknown", "The claude CLI subprocess failed; see raw stderr below."
```

---

## Capture helper

```python
# agent_sdk_adapter.py
import subprocess
from attune.security.session_redaction import redact

def capture_subprocess_failure(
    args: list[str],
    env: dict[str, str] | None = None,
    timeout_s: float = 10.0,
) -> str:
    """Re-run the failed ``claude`` invocation with stderr capture.

    Called from the broad-except branch around a
    ``claude_agent_sdk.query()`` call when the bare 'Command failed'
    exception fires. Returns redacted stderr ready to attach to a
    ``SdkSubprocessError``.

    Args:
        args: Exact argv used by the SDK's first invocation. Pulled
            from the SDK's ``subprocess_cli`` log-prefix line (the
            "$ claude --output-format stream-json …" we already see
            in the run log).
        env: Optional env override. Defaults to ``os.environ``.
        timeout_s: Subprocess timeout. The failure mode we care about
            (quota / auth / not-found) all exit in sub-second; 10s
            is a generous ceiling.

    Returns:
        Redacted stderr text, or a synthetic
        "(capture-call also failed: <reason>)" string if the second
        subprocess itself raises.
    """
    try:
        result = subprocess.run(  # noqa: S603
            args,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,  # we want to inspect failure output
        )
        # Some failures put real errors on stdout (e.g. JSON envelope).
        # Concatenate; the classifier scans both anyway.
        combined = (result.stderr or "") + ("\n" + result.stdout if result.stdout else "")
        return redact(combined)
    except subprocess.TimeoutExpired:
        return f"(capture-call timed out after {timeout_s}s)"
    except (OSError, subprocess.SubprocessError) as exc:
        return f"(capture-call also failed: {type(exc).__name__}: {exc})"
```

---

## Call-site integration

Each affected workflow's `_run_agent_<stage>()` already has a broad-except wrapper. We change the body of that except branch.

**Before:**

```python
# workflows/dependency_check.py
except Exception as exc:  # noqa: BLE001
    logger.exception("Agent SDK dependency check failed: %s", type(exc).__name__)
    duration = (datetime.now() - started_at).total_seconds()
    return self._error_result(
        sdk_error_message(exc, duration_seconds=duration, depth=depth)
    )
```

**After:**

```python
except Exception as exc:  # noqa: BLE001
    logger.exception("Agent SDK dependency check failed: %s", type(exc).__name__)
    duration = (datetime.now() - started_at).total_seconds()
    stderr = capture_subprocess_failure(_last_subprocess_argv(exc))
    kind, summary = classify_subprocess_failure(stderr)
    sdk_err = SdkSubprocessError(
        message=summary, stderr=stderr, kind=kind, original_exc=exc
    )
    return self._error_result(
        sdk_err.format_user_message(),
        sdk_stderr=stderr,
        sdk_error_kind=kind,
    )
```

`_last_subprocess_argv(exc)` extracts the argv from the SDK exception's repr (we already log it; the SDK stores it on the inner attr `exc.__cause__.args` in current versions — needs verification in Phase 1).

---

## Persistence + render

**`Run.to_record()`** gains:

```python
sdk_stderr: str | None = None
sdk_error_kind: str | None = None
```

Both default-None so existing run records on disk read back correctly (missing keys → None).

**`run_view.html`** gains, immediately under the existing "What Went Wrong" block:

```html
{% if run.sdk_stderr %}
<details class="sdk-error-detail">
  <summary>Raw stderr from claude CLI
    {% if run.sdk_error_kind %} ({{ run.sdk_error_kind }}){% endif %}
  </summary>
  <pre class="sdk-error-stderr">{{ run.sdk_stderr }}</pre>
</details>
{% endif %}
```

CSS: `.sdk-error-stderr` matches the existing log-pre style — monospace, muted background, scroll-on-overflow.

---

## Failure modes (what could go wrong)

| Mode | Mitigation |
|---|---|
| Second subprocess call hangs | 10s timeout in `capture_subprocess_failure()`; synthetic "timed out" message. |
| SDK argv format changes across versions | Pinned `claude-agent-sdk` minor version; drift-guard test in Phase 1 asserts the argv-extraction path still works against installed SDK. |
| Captured stderr contains secrets | All paths route through `redact()` before persistence + render. |
| Classifier false-positive | "unknown" fallback always shows the raw stderr, so a misclassification still leaves the user with the truth. |
| Capture call itself rate-limited (the "rate_limit" kind ironically can't capture) | Synthetic "(capture-call also failed: …)" string preserves the first-class failure indication; user sees "rate-limited" from the first call's exception text. |

---

## Out of scope

- Retry / backoff on transient errors — surface, don't recover.
- Predicting every error class — five-shape menu + unknown fallback is the v1 surface.
- SDK fork or upstream PR — explicit non-goal per decisions.md.
- Exit-code propagation — sibling spec `workflow-failure-exit-propagation` owns it.
