"""MCP tool handlers for attune-author.

Each handler validates inputs (especially paths), calls the
relevant attune-author library function, and returns a uniform
{"success": bool, ...} dict.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from attune_author.mcp.path_validation import validate_file_path

logger = logging.getLogger(__name__)


class AttuneAuthorHandlers:
    """Async handlers for the 6 attune-author MCP tools.

    Holds workspace_root for path containment so user input
    cannot escape the project directory.
    """

    def __init__(self, workspace_root: str) -> None:
        """Initialize with a pinned workspace root.

        Args:
            workspace_root: Absolute path used to constrain
                all file operations.
        """
        self._workspace_root = workspace_root

    async def author_init(self, args: dict[str, Any]) -> dict[str, Any]:
        """Bootstrap a .help/ directory with discovered features."""
        from attune_author.bootstrap import (
            proposals_to_manifest,
            scan_project,
        )
        from attune_author.manifest import save_manifest

        try:
            project_root = validate_file_path(
                args.get("project_root", "."),
                allowed_dir=self._workspace_root,
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        help_dir = project_root / ".help"
        if (help_dir / "features.yaml").exists():
            return {
                "success": True,
                "already_initialized": True,
                "manifest_path": str(help_dir / "features.yaml"),
                "message": f"Already initialized at {help_dir / 'features.yaml'}",
            }

        proposals = scan_project(project_root)
        if not proposals:
            return {
                "success": True,
                "discovered": 0,
                "message": "No features discovered.",
            }

        manifest = proposals_to_manifest(proposals)
        manifest_path = save_manifest(manifest, help_dir)

        return {
            "success": True,
            "discovered": len(proposals),
            "manifest_path": str(manifest_path),
            "features": [
                {
                    "name": p.name,
                    "description": p.description,
                    "confidence": p.confidence,
                    "files": p.files,
                }
                for p in proposals
            ],
        }

    async def author_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Report stale features as a markdown table."""
        from attune_author.maintenance import format_status_report
        from attune_author.manifest import load_manifest
        from attune_author.staleness import check_staleness

        try:
            help_dir = validate_file_path(
                args.get("help_dir", ".help"),
                allowed_dir=self._workspace_root,
            )
            project_root = validate_file_path(
                args.get("project_root", "."),
                allowed_dir=self._workspace_root,
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            manifest = load_manifest(help_dir)
        except (FileNotFoundError, ValueError) as e:
            return {"success": False, "error": f"Cannot load manifest: {e}"}

        report = check_staleness(manifest, help_dir, project_root)

        return {
            "success": True,
            "stale_count": report.stale_count,
            "current_count": report.current_count,
            "stale_features": report.stale_features,
            "report": format_status_report(report, help_dir),
        }

    async def author_generate(self, args: dict[str, Any]) -> dict[str, Any]:
        """Generate templates for one feature."""
        from attune_author.generator import generate_feature_templates
        from attune_author.manifest import load_manifest

        feature_name = args.get("feature")
        if not feature_name:
            return {"success": False, "error": "feature name is required"}

        try:
            help_dir = validate_file_path(
                args.get("help_dir", ".help"),
                allowed_dir=self._workspace_root,
            )
            project_root = validate_file_path(
                args.get("project_root", "."),
                allowed_dir=self._workspace_root,
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            manifest = load_manifest(help_dir)
        except (FileNotFoundError, ValueError) as e:
            return {"success": False, "error": f"Cannot load manifest: {e}"}

        feature = manifest.features.get(feature_name)
        if not feature:
            return {
                "success": False,
                "error": (
                    f"Feature '{feature_name}' not in manifest. "
                    f"Available: {sorted(manifest.features)}"
                ),
            }

        try:
            result = generate_feature_templates(
                feature=feature,
                help_dir=help_dir,
                project_root=project_root,
                overwrite=bool(args.get("overwrite", False)),
            )
        except (ValueError, OSError) as e:
            return {"success": False, "error": str(e)}

        return {
            "success": True,
            "feature": result.feature,
            "generated": [{"depth": t.depth, "path": str(t.path)} for t in result.templates],
            "source_hash": result.source_hash,
            "matched_files": result.matched_files,
        }

    async def author_maintain(self, args: dict[str, Any]) -> dict[str, Any]:
        """Regenerate all stale features."""
        from attune_author.maintenance import run_maintenance

        try:
            help_dir = validate_file_path(
                args.get("help_dir", ".help"),
                allowed_dir=self._workspace_root,
            )
            project_root = validate_file_path(
                args.get("project_root", "."),
                allowed_dir=self._workspace_root,
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        features = args.get("features")
        dry_run = bool(args.get("dry_run", False))

        try:
            result = run_maintenance(
                help_dir=help_dir,
                project_root=project_root,
                features=features,
                dry_run=dry_run,
            )
        except (FileNotFoundError, ValueError) as e:
            return {"success": False, "error": str(e)}

        return {
            "success": True,
            "stale_count": result.stale_count,
            "regenerated_count": result.regenerated_count,
            "regenerated": [r.feature for r in result.regenerated],
            "failed": result.failed,
            "dry_run": dry_run,
        }

    async def author_docs(self, args: dict[str, Any]) -> dict[str, Any]:
        """Generate documentation via the 3-stage pipeline."""
        try:
            from attune_author.doc_gen import DocGenConfig, generate_docs
        except ImportError:
            return {
                "success": False,
                "error": (
                    "Doc generation requires the [ai] extra: " "pip install 'attune-author[ai]'"
                ),
            }

        target = args.get("target")
        if not target:
            return {"success": False, "error": "target is required"}

        # If target is a file path, validate it
        target_path: str = target
        if Path(target).exists():
            try:
                validated = validate_file_path(target, allowed_dir=self._workspace_root)
                target_path = str(validated)
            except ValueError as e:
                return {"success": False, "error": str(e)}

        output_path: str | None = None
        if args.get("output_path"):
            try:
                # Use parent dir for validation since output may not exist yet
                out = Path(args["output_path"])
                out.parent.mkdir(parents=True, exist_ok=True)
                validated_parent = validate_file_path(
                    str(out.parent), allowed_dir=self._workspace_root
                )
                output_path = str(validated_parent / out.name)
            except ValueError as e:
                return {"success": False, "error": str(e)}

        config = DocGenConfig(
            doc_type=args.get("doc_type", "api-reference"),
            audience=args.get("audience", "developers"),
        )

        try:
            result = generate_docs(
                target=target_path,
                config=config,
                output_path=output_path,
            )
        except (RuntimeError, FileNotFoundError) as e:
            return {"success": False, "error": str(e)}

        return {
            "success": True,
            "stages_completed": result.stages_completed,
            "source_path": result.source_path,
            "output_path": output_path,
            "content": result.content if not output_path else None,
            "content_length": len(result.content),
        }

    async def author_lookup(self, args: dict[str, Any]) -> dict[str, Any]:
        """Look up help for a topic by name or tag."""
        from attune_author.manifest import load_manifest, resolve_topic

        query = args.get("query")
        if not query:
            return {"success": False, "error": "query is required"}

        depth = args.get("depth", "concept")
        if depth not in ("concept", "task", "reference"):
            return {
                "success": False,
                "error": f"depth must be concept|task|reference, got {depth}",
            }

        try:
            help_dir = validate_file_path(
                args.get("help_dir", ".help"),
                allowed_dir=self._workspace_root,
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            manifest = load_manifest(help_dir)
        except (FileNotFoundError, ValueError) as e:
            return {"success": False, "error": f"Cannot load manifest: {e}"}

        feature_name = resolve_topic(query, manifest)
        if not feature_name:
            return {
                "success": False,
                "error": f"No feature matches query: {query}",
                "available": sorted(manifest.features),
            }

        template_path = help_dir / "templates" / feature_name / f"{depth}.md"
        if not template_path.exists():
            return {
                "success": False,
                "error": (
                    f"No {depth} template for '{feature_name}'. " f"Run author_generate first."
                ),
                "feature": feature_name,
            }

        try:
            content = template_path.read_text(encoding="utf-8")
        except OSError as e:
            return {"success": False, "error": f"Cannot read template: {e}"}

        return {
            "success": True,
            "feature": feature_name,
            "depth": depth,
            "path": str(template_path),
            "content": content,
        }
