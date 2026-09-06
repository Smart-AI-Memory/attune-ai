"""Explicit, read-only Claude review through a verified subscription login."""

from __future__ import annotations

import json
import logging
import os
import subprocess  # nosec B404 — fixed CLI argv, no shell
from typing import Any

from attune.gates import session_ledger

logger = logging.getLogger(__name__)


class SubscriptionReviewError(RuntimeError):
    """Subscription authentication could not be established before inference."""


def invoke_subscription_review(brief: str, *, reply_chars: int = 8000) -> tuple[int, str]:
    """Review via saved Pro/Max auth, refusing API or ambiguous authentication.

    Authentication and inference use the same scrubbed child environment and
    safe-mode CLI configuration. Parent authentication and the API spend cap
    are unchanged. Subscription entitlement is not an invoice/overage receipt.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("ANTHROPIC_", "CLAUDE"))
    }
    command = ["claude", "--safe-mode", "--strict-mcp-config"]
    try:
        probe = subprocess.run(  # nosec B603 — fixed authentication diagnostic
            [*command, "auth", "status"],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        auth: Any = json.loads(probe.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        logger.warning("Subscription authentication unavailable: %s", type(exc).__name__)
        raise SubscriptionReviewError("Claude subscription authentication unavailable") from exc
    if (
        probe.returncode != 0
        or not isinstance(auth, dict)
        or auth.get("loggedIn") is not True
        or auth.get("authMethod") != "claude.ai"
        or auth.get("apiProvider") != "firstParty"
        or auth.get("subscriptionType") not in ("max", "pro")
        or auth.get("apiKeySource") not in (None, "")
    ):
        raise SubscriptionReviewError("Claude requires verified Pro/Max auth without an API key")
    try:
        result = subprocess.run(  # nosec B603 — fixed read-only CLI; brief on stdin
            [
                *command,
                "--mcp-config",
                '{"mcpServers":{}}',
                "--tools",
                "",
                "--no-session-persistence",
                "--output-format",
                "json",
                "-p",
            ],
            input=brief,
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Subscription review unavailable: %s", type(exc).__name__)
        return 1, f"Subscription review unavailable: {type(exc).__name__}"
    # Record this explicit route separately; never disable or raise the API cap.
    session_ledger.record("seat:claude:subscription", 0.0)
    if result.returncode != 0:
        return result.returncode, "Claude subscription review failed; no automatic API fallback"
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        logger.warning("Subscription review returned invalid JSON")
        return 1, "Claude subscription review returned invalid JSON"
    if not isinstance(payload, dict) or payload.get("is_error"):
        return 1, "Claude subscription review did not complete successfully"
    reply = payload.get("result")
    if not isinstance(reply, str) or not reply.strip():
        return 1, "Claude subscription review returned no review text"
    if len(reply) > reply_chars:
        return 1, "Claude subscription review exceeded the reply budget; result not truncated"
    return 0, reply.strip()
