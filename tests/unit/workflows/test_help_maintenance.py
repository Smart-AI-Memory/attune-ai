"""Tests for HelpMaintenanceWorkflow in attune.workflows.help_maintenance.

Covers class attributes, utility functions, instantiation, and
the execute() pipeline with subprocess/file I/O fully mocked.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.help_maintenance import (
    HelpMaintenanceWorkflow,
    _hash_file,
    _repo_root,
)

# ------------------------------------------------------------------
# Class attributes
# ------------------------------------------------------------------


class TestClassAttributes:
    """Verify HelpMaintenanceWorkflow has the expected metadata."""

    def test_name_attribute_exists(self):
        """Workflow name is set."""
        assert HelpMaintenanceWorkflow.name == "help-maintenance"

    def test_description_attribute_exists(self):
        """Workflow description is non-empty."""
        assert HelpMaintenanceWorkflow.description
        assert isinstance(HelpMaintenanceWorkflow.description, str)

    def test_stages_defined(self):
        """Five stages are declared."""
        expected = ["detect", "map", "regenerate", "rebuild", "validate"]
        assert HelpMaintenanceWorkflow.stages == expected

    def test_tier_map_covers_all_stages(self):
        """Every stage has a model tier entry."""
        for stage in HelpMaintenanceWorkflow.stages:
            assert stage in HelpMaintenanceWorkflow.tier_map


# ------------------------------------------------------------------
# _hash_file
# ------------------------------------------------------------------


class TestHashFile:
    """Tests for the _hash_file utility."""

    def test_hash_returns_sha256_hex(self, tmp_path):
        """Hash matches independent SHA-256 computation."""
        p = tmp_path / "sample.txt"
        content = b"hello world"
        p.write_bytes(content)

        result = _hash_file(p)

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_hash_changes_with_content(self, tmp_path):
        """Different content produces different hashes."""
        p = tmp_path / "file.txt"

        p.write_bytes(b"version-1")
        h1 = _hash_file(p)

        p.write_bytes(b"version-2")
        h2 = _hash_file(p)

        assert h1 != h2

    def test_hash_empty_file(self, tmp_path):
        """Empty file has a well-known SHA-256 hash."""
        p = tmp_path / "empty.txt"
        p.write_bytes(b"")

        result = _hash_file(p)

        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_hash_file_not_found_raises(self, tmp_path):
        """Raises when the file does not exist."""
        p = tmp_path / "missing.txt"

        with pytest.raises(FileNotFoundError):
            _hash_file(p)


# ------------------------------------------------------------------
# _repo_root
# ------------------------------------------------------------------


class TestRepoRoot:
    """Tests for _repo_root path resolution."""

    def test_returns_path_object(self):
        """Return type is pathlib.Path."""
        result = _repo_root()
        assert isinstance(result, Path)

    def test_directory_exists(self):
        """Resolved directory exists on disk."""
        result = _repo_root()
        assert result.is_dir()

    def test_contains_pyproject(self):
        """Repo root contains pyproject.toml (sanity check)."""
        result = _repo_root()
        assert (result / "pyproject.toml").exists()


# ------------------------------------------------------------------
# Instantiation
# ------------------------------------------------------------------


class TestInstantiation:
    """Verify the workflow can be created."""

    def test_can_instantiate(self):
        """Constructor does not raise."""
        wf = HelpMaintenanceWorkflow()
        assert wf is not None

    def test_instance_has_name(self):
        """Instance exposes the class name."""
        wf = HelpMaintenanceWorkflow()
        assert wf.name == "help-maintenance"


# ------------------------------------------------------------------
# execute — mocked
# ------------------------------------------------------------------


class TestExecuteNoManifest:
    """execute() when source_manifest.json is missing."""

    @pytest.mark.asyncio
    async def test_returns_failure_when_manifest_missing(self, tmp_path):
        """Fail gracefully when the manifest file does not exist."""
        wf = HelpMaintenanceWorkflow()

        with patch(
            "attune.workflows.help_maintenance._repo_root",
            return_value=tmp_path,
        ):
            # Ensure the generated dir exists but manifest does not
            gen_dir = tmp_path / "plugin" / "help" / "generated"
            gen_dir.mkdir(parents=True, exist_ok=True)
            (tmp_path / "scripts").mkdir(exist_ok=True)

            result = await wf.execute()

        assert result.success is False
        assert "error" in result.final_output


class TestExecuteDryRun:
    """execute(dry_run=True) with a valid manifest."""

    @pytest.mark.asyncio
    async def test_dry_run_reports_stale_without_regenerating(self, tmp_path):
        """Dry run detects stale templates but does not call subprocess."""
        wf = HelpMaintenanceWorkflow()

        # Set up directory structure
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Create a source file and manifest
        src_file = tmp_path / "src" / "module.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("# original", encoding="utf-8")

        manifest = {
            "ref-001": {
                "source": "src/module.py",
                "hash": "stale-hash-that-wont-match",
            },
        }
        (gen_dir / "source_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with patch(
            "attune.workflows.help_maintenance._repo_root",
            return_value=tmp_path,
        ):
            result = await wf.execute(dry_run=True)

        assert result.success is True
        assert result.final_output["dry_run"] is True
        assert result.final_output["stale_count"] >= 1

    @pytest.mark.asyncio
    async def test_dry_run_no_stale(self, tmp_path):
        """Dry run with all templates up to date."""
        wf = HelpMaintenanceWorkflow()

        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Source file with matching hash
        src_file = tmp_path / "src" / "module.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        content = b"# up to date"
        src_file.write_bytes(content)
        correct_hash = hashlib.sha256(content).hexdigest()

        manifest = {
            "ref-001": {
                "source": "src/module.py",
                "hash": correct_hash,
            },
        }
        (gen_dir / "source_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with patch(
            "attune.workflows.help_maintenance._repo_root",
            return_value=tmp_path,
        ):
            result = await wf.execute(dry_run=True)

        assert result.success is True
        assert result.final_output["stale_count"] == 0
        assert result.final_output["validated"] is True


class TestExecuteRegeneration:
    """execute() triggers subprocess when stale templates exist."""

    @pytest.mark.asyncio
    async def test_calls_generator_script(self, tmp_path):
        """Subprocess is invoked for stale template types."""
        wf = HelpMaintenanceWorkflow()

        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Create the generator script file so it passes exists()
        (scripts_dir / "generate_reference_templates.py").write_text(
            "# stub",
            encoding="utf-8",
        )
        # Also create cross-links and generate_all stubs
        (scripts_dir / "build_cross_links.py").write_text(
            "# stub",
            encoding="utf-8",
        )
        (scripts_dir / "generate_all.py").write_text(
            "# stub",
            encoding="utf-8",
        )

        # Source file with stale hash
        src_file = tmp_path / "src" / "module.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("# changed", encoding="utf-8")

        manifest = {
            "ref-001": {
                "source": "src/module.py",
                "hash": "old-hash",
            },
        }
        (gen_dir / "source_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        mock_run = MagicMock(return_value=MagicMock(returncode=0))

        with (
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
            patch(
                "attune.workflows.help_maintenance.subprocess.run",
                mock_run,
            ),
        ):
            result = await wf.execute(dry_run=False)

        # At least one subprocess call for the generator
        assert mock_run.call_count >= 1
        assert "regenerated" in result.final_output


class TestExecuteMissingSource:
    """execute() when the source file referenced in the manifest is gone."""

    @pytest.mark.asyncio
    async def test_missing_source_detected_as_stale(self, tmp_path):
        """A manifest entry whose source file is missing is flagged stale."""
        wf = HelpMaintenanceWorkflow()

        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        (tmp_path / "scripts").mkdir(exist_ok=True)

        manifest = {
            "ref-002": {
                "source": "src/gone.py",
                "hash": "any",
            },
        }
        (gen_dir / "source_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with patch(
            "attune.workflows.help_maintenance._repo_root",
            return_value=tmp_path,
        ):
            result = await wf.execute(dry_run=True)

        assert result.final_output["stale_count"] == 1


# ------------------------------------------------------------------
# _build_result
# ------------------------------------------------------------------


class TestBuildResult:
    """Verify _build_result produces valid WorkflowResult objects."""

    def test_build_result_fields(self):
        """WorkflowResult has required fields populated."""
        wf = HelpMaintenanceWorkflow()
        started = datetime.now()

        result = wf._build_result(
            started_at=started,
            success=True,
            output={"msg": "ok"},
        )

        assert result.success is True
        assert result.final_output == {"msg": "ok"}
        assert result.total_duration_ms >= 0
        assert result.started_at == started
        assert result.completed_at >= started


# ------------------------------------------------------------------
# _prioritize_stale
# ------------------------------------------------------------------


class TestPrioritizeStale:
    """Tests for feedback-based stale ordering."""

    def test_returns_same_items_on_import_failure(self):
        """Falls back to original order when help engine is unavailable."""
        wf = HelpMaintenanceWorkflow()
        items = [
            {"id": "ref-001", "reason": "changed", "source": "a.py"},
            {"id": "tip-002", "reason": "missing", "source": "b.py"},
        ]

        with patch(
            "attune.help.engine.get_template_confidence",
            side_effect=ImportError("no engine"),
        ):
            result = wf._prioritize_stale(items)

        assert len(result) == len(items)

    def test_returns_list_unchanged_length(self):
        """Output length equals input length regardless of sorting."""
        wf = HelpMaintenanceWorkflow()
        items = [
            {"id": "ref-001", "reason": "changed", "source": "a.py"},
            {"id": "ref-002", "reason": "changed", "source": "b.py"},
            {"id": "ref-003", "reason": "changed", "source": "c.py"},
        ]

        # Mock both functions needed by _prioritize_stale
        with (
            patch(
                "attune.help.engine.get_template_confidence",
                return_value=0.5,
            ),
            patch(
                "attune.help.engine.get_usage_weights",
                return_value={},
            ),
        ):
            result = wf._prioritize_stale(items)

        assert len(result) == 3


# ------------------------------------------------------------------
# Coverage-gap tests for help_maintenance.py
# ------------------------------------------------------------------


class TestExecuteEdgeCases:
    """Cover branches in execute()."""

    @pytest.mark.asyncio
    async def test_manifest_entry_with_empty_source_skipped(self, tmp_path):
        """Line 138: entry with no 'source' is skipped."""
        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        (tmp_path / "scripts").mkdir(exist_ok=True)

        manifest = {"ref-empty": {"source": "", "hash": "x"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        with patch(
            "attune.workflows.help_maintenance._repo_root",
            return_value=tmp_path,
        ):
            result = await wf.execute(dry_run=True)
        assert result.final_output["stale_count"] == 0

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, tmp_path):
        """Lines 145-150: path traversal in manifest source is skipped."""
        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        (tmp_path / "scripts").mkdir(exist_ok=True)

        manifest = {"ref-bad": {"source": "../../etc/passwd", "hash": "x"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        with patch(
            "attune.workflows.help_maintenance._repo_root",
            return_value=tmp_path,
        ):
            result = await wf.execute(dry_run=True)
        # Skipped because of path traversal — counts as not-stale
        assert result.final_output["stale_count"] == 0

    @pytest.mark.asyncio
    async def test_unknown_prefix_skipped_in_types_to_regen(self, tmp_path):
        """Line 193->190: stale id with unknown prefix → no type to regen."""
        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {
            "unknownprefix-001": {"source": "src/x.py", "hash": "stale"},
        }
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        with (
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
            patch(
                "attune.workflows.help_maintenance.subprocess.run",
                mock_run,
            ),
        ):
            result = await wf.execute(dry_run=False)
        # types_to_regen empty → regenerated should be empty
        assert result.final_output["regenerated"] == []

    @pytest.mark.asyncio
    async def test_type_without_generator_skipped(self, tmp_path):
        """Line 210: type_dir not in _TYPE_TO_GENERATOR → continue."""
        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {"ref-001": {"source": "src/x.py", "hash": "stale"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        # Map references → "references" prefix, but remove "references" from generators
        with (
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
            patch.dict(
                "attune.workflows.help_maintenance._TYPE_TO_GENERATOR",
                clear=True,
            ),
        ):
            result = await wf.execute(dry_run=False)
        # Type 'references' has no generator → regenerated empty, no failed
        assert result.final_output["regenerated"] == []

    @pytest.mark.asyncio
    async def test_script_not_found_added_to_failed(self, tmp_path):
        """Lines 212-214: script_path doesn't exist → failed entry."""
        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        # Don't create the generator script — it will be missing
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {
            "ref-001": {"source": "src/x.py", "hash": "stale"},
        }
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        with patch(
            "attune.workflows.help_maintenance._repo_root",
            return_value=tmp_path,
        ):
            result = await wf.execute(dry_run=False)
        assert any(
            f.get("reason") == "script not found" for f in result.final_output.get("failed", [])
        )

    @pytest.mark.asyncio
    async def test_generator_timeout(self, tmp_path):
        """Lines 225-227: TimeoutExpired on generator → 'timeout' failure."""
        import subprocess as sp_mod

        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        (scripts_dir / "generate_reference_templates.py").write_text("stub", encoding="utf-8")
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {"ref-001": {"source": "src/x.py", "hash": "stale"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        def fake_run(*args, **kwargs):
            raise sp_mod.TimeoutExpired(cmd="x", timeout=60)

        with (
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
            patch(
                "attune.workflows.help_maintenance.subprocess.run",
                side_effect=fake_run,
            ),
        ):
            result = await wf.execute(dry_run=False)
        assert any(f.get("reason") == "timeout" for f in result.final_output.get("failed", []))

    @pytest.mark.asyncio
    async def test_generator_called_process_error(self, tmp_path):
        """Lines 228-231: CalledProcessError → 'exit N' failure."""
        import subprocess as sp_mod

        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        (scripts_dir / "generate_reference_templates.py").write_text("stub", encoding="utf-8")
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {"ref-001": {"source": "src/x.py", "hash": "stale"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        call_idx = [0]

        def fake_run(*args, **kwargs):
            call_idx[0] += 1
            if call_idx[0] == 1:
                raise sp_mod.CalledProcessError(returncode=1, cmd="x", stderr=b"boom")
            return MagicMock(returncode=0)

        with (
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
            patch(
                "attune.workflows.help_maintenance.subprocess.run",
                side_effect=fake_run,
            ),
        ):
            result = await wf.execute(dry_run=False)
        failures = result.final_output.get("failed", [])
        assert any("exit 1" in f.get("reason", "") for f in failures)

    @pytest.mark.asyncio
    async def test_cross_link_timeout_swallowed(self, tmp_path):
        """Lines 244-245: cross-link TimeoutExpired → swallowed."""
        import subprocess as sp_mod

        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        (scripts_dir / "generate_reference_templates.py").write_text("stub", encoding="utf-8")
        (scripts_dir / "build_cross_links.py").write_text("stub", encoding="utf-8")
        (scripts_dir / "generate_all.py").write_text("stub", encoding="utf-8")
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {"ref-001": {"source": "src/x.py", "hash": "stale"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        # First call (generator) succeeds; second call (cross-link) times out
        call_idx = [0]

        def fake_run(*args, **kwargs):
            call_idx[0] += 1
            if call_idx[0] == 2:
                raise sp_mod.TimeoutExpired(cmd="x", timeout=30)
            return MagicMock(returncode=0)

        with (
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
            patch(
                "attune.workflows.help_maintenance.subprocess.run",
                side_effect=fake_run,
            ),
        ):
            result = await wf.execute(dry_run=False)
        # Should not raise; result has regenerated
        assert "regenerated" in result.final_output

    @pytest.mark.asyncio
    async def test_manifest_update_oserror_swallowed(self, tmp_path):
        """Lines 262-263: manifest-update OSError swallowed."""
        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        (scripts_dir / "generate_reference_templates.py").write_text("stub", encoding="utf-8")
        # No build_cross_links.py to cover line 235->248 (skips cross-link)
        (scripts_dir / "generate_all.py").write_text("stub", encoding="utf-8")
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {"ref-001": {"source": "src/x.py", "hash": "stale"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        call_idx = [0]

        def fake_run(*args, **kwargs):
            call_idx[0] += 1
            # First (generator) succeeds. Second (manifest update) raises OSError.
            # Third (validate) raises OSError too.
            if call_idx[0] >= 2:
                raise OSError("disk failure")
            return MagicMock(returncode=0)

        with (
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
            patch(
                "attune.workflows.help_maintenance.subprocess.run",
                side_effect=fake_run,
            ),
        ):
            result = await wf.execute(dry_run=False)
        # validate failed → committed False, but still a result
        assert result.final_output["validated"] is False

    @pytest.mark.asyncio
    async def test_validation_passes_triggers_commit_with_failure(self, tmp_path):
        """Lines 287->314 + 311-312: commit step where git fails (CalledProcessError)."""
        import subprocess as sp_mod

        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        (scripts_dir / "generate_reference_templates.py").write_text("stub", encoding="utf-8")
        (scripts_dir / "generate_all.py").write_text("stub", encoding="utf-8")
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {"ref-001": {"source": "src/x.py", "hash": "stale"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        call_idx = [0]

        def fake_run(*args, **kwargs):
            call_idx[0] += 1
            # 1: generator success; 2: manifest update success; 3: validate success;
            # 4: git add success; 5: git commit fails
            if call_idx[0] == 5:
                raise sp_mod.CalledProcessError(returncode=1, cmd="git commit")
            return MagicMock(returncode=0)

        with (
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
            patch(
                "attune.workflows.help_maintenance.subprocess.run",
                side_effect=fake_run,
            ),
        ):
            result = await wf.execute(dry_run=False)
        # Commit failed → committed False, validated True
        assert result.final_output["validated"] is True
        assert result.final_output["committed"] is False


class TestExecuteBatch:
    """Cover _execute_batch (lines 348-424)."""

    @pytest.mark.asyncio
    async def test_batch_mode_with_stub_workflow(self, tmp_path):
        """Lines 348-422: batch=True path runs BatchProcessingWorkflow."""
        import sys
        from types import SimpleNamespace
        from unittest.mock import AsyncMock as AM

        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {"ref-001": {"source": "src/x.py", "hash": "stale"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        fake_workflow = MagicMock()
        fake_workflow.execute_batch = AM(
            return_value=[SimpleNamespace(task_id="regen-references", success=True, error=None)]
        )

        class FakeRequest:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        fake_module = SimpleNamespace(
            BatchProcessingWorkflow=lambda: fake_workflow,
            BatchRequest=FakeRequest,
        )

        with (
            patch.dict(sys.modules, {"attune.workflows.batch_processing": fake_module}),
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
        ):
            result = await wf.execute(dry_run=False, batch=True)

        assert result.final_output["batch"] is True
        assert result.final_output["submitted"] == 1
        assert result.final_output["results"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_batch_mode_no_requests(self, tmp_path):
        """Lines 386-395: empty requests → 'No generators needed'."""
        import sys
        from types import SimpleNamespace

        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        # Use a prefix that maps to a type without a generator script
        # (we'll force types_to_regen to be empty by removing the type from generator map)
        manifest = {"ref-001": {"source": "src/x.py", "hash": "stale"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        # Patch _TYPE_TO_GENERATOR so the type has no script
        fake_module = SimpleNamespace(
            BatchProcessingWorkflow=MagicMock(),
            BatchRequest=lambda **kw: kw,
        )

        with (
            patch.dict(sys.modules, {"attune.workflows.batch_processing": fake_module}),
            patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ),
            patch.dict(
                "attune.workflows.help_maintenance._TYPE_TO_GENERATOR",
                clear=True,
            ),
        ):
            result = await wf.execute(dry_run=False, batch=True)
        assert result.final_output["batch"] is True
        assert "No generators needed" in result.final_output.get("message", "")

    @pytest.mark.asyncio
    async def test_batch_mode_import_error(self, tmp_path):
        """Lines 423-432: ImportError → returns failure with 'Batch API not available'."""
        import sys

        wf = HelpMaintenanceWorkflow()
        gen_dir = tmp_path / "plugin" / "help" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        src_file = tmp_path / "src" / "x.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("changed", encoding="utf-8")

        manifest = {"ref-001": {"source": "src/x.py", "hash": "stale"}}
        (gen_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        # Make import fail by setting the module to None (raises ImportError on access)
        # Actually we need to delete it from sys.modules and patch finder
        original = sys.modules.pop("attune.workflows.batch_processing", None)
        try:
            with patch(
                "attune.workflows.help_maintenance._repo_root",
                return_value=tmp_path,
            ):
                # patch builtins.__import__ to raise ImportError for the target
                import builtins as _b

                real_import = _b.__import__

                def fake_import(name, *args, **kwargs):
                    if "batch_processing" in name:
                        raise ImportError("not available")
                    return real_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=fake_import):
                    result = await wf.execute(dry_run=False, batch=True)
        finally:
            if original is not None:
                sys.modules["attune.workflows.batch_processing"] = original

        assert result.success is False
        assert "Batch API not available" in result.final_output.get("error", "")
