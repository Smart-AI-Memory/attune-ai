"""Same-call native form execution using the Task 1B policy and common collector.

The server injects trusted evidence, a persistent installation-key-backed store,
and its authenticated session adapter. No request can supply these authorities.
Only native transport is implemented here; other routes remain unavailable until
an actual presentation adapter and its evidence are installed.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import secrets
import time
from dataclasses import asdict, replace
from typing import Any

from anyio import BrokenResourceError, ClosedResourceError, EndOfStream
from mcp.shared.exceptions import McpError

from attune.elicitation import form_to_elicitation_schema
from attune.elicitation.surface_policy import (
    CapabilitySnapshot,
    SurfaceBinding,
    SurfaceContextStore,
    select_surface,
)
from attune.elicitation.surface_registry import InventoryReport, canonical_digest

logger = logging.getLogger(__name__)
NATIVE_ROUTE = "mcp-native:native-elicitation"


class SurfaceFormRuntime:
    """Execute an evidence-admissible native form on one authenticated MCP session."""

    def __init__(
        self,
        store: SurfaceContextStore,
        registry: dict[str, Any],
        report: InventoryReport,
        *,
        subject_id: str,
        response_deadline_seconds: float = 300,
        max_validation_attempts: int = 3,
        hard_surface: str | None = None,
    ) -> None:
        import math

        if not math.isfinite(response_deadline_seconds) or response_deadline_seconds <= 0:
            raise ValueError("response deadline must be finite and positive")
        if type(max_validation_attempts) is not int or max_validation_attempts < 1:
            raise ValueError("validation attempt limit must be a positive integer")
        self._max_attempts = max_validation_attempts
        self._hard_surface = hard_surface
        self._chains: dict[tuple[str, str], str] = {}
        self.store = store
        self._registry = copy.deepcopy(registry)
        self._report = report
        self._subject_id = subject_id
        self._deadline = response_deadline_seconds
        # Identity mapping is owned by the runtime, never by request fields.
        self._sessions: dict[int, tuple[Any, str]] = {}

    def session_id(self, session: Any) -> str:
        """Bind an authenticated session object to a server-generated identity."""
        key = id(session)
        if key not in self._sessions:
            self._sessions[key] = (session, secrets.token_hex(16))
        return self._sessions[key][1]

    def close_session(self, session: Any) -> None:
        """Invalidate in-flight interactions on transport/session teardown."""
        entry = self._sessions.get(id(session))
        if entry is not None:
            self.store.close_session(entry[1])

    async def route_form(
        self,
        form: Any,
        session: Any,
        request_id: Any,
        *,
        receipt_id: str | None = None,
        message: str = "",
    ) -> dict[str, Any]:
        """Read current negotiation once, select once, render once, then collect.

        MCP initializes the session capability object; form/request contents
        never populate capability or accessibility fields. Native elicitation
        capability omission is false. Presentation failures do not fall back.
        """
        form = copy.deepcopy(form)
        try:
            capabilities = session.client_params.capabilities
        except AttributeError:
            capabilities = None
        elicitation = getattr(capabilities, "elicitation", None)
        native = elicitation is not None and getattr(elicitation, "form", None) is not None
        snapshot = CapabilitySnapshot(
            secrets.token_hex(16),
            ((NATIVE_ROUTE, native),),
            hard_surface=self._hard_surface,
        )
        # Chains are server-owned; an echoed receipt never supplies its binding.
        current_session = self.session_id(session)
        chain_key = (current_session, form.form_id)
        chain_id = self._chains.setdefault(chain_key, secrets.token_hex(16))
        binding = SurfaceBinding(
            self.store.server_instance_id,
            current_session,
            chain_id,
            "interactive_form",
            form.form_id,
            form.form_id,
            canonical_digest(asdict(form)),
        )
        context = self.store.context_reason(receipt_id, binding)
        decision = select_surface(
            self._registry,
            self._report,
            self._subject_id,
            snapshot,
            context_reason=context,
            deliverable_routes=frozenset({NATIVE_ROUTE}) if native else frozenset(),
        )
        output = {
            "success": False,
            "selected_route": decision.selected_route,
            "payload_kind": None,
            "payload": None,
            "receipt_id": None,
            "submission_id": None,
            "completion": None,
            "decision_summary": decision.summary(),
        }
        if decision.selected_route is None:
            return {**output, "error": "no_supported_surface"}
        decision = replace(decision, renderer_attempt_count=1)
        output["decision_summary"] = decision.summary()
        try:
            schema = form_to_elicitation_schema(form)
            challenge = self.store.begin_challenge(binding, form, schema, NATIVE_ROUTE)
        except (TypeError, ValueError) as exc:
            logger.warning("Native form preparation failed: %s", type(exc).__name__)
            return {
                **output,
                "error": "session_ended" if str(exc) == "session_ended" else "render_failed",
            }
        deadline = time.monotonic() + self._deadline
        presentation_message = message or form.title
        for attempt in range(1, self._max_attempts + 1):
            decision = replace(decision, presentation_attempt_count=attempt)
            output["decision_summary"] = decision.summary()
            try:
                result = await asyncio.wait_for(
                    session.elicit_form(presentation_message, copy.deepcopy(schema), request_id),
                    max(0, deadline - time.monotonic()),
                )
            except asyncio.CancelledError:
                self.store.invalidate_challenge(challenge)
                raise
            except (
                asyncio.TimeoutError,
                OSError,
                RuntimeError,
                ValueError,
                TypeError,
                McpError,
                BrokenResourceError,
                ClosedResourceError,
                EndOfStream,
            ) as exc:
                # Known MCP/stream failures terminate this selected route.
                logger.warning("Native form transport failed: %s", type(exc).__name__)
                self.store.invalidate_challenge(challenge)
                return {**output, "error": "render_failed"}
            if time.monotonic() >= deadline:
                self.store.invalidate_challenge(challenge)
                return {**output, "error": "render_failed"}
            action = getattr(result, "action", None)
            if action == "accept":
                raw = {"action": "accept", "answers": getattr(result, "content", None)}
            elif isinstance(action, str) and action in {"cancel", "decline"}:
                raw = {"action": "abort"}
            else:
                self.store.invalidate_challenge(challenge)
                return {**output, "error": "render_failed"}
            completion = self.store.complete_challenge(challenge, raw)
            if "error" in completion:
                error = completion["error"]
                if error not in {"session_ended", "challenge_invalidated", "challenge_consumed"}:
                    error = "render_failed"
                return {**output, "error": error}
            if completion["action"] != "validation_feedback_delivery":
                self._chains.pop(chain_key, None)
                completion.pop("submission_id", None)
                return {
                    **output,
                    "success": True,
                    "payload_kind": "completion",
                    "completion": completion,
                    "receipt_id": completion.get("receipt_id"),
                }
            if attempt == self._max_attempts:
                self.store.transition(completion["receipt_id"], binding, terminal=True)
                self._chains.pop(chain_key, None)
                return {
                    **output,
                    "success": True,
                    "payload_kind": "completion",
                    "completion": {
                        "success": False,
                        "action": "abort",
                        "reason": "validation_exhausted",
                    },
                }
            presentation_message = (
                (message or form.title) + "\n" + "\n".join(completion["problems"])
            )
            challenge = self.store.begin_challenge(binding, form, schema, NATIVE_ROUTE)
        raise AssertionError("positive validation limit must yield a result")
