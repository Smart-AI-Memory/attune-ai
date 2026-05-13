"""Discovery Sweep — meta-workflow that fans out across audit sources.

Triages findings into three buckets:

- ``queue`` — act on (high confidence, located, severity ≥ threshold)
- ``questions`` — need human judgment (missing location, low confidence,
  conflicting severity, source crashed)
- ``rejected`` — filtered noise (below severity threshold, duplicate)

Public surface:

- :class:`DiscoverySweepWorkflow` — BaseWorkflow registered as
  ``discovery-sweep`` in the workflow registry.
- :class:`Finding`, :class:`QuestionFinding`, :class:`RejectedFinding`,
  :class:`SweepResult`, :class:`SweepMetadata` — typed result shapes.
- :class:`FindingSource` — runtime-checkable Protocol every source
  adapter must implement.

See ``docs/specs/discovery-sweep/`` for the approved spec.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .workflow import (
    DEFAULT_BUDGET_USD,
    DiscoverySweepWorkflow,
    Finding,
    FindingSource,
    QuestionFinding,
    RejectedFinding,
    Severity,
    SweepMetadata,
    SweepResult,
)

__all__ = [
    "DEFAULT_BUDGET_USD",
    "DiscoverySweepWorkflow",
    "Finding",
    "FindingSource",
    "QuestionFinding",
    "RejectedFinding",
    "Severity",
    "SweepMetadata",
    "SweepResult",
]
