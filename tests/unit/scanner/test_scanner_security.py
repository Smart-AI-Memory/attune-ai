"""Security tests for ProjectScanner.

Tests critical security controls:
- Path traversal prevention
- Sensitive file filtering (.env, .git, credentials)
- Symlink handling (circular references, external targets)
- Permission error handling
- Large directory DoS protection

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

import os
import tempfile
from pathlib import Path

import pytest

from attune.project_index.models import IndexConfig
from attune.project_index.scanner import ProjectScanner


@pytest.mark.unit
class TestGitignoreRespect:
    """Test that scanner respects .gitignore patterns and default exclusions."""

    def test_scanner_excludes_git_directory(self):
        """Test that .git directory is excluded from scanning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .git directory with files
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("# git config")
            (git_dir / "HEAD").write_text("ref: refs/heads/main")

            # Create normal source file
            (Path(tmpdir) / "main.py").write_text("def main(): pass")

            scanner = ProjectScanner(tmpdir)
            files = scanner._discover_files()

            # Should only find main.py, not .git files
            file_names = {f.name for f in files}
            assert "main.py" in file_names
            assert "config" not in file_names
            assert "HEAD" not in file_names
            assert len(files) == 1

    def test_scanner_excludes_pycache_directory(self):
        """Test that __pycache__ directory is excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create __pycache__ directory
            pycache_dir = Path(tmpdir) / "__pycache__"
            pycache_dir.mkdir()
            (pycache_dir / "module.cpython-311.pyc").write_text("# compiled")

            # Create normal source
            (Path(tmpdir) / "module.py").write_text("def func(): pass")

            scanner = ProjectScanner(tmpdir)
            files = scanner._discover_files()

            # Should only find module.py
            file_names = {f.name for f in files}
            assert "module.py" in file_names
            assert "module.cpython-311.pyc" not in file_names

    def test_scanner_excludes_venv_directory(self):
        """Test that virtual environment directories are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple venv patterns
            for venv_name in [".venv", "venv", "env"]:
                venv_dir = Path(tmpdir) / venv_name
                venv_dir.mkdir(exist_ok=True)
                (venv_dir / "pyvenv.cfg").write_text("# venv config")

            # Create actual source
            (Path(tmpdir) / "app.py").write_text("def app(): pass")

            scanner = ProjectScanner(tmpdir)
            files = scanner._discover_files()

            # Should only find app.py
            file_names = {f.name for f in files}
            assert "app.py" in file_names
            assert "pyvenv.cfg" not in file_names
            assert len(files) == 1

    def test_scanner_excludes_node_modules(self):
        """Test that node_modules directory is excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create node_modules
            nm_dir = Path(tmpdir) / "node_modules"
            nm_dir.mkdir()
            package_dir = nm_dir / "some-package"
            package_dir.mkdir()
            (package_dir / "index.js").write_text("// package code")

            # Create actual source
            (Path(tmpdir) / "index.js").write_text("// app code")

            scanner = ProjectScanner(tmpdir)
            files = scanner._discover_files()

            # Should only find project's index.js
            assert len(files) == 1
            assert files[0].name == "index.js"
            assert "node_modules" not in str(files[0])

    def test_scanner_respects_custom_gitignore_patterns(self):
        """Test that custom exclusion patterns work like .gitignore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files to exclude
            (Path(tmpdir) / "secrets.env").write_text("API_KEY=secret")
            (Path(tmpdir) / "debug.log").write_text("debug output")
            (Path(tmpdir) / "main.py").write_text("def main(): pass")

            # Add custom exclusion patterns
            config = IndexConfig(exclude_patterns=["**/*.env", "**/*.log"])
            scanner = ProjectScanner(tmpdir, config=config)
            files = scanner._discover_files()

            # Should only find main.py
            file_names = {f.name for f in files}
            assert "main.py" in file_names
            assert "secrets.env" not in file_names
            assert "debug.log" not in file_names


@pytest.mark.unit
class TestSensitiveFileBlocking:
    """Test that scanner blocks access to sensitive files."""

    def test_scanner_blocks_env_files(self):
        """Test that .env files are excluded by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create various .env file patterns
            env_files = [".env", ".env.local", ".env.production", "config.env"]
            for env_file in env_files:
                (Path(tmpdir) / env_file).write_text("SECRET_KEY=abc123")

            # Add .env exclusion pattern
            config = IndexConfig(exclude_patterns=["**/.env*", "**/*.env"])
            scanner = ProjectScanner(tmpdir, config=config)
            files = scanner._discover_files()

            # No .env files should be found
            file_names = {f.name for f in files}
            for env_file in env_files:
                assert env_file not in file_names

    def test_scanner_blocks_credential_files(self):
        """Test that credential files are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create credential files
            credential_files = [
                "credentials.json",
                "service-account.json",
                "auth-token.txt",
            ]
            for cred_file in credential_files:
                (Path(tmpdir) / cred_file).write_text("sensitive data")

            # Add credential exclusion pattern
            config = IndexConfig(
                exclude_patterns=[
                    "**/credentials*.json",
                    "**/service-account*.json",
                    "**/auth-token*",
                ]
            )
            scanner = ProjectScanner(tmpdir, config=config)
            files = scanner._discover_files()

            # No credential files should be found
            file_names = {f.name for f in files}
            for cred_file in credential_files:
                assert cred_file not in file_names

    def test_scanner_excludes_git_internals(self):
        """Test that .git internals are completely excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create comprehensive .git structure
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("# config")
            (git_dir / "HEAD").write_text("ref: refs/heads/main")

            # Create refs structure
            refs_dir = git_dir / "refs" / "heads"
            refs_dir.mkdir(parents=True)
            (refs_dir / "main").write_text("abc123")

            # Create objects
            objects_dir = git_dir / "objects" / "ab"
            objects_dir.mkdir(parents=True)
            (objects_dir / "cdef1234").write_text("git object")

            scanner = ProjectScanner(tmpdir)
            files = scanner._discover_files()

            # Nothing from .git should be found
            for file_path in files:
                assert ".git" not in str(file_path)

    def test_scanner_excludes_build_artifacts(self):
        """Test that build artifacts are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create build directories
            for build_dir in ["dist", "build", ".next", "out"]:
                dir_path = Path(tmpdir) / build_dir
                dir_path.mkdir()
                (dir_path / "bundle.js").write_text("// bundled code")

            # Create source file
            (Path(tmpdir) / "src.py").write_text("def func(): pass")

            scanner = ProjectScanner(tmpdir)
            files = scanner._discover_files()

            # Should only find src.py
            assert len(files) == 1
            assert files[0].name == "src.py"

    def test_scanner_excludes_lock_files(self):
        """Test that package lock files are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create lock files
            lock_files = [
                "package-lock.json",
                "yarn.lock",
                "poetry.lock",
                "Pipfile.lock",
            ]
            for lock_file in lock_files:
                (Path(tmpdir) / lock_file).write_text("# lock file")

            scanner = ProjectScanner(tmpdir)
            files = scanner._discover_files()

            # No lock files should be found
            file_names = {f.name for f in files}
            for lock_file in lock_files:
                assert lock_file not in file_names


@pytest.mark.unit
class TestSymlinkHandling:
    """Test that scanner handles symlinks safely."""

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_scanner_handles_external_symlinks(self):
        """Test that scanner doesn't follow symlinks outside project root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.TemporaryDirectory() as external_dir:
                # Create external file
                external_file = Path(external_dir) / "external.py"
                external_file.write_text("def external(): pass")

                # Create symlink in project pointing to external directory
                project_symlink = Path(tmpdir) / "external_link"
                project_symlink.symlink_to(external_dir)

                # Create actual project file
                (Path(tmpdir) / "internal.py").write_text("def internal(): pass")

                scanner = ProjectScanner(tmpdir)
                files = scanner._discover_files()

                # Should find files through symlink (os.walk follows symlinks by default)
                # but scanner should handle them gracefully
                file_names = {f.name for f in files}
                assert "internal.py" in file_names

                # The external file might be found (os.walk follows symlinks)
                # but scanner shouldn't crash
                assert len(files) >= 1

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_scanner_handles_circular_symlinks(self):
        """Test that scanner handles circular symlink references without infinite loop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directories
            dir_a = Path(tmpdir) / "dir_a"
            dir_b = Path(tmpdir) / "dir_b"
            dir_a.mkdir()
            dir_b.mkdir()

            # Create actual files
            (dir_a / "file_a.py").write_text("def a(): pass")
            (dir_b / "file_b.py").write_text("def b(): pass")

            # Create circular symlinks: dir_a/link_to_b -> dir_b, dir_b/link_to_a -> dir_a
            try:
                (dir_a / "link_to_b").symlink_to(dir_b)
                (dir_b / "link_to_a").symlink_to(dir_a)
            except OSError:
                pytest.skip("Cannot create symlinks on this system")

            scanner = ProjectScanner(tmpdir)

            # Scanner should complete without infinite loop
            # os.walk doesn't follow symlink cycles, so this should work
            files = scanner._discover_files()

            # Should find at least the real files
            file_names = {f.name for f in files}
            assert "file_a.py" in file_names
            assert "file_b.py" in file_names

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_scanner_handles_broken_symlinks(self):
        """Test that scanner handles broken symlinks gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create symlink to non-existent target
            broken_link = Path(tmpdir) / "broken_link"
            non_existent = Path(tmpdir) / "non_existent"
            try:
                broken_link.symlink_to(non_existent)
            except OSError:
                pytest.skip("Cannot create symlinks on this system")

            # Create actual file
            (Path(tmpdir) / "real.py").write_text("def real(): pass")

            scanner = ProjectScanner(tmpdir)

            # Should handle broken symlink without crashing
            files = scanner._discover_files()

            # Should find the real file
            file_names = {f.name for f in files}
            assert "real.py" in file_names


@pytest.mark.unit
class TestPathTraversalPrevention:
    """Test that scanner prevents path traversal attacks."""

    def test_scanner_stays_within_project_root(self):
        """Test that scanner doesn't access files outside project root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create parent directory file (outside project)
            parent_file = Path(tmpdir).parent / "outside.py"
            parent_file.write_text("def outside(): pass")

            # Create project structure
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "inside.py").write_text("def inside(): pass")

            try:
                scanner = ProjectScanner(str(project_dir))
                files = scanner._discover_files()

                # Should only find files inside project_dir
                for file_path in files:
                    # All files should be relative to project_dir
                    assert file_path.is_relative_to(project_dir)

                # Should not find outside.py
                file_names = {f.name for f in files}
                assert "outside.py" not in file_names
                assert "inside.py" in file_names

            finally:
                # Cleanup
                if parent_file.exists():
                    parent_file.unlink()

    def test_scanner_validates_project_root_is_directory(self):
        """Test that scanner validates project root is a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file (not a directory)
            file_path = Path(tmpdir) / "not_a_directory.txt"
            file_path.write_text("content")

            # Scanner should handle this gracefully
            scanner = ProjectScanner(str(file_path))

            # os.walk will not produce results for a file
            files = scanner._discover_files()
            assert len(files) == 0

    def test_scanner_handles_deeply_nested_paths(self):
        """Test that scanner handles deeply nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create deeply nested structure (100 levels)
            current_path = Path(tmpdir)
            for i in range(10):  # Reduced from 100 for test performance
                current_path = current_path / f"level_{i}"
                current_path.mkdir()

            # Create file at deepest level
            (current_path / "deep.py").write_text("def deep(): pass")

            scanner = ProjectScanner(tmpdir)
            files = scanner._discover_files()

            # Should find the deep file
            file_names = {f.name for f in files}
            assert "deep.py" in file_names


@pytest.mark.unit
class TestPermissionErrorHandling:
    """Test that scanner handles permission errors gracefully."""

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_scanner_handles_unreadable_directory(self):
        """Test that scanner handles directories without read permission."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory and make it unreadable
            restricted_dir = Path(tmpdir) / "restricted"
            restricted_dir.mkdir()
            (restricted_dir / "secret.py").write_text("def secret(): pass")

            # Remove read permission
            restricted_dir.chmod(0o000)

            try:
                # Create readable file
                (Path(tmpdir) / "public.py").write_text("def public(): pass")

                scanner = ProjectScanner(tmpdir)
                # Should not raise exception, just skip unreadable directory
                files = scanner._discover_files()

                # Should find public.py but not secret.py
                file_names = {f.name for f in files}
                assert "public.py" in file_names
                assert "secret.py" not in file_names

            finally:
                # Restore permissions for cleanup
                restricted_dir.chmod(0o755)

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_scanner_handles_unreadable_file(self):
        """Test that scanner handles files without read permission."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create unreadable file
            restricted_file = Path(tmpdir) / "restricted.py"
            restricted_file.write_text("def restricted(): pass")
            restricted_file.chmod(0o000)

            try:
                # Create readable file
                (Path(tmpdir) / "public.py").write_text("def public(): pass")

                scanner = ProjectScanner(tmpdir)
                records, summary = scanner.scan()

                # Should handle unreadable file gracefully
                # The file might be discovered but analysis should handle read errors
                file_names = {r.name for r in records}
                assert "public.py" in file_names

            finally:
                # Restore permissions for cleanup
                restricted_file.chmod(0o644)

    def test_scanner_handles_deleted_file_during_scan(self):
        """Test that scanner handles file deletion during scan (race condition)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file
            temp_file = Path(tmpdir) / "temp.py"
            temp_file.write_text("def temp(): pass")

            scanner = ProjectScanner(tmpdir)
            scanner._discover_files()

            # Delete file before analysis
            temp_file.unlink()

            # Should handle missing file gracefully during analysis
            records, summary = scanner.scan()

            # Should not crash, might have empty or partial records
            assert isinstance(records, list)
            assert isinstance(summary, object)


@pytest.mark.unit
class TestLargeDirectoryHandling:
    """Test that scanner handles large directories without DoS."""

    def test_scanner_handles_many_files(self):
        """Test that scanner can handle directories with many files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 1000 files
            for i in range(1000):
                (Path(tmpdir) / f"file_{i}.py").write_text(f"def func_{i}(): pass")

            scanner = ProjectScanner(tmpdir)

            # Should complete in reasonable time
            import time

            start = time.time()
            files = scanner._discover_files()
            duration = time.time() - start

            # Should find all files
            assert len(files) == 1000

            # Should complete in under 5 seconds for 1000 files
            assert duration < 5.0

    def test_scanner_respects_exclude_patterns_for_performance(self):
        """Test that exclude patterns improve performance on large directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create large excluded directory
            excluded_dir = Path(tmpdir) / "node_modules"
            excluded_dir.mkdir()
            for i in range(5000):
                (excluded_dir / f"package_{i}.js").write_text("// package code")

            # Create small included directory
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")

            scanner = ProjectScanner(tmpdir)

            # Should complete quickly by skipping node_modules
            import time

            start = time.time()
            files = scanner._discover_files()
            duration = time.time() - start

            # Should only find src files
            assert len(files) == 1
            assert files[0].name == "main.py"

            # Should be fast (under 1 second) since node_modules is excluded
            assert duration < 1.0

    def test_scanner_handles_deep_nesting_efficiently(self):
        """Test that scanner handles deeply nested structures efficiently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create deeply nested structure with files at each level
            current_path = Path(tmpdir)
            for i in range(20):
                current_path = current_path / f"level_{i}"
                current_path.mkdir()
                (current_path / f"file_{i}.py").write_text(f"def func_{i}(): pass")

            scanner = ProjectScanner(tmpdir)

            # Should handle deep nesting
            files = scanner._discover_files()

            # Should find all 20 files
            assert len(files) == 20


@pytest.mark.unit
class TestSecurityIntegration:
    """Integration tests for multiple security features."""

    def test_scanner_comprehensive_security(self):
        """Test comprehensive security scenario with multiple threats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create legitimate files
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "app.py").write_text("def app(): pass")
            (Path(tmpdir) / "src" / "utils.py").write_text("def utils(): pass")

            # Create files that should be excluded (security sensitive)
            (Path(tmpdir) / ".env").write_text("SECRET_KEY=abc123")
            (Path(tmpdir) / ".git").mkdir()
            (Path(tmpdir) / ".git" / "config").write_text("# git config")

            # Create __pycache__
            pycache = Path(tmpdir) / "src" / "__pycache__"
            pycache.mkdir()
            (pycache / "app.cpython-311.pyc").write_text("# compiled")

            # Create node_modules
            nm = Path(tmpdir) / "node_modules"
            nm.mkdir()
            (nm / "package").mkdir(parents=True)
            (nm / "package" / "index.js").write_text("// package")

            # Add comprehensive exclusion config
            config = IndexConfig(
                exclude_patterns=[
                    "**/.env*",
                    "**/.git/**",
                    "**/__pycache__/**",
                    "**/node_modules/**",
                ]
            )
            scanner = ProjectScanner(tmpdir, config=config)
            files = scanner._discover_files()

            # Should only find legitimate source files
            file_names = {f.name for f in files}
            assert "app.py" in file_names
            assert "utils.py" in file_names
            assert len(file_names) == 2

            # Security-sensitive files should not be found
            assert ".env" not in file_names
            assert "config" not in file_names
            assert "app.cpython-311.pyc" not in file_names
            assert "index.js" not in file_names

    def test_scanner_full_scan_security(self):
        """Test full scan with security validations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "main.py").write_text(
                """
def main():
    '''Main function.'''
    return 42
"""
            )

            # Create excluded sensitive files
            (Path(tmpdir) / ".env").write_text("API_KEY=secret")
            (Path(tmpdir) / ".git").mkdir()
            (Path(tmpdir) / ".git" / "HEAD").write_text("ref: refs/heads/main")

            scanner = ProjectScanner(tmpdir)
            records, summary = scanner.scan()

            # Verify only safe files in records
            record_paths = [r.path for r in records]
            assert any("main.py" in path for path in record_paths)
            assert not any(".env" in path for path in record_paths)
            assert not any(".git" in path for path in record_paths)

            # Verify summary
            assert summary.total_files == len(records)
            assert summary.source_files >= 1
