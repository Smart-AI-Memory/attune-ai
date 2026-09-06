"""Server-owned context and metadata-only surface selection (Task 1B).

This module neither renders nor accepts request-supplied capabilities/evidence.
The integrating server supplies an installation key and authoritative bindings.
Records are process-local; reusing the key after restart preserves authenticity,
not the old records. No receipt or decision is proof of host paint.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from attune.elicitation.surface_registry import InventoryReport, route_evidence_missing

_WORKSPACE_FIELDS = (
    "workspace_id",
    "adapter_id",
    "adapter_version",
    "revision",
    "event_sequence",
    "contract_hash",
    "action_nonce",
)
_COMMON_FIELDS = (
    "server_instance_id",
    "session_id",
    "chain_id",
    "subject_kind",
    "subject_id",
    "schema_id",
    "schema_digest",
)
_TOKEN = re.compile(r"[0-9a-f]{48}\.[0-9a-f]{64}\Z")


def _response_digest(response: Any) -> str | None:
    """Validate the closed response envelope and digest canonical JSON."""
    from attune.elicitation.surface_registry import canonical_digest

    if not isinstance(response, dict) or set(response) - {"action", "answers"}:
        return None
    action = response.get("action")
    if not isinstance(action, str) or action not in {"accept", "abort", "timeout"}:
        return None
    if action != "accept" and "answers" in response:
        return None
    try:
        json.dumps(response, allow_nan=False)
        return canonical_digest(response)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class SurfaceBinding:
    """Immutable authoritative identity; workspace values follow the spec order."""

    server_instance_id: str
    session_id: str
    chain_id: str
    subject_kind: str
    subject_id: str
    schema_id: str
    schema_digest: str
    workspace: tuple[Any, ...] | None = None

    def valid(self) -> bool:
        """Reject unknown kinds and missing, invalid or forbidden binding fields."""
        if any(not isinstance(getattr(self, key), str) for key in _COMMON_FIELDS):
            return False
        if any(
            not getattr(self, key)
            for key in _COMMON_FIELDS
            if key
            not in (
                {"subject_id", "schema_id"}
                if self.subject_kind == "interactive_form"
                else {"subject_id"}
            )
        ):
            return False
        if self.subject_kind == "interactive_form":
            return self.workspace is None
        if self.subject_kind != "interactive_workspace" or not self.subject_id:
            return False
        if not isinstance(self.workspace, tuple) or len(self.workspace) != 7:
            return False
        for index, value in enumerate(self.workspace):
            if index in (2, 3, 4):
                if type(value) is not int or value < (1 if index == 2 else 0):
                    return False
            elif not isinstance(value, str) or not value:
                return False
        return True

    def mismatch(self, other: SurfaceBinding) -> str | None:
        """Compare validated identities in the spec's fixed first-match order."""
        if not other.valid() or not self.valid():
            return "record_shape_mismatch"
        for name, reason in (
            ("server_instance_id", "server_instance_mismatch"),
            ("session_id", "session_mismatch"),
            ("chain_id", "chain_mismatch"),
            ("subject_kind", "subject_mismatch"),
            ("subject_id", "subject_mismatch"),
            ("schema_id", "schema_mismatch"),
            ("schema_digest", "schema_mismatch"),
        ):
            if getattr(other, name) != getattr(self, name):
                return reason
        if self.subject_kind == "interactive_workspace":
            for name, left, right in zip(
                _WORKSPACE_FIELDS, other.workspace, self.workspace, strict=True
            ):
                if left != right:
                    return "workspace_mismatch" if name == "workspace_id" else f"{name}_mismatch"
        return None


@dataclass(frozen=True)
class ContextRecord:
    """One active receipt or retained tombstone; terminal is never active."""

    binding: SurfaceBinding
    observed_at: float
    reason: str | None = None
    tombstoned_at: float | None = None


@dataclass(frozen=True, eq=False)
class PresentationChallenge:
    """Opaque server-owned identity; never serialize this into a tool response."""

    def __reduce__(self) -> Any:
        """Refuse serialization across the trusted in-process boundary."""
        raise TypeError("presentation challenges are process-local")


class SurfaceContextStore:
    """Authenticate, retain and atomically invalidate server-owned receipts.

    ``installation_key`` must be supplied by the server's durable installation
    configuration; it must not come from a tool argument. The store never
    persists that key. All mutations and context reads share one reentrant lock.
    """

    def __init__(
        self,
        installation_key: bytes,
        *,
        clock: Callable[[], float] = time.time,
        server_instance_id: str | None = None,
    ) -> None:
        if not isinstance(installation_key, bytes) or len(installation_key) < 32:
            raise ValueError("installation key must contain at least 32 bytes")
        self._key = installation_key
        self._clock = clock
        self.server_instance_id = server_instance_id or secrets.token_hex(16)
        self._records: dict[str, ContextRecord] = {}
        self._active: dict[tuple[str, str], str] = {}
        self._ended: set[str] = set()
        self._closed_chains: set[tuple[str, str]] = set()
        self._subject_kinds: dict[str, str] = {}
        self._challenges: dict[PresentationChallenge, tuple[Any, ...]] = {}
        self._challenge_dispositions: dict[PresentationChallenge, str] = {}
        self._interactions: dict[str, tuple[Any, str, str]] = {}
        self._submissions: dict[str, tuple[str, str | None, dict[str, Any] | None]] = {}
        self._lock = threading.RLock()

    def _token(self) -> str:
        nonce = secrets.token_hex(24)
        mac = hmac.new(self._key, nonce.encode("ascii"), hashlib.sha256).hexdigest()
        return f"{nonce}.{mac}"

    def _authentic(self, token: str) -> bool:
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            return False
        nonce, mac = token.split(".")
        expected = hmac.new(self._key, nonce.encode("ascii"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(mac, expected)

    def _reason(
        self,
        token: str | None,
        current: SurfaceBinding,
        now: float,
        *,
        action: bool = False,
    ) -> str:
        if not action and current.subject_kind == "interactive_form" and not current.subject_id:
            return "empty_form_id"
        if not token:
            return "missing_receipt"
        if not self._authentic(token):
            return "invalid_receipt"
        record = self._records.get(token)
        if record is None:
            return "foreign_receipt"
        retained_since = record.tombstoned_at if record.reason else record.observed_at
        if retained_since is not None and now - retained_since >= 7200:
            return "foreign_receipt"
        if record.reason in {"session_ended", "superseded_receipt", "terminal"}:
            return record.reason
        mismatch = current.mismatch(record.binding)
        if mismatch is not None:
            return mismatch
        if record.observed_at > now:
            return "future_timestamp"
        if now - record.observed_at >= 3600:
            return "expired"
        return "warm"

    def context_reason(self, token: str | None, current: SurfaceBinding) -> str:
        """Apply the spec's first-match context predicates with one record lookup."""
        with self._lock:
            return self._reason(token, current, self._clock())

    def issue(self, binding: SurfaceBinding, *, reuse: bool = True) -> str:
        """Issue after successful presentation; unchanged active bindings reuse ID."""
        with self._lock:
            if not binding.valid() or binding.server_instance_id != self.server_instance_id:
                raise ValueError("invalid authoritative binding")
            if binding.session_id in self._ended:
                raise ValueError("session_ended")
            known = self._subject_kinds.get(binding.subject_id)
            if known is not None and known != binding.subject_kind:
                raise ValueError("subject kind cannot change")
            self._subject_kinds[binding.subject_id] = binding.subject_kind
            chain = (binding.session_id, binding.chain_id)
            if chain in self._closed_chains:
                raise ValueError("terminal")
            prior = self._active.get(chain)
            now = self._clock()
            if prior:
                if reuse and self._reason(prior, binding, now, action=True) == "warm":
                    return prior
                self._tombstone(prior, "superseded_receipt", now)
            token = self._token()
            self._records[token] = ContextRecord(binding, now)
            self._active[chain] = token
            return token

    def _tombstone(self, token: str, reason: str, now: float) -> None:
        record = self._records[token]
        self._records[token] = ContextRecord(record.binding, record.observed_at, reason, now)
        chain = (record.binding.session_id, record.binding.chain_id)
        self._active.pop(chain, None)
        if reason == "terminal":
            self._closed_chains.add(chain)

    def transition(
        self,
        token: str,
        binding: SurfaceBinding,
        *,
        terminal: bool,
    ) -> tuple[str, str | None]:
        """Compare and consume once, returning a successor only when nonterminal."""
        with self._lock:
            reason = self._reason(token, binding, self._clock(), action=True)
            if reason != "warm":
                return reason, None
            self._tombstone(token, "terminal" if terminal else "superseded_receipt", self._clock())
            return "committed", None if terminal else self.issue(binding, reuse=False)

    def close_session(self, session_id: str) -> None:
        """End a session and tombstone all its active receipts before another commit."""
        with self._lock:
            self._ended.add(session_id)
            now = self._clock()
            for challenge, state in self._challenges.items():
                if state[0].session_id == session_id:
                    self._challenge_dispositions.setdefault(challenge, "session_ended")
            for (session, _), token in tuple(self._active.items()):
                if session == session_id:
                    self._tombstone(token, "session_ended", now)

    def begin_challenge(
        self,
        binding: SurfaceBinding,
        form: Any,
        payload: Any,
        route: str,
    ) -> PresentationChallenge:
        """Capture a projection before same-call transport, without issuing a receipt."""
        from attune.elicitation.surface_registry import canonical_digest

        if not binding.valid() or binding.server_instance_id != self.server_instance_id:
            raise ValueError("invalid authoritative binding")
        if binding.subject_kind != "interactive_form":
            raise ValueError("form challenge requires a form binding")
        frozen_form = copy.deepcopy(form)
        if binding.schema_id != frozen_form.form_id or binding.schema_digest != canonical_digest(
            asdict(frozen_form)
        ):
            raise ValueError("canonical schema does not match binding")
        frozen_payload = copy.deepcopy(payload)
        canonical_digest(frozen_payload)
        with self._lock:
            if binding.session_id in self._ended:
                raise ValueError("session_ended")
            if (binding.session_id, binding.chain_id) in self._closed_chains:
                raise ValueError("terminal")
            challenge = PresentationChallenge()
            self._challenges[challenge] = (
                binding,
                frozen_form,
                frozen_payload,
                route,
                self._clock(),
                self._active.get((binding.session_id, binding.chain_id)),
            )
            return challenge

    def invalidate_challenge(self, challenge: PresentationChallenge) -> None:
        """Invalidate an outstanding transport attempt without touching its predecessor."""
        with self._lock:
            if challenge in self._challenges:
                self._challenge_dispositions.setdefault(challenge, "challenge_invalidated")

    def complete_challenge(
        self,
        challenge: PresentationChallenge,
        host_response: dict[str, Any],
    ) -> dict[str, Any]:
        """Consume one server-observed same-call completion, rejecting late callbacks.

        The server invokes this with the original object after its transport
        returns. No public tool accepts a challenge or claimed completion.
        """
        with self._lock:
            if challenge not in self._challenges:
                return {"success": False, "error": "challenge_invalidated"}
            binding, form, payload, route, started, predecessor = self._challenges[challenge]
            disposition = self._challenge_dispositions.get(challenge)
            if disposition:
                return {"success": False, "error": disposition}
            if binding.session_id in self._ended:
                return {"success": False, "error": "session_ended"}
            if self._clock() < started or self._clock() - started >= 3600:
                self._challenge_dispositions[challenge] = "challenge_invalidated"
                return {"success": False, "error": "challenge_invalidated"}
            if (binding.session_id, binding.chain_id) in self._closed_chains:
                return {"success": False, "error": "challenge_invalidated"}
            if self._active.get((binding.session_id, binding.chain_id)) != predecessor:
                self._challenge_dispositions[challenge] = "challenge_invalidated"
                return {"success": False, "error": "challenge_invalidated"}
            action = host_response.get("action") if isinstance(host_response, dict) else None
            if (
                not isinstance(action, str)
                or action not in {"accept", "abort", "timeout"}
                or set(host_response) - {"action", "answers"}
                or (action == "accept" and not isinstance(host_response.get("answers"), dict))
                or (action != "accept" and "answers" in host_response)
            ):
                self._challenge_dispositions[challenge] = "challenge_invalidated"
                return {"success": False, "error": "render_failed"}
            try:
                json.dumps(host_response, allow_nan=False)
            except (TypeError, ValueError):
                self._challenge_dispositions[challenge] = "challenge_invalidated"
                return {"success": False, "error": "render_failed"}
            self._challenge_dispositions[challenge] = "challenge_consumed"
            receipt, submission = self.present_form(binding, form, payload, route)
            result = self.collect_form(
                receipt, submission, host_response, session_id=binding.session_id
            )
            if "action" in result:
                result["provenance_status"] = "server_observed_completion"
            return result

    def present_form(
        self,
        binding: SurfaceBinding,
        form: Any,
        payload: Any,
        route: str,
    ) -> tuple[str, str]:
        """Retain canonical form/payload state and mint a token per presentation.

        Call only after the selected renderer succeeds. Public collection cannot
        replace the form, schema, route or payload. Identical re-presentation
        preserves the active receipt and gives each presentation its own token.
        """
        from attune.elicitation.surface_registry import canonical_digest

        if binding.subject_kind != "interactive_form":
            raise ValueError("form presentation requires a form binding")
        frozen_form = copy.deepcopy(form)
        if binding.schema_digest != canonical_digest(asdict(frozen_form)):
            raise ValueError("canonical schema does not match binding")
        if binding.schema_id != frozen_form.form_id:
            raise ValueError("canonical form identity does not match binding")
        payload_digest = canonical_digest(payload)
        with self._lock:
            prior = self._active.get((binding.session_id, binding.chain_id))
            prior_state = self._interactions.get(prior)
            same_projection = prior_state is not None and prior_state[1:] == (route, payload_digest)
            receipt = self.issue(binding, reuse=same_projection)
            self._interactions[receipt] = (frozen_form, route, payload_digest)
            submission = self._token()
            self._submissions[submission] = (receipt, None, None)
            return receipt, submission

    def collect_form(
        self,
        receipt: str,
        submission: str,
        host_response: dict[str, Any],
        *,
        session_id: str,
    ) -> dict[str, Any]:
        """Validate against retained form and atomically commit or replay the result.

        ``session_id`` is supplied by the authenticated server transport. This
        deferred caller-mediated path does not attest paint or host provenance.
        Validation rejection rotates authority and returns a fresh attempt token.
        """
        with self._lock:
            if not self._authentic(submission) or submission not in self._submissions:
                return {"success": False, "error": "invalid_submission"}
            owner, saved_digest, saved_result = self._submissions[submission]
            if receipt != owner:
                return {"success": False, "error": "submission_mismatch"}
            record = self._records.get(receipt)
            if record is None or record.binding.session_id != session_id:
                return {"success": False, "error": "submission_mismatch"}
            retained_since = record.tombstoned_at if record.reason else record.observed_at
            if self._clock() - retained_since >= 7200:
                return {"success": False, "error": "foreign_receipt"}
            response_digest = _response_digest(host_response)
            if response_digest is None:
                return {"success": False, "error": "invalid_response"}
            if saved_result is not None:
                if saved_digest == response_digest:
                    return copy.deepcopy(saved_result)
                return {"success": False, "error": "submission_conflict"}
            reason = self._reason(receipt, record.binding, self._clock(), action=True)
            if reason != "warm":
                return {"success": False, "error": reason}
            return self._collect_active(receipt, submission, host_response, response_digest, record)

    def _collect_active(
        self,
        receipt: str,
        submission: str,
        host_response: dict[str, Any],
        response_digest: str,
        record: ContextRecord,
    ) -> dict[str, Any]:
        """Validate/transition with the caller holding the store transaction lock."""
        from attune.elicitation import FormValidationError, collect_form_response

        action = host_response["action"]
        form, route, payload_digest = self._interactions[receipt]
        result: dict[str, Any] = {
            "success": True,
            "action": action,
            "receipt_id": None,
            "submission_id": None,
            "provenance_status": "unverified_transport",
        }
        if action == "accept":
            answers = host_response.get("answers")
            if not isinstance(answers, dict):
                return {"success": False, "error": "invalid_response"}
            try:
                validated = collect_form_response(form, answers)
            except FormValidationError as exc:
                status, successor = self.transition(receipt, record.binding, terminal=False)
                if status != "committed":
                    return {"success": False, "error": status}
                self._interactions[successor] = (form, route, payload_digest)
                next_submission = self._token()
                self._submissions[next_submission] = (successor, None, None)
                result.update(
                    success=False,
                    action="validation_feedback_delivery",
                    problems=list(exc.problems),
                    receipt_id=successor,
                    submission_id=next_submission,
                )
            else:
                result.update(responses=validated.responses, response_id=validated.response_id)
        if result["receipt_id"] is None:
            status, _ = self.transition(receipt, record.binding, terminal=True)
            if status != "committed":
                return {"success": False, "error": status}
        self._submissions[submission] = (receipt, response_digest, copy.deepcopy(result))
        return result


@dataclass(frozen=True)
class CapabilitySnapshot:
    """Trusted provider value, constructed in process, never from tool arguments.

    Negotiated MCP cells are separate from static host cells. Absent current
    negotiation cannot be filled by a doctor cache. Explicit False wins.
    """

    snapshot_id: str
    negotiated: tuple[tuple[str, bool], ...] = ()
    host_static: tuple[tuple[str, bool | None], ...] = ()
    cached_static: tuple[tuple[str, bool], ...] = ()
    hard_surface: str | None = None
    noninteractive: bool = False

    def supports(self, route: str) -> bool:
        """Resolve a route from its authoritative channel without probing."""
        if route == "RICH" or route.startswith("mcp-native:"):
            return dict(self.negotiated).get(route) is True
        current = dict(self.host_static)
        value = current.get(route)
        if value is not None:
            return value is True
        return dict(self.cached_static).get(route) is True


@dataclass(frozen=True)
class SurfaceDecision:
    """Internal decision details; public summaries deliberately expose only four keys."""

    selected_route: str | None
    context_reason: str
    selection_elapsed_ms: float
    candidates: tuple[tuple[str, str], ...]
    registry_digest: str
    capability_snapshot_id: str
    renderer_attempt_count: int = 0
    presentation_attempt_count: int = 0

    def summary(self) -> dict[str, Any]:
        """Return the exact server-output-only decision-summary whitelist."""
        return {
            "context_reason": self.context_reason,
            "selection_elapsed_ms": self.selection_elapsed_ms,
            "renderer_attempt_count": self.renderer_attempt_count,
            "presentation_attempt_count": self.presentation_attempt_count,
        }


def select_surface(
    registry: dict[str, Any],
    report: InventoryReport,
    subject_id: str,
    capabilities: CapabilitySnapshot,
    *,
    context_reason: str,
    deliverable_routes: frozenset[str],
) -> SurfaceDecision:
    """Select once from trusted evidence and registered delivery objects, without I/O.

    Like ``route_evidence_missing``, the inventory/report must be produced by
    trusted validation over executed receipts. ``deliverable_routes`` is derived
    from server-registered live adapters, never a caller's capability claim.
    """
    started = time.perf_counter()
    subject = next(s for s in registry["subjects"] if s["id"] == subject_id)
    order = subject["warm_routes" if context_reason == "warm" else "cold_routes"]
    if capabilities.noninteractive:
        order = [route for route in order if route == "HEADLESS"]
    dispositions = []
    selected = None
    for route in order:
        if capabilities.hard_surface is not None and route != capabilities.hard_surface:
            reason = "accessibility_constraint"
        elif not capabilities.supports(route):
            reason = "unsupported_capability"
        elif route not in deliverable_routes:
            reason = "missing_adapter"
        elif route_evidence_missing(registry, report, subject_id, route):
            reason = "missing_evidence"
        else:
            reason = "selected"
            selected = route
        dispositions.append((route, reason))
        if selected is not None:
            break
    return SurfaceDecision(
        selected,
        context_reason,
        (time.perf_counter() - started) * 1000,
        tuple(dispositions),
        report.registry_digest,
        capabilities.snapshot_id,
    )
