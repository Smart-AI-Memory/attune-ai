# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Docs outbox — conflict-free batching for small docs artifacts.

Phase 1 of ``docs/specs/docs-outbox`` (R1-R4, ratified 2026-08-06).
Small docs (lessons, reports, drafts, plans) land as per-artifact
timestamped files in ``~/.attune/docs-outbox/``; a curating sweep
dedupes, lints, and composes ONE digest for chair approval before a
single batched PR ships them. ``decisions.md`` rulings and spec
status flips never route here — they merge now (see ``routing``).
"""

from attune.docs_outbox.routing import MERGE_NOW_KINDS, OUTBOX_TARGETS, route
from attune.docs_outbox.store import (
    Artifact,
    OutboxStatus,
    list_artifacts,
    outbox_dir,
    outbox_status,
    write_artifact,
)
from attune.docs_outbox.sweep import SweepResult, run_sweep

__all__ = [
    "MERGE_NOW_KINDS",
    "OUTBOX_TARGETS",
    "Artifact",
    "OutboxStatus",
    "SweepResult",
    "list_artifacts",
    "outbox_dir",
    "outbox_status",
    "route",
    "run_sweep",
    "write_artifact",
]
