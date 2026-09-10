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
* **The store still owns the lifecycle.** Nothing here mints, advances or
  tombstones a receipt. Every state change goes through the store, as
  either a completion or an invalidation.

KNOWN DEFECT, HELD DELIBERATELY (chair, 2026-09-09), because closing it
requires a store change that invalidates a parity receipt this repo cannot
currently regenerate: **the challenge is validated on the way BACK, not on
the way in.** ``present_host_question`` calls the adapter first and only
then hands the completion to the store, so a challenge that is already
consumed, closed or being presented elsewhere still reaches the renderer
once. The store correctly refuses the second COMPLETION — but the second
PROMPT has already been shown to a person by then. The check is a report,
not a gate. Three tests carry this as a strict xfail so the day it is
fixed they fail loudly instead of passing silently. Do not describe this
module as replay-safe until that reservation exists.

Trust is bound to identity SNAPSHOTS taken at registration, not to live
attribute reads: an adapter object can mutate its own ``profile_id`` after
being registered, and failure handling must not depend on reading anything
off the object that just failed.

What this module does NOT do, deliberately: it selects no route and reads
no capability. A registered adapter is necessary but not sufficient to
make a host-native route selectable. Today it is not even a candidate —
the routing subject declares no host-native route, so no disposition for
one is produced at all; and were one introduced, the capability
snapshot's static channel is unwritten, so it would be refused before
adapter presence was ever consulted (host-surface-parity D20 rulings 3
and 4). No receipt from this module may be read as the route being live.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
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


def _feedback_digest(attempt: int, problems: tuple[str, ...]) -> str:
    """Digest the canonical feedback content."""
    return canonical_digest({"attempt": attempt, "problems": list(problems)})


@dataclass(frozen=True)
class ValidationFeedbackEnvelope:
    """Server-derived re-ask feedback, carried beside an unchanged batch.

    ``digest`` covers the canonical ``(attempt, problems)`` content, so a
    mutated or mismatched pair is refused at the presentation boundary.

    The honest scope of that check: it detects MUTATION and mismatched
    pairing, not forgery. The digest is unkeyed, so in-process code could
    compute one — which is not a gap, because in-process code is already
    inside the trust boundary. The boundary this envelope defends is the
    tool/model edge, and no tool accepts an envelope, a challenge or a
    completion. Server derivation is therefore a CALLER OBLIGATION that
    this type records; build one through :func:`derive_validation_feedback`.

    Field invariants are enforced on construction so that a malformed
    envelope cannot exist. ``intact()`` is consequently total: it answers
    the digest question and never raises, which matters because it is
    consulted at a boundary whose whole job is to convert failure into a
    disposition rather than an exception.
    """

    attempt: int
    problems: tuple[str, ...]
    digest: str

    def __post_init__(self) -> None:
        """Reject a malformed envelope at construction, not at use."""
        if not isinstance(self.attempt, int) or isinstance(self.attempt, bool) or self.attempt < 1:
            raise ValueError("attempt must be a positive integer")
        if not isinstance(self.problems, tuple) or not all(
            isinstance(problem, str) for problem in self.problems
        ):
            raise TypeError("problems must be a tuple of strings")
        if not isinstance(self.digest, str) or not self.digest:
            raise TypeError("digest must be a non-empty string")

    def intact(self) -> bool:
        """Report whether the content still matches the digest it was minted with."""
        return self.digest == _feedback_digest(self.attempt, self.problems)


def derive_validation_feedback(
    attempt: int, problems: tuple[str, ...]
) -> ValidationFeedbackEnvelope:
    """Mint an envelope from canonical validation errors the server produced.

    ``attempt`` is 1-based and counts the initial presentation, matching the
    profile's ``max_validation_attempts``. Field validation lives in
    :meth:`ValidationFeedbackEnvelope.__post_init__` so that a directly
    constructed envelope is held to the same invariants as a derived one.
    """
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

    ``advisory_deadline_seconds`` is exactly what its name says: the profile's
    declared deadline, passed through for the adapter to honour. This module
    does NOT enforce it — the call is synchronous, so a blocking adapter
    blocks. Enforcement belongs to the implementation, which owns the
    transport and can cancel it. The store's own staleness bound remains the
    backstop for a challenge completed long after it was issued.
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
        advisory_deadline_seconds: int,
    ) -> HostQuestionCompletion | None:
        """Present ``batch`` and return its completion, or ``None`` on failure."""
        ...  # pragma: no cover - protocol declaration


@dataclass(frozen=True)
class HostAdapterRegistration:
    """An installed adapter plus the identity the server registered it under.

    Constructing this is the registration act, and it SNAPSHOTS the adapter's
    declared identity. Freezing this wrapper does not freeze the adapter, so
    every later trust decision compares the adapter's current identity against
    the snapshot rather than trusting either alone.
    """

    adapter: HostQuestionAdapter
    profile_id: str
    target_id: str
    adapter_id: str = field(init=False)

    def __post_init__(self) -> None:
        """Refuse an adapter whose declared identity contradicts the registration."""
        if not callable(getattr(self.adapter, "present_and_collect", None)):
            raise TypeError("adapter must implement present_and_collect")
        for name in ("adapter_id", "profile_id", "target_id"):
            value = getattr(self.adapter, name, None)
            if not isinstance(value, str) or not value:
                raise ValueError(f"adapter must declare a non-empty {name}")
        if self.adapter.profile_id != self.profile_id:
            raise ValueError("adapter profile_id does not match its registration")
        if self.adapter.target_id != self.target_id:
            raise ValueError("adapter target_id does not match its registration")
        object.__setattr__(self, "adapter_id", self.adapter.adapter_id)

    def identity_intact(self) -> bool:
        """Report whether the adapter still declares what it registered as."""
        return (
            callable(getattr(self.adapter, "present_and_collect", None))
            and getattr(self.adapter, "adapter_id", None) == self.adapter_id
            and getattr(self.adapter, "profile_id", None) == self.profile_id
            and getattr(self.adapter, "target_id", None) == self.target_id
        )

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

    ``None`` is the answer a route policy needs BEFORE rendering: an absent,
    mismatched or since-mutated adapter makes a host-native candidate
    inadmissible rather than failing mid-presentation.
    """
    if registration is None or not registration.matches(profile_id, target_id):
        return None
    if not registration.identity_intact():
        logger.warning("adapter %s no longer matches its registration", registration.adapter_id)
        return None
    return registration


def present_host_question(
    store: SurfaceContextStore,
    registration: HostAdapterRegistration,
    challenge: PresentationChallenge,
    batch: Any,
    *,
    feedback: ValidationFeedbackEnvelope | None = None,
    advisory_deadline_seconds: int,
) -> dict[str, Any]:
    """Run one presentation attempt and consume its completion in the same call.

    Returns the store's collection result on success, or ``{"success": False,
    "error": ...}``. Every failure of the adapter itself is ``render_failed``:
    no other surface is attempted here, because a route that was selected and
    then failed to paint must not silently become a different route's receipt.

    NOT replay-safe yet: the challenge is checked by the store only when the
    completion comes back, so a consumed or closed challenge still reaches the
    adapter once and a person may see a second prompt. See the module
    docstring's held-defect note; the fix is a store-side reservation.
    """
    adapter_id = registration.adapter_id
    if not registration.identity_intact():
        logger.warning("adapter %s mutated its identity before presentation", adapter_id)
        store.invalidate_challenge(challenge)
        return {"success": False, "error": "render_failed"}
    if feedback is not None and not feedback.intact():
        logger.warning("refusing mutated validation feedback for %s", adapter_id)
        store.invalidate_challenge(challenge)
        return {"success": False, "error": "render_failed"}
    try:
        completion = registration.adapter.present_and_collect(
            challenge,
            batch,
            feedback=feedback,
            advisory_deadline_seconds=advisory_deadline_seconds,
        )
    # BLE001: an installed adapter is third-party presentation code; ANY
    # failure it raises is this route's render_failed, never a crash that
    # escapes into the caller's arm and never a fall-through to another
    # surface. The exception is logged before it is converted, and the
    # handler reads only the identity SNAPSHOT taken at registration — never
    # an attribute of the object that just failed, which an adapter tearing
    # itself down could otherwise use to defeat its own invalidation.
    except Exception:  # noqa: BLE001
        logger.exception("host question adapter %s raised", adapter_id)
        store.invalidate_challenge(challenge)
        return {"success": False, "error": "render_failed"}
    if not isinstance(completion, HostQuestionCompletion) or completion.challenge is not challenge:
        logger.warning("host question adapter %s returned no usable completion", adapter_id)
        store.invalidate_challenge(challenge)
        return {"success": False, "error": "render_failed"}
    return store.complete_challenge(challenge, completion.response)
