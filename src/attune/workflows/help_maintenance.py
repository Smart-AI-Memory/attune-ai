"""Help knowledge base maintenance workflow.

Detects stale help templates, regenerates them, and
validates the result. Keeps the knowledge base in sync
with source code changes without manual intervention.

Usage::

    workflow = HelpMaintenanceWorkflow()
    result = await workflow.execute(dry_run=False)
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.workflows.base import BaseWorkflow, ModelTier
from attune.workflows.data_classes import CostReport, WorkflowResult

logger = logging.getLogger(__name__)

# Generator scripts by template type directory.
_TYPE_TO_GENERATOR: dict[str, str] = {
    "errors": "generate_error_templates.py",
    "warnings": "generate_warning_templates.py",
    "tips": "generate_tip_templates.py",
    "references": "generate_reference_templates.py",
    "tasks": "generate_task_templates.py",
    "faqs": "generate_faq_templates.py",
    "notes": "generate_note_templates.py",
    "quickstarts": "generate_quickstart_templates.py",
    "concepts": "generate_concept_templates.py",
    "troubleshooting": "generate_troubleshooting_templates.py",
    "comparisons": "generate_comparison_templates.py",
}

# Reverse lookup: template ID prefix -> type dir name.
_PREFIX_TO_TYPE: dict[str, str] = {
    "err": "errors",
    "war": "warnings",
    "tip": "tips",
    "ref": "references",
    "tas": "tasks",
    "faq": "faqs",
    "not": "notes",
    "qui": "quickstarts",
    "con": "concepts",
    "tro": "troubleshooting",
    "com": "comparisons",
}


def _hash_file(path: Path) -> str:
    """SHA-256 hash of a file's contents.

    Args:
        path: File to hash.

    Returns:
        Hex digest string.
    """
    return hashlib.sha256(
        path.read_bytes(),
    ).hexdigest()


def _repo_root() -> Path:
    """Get repository root (3 levels up from this file).

    File lives at src/attune/workflows/help_maintenance.py,
    so parents[3] = repo root.
    """
    return Path(__file__).resolve().parents[3]


class HelpMaintenanceWorkflow(BaseWorkflow):
    """Maintain the help knowledge base automatically.

    Five phases:
    1. DETECT — find changed source files
    2. MAP — cross-reference against source manifest
    3. REGENERATE — run generators for stale types
    4. REBUILD — rebuild cross-links
    5. VALIDATE — verify sync with --check

    Usage::

        workflow = HelpMaintenanceWorkflow()
        result = await workflow.execute(dry_run=True)
    """

    name = "help-maintenance"
    description = "Detect and regenerate stale help templates"
    stages = ["detect", "map", "regenerate", "rebuild", "validate"]
    tier_map = {
        "detect": ModelTier.CHEAP,
        "map": ModelTier.CHEAP,
        "regenerate": ModelTier.CHEAP,
        "rebuild": ModelTier.CHEAP,
        "validate": ModelTier.CHEAP,
    }

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the help maintenance pipeline.

        Args:
            **kwargs: Keyword arguments.
                dry_run (bool): If True, only report stale
                    templates without regenerating.
                batch (bool): If True, submit regeneration to
                    Anthropic Batch API (50% cost savings).
                    Returns immediately with batch info.

        Returns:
            WorkflowResult with regenerated list, validated
            bool, and coverage_gaps.
        """
        dry_run: bool = kwargs.get("dry_run", False)
        batch: bool = kwargs.get("batch", False)
        started_at = datetime.now()
        repo = _repo_root()
        generated_dir = repo / "plugin" / "help" / "generated"
        scripts_dir = repo / "scripts"
        manifest_path = generated_dir / "source_manifest.json"

        # Phase 1: DETECT — load manifest
        if not manifest_path.exists():
            return self._build_result(
                started_at=started_at,
                success=False,
                output={
                    "error": "No source_manifest.json found. "
                    "Run: python scripts/generate_all.py",
                },
            )

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8"),
        )

        # Phase 2: MAP — find stale templates
        stale: list[dict[str, str]] = []
        for template_id, entry in manifest.items():
            source_rel = entry.get("source", "")
            if not source_rel:
                continue

            source_path = repo / source_rel

            # Path containment check (CWE-22)
            try:
                source_path.resolve().relative_to(repo.resolve())
            except ValueError:
                logger.warning(
                    "Path traversal blocked in manifest: %s",
                    source_rel,
                )
                continue

            if not source_path.exists():
                stale.append(
                    {
                        "id": template_id,
                        "reason": "source missing",
                        "source": source_rel,
                    }
                )
                continue

            current_hash = _hash_file(source_path)
            if current_hash != entry["hash"]:
                stale.append(
                    {
                        "id": template_id,
                        "reason": "source changed",
                        "source": source_rel,
                    }
                )

        # Sort by feedback/usage priority
        stale = self._prioritize_stale(stale)

        if dry_run or not stale:
            return self._build_result(
                started_at=started_at,
                success=True,
                output={
                    "stale_count": len(stale),
                    "stale": stale[:20],
                    "dry_run": dry_run,
                    "regenerated": [],
                    "validated": len(stale) == 0,
                },
            )

        # Determine affected types
        types_to_regen: set[str] = set()
        for item in stale:
            prefix = item["id"].split("-", 1)[0]
            type_dir = _PREFIX_TO_TYPE.get(prefix)
            if type_dir:
                types_to_regen.add(type_dir)

        # Phase 3 (batch): Submit to Batch API at 50% cost
        if batch:
            return await self._execute_batch(
                started_at,
                stale,
                types_to_regen,
                scripts_dir,
            )

        regenerated: list[str] = []
        failed: list[dict[str, str]] = []
        for type_dir in sorted(types_to_regen):
            script = _TYPE_TO_GENERATOR.get(type_dir)
            if not script:
                continue
            script_path = scripts_dir / script
            if not script_path.exists():
                failed.append({"type": type_dir, "reason": "script not found"})
                continue

            try:
                subprocess.run(
                    ["uv", "run", "python", str(script_path)],
                    cwd=str(scripts_dir),
                    capture_output=True,
                    timeout=60,
                    check=True,
                )
                regenerated.append(type_dir)
            except subprocess.TimeoutExpired:
                failed.append({"type": type_dir, "reason": "timeout"})
                logger.warning("Generator timed out: %s", script)
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode()[:200] if e.stderr else ""
                failed.append({"type": type_dir, "reason": f"exit {e.returncode}: {stderr}"})
                logger.warning("Generator failed: %s (exit %d)", script, e.returncode)

        # Phase 4: REBUILD — cross-links
        cross_link_script = scripts_dir / "build_cross_links.py"
        if cross_link_script.exists():
            try:
                subprocess.run(
                    ["uv", "run", "python", str(cross_link_script)],
                    cwd=str(scripts_dir),
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                logger.warning("Cross-link rebuild timed out")

        # Update manifest after regeneration
        try:
            subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    str(scripts_dir / "generate_all.py"),
                    "--manifest-only",
                ],
                cwd=str(scripts_dir),
                capture_output=True,
                timeout=30,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Phase 5: VALIDATE — check sync
        validated = False
        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    str(scripts_dir / "generate_all.py"),
                    "--check",
                ],
                cwd=str(scripts_dir),
                capture_output=True,
                timeout=120,
                check=False,
            )
            validated = result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Phase 6: COMMIT — auto-commit if validation passed
        committed = False
        if validated and regenerated:
            try:
                subprocess.run(
                    ["git", "add", str(generated_dir)],
                    cwd=str(repo),
                    capture_output=True,
                    timeout=10,
                    check=True,
                )
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"chore: regenerate {len(regenerated)} help template type(s)\n\n"
                        f"Types: {', '.join(regenerated)}\n"
                        f"Stale: {len(stale)} templates detected",
                    ],
                    cwd=str(repo),
                    capture_output=True,
                    timeout=30,
                    check=True,
                )
                committed = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                logger.debug("Auto-commit skipped (pre-commit or no changes)")

        return self._build_result(
            started_at=started_at,
            success=len(failed) == 0,
            output={
                "stale_count": len(stale),
                "regenerated": regenerated,
                "failed": failed,
                "validated": validated,
                "committed": committed,
                "dry_run": False,
            },
        )

    async def _execute_batch(
        self,
        started_at: datetime,
        stale: list[dict[str, str]],
        types_to_regen: set[str],
        scripts_dir: Path,
    ) -> WorkflowResult:
        """Submit regeneration to the Anthropic Batch API.

        Returns immediately with batch metadata. Results
        arrive asynchronously (up to 24 hours, 50% cost).

        Args:
            started_at: Execution start time.
            stale: List of stale template dicts.
            types_to_regen: Set of type directory names.
            scripts_dir: Path to scripts/ directory.

        Returns:
            WorkflowResult with batch submission info.
        """
        try:
            from attune.workflows.batch_processing import (
                BatchProcessingWorkflow,
                BatchRequest,
            )

            requests = []
            for type_dir in sorted(types_to_regen):
                script = _TYPE_TO_GENERATOR.get(type_dir)
                if not script:
                    continue
                stale_ids = [
                    s["id"]
                    for s in stale
                    if s["id"].split("-", 1)[0]
                    == next(
                        (k for k, v in _PREFIX_TO_TYPE.items() if v == type_dir),
                        "",
                    )
                ]
                requests.append(
                    BatchRequest(
                        task_id=f"regen-{type_dir}",
                        task_type="generate_docs",
                        input_data={
                            "type_dir": type_dir,
                            "script": script,
                            "stale_count": len(stale_ids),
                            "instruction": (
                                f"Regenerate {type_dir} help templates. "
                                f"{len(stale_ids)} templates are stale. "
                                f"Run: python scripts/{script}"
                            ),
                        },
                        model_tier="cheap",
                    ),
                )

            if not requests:
                return self._build_result(
                    started_at=started_at,
                    success=True,
                    output={
                        "stale_count": len(stale),
                        "batch": True,
                        "message": "No generators needed",
                    },
                )

            workflow = BatchProcessingWorkflow()
            results = await workflow.execute_batch(
                requests,
                poll_interval=60,
                timeout=3600,
            )

            return self._build_result(
                started_at=started_at,
                success=all(r.success for r in results),
                output={
                    "stale_count": len(stale),
                    "batch": True,
                    "submitted": len(requests),
                    "types": sorted(types_to_regen),
                    "results": [
                        {
                            "task_id": r.task_id,
                            "success": r.success,
                            "error": r.error,
                        }
                        for r in results
                    ],
                },
            )

        except ImportError:
            return self._build_result(
                started_at=started_at,
                success=False,
                output={
                    "error": (
                        "Batch API not available. " "Set ANTHROPIC_API_KEY or use batch=false."
                    ),
                },
            )

    def _prioritize_stale(
        self,
        stale: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Sort stale templates by feedback and usage priority.

        Bad-rated templates first, then high-usage, then by age.

        Args:
            stale: List of stale template dicts.

        Returns:
            Sorted list (highest priority first).
        """
        try:
            from attune.help.engine import (
                get_template_confidence,
                get_usage_weights,
            )

            weights = get_usage_weights()

            def sort_key(item: dict[str, str]) -> tuple[float, float]:
                tid = item["id"]
                confidence = get_template_confidence(tid)
                usage = weights.get(tid, 0.0)
                # Low confidence = high priority (sort ascending)
                # High usage = high priority (sort descending)
                return (confidence, -usage)

            return sorted(stale, key=sort_key)
        except Exception:  # noqa: BLE001
            # INTENTIONAL: feedback/usage is optional
            return stale

    def _build_result(
        self,
        started_at: datetime,
        success: bool,
        output: dict[str, Any],
    ) -> WorkflowResult:
        """Build a WorkflowResult.

        Args:
            started_at: When execution began.
            success: Whether the workflow succeeded.
            output: The final_output dict.

        Returns:
            WorkflowResult instance.
        """
        completed_at = datetime.now()
        duration_ms = int(
            (completed_at - started_at).total_seconds() * 1000,
        )
        return WorkflowResult(
            success=success,
            stages=self.stages,
            final_output=output,
            cost_report=CostReport(
                total_cost=0.0,
                baseline_cost=0.0,
                savings=0.0,
                savings_percent=0.0,
                by_stage={},
            ),
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=duration_ms,
        )
