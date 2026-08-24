"""Project Index - Main index class with persistence.

Manages the project index, persists to JSON, syncs with Redis.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path

from .models import FileRecord, IndexConfig, ProjectSummary
from .scanner import ProjectScanner
from .scanner_parallel import ParallelProjectScanner

logger = logging.getLogger(__name__)


class ProjectIndex:
    """Central project index with file metadata.

    Features:
    - JSON persistence in .attune/project_index.json
    - Optional Redis sync for real-time access
    - Query API for workflows and agents
    - Update API for writing metadata
    """

    SCHEMA_VERSION = "1.0"
    DEFAULT_INDEX_PATH = ".attune/project_index.json"

    def __init__(
        self,
        project_root: str,
        config: IndexConfig | None = None,
        redis_client: Any | None = None,
        workers: int | None = None,
        use_parallel: bool = True,
    ):
        """Initialize ProjectIndex.

        Args:
            project_root: Root directory of the project
            config: Optional index configuration
            redis_client: Optional Redis client for real-time sync
            workers: Number of worker processes for parallel scanning.
                None (default): Use all CPU cores
                1: Sequential processing
                N: Use N worker processes
            use_parallel: Whether to use parallel scanner (default: True).
                Set to False to force sequential processing.

        """
        self.project_root = Path(project_root)
        self.config = config or IndexConfig()
        self.redis_client = redis_client
        self.workers = workers
        self.use_parallel = use_parallel

        # In-memory state
        self._records: dict[str, FileRecord] = {}
        self._summary: ProjectSummary = ProjectSummary()
        self._generated_at: datetime | None = None

        # Index file path
        self._index_path = self.project_root / self.DEFAULT_INDEX_PATH

    # ===== Persistence =====

    def load(self) -> bool:
        """Load index from JSON file.

        Returns:
            True if loaded successfully, False otherwise

        """
        if not self._index_path.exists():
            logger.info("No index found at %s", self._index_path)
            return False

        try:
            with open(self._index_path, encoding="utf-8") as f:
                data = json.load(f)

            # Validate schema version
            if data.get("schema_version") != self.SCHEMA_VERSION:
                logger.warning("Schema version mismatch, regenerating index")
                return False

            # Load config
            if "config" in data:
                self.config = IndexConfig.from_dict(data["config"])

            # Load summary
            if "summary" in data:
                self._summary = ProjectSummary.from_dict(data["summary"])

            # Load records
            self._records = {}
            for path, record_data in data.get("files", {}).items():
                self._records[path] = FileRecord.from_dict(record_data)

            # Load timestamp
            if data.get("generated_at"):
                self._generated_at = datetime.fromisoformat(data["generated_at"])

            logger.info("Loaded index with %d files", len(self._records))
            return True

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to load index: %s", e)
            return False

    def save(self) -> bool:
        """Save index to JSON file.

        Returns:
            True if saved successfully, False otherwise

        """
        try:
            # Ensure directory exists
            self._index_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "schema_version": self.SCHEMA_VERSION,
                "project": self.project_root.name,
                "generated_at": datetime.now().isoformat(),
                "config": self.config.to_dict(),
                "summary": self._summary.to_dict(),
                "files": {path: record.to_dict() for path, record in self._records.items()},
            }

            validated_path = _validate_file_path(str(self._index_path))
            with open(validated_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info("Saved index with %d files to %s", len(self._records), validated_path)

            # Sync to Redis if enabled
            if self.redis_client and self.config.use_redis:
                self._sync_to_redis()

            return True

        except OSError as e:
            logger.error("Failed to save index: %s", e)
            return False

    def _sync_to_redis(self) -> None:
        """Sync index to Redis for real-time access."""
        if not self.redis_client:
            return

        try:
            prefix = self.config.redis_key_prefix

            # Store summary
            self.redis_client.set(
                f"{prefix}:summary",
                json.dumps(self._summary.to_dict()),
            )

            # Store each file record
            for path, record in self._records.items():
                self.redis_client.hset(
                    f"{prefix}:files",
                    path,
                    json.dumps(record.to_dict()),
                )

            # Store metadata
            self.redis_client.set(
                f"{prefix}:meta",
                json.dumps(
                    {
                        "generated_at": datetime.now().isoformat(),
                        "file_count": len(self._records),
                    },
                ),
            )

            logger.info("Synced index to Redis with prefix %s", prefix)

        except Exception as e:  # noqa: BLE001
            logger.error("Failed to sync to Redis: %s", e)

    # ===== Index Operations =====

    def refresh(self, analyze_dependencies: bool = True) -> None:
        """Refresh the entire index by scanning the project.

        This rebuilds the index from scratch using parallel processing when enabled.

        Args:
            analyze_dependencies: Whether to analyze import dependencies.
                Set to False for faster scans when dependency graph not needed.
                Default: True.

        Performance:
            - Sequential: ~3.6s for 3,472 files
            - Parallel (12 workers): ~1.8s for 3,472 files
            - Parallel without deps: ~1.0s for 3,472 files

        """
        logger.info("Refreshing index for %s", self.project_root)

        # Use parallel scanner by default for better performance
        if self.use_parallel and (self.workers is None or self.workers > 1):
            logger.info("Using parallel scanner (workers: %s)", self.workers or "auto")
            scanner = ParallelProjectScanner(
                str(self.project_root),
                self.config,
                workers=self.workers,
            )
        else:
            logger.info("Using sequential scanner")
            scanner = ProjectScanner(str(self.project_root), self.config)

        records, summary = scanner.scan(analyze_dependencies=analyze_dependencies)

        # Update internal state
        self._records = {r.path: r for r in records}
        self._summary = summary
        self._generated_at = datetime.now()

        # Save to disk
        self.save()

        logger.info(
            "Index refreshed: %d files, %d need attention",
            len(self._records),
            summary.files_needing_attention,
        )

    def refresh_incremental(
        self,
        analyze_dependencies: bool = True,
        base_ref: str = "HEAD",
    ) -> tuple[int, int]:
        """Incrementally refresh index by scanning only changed files.

        Uses git diff to identify changed files since last index generation.
        This is significantly faster than full refresh for small changes.

        Args:
            analyze_dependencies: Whether to rebuild dependency graph.
                Note: Even if True, only changed files are re-scanned.
                Default: True.
            base_ref: Git ref to diff against (default: "HEAD").
                Use "HEAD~1" for changes since last commit,
                "origin/main" for changes vs remote, etc.

        Returns:
            Tuple of (files_updated, files_removed)

        Performance:
            - Small change (10 files): ~0.1s vs ~1.0s full refresh (10x faster)
            - Medium change (100 files): ~0.3s vs ~1.0s full refresh (3x faster)
            - Large change (1000+ files): Similar to full refresh

        Raises:
            RuntimeError: If not in a git repository
            ValueError: If no previous index exists

        Example:
            >>> index = ProjectIndex(".")
            >>> index.load()
            >>> updated, removed = index.refresh_incremental()
            >>> print(f"Updated {updated} files, removed {removed}")

        """
        import subprocess

        # Ensure we have a previous index to update
        if not self._records:
            raise ValueError(
                "No existing index to update. Run refresh() first to create initial index.",
            )

        # Get changed files from git
        try:
            # Get untracked files
            result_untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            untracked_files = (
                set(result_untracked.stdout.strip().split("\n"))
                if result_untracked.stdout.strip()
                else set()
            )

            # Get modified/added files since base_ref
            result_modified = subprocess.run(
                ["git", "diff", "--name-only", base_ref],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            modified_files = (
                set(result_modified.stdout.strip().split("\n"))
                if result_modified.stdout.strip()
                else set()
            )

            # Get deleted files
            result_deleted = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=D", base_ref],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            deleted_files = (
                set(result_deleted.stdout.strip().split("\n"))
                if result_deleted.stdout.strip()
                else set()
            )

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e}. Are you in a git repository?") from e
        except FileNotFoundError:
            raise RuntimeError("Git not found. Incremental refresh requires git.") from None

        # Combine untracked and modified
        changed_files = untracked_files | modified_files

        # Filter out files that don't match our patterns
        changed_paths = []
        for file_str in changed_files:
            if not file_str:  # Skip empty strings
                continue
            file_path = self.project_root / file_str
            if file_path.exists() and not self._is_excluded(file_path):
                changed_paths.append(file_path)

        logger.info(
            "Incremental refresh: %d changed, %d deleted",
            len(changed_paths),
            len(deleted_files),
        )

        # If no changes, nothing to do
        if not changed_paths and not deleted_files:
            logger.info("No changes detected, index is up to date")
            return 0, 0

        # Re-scan changed files using appropriate scanner
        if changed_paths:
            if self.use_parallel and len(changed_paths) > 100:
                # Use parallel scanner for large change sets
                scanner = ParallelProjectScanner(
                    str(self.project_root),
                    self.config,
                    workers=self.workers,
                )
                # Monkey-patch _discover_files to return only changed files
                scanner._discover_files = lambda: changed_paths
            else:
                # Use sequential scanner for small change sets
                scanner = ProjectScanner(str(self.project_root), self.config)
                scanner._discover_files = lambda: changed_paths

            # Scan only changed files (without dependency analysis yet)
            new_records, _ = scanner.scan(analyze_dependencies=False)

            # Update records
            for record in new_records:
                self._records[record.path] = record

        # Remove deleted files
        files_removed = 0
        for deleted_file in deleted_files:
            if deleted_file and deleted_file in self._records:
                del self._records[deleted_file]
                files_removed += 1

        # Rebuild dependency graph if requested
        if analyze_dependencies:
            scanner = ProjectScanner(str(self.project_root), self.config)
            all_records = list(self._records.values())
            scanner._analyze_dependencies(all_records)
            scanner._calculate_impact_scores(all_records)

        # Rebuild summary
        scanner = ProjectScanner(str(self.project_root), self.config)
        self._summary = scanner._build_summary(list(self._records.values()))
        self._generated_at = datetime.now()

        # Save to disk
        self.save()

        files_updated = len(changed_paths)
        logger.info(
            "Incremental refresh complete: %d updated, %d removed",
            files_updated,
            files_removed,
        )

        return files_updated, files_removed

    def _is_excluded(self, path: Path) -> bool:
        """Check if a path should be excluded from indexing."""
        scanner = ProjectScanner(str(self.project_root), self.config)
        return scanner._is_excluded(path)

    def update_file(self, path: str, **updates: Any) -> bool:
        """Update metadata for a specific file.

        This is the write API for workflows and agents.

        Args:
            path: Relative path to the file
            **updates: Key-value pairs to update

        Returns:
            True if updated successfully

        """
        if path not in self._records:
            logger.warning("File not in index: %s", path)
            return False

        record = self._records[path]

        # Apply updates
        for key, value in updates.items():
            if hasattr(record, key):
                setattr(record, key, value)
            else:
                # Store in metadata
                record.metadata[key] = value

        record.last_indexed = datetime.now()

        # Save changes
        self.save()

        return True

    def update_coverage(self, coverage_data: dict[str, float]) -> int:
        """Update coverage data for files.

        Args:
            coverage_data: Dict mapping file paths to coverage percentages

        Returns:
            Number of files updated

        """
        updated = 0

        for path, coverage in coverage_data.items():
            # Normalize path
            path = path.removeprefix("./")

            if path in self._records:
                self._records[path].coverage_percent = coverage
                updated += 1

        if updated > 0:
            # Recalculate summary
            self._recalculate_summary()
            self.save()

        logger.info("Updated coverage for %d files", updated)
        return updated

    def _recalculate_summary(self) -> None:
        """Recalculate summary from current records."""
        records = list(self._records.values())

        # Testing health with coverage
        covered = [r for r in records if r.coverage_percent > 0]
        if covered:
            self._summary.test_coverage_avg = sum(r.coverage_percent for r in covered) / len(
                covered,
            )

    # ===== Query API =====

    def get_file(self, path: str) -> FileRecord | None:
        """Get record for a specific file."""
        return self._records.get(path)

    def get_summary(self) -> ProjectSummary:
        """Get project summary."""
        return self._summary

    def iter_all_files(self) -> Iterator[FileRecord]:
        """Iterate over all file records (memory-efficient).

        Use this when you don't need all records at once.
        """
        yield from self._records.values()

    def get_all_files(self) -> list[FileRecord]:
        """Get all file records as a list.

        Note: For large indexes, prefer iter_all_files() to avoid
        loading all records into memory at once.
        """
        return list(self.iter_all_files())

    def iter_files_needing_tests(self) -> Iterator[FileRecord]:
        """Iterate over files that need tests (memory-efficient)."""
        for r in self._records.values():
            if r.test_requirement.value == "required" and not r.tests_exist:
                yield r

    def get_files_needing_tests(self) -> list[FileRecord]:
        """Get files that need tests but don't have them."""
        return list(self.iter_files_needing_tests())

    def iter_stale_files(self) -> Iterator[FileRecord]:
        """Iterate over files with stale tests (memory-efficient)."""
        for r in self._records.values():
            if r.is_stale:
                yield r

    def get_stale_files(self) -> list[FileRecord]:
        """Get files with stale tests."""
        return list(self.iter_stale_files())

    def iter_files_needing_attention(self) -> Iterator[FileRecord]:
        """Iterate over files that need attention (memory-efficient).

        Note: For sorted results, use get_files_needing_attention().
        """
        for r in self._records.values():
            if r.needs_attention:
                yield r

    def get_files_needing_attention(self) -> list[FileRecord]:
        """Get files that need attention, sorted by impact score."""
        return sorted(
            self.iter_files_needing_attention(),
            key=lambda r: -r.impact_score,
        )

    def iter_high_impact_files(self) -> Iterator[FileRecord]:
        """Iterate over high-impact files (memory-efficient).

        Note: For sorted results, use get_high_impact_files().
        """
        for r in self._records.values():
            if r.impact_score >= self.config.high_impact_threshold:
                yield r

    def get_high_impact_files(self) -> list[FileRecord]:
        """Get high-impact files sorted by impact score."""
        return sorted(
            self.iter_high_impact_files(),
            key=lambda r: -r.impact_score,
        )

    def get_files_by_category(self, category: str) -> list[FileRecord]:
        """Get files by category."""
        return [r for r in self._records.values() if r.category.value == category]

    def get_files_by_language(self, language: str) -> list[FileRecord]:
        """Get files by programming language."""
        return [r for r in self._records.values() if r.language == language]

    def search_files(self, pattern: str) -> list[FileRecord]:
        """Search files by path pattern."""
        import fnmatch

        return [r for r in self._records.values() if fnmatch.fnmatch(r.path, pattern)]

    def get_dependents(self, path: str) -> list[FileRecord]:
        """Get files that depend on the given file."""
        record = self._records.get(path)
        if not record:
            return []
        return [self._records[p] for p in record.imported_by if p in self._records]

    def get_dependencies(self, path: str) -> list[FileRecord]:
        """Get files that the given file depends on."""
        record = self._records.get(path)
        if not record:
            return []
        # Match imports to paths
        results = []
        for imp in record.imports:
            for other_path, other_record in self._records.items():
                if imp in other_path.replace("/", ".").replace("\\", "."):
                    results.append(other_record)
                    break
        return results

    # ===== Statistics =====

    def get_test_gap_stats(self) -> dict[str, Any]:
        """Get statistics about test gaps."""
        files_needing_tests = self.get_files_needing_tests()

        return {
            "files_without_tests": len(files_needing_tests),
            "high_impact_untested": len(
                [
                    f
                    for f in files_needing_tests
                    if f.impact_score >= self.config.high_impact_threshold
                ],
            ),
            "total_loc_untested": sum(f.lines_of_code for f in files_needing_tests),
            "by_directory": self._group_by_directory(files_needing_tests),
        }

    def get_staleness_stats(self) -> dict[str, Any]:
        """Get statistics about stale tests."""
        stale = self.get_stale_files()

        return {
            "stale_count": len(stale),
            "avg_staleness_days": sum(f.staleness_days for f in stale) / len(stale) if stale else 0,
            "max_staleness_days": max((f.staleness_days for f in stale), default=0),
            "by_directory": self._group_by_directory(stale),
        }

    def _group_by_directory(self, records: list[FileRecord]) -> dict[str, int]:
        """Group records by top-level directory."""
        counts: dict[str, int] = {}
        for r in records:
            parts = r.path.split("/")
            if len(parts) > 1:
                dir_name = parts[0]
            else:
                dir_name = "."
            counts[dir_name] = counts.get(dir_name, 0) + 1
        return counts

    # ===== Context for Workflows =====

    def get_context_for_workflow(self, workflow_type: str) -> dict[str, Any]:
        """Get relevant context for a specific workflow type.

        This provides a filtered view of the index tailored to workflow needs.
        """
        if workflow_type == "test_gen":
            files = self.get_files_needing_tests()
            return {
                "files_needing_tests": [f.to_dict() for f in files[:20]],
                "summary": self.get_test_gap_stats(),
                "priority_files": [
                    f.path for f in files if f.impact_score >= self.config.high_impact_threshold
                ][:10],
            }

        if workflow_type == "code_review":
            return {
                "high_impact_files": [f.to_dict() for f in self.get_high_impact_files()[:10]],
                "stale_files": [f.to_dict() for f in self.get_stale_files()[:10]],
                "summary": self._summary.to_dict(),
            }

        if workflow_type == "security_audit":
            return {
                "all_source_files": [f.to_dict() for f in self.get_files_by_category("source")],
                "untested_files": [f.to_dict() for f in self.get_files_needing_tests()],
                "summary": self._summary.to_dict(),
            }

        if workflow_type == "documentation":
            # Doc-coverage view (#2220). The doc-orchestrator's index
            # fallback consumed this key for years while NO branch
            # produced it — every read defaulted empty and zero items
            # rendered as "no gaps found". The presence of
            # ``files_without_docstrings`` is also the scout's
            # scan-was-performed marker, so only emit it from this
            # branch, where it is genuinely computed.
            undocumented = [f for f in self.get_files_by_category("source") if not f.has_docstrings]
            return {
                "files_without_docstrings": [
                    {"path": f.path, "loc": f.lines_of_code} for f in undocumented[:50]
                ],
                "summary": self._summary.to_dict(),
            }

        return {
            "summary": self._summary.to_dict(),
            "files_needing_attention": [
                f.to_dict() for f in self.get_files_needing_attention()[:20]
            ],
        }
