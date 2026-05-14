"""Background watcher that persists discovery-sweep results on run-complete.

Phase 2B of ``docs/specs/discovery-sweep-ops-integration/``.

When a discovery-sweep run starts via the ops daemon, the runner's
``start()`` method is wrapped (in :func:`attune.ops.server.create_app`)
to spawn :func:`watch_and_persist` as a background task. The watcher
subscribes to the run's event stream and, on successful completion,
parses the captured ATTUNE_DS lines and writes the scope-keyed
sidecar JSON via :mod:`attune.ops.sweep_results`.

Why a watcher and not a direct hook in ``runner.py``: ``runner.py``
is in a conflict-prone file list (in-flight ops-runner-tier2 PRs).
The Run.subscribe() API is stable and lets us wire the persistence
without modifying the runner. When those PRs land and the runner
gains a generic post-run hook, this watcher can migrate to it
without changing the public contract.

Watcher contract:

- No-op for runs whose workflow is not "discovery-sweep" — the
  wrapping in server.py already filters, but defense in depth keeps
  the watcher safe to call on any run.
- No-op when ``run.exit_code != 0`` — a failed sweep emits partial
  ATTUNE_DS lines that aren't safe to persist as a complete result.
- No-op when no scope path is available — pre-PR-#324 main has
  no ``Run.path`` attribute; ``getattr(run, "path", None)`` gates
  the persistence so the watcher gracefully degrades to "do
  nothing" until paths flow through.
- All filesystem writes happen via :func:`sweep_results.persist_from_lines`
  which already handles atomic writes + version-mismatch refusal.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from attune.ops import sweep_results

if TYPE_CHECKING:  # pragma: no cover — type-only import to avoid cycles
    from attune.ops.config import Config
    from attune.ops.runner import Run

logger = logging.getLogger(__name__)


async def watch_and_persist(run: Run, config: Config) -> None:
    """Subscribe to a discovery-sweep run; persist its result on success.

    Iterates the run's event stream until the terminal ``done`` event,
    then checks success criteria. On a successful sweep with a known
    scope path, parses the captured stdout via
    :func:`sweep_results.persist_from_lines`.

    All exceptions are caught + logged. Persistence is observability,
    not correctness — a failed persist must never crash the dashboard
    or surface as a runtime error to the operator.
    """
    if run.workflow != "discovery-sweep":
        return

    try:
        async for kind, _payload in run.subscribe():
            if kind == "done":
                break
    except Exception:  # noqa: BLE001
        # INTENTIONAL: subscription failure is not a sweep failure.
        logger.exception(
            "discovery-sweep watcher subscription failed for run %s",
            run.id,
        )
        return

    if run.exit_code != 0:
        # Failed sweep — don't persist a half-emitted ATTUNE_DS stream.
        return

    scope_path = getattr(run, "path", None) or ""
    if not scope_path:
        # Pre-PR-#324 main carries no Run.path; nothing to scope-hash by.
        # Once that lands and the runner threads --path into the
        # subprocess, this branch becomes inactive and persistence
        # activates automatically.
        logger.debug(
            "discovery-sweep watcher skipping persistence for run %s " "(no scope path available)",
            run.id,
        )
        return

    try:
        target = sweep_results.persist_from_lines(scope_path, run.lines, config)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: persistence is observability; failures are
        # logged but don't bubble.
        logger.exception(
            "discovery-sweep persistence failed for run %s scope %r",
            run.id,
            scope_path,
        )
        return

    if target is None:
        logger.info(
            "discovery-sweep watcher: no ATTUNE_DS final line found in "
            "run %s output — emission may be disabled or the workflow "
            "may not have completed cleanly",
            run.id,
        )
    else:
        logger.info(
            "discovery-sweep watcher persisted run %s scope %r to %s",
            run.id,
            scope_path,
            target,
        )
