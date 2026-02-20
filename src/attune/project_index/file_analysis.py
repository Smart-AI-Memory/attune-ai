"""File Analysis - Categorization, language detection, and test mapping.

Handles file-level classification: determining category (source, test, config,
docs, asset), programming language, test requirement level, and matching
source files to their corresponding test files.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import fnmatch
import os
import re
from pathlib import Path

from .models import FileCategory, TestRequirement


class FileAnalysisMixin:
    """Mixin providing file categorization, exclusion, and test mapping.

    Expects the consuming class to provide:
        - self.project_root: Path
        - self.config: IndexConfig
        - self._test_file_map: dict[str, str]
        - self._compiled_patterns: dict[str, tuple[re.Pattern, str | None]]
    """

    # Optimization: Use frozensets for O(1) membership testing (vs O(n) with lists)
    # These are used on every file during categorization (thousands of files)
    CONFIG_SUFFIXES = frozenset({".yml", ".yaml", ".toml", ".ini", ".cfg", ".json"})
    DOC_SUFFIXES = frozenset({".md", ".rst", ".txt"})
    DOC_NAMES = frozenset({"README", "CHANGELOG", "LICENSE"})
    ASSET_SUFFIXES = frozenset({".css", ".scss", ".html", ".svg", ".png", ".jpg", ".gif"})
    SOURCE_SUFFIXES = frozenset({".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java"})

    def _compile_glob_patterns(self) -> None:
        """Pre-compile glob patterns for faster matching.

        Called once at init to avoid recompiling patterns on every file check.
        Profiling showed fnmatch.fnmatch() called 823,433 times - this optimization
        reduces that overhead by ~70% by using pre-compiled regex patterns.
        """
        all_patterns = list(self.config.exclude_patterns) + list(self.config.no_test_patterns)

        for pattern in all_patterns:
            if pattern in self._compiled_patterns:
                continue

            # Extract directory name for ** patterns
            dir_name = None
            if "**" in pattern:
                if pattern.startswith("**/") and pattern.endswith("/**"):
                    dir_name = pattern[3:-3]  # e.g., "**/node_modules/**" -> "node_modules"
                elif pattern.endswith("/**"):
                    dir_name = pattern.replace("**/", "").replace("/**", "")

            # Compile simple pattern (without **) for fnmatch-style matching
            simple_pattern = pattern.replace("**/", "")
            try:
                regex_pattern = fnmatch.translate(simple_pattern)
                compiled = re.compile(regex_pattern)
            except re.error:
                # Fallback for invalid patterns
                compiled = re.compile(re.escape(simple_pattern))

            self._compiled_patterns[pattern] = (compiled, dir_name)

    def _matches_glob_pattern(self, path: Path, pattern: str) -> bool:
        """Check if a path matches a glob pattern (handles ** patterns).

        Uses pre-compiled regex patterns for performance. This method is called
        ~800K+ times during a full scan, so caching the compiled patterns
        provides significant speedup.
        """
        rel_str = str(path)
        path_parts = path.parts

        # Get pre-compiled pattern (or compile on-demand if not cached)
        if pattern not in self._compiled_patterns:
            # Lazily compile patterns not seen at init time
            dir_name = None
            if "**" in pattern:
                if pattern.startswith("**/") and pattern.endswith("/**"):
                    dir_name = pattern[3:-3]
                elif pattern.endswith("/**"):
                    dir_name = pattern.replace("**/", "").replace("/**", "")

            simple_pattern = pattern.replace("**/", "")
            try:
                regex_pattern = fnmatch.translate(simple_pattern)
                compiled = re.compile(regex_pattern)
            except re.error:
                compiled = re.compile(re.escape(simple_pattern))
            self._compiled_patterns[pattern] = (compiled, dir_name)

        compiled_regex, dir_name = self._compiled_patterns[pattern]

        # Handle ** glob patterns
        if "**" in pattern:
            # Check if the pattern matches the path or filename using compiled regex
            if compiled_regex.match(rel_str):
                return True
            if compiled_regex.match(path.name):
                return True

            # Check directory-based exclusions (fast path check)
            if dir_name and dir_name in path_parts:
                return True
        else:
            # Use compiled regex instead of fnmatch.fnmatch()
            if compiled_regex.match(rel_str):
                return True
            if compiled_regex.match(path.name):
                return True

        return False

    def _is_excluded(self, path: Path) -> bool:
        """Check if a path should be excluded."""
        for pattern in self.config.exclude_patterns:
            if self._matches_glob_pattern(path, pattern):
                return True
        return False

    def _discover_files(self) -> list[Path]:
        """Discover all relevant files in the project."""
        files = []

        for root, dirs, filenames in os.walk(self.project_root):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self._is_excluded(Path(root) / d)]

            for filename in filenames:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(self.project_root)

                if not self._is_excluded(rel_path):
                    files.append(file_path)

        return files

    def _is_test_file(self, path: Path) -> bool:
        """Check if a file is a test file."""
        name = path.stem
        return (
            name.startswith("test_")
            or name.endswith("_test")
            or "tests" in path.parts
            or path.parent.name == "test"
        )

    def _determine_category(self, path: Path) -> FileCategory:
        """Determine the category of a file."""
        if self._is_test_file(path):
            return FileCategory.TEST

        suffix = path.suffix.lower()

        # Optimization: Use frozensets for O(1) lookup (called for every file)
        if suffix in self.CONFIG_SUFFIXES:
            return FileCategory.CONFIG

        if suffix in self.DOC_SUFFIXES or path.name in self.DOC_NAMES:
            return FileCategory.DOCS

        if suffix in self.ASSET_SUFFIXES:
            return FileCategory.ASSET

        if suffix in self.SOURCE_SUFFIXES:
            return FileCategory.SOURCE

        return FileCategory.UNKNOWN

    def _determine_language(self, path: Path) -> str:
        """Determine the programming language of a file."""
        suffix_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
        }
        return suffix_map.get(path.suffix.lower(), "")

    def _determine_test_requirement(self, path: Path, category: FileCategory) -> TestRequirement:
        """Determine if a file requires tests."""
        rel_path = path.relative_to(self.project_root)

        # Test files don't need tests
        if category == FileCategory.TEST:
            return TestRequirement.NOT_APPLICABLE

        # Config, docs, assets don't need tests
        if category in [FileCategory.CONFIG, FileCategory.DOCS, FileCategory.ASSET]:
            return TestRequirement.NOT_APPLICABLE

        # Check exclusion patterns using glob matching
        for pattern in self.config.no_test_patterns:
            if self._matches_glob_pattern(rel_path, pattern):
                return TestRequirement.NOT_APPLICABLE

        # __init__.py files usually don't need tests unless they have logic
        if path.name == "__init__.py":
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                # If it's just imports/exports, no tests needed
                if len(content.strip().split("\n")) < 20:
                    return TestRequirement.OPTIONAL
            except OSError:
                pass

        return TestRequirement.REQUIRED

    def _build_test_mapping(self, files: list[Path]) -> None:
        """Build mapping from source files to their test files.

        Optimized to use O(1) dict lookups instead of O(n) linear search.
        Previous implementation was O(n*m), now O(n+m).
        """
        # Build index of non-test files by stem name for O(1) lookups
        # This replaces the inner loop that searched all files
        source_files_by_stem: dict[str, list[Path]] = {}
        for f in files:
            if not self._is_test_file(f):
                stem = f.stem
                if stem not in source_files_by_stem:
                    source_files_by_stem[stem] = []
                source_files_by_stem[stem].append(f)

        # Now match test files to source files with O(1) lookups
        for f in files:
            if not self._is_test_file(f):
                continue

            test_name = f.stem  # e.g., "test_core"

            # Common patterns: test_foo.py -> foo.py
            if test_name.startswith("test_"):
                source_name = test_name[5:]  # Remove "test_" prefix
            elif test_name.endswith("_test"):
                source_name = test_name[:-5]  # Remove "_test" suffix
            else:
                continue

            # O(1) lookup instead of O(n) linear search
            matching_sources = source_files_by_stem.get(source_name, [])
            if matching_sources:
                # Use first match (typically there's only one)
                source_file = matching_sources[0]
                rel_source = str(source_file.relative_to(self.project_root))
                rel_test = str(f.relative_to(self.project_root))
                self._test_file_map[rel_source] = rel_test
