"""In-memory dashboard interaction counters.

Phase 6.1 of ops-runner-tier2. Tracks three user-driven UI events
across the lifetime of the dashboard process so we can answer
"is anyone using the pill/recommendation/scope features?" without
shipping a network endpoint or writing PII to disk.

Counters reset on dashboard restart. No persistence, no network,
no PII — just per-process tallies surfaced on the /telemetry tab.

Bucket layout
-------------

- ``pill_clicks`` — keyed by the *target* workflow (the pill the
  user clicked, not the source page). Empty/unknown target is
  bucketed as ``"(unknown)"``.
- ``rec_card_clicks`` — keyed by the recommendation card kind
  (``"next-workflow"`` or ``"open-url"``). Unknown kinds bucket
  as ``"(unknown)"``.
- ``scope_picker_changes`` — keyed by the *source* workflow whose
  scope picker the user touched. Empty/unknown source bucket as
  ``"(unknown)"``.

Targets are length-capped (64 chars) and stripped to a conservative
charset (workflow-name shape + a few separators). The cap protects
the in-memory map from a runaway client that POSTs many distinct
targets; the charset filter keeps the rendered HTML safe even if
the template ever stops escaping. Unparseable inputs bucket as
``"(unknown)"`` rather than raising.
"""

from __future__ import annotations

import re
import threading
from collections import Counter
from dataclasses import dataclass, field

# Allowed UI events. New events should be added here AND mapped in
# ``_BUCKET_FOR_EVENT`` below.
EVENTS: tuple[str, ...] = (
    "pill_click",
    "rec_card_click",
    "scope_picker_change",
)

# Conservative target charset. Workflow names are lowercase
# kebab-case but we also accept underscore, dot, and slash so a
# future scope-picker call site can pass a path-like target without
# raising. Anything else collapses to "(unknown)".
_TARGET_RE = re.compile(r"^[A-Za-z0-9_./-]{1,64}$")

_UNKNOWN = "(unknown)"


def _normalize_target(target: str | None) -> str:
    """Return a safe-to-bucket key for ``target``.

    Empty string, ``None``, or anything that doesn't match the
    conservative charset collapses to the ``"(unknown)"`` sentinel
    so we still record the event without trusting the input.
    """
    if not target:
        return _UNKNOWN
    if not isinstance(target, str):
        return _UNKNOWN
    if not _TARGET_RE.match(target):
        return _UNKNOWN
    return target


@dataclass
class InteractionCounters:
    """Process-lifetime counters for dashboard UI interactions.

    Thread-safe via a single lock. We use ``collections.Counter``
    per bucket so increments are cheap and read-out can sort by
    count without extra structure.
    """

    pill_clicks: Counter[str] = field(default_factory=Counter)
    rec_card_clicks: Counter[str] = field(default_factory=Counter)
    scope_picker_changes: Counter[str] = field(default_factory=Counter)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, event: str, target: str | None = None) -> bool:
        """Increment the bucket for ``event`` keyed by ``target``.

        Returns ``True`` if the event was recorded, ``False`` if
        the event name is unrecognized (caller may want to log).
        Never raises.
        """
        bucket = self._bucket_for(event)
        if bucket is None:
            return False
        key = _normalize_target(target)
        with self._lock:
            bucket[key] += 1
        return True

    def snapshot(self) -> dict[str, dict[str, int]]:
        """Return a deep copy of all buckets for rendering.

        Returns ordered top-down so the JSON / template renders are
        deterministic across calls.
        """
        with self._lock:
            return {
                "pill_clicks": dict(self.pill_clicks),
                "rec_card_clicks": dict(self.rec_card_clicks),
                "scope_picker_changes": dict(self.scope_picker_changes),
            }

    def totals(self) -> dict[str, int]:
        """Return the total count per event type (not per target)."""
        with self._lock:
            return {
                "pill_clicks": sum(self.pill_clicks.values()),
                "rec_card_clicks": sum(self.rec_card_clicks.values()),
                "scope_picker_changes": sum(self.scope_picker_changes.values()),
            }

    def top(self, event: str, limit: int = 10) -> list[tuple[str, int]]:
        """Top-N targets for ``event``, descending by count.

        Returns an empty list for unrecognized events.
        """
        bucket = self._bucket_for(event)
        if bucket is None:
            return []
        with self._lock:
            return bucket.most_common(limit)

    def _bucket_for(self, event: str) -> Counter[str] | None:
        if event == "pill_click":
            return self.pill_clicks
        if event == "rec_card_click":
            return self.rec_card_clicks
        if event == "scope_picker_change":
            return self.scope_picker_changes
        return None
