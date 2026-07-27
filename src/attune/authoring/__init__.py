"""Single-source authoring infrastructure.

The machinery absorbed from attune-author during its consolidation
(``docs/specs/attune-author-consolidation/``), in two halves split on
the thesis seam:

- **Mechanics** (deterministic — no LLM): the feature projector and
  its supporting source-introspection, manifest, staleness, and
  fact-check helpers. Pure transforms, so the fan-out from one master
  to its rendered kinds/pages is byte-stable.
- **Authoring** (LLM, ruling D10): the generator/polish machinery.
  LLM polish runs at *authoring time on the master* (reviewed,
  committed), never on projected output. Calls route through
  :mod:`attune.models.single_turn` (tier routing, subscription-first
  auth, telemetry).
"""

from __future__ import annotations

from attune.authoring.polish import PolishError, polish_template
from attune.authoring.projector import project_feature, validate_master_file

__all__ = [
    "PolishError",
    "polish_template",
    "project_feature",
    "validate_master_file",
]
