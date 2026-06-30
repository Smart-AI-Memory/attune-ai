"""Single-source authoring infrastructure (deterministic — no LLM).

The distribution machinery absorbed from attune-author during its
consolidation (``docs/specs/attune-author-consolidation/``): the
deterministic feature projector and its supporting source-introspection
and fact-check helpers. Pure transforms — no LLM, no network — so the
fan-out from one master to its rendered kinds/pages is byte-stable.

The retired authoring (LLM generation/polish) half is replaced by the
driving session + the single-source-authoring skill, not by code here.
"""

from __future__ import annotations

from attune.authoring.projector import project_feature, validate_master_file

__all__ = ["project_feature", "validate_master_file"]
