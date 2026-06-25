"""Regression tests for ParallelProjectScanner's multiprocessing guard.

The parallel scanner must NOT spin up a multiprocessing.Pool for tiny
scans. Forking a Pool of ``cpu_count`` processes inside an already
multi-threaded host (e.g. a pytest-xdist worker) is a deadlock hazard: a
fork child can inherit a parent FD (an open socket, a held lock) and never
release it. On Linux (default start method ``fork``) a leaked execnet
socket FD kept the xdist *controller* from ever seeing the worker exit,
wedging CI at ~99% (see scanner-pool-fork-hang). Below the threshold the
scanner stays sequential — both faster and fork-free.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import patch

from attune.project_index.scanner_parallel import (
    _PARALLEL_MIN_FILES,
    ParallelProjectScanner,
)

# The scanner builds its Pool via ``mp.get_context("spawn").Pool`` (spawn,
# not fork — see scanner_parallel.py's fork-fd-leak note), so the parallel
# path is observed by patching ``mp.get_context``: ``.return_value.Pool`` is
# the Pool factory.
GET_CONTEXT = "attune.project_index.scanner_parallel.mp.get_context"


def _make_py_files(tmp_path, count: int) -> None:
    """Create ``count`` trivial top-level .py source files."""
    for i in range(count):
        (tmp_path / f"mod_{i}.py").write_text("x = 1\n")


class TestParallelMinFilesGuard:
    """The Pool is created only when the file count justifies the fork cost."""

    def test_empty_scan_does_not_fork_a_pool(self, tmp_path):
        """0 files (the CI hang scenario) must stay sequential — no Pool."""
        scanner = ParallelProjectScanner(str(tmp_path), workers=4)
        with patch(GET_CONTEXT) as get_ctx:
            scanner.scan(analyze_dependencies=False)
        get_ctx.assert_not_called()

    def test_small_scan_does_not_fork_a_pool(self, tmp_path):
        """A handful of files (< threshold) must stay sequential — no Pool."""
        _make_py_files(tmp_path, 3)
        scanner = ParallelProjectScanner(str(tmp_path), workers=4)
        with patch(GET_CONTEXT) as get_ctx:
            records, summary = scanner.scan(analyze_dependencies=False)
        get_ctx.assert_not_called()
        # The sequential fallback still produces records.
        assert summary.total_files == 3
        assert len(records) == 3

    def test_large_scan_uses_a_spawn_pool(self, tmp_path):
        """At/above the threshold the parallel path is taken via a SPAWN Pool.

        Pins the fork-fd-leak fix (ci-runner-hang): the Pool must be built
        from the ``spawn`` context, never the Linux-default ``fork``.
        """
        _make_py_files(tmp_path, _PARALLEL_MIN_FILES + 5)
        scanner = ParallelProjectScanner(str(tmp_path), workers=2)
        with patch(GET_CONTEXT) as get_ctx:
            # Keep the test itself fork-free: the patched Pool's context
            # manager returns no records.
            pool_ctor = get_ctx.return_value.Pool
            pool_ctor.return_value.__enter__.return_value.map.return_value = []
            scanner.scan(analyze_dependencies=False)
        get_ctx.assert_called_once_with("spawn")
        pool_ctor.assert_called_once()

    def test_single_worker_never_forks(self, tmp_path):
        """workers=1 is sequential regardless of file count."""
        _make_py_files(tmp_path, _PARALLEL_MIN_FILES + 5)
        scanner = ParallelProjectScanner(str(tmp_path), workers=1)
        with patch(GET_CONTEXT) as get_ctx:
            scanner.scan(analyze_dependencies=False)
        get_ctx.assert_not_called()
