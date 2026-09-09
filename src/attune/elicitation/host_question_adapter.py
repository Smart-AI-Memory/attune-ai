"""Trusted in-process host-question presentation boundary (Task 2).

Task 1B gave the server a route-neutral :class:`PresentationChallenge` and
the compare-and-consume lifecycle around it. This module adds the ONE
non-MCP way to put a question batch in front of a person and read the
answer back in the same call: a :class:`HostQuestionAdapter` the server
installs from its own configuration, never from request, tool or model
data.

Three properties are load-bearing, and each is narrower than it looks:

* **Same call.** ``present_and_collect`` presents and collects inside one
  invocation. There is no deferred callback to authenticate later, so a
  completion is server-observed by construction.
* **Object identity, not equality.** A completion is accepted only when it
  carries back the very challenge object that was handed out. The
  challenge refuses serialization, so it cannot round-trip through a tool
  argument and come back as a look-alike.
* **The store still owns the receipt.** Nothing here mints, advances or
  tombstones a receipt; every state change goes through
  :meth:`SurfaceContextStore.complete_challenge`, which already rejects a
  second completion, a closed session and an invalidated challenge.

What this module does NOT do, deliberately: it selects no route and reads
no capability. A registered adapter is necessary but not sufficient to
make a host-native route selectable — the capability snapshot's static
channel is unwritten, so such a route is rejected as
``unsupported_capability`` before adapter presence is ever consulted
(host-surface-parity D20 ruling 3).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from attune.elicitation.surface_policy import PresentationChallenge, SurfaceContextStore
from attune.elicitation.surface_registry import canonical_digest

logger = logging.getLogger(__name__)

__all__ = [
    "HostAdapterRegistration",
    "HostQuestionAdapter",
    "HostQuestionCompletion",
    "ValidationFeedbackEnvelope",
    "derive_validation_feedback",
    "present_host_question",
    "resolve_host_adapter",
]


@dataclass(frozen=True)
class ValidationFeedbackEnvelope:
    """Server-derived re-ask feedback, carried beside an unchanged batch.

    ``digest`` covers the canonical ``(attempt, problems)`` content so a
    mutated or mismatched pair is refused at the presentation boundary.

    The honest scope of that check: it detects MUTATION and mismatched
    pairing, not forgery. The digest is unkeyed, so in-process code could
    compute one — which is not a gap, because in-process code is already
    inside the trust boundary. The boundary this envelope defends is the
    tool/model edge, and no tool accepts an envelope, a challenge or a
    completion. Build one only through :func:`derive_validation_feedback`.
    """

    attempt: int
    problems: tuple[str, ...]
    digest: str

    def intact(self) -> bool:
        """Report whether the content still matches the digest it was minted with."""
        return self.digest == _feedback_digest(self.attempt, self.problems)


def _feedback_digest(attempt: int, problems: tuple[str, ...]) -> str:
    """Digest the canonical feedback content."""
    return canonical_digest({"attempt": attempt, "problems": list(problems)})


def derive_validation_feedback(
    attempt: int, problems: tuple[str, ...]
) -> ValidationFeedbackEnvelope:
    """Mint an envelope from canonical validation errors the server produced.

    ``attempt`` is 1-based and counts the initial presentation, matching the
    profile's ``max_validation_attempts``.
    """
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        raise ValueError("attempt must be a positive integer")
    if not isinstance(problems, tuple) or not all(isinstance(p, str) for p in problems):
        raise TypeError("problems must be a tuple of strings")
    return ValidationFeedbackEnvelope(attempt, problems, _feedback_digest(attempt, problems))


@dataclass(frozen=True)
class HostQuestionCompletion:
    """One same-call host answer, returning the challenge it was issued against.

    ``response`` uses the store's closed envelope: ``{"action": "accept",
    "answers": {...}}``, or ``{"action": "abort"|"timeout"}``. Anything else
    is refused by :meth:`SurfaceContextStore.complete_challenge` as
    ``render_failed``.
    """

    challenge: PresentationChallenge
    response: dict[str, Any]


@runtime_checkable
class HostQuestionAdapter(Protocol):
    """The only trusted non-MCP presentation boundary.

    Implementations are installed by the server from its own configuration.
    ``adapter_id``, ``profile_id`` and ``target_id`` bind one adapter to one
    installed interaction profile and one route-active registry target.
    """

    adapter_id: str
    profile_id: str
    target_id: str

    def present_and_collect(
        self,
        challenge: PresentationChallenge,
        batch: Any,
        *,
        feedback: ValidationFeedbackEnvelope | None = None,
        deadline_seconds: int,
    ) -> HostQuestionCompletion | None:
        """Present ``batch`` and return its completion, or ``None`` on failure."""
        ...  # pragma: no cover - protocol declaration


@dataclass(frozen=True)
class HostAdapterRegistration:
    """An installed adapter plus the identity the server registered it under.

    Constructing this is the registration act. It is deliberately separate
    from the adapter object so a mismatched or half-configured adapter fails
    at registration, where a human sees it, rather than at presentation.
    """

    adapter: HostQuestionAdapter
    profile_id: str
    target_id: str

    def __post_init__(self) -> None:
        """Refuse an adapter whose declared identity contradicts the registration."""
        if not callable(getattr(self.adapter, "present_and_collect", None)):
            raise TypeError("adapter must implement present_and_collect")
        for name in ("adapter_id", "profile_id", "target_id"):
            if not isinstance(getattr(self.adapter, name, None), str) or not getattr(
                self.adapter, name
            ):
                raise ValueError(f"adapter must declare a non-empty {name}")
        if self.adapter.profile_id != self.profile_id:
            raise ValueError("adapter profile_id does not match its registration")
        if self.adapter.target_id != self.target_id:
            raise ValueError("adapter target_id does not match its registration")

    def matches(self, profile_id: str, target_id: str) -> bool:
        """Report whether this registration serves that profile and target."""
        return self.profile_id == profile_id and self.target_id == target_id


def resolve_host_adapter(
    registration: HostAdapterRegistration | None,
    *,
    profile_id: str,
    target_id: str,
) -> HostAdapterRegistration | None:
    """Return the registration when it serves this route, else ``None``.

    ``None`` is the answer a route policy needs BEFORE rendering: an absent
    or mismatched adapter makes a host-native candidate inadmissible rather
    than failing mid-presentation.
    """
    if registration is None or not registration.matches(profile_id, target_id):
        return None
    return registration


def present_host_question(
    store: SurfaceContextStore,
    registration: HostAdapterRegistration,
    challenge: PresentationChallenge,
    batch: Any,
    *,
    feedback: ValidationFeedbackEnvelope | None = None,
    deadline_seconds: int,
) -> dict[str, Any]:
    """Run one presentation attempt and consume its completion in the same call.

    Returns the store's collection result on success, or
    ``{"success": False, "error": ...}``. Every failure of the adapter
    itself is ``render_failed``: no other surface is attempted here, because
    a route that was selected and then failed to paint must not silently
    become a different route's receipt.
    """
    if feedback is not None and not feedback.intact():
        logger.warning(
            "refusing mutated validation feedback for %s", registration.adapter.adapter_id
        )
        store.invalidate_challenge(challenge)
        return {"success": False, "error": "render_failed"}
    try:
        completion = registration.adapter.present_and_collect(
            challenge, batch, feedback=feedback, deadline_seconds=deadline_seconds
        )
    # BLE001: an installed adapter is third-party presentation code; ANY
    # failure it raises is this route's render_failed, never a crash that
    # escapes into the caller's arm and never a fall-through to another
    # surface. The exception is logged before it is converted.
    except Exception:  # noqa: BLE001
        logger.exception("host question adapter %s raised", registration.adapter.adapter_id)
        store.invalidate_challenge(challenge)
        return {"success": False, "error": "render_failed"}
    if not isinstance(completion, HostQuestionCompletion) or completion.challenge is not challenge:
        logger.warning(
            "host question adapter %s returned no usable completion",
            registration.adapter.adapter_id,
        )
        store.invalidate_challenge(challenge)
        return {"success": False, "error": "render_failed"}
    return store.complete_challenge(challenge, completion.response)
