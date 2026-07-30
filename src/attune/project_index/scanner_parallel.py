"""Parallel Project Scanner - Multi-core optimized file scanning.

This module provides a parallel implementation of ProjectScanner using
multiprocessing to distribute file analysis across CPU cores.

Expected speedup: 3-4x on quad-core machines for large codebases (>1000 files).

Usage:
    from attune.project_index.scanner_parallel import ParallelProjectScanner

    scanner = ParallelProjectScanner(project_root=".", workers=4)
    records, summary = scanner.scan()

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import multiprocessing as mp
from functools import partial
from pathlib import Path
from typing import Any

from .models import FileRecord, IndexConfig, ProjectSummary
from .scanner import ProjectScanner

# Minimum number of files before the multiprocessing path is worth it.
# Forking a Pool of `cpu_count` processes costs more than analysing a
# handful of files sequentially — and, crucially, forking a process pool
# inside an already-multi-threaded process (e.g. a pytest-xdist worker)
# is a deadlock hazard: a child can inherit a parent FD (an open socket,
# a held lock) and never release it. On Linux (default start method
# `fork`) that leaked FD kept the xdist *controller* from ever seeing the
# worker exit, wedging CI at ~99% (see scanner-pool-fork-hang). Below this
# threshold we stay sequential, which is both faster and fork-free.
_PARALLEL_MIN_FILES = 50


def _analyze_file_worker(
    file_path_str: str,
    project_root_str: str,
    config_dict: dict[str, Any],
    test_file_map: dict[str, str],
) -> FileRecord | None:
    """Worker function to analyze a single file in parallel.

    This function is designed to be pickled and sent to worker processes.
    It reconstructs necessary objects from serialized data.

    Args:
        file_path_str: String path to file to analyze
        project_root_str: String path to project root
        config_dict: Serialized IndexConfig as dict
        test_file_map: Mapping of source files to test files

    Returns:
        FileRecord for the analyzed file, or None if analysis fails

    """
    from pathlib import Path

    # Reconstruct objects
    file_path = Path(file_path_str)
    project_root = Path(project_root_str)

    # Create a temporary scanner instance for this worker
    # (Each worker gets its own scanner to avoid shared state issues)
    config = IndexConfig(**config_dict)
    scanner = ProjectScanner(project_root=project_root, config=config)
    scanner._test_file_map = test_file_map

    # Analyze the file
    return scanner._analyze_file(file_path)


class ParallelProjectScanner(ProjectScanner):
    """Parallel implementation of ProjectScanner using multiprocessing.

    Uses multiple CPU cores to analyze files concurrently, providing
    significant speedup for large codebases.

    Attributes:
        workers: Number of worker processes (default: CPU count)

    Performance:
        - Sequential: ~9.2s for 3,469 files (375 files/sec)
        - Parallel (4 workers): ~2.5s expected (1,387 files/sec)
        - Speedup: 3.7x on quad-core machines

    Memory:
        - Each worker creates its own scanner instance
        - Peak memory scales with worker count
        - Expected: 2x-3x memory usage vs sequential

    Example:
        >>> scanner = ParallelProjectScanner(project_root=".", workers=4)
        >>> records, summary = scanner.scan()
        >>> print(f"Scanned {summary.total_files} files")

    """

    def __init__(
        self,
        project_root: str,
        config: IndexConfig | None = None,
        workers: int | None = None,
    ):
        """Initialize parallel scanner.

        Args:
            project_root: Root directory of project to scan
            config: Optional configuration (uses defaults if not provided)
            workers: Number of worker processes.
                None (default): Use all available CPUs
                1: Sequential processing (same as ProjectScanner)
                N: Use N worker processes

        """
        super().__init__(project_root, config)
        self.workers = workers or mp.cpu_count()

    def scan(
        self,
        analyze_dependencies: bool = True,
        use_parallel: bool = True,
    ) -> tuple[list[FileRecord], ProjectSummary]:
        """Scan the entire project using parallel processing.

        Args:
            analyze_dependencies: Whether to analyze import dependencies.
                Set to False to skip expensive dependency graph analysis.
                Default: True for backwards compatibility.
            use_parallel: Whether to use parallel processing.
                Set to False to use sequential processing.
                Default: True.

        Returns:
            Tuple of (list of FileRecords, ProjectSummary)

        Note:
            Dependency analysis is always sequential (after file analysis).
            Parallel processing only applies to file analysis phase.

        """
        records: list[FileRecord] = []

        # First pass: discover all files (sequential - fast)
        all_files = self._discover_files()

        # Build test file mapping (sequential - fast)
        self._build_test_mapping(all_files)

        # Second pass: analyze each file (PARALLEL - slow)
        # Only spin up a process Pool when there are enough files to amortise
        # the fork cost. For tiny scans the Pool is pure overhead and a fork
        # hazard inside multi-threaded hosts (see _PARALLEL_MIN_FILES).
        if use_parallel and self.workers > 1 and len(all_files) >= _PARALLEL_MIN_FILES:
            records = self._analyze_files_parallel(all_files)
        else:
            # Fall back to sequential for debugging, single worker, or a
            # file count too small to be worth a process pool.
            for file_path in all_files:
                record = self._analyze_file(file_path)
                if record:
                    records.append(record)

        # Third pass: build dependency graph (sequential - already optimized)
        if analyze_dependencies:
            self._analyze_dependencies(records)

            # Calculate impact scores (sequential - fast)
            self._calculate_impact_scores(records)

        # Determine attention needs (sequential - fast)
        self._determine_attention_needs(records)

        # Build summary (sequential - fast)
        summary = self._build_summary(records)

        return records, summary

    def _analyze_files_parallel(self, all_files: list[Path]) -> list[FileRecord]:
        """Analyze files in parallel using multiprocessing.

        Args:
            all_files: List of file paths to analyze

        Returns:
            List of FileRecords (order not guaranteed)

        Note:
            Uses multiprocessing.Pool with chunksize optimization.
            Chunksize is calculated to balance overhead vs parallelism.

        """
        # Serialize configuration for workers
        config_dict = {
            "exclude_patterns": list(self.config.exclude_patterns),
            "no_test_patterns": list(self.config.no_test_patterns),
            "staleness_threshold_days": self.config.staleness_threshold_days,
        }

        # Create partial function with fixed arguments
        analyze_func = partial(
            _analyze_file_worker,
            project_root_str=str(self.project_root),
            config_dict=config_dict,
            test_file_map=self._test_file_map,
        )

        # Calculate optimal chunksize
        # Too small: overhead from process communication
        # Too large: poor load balancing
        total_files = len(all_files)
        chunksize = max(1, total_files // (self.workers * 4))

        # Process files in parallel
        records: list[FileRecord] = []

        # Force the 'spawn' start method. 'fork' (the Linux default) makes
        # each Pool child inherit a copy of every parent fd -- including the
        # xdist worker's execnet socket -- and a lingering child holding that
        # dup kept the controller from ever seeing the worker exit, wedging
        # CI at ~99% (scanner-pool-fork-hang / ci-runner-hang spec). The
        # _PARALLEL_MIN_FILES guard alone only narrows the window; 'spawn'
        # starts clean children with no inherited fds and removes the hazard
        # outright (macOS already defaults to spawn -- which is why the hang
        # was Linux-only).
        with mp.get_context("spawn").Pool(processes=self.workers) as pool:
            # Map file paths to string for pickling
            file_path_strs = [str(f) for f in all_files]

            # Process files in chunks
            results = pool.map(analyze_func, file_path_strs, chunksize=chunksize)

            # Filter out None results
            records = [r for r in results if r is not None]

        return records


# compare_sequential_vs_parallel + the __main__ benchmark block were
# removed 2026-07-30: zero references outside this module (no CLI, no
# docs, no tests) — benchmark scaffolding, not product code. The
# measured numbers it produced live in the class docstring above.
