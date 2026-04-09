"""MCP tool handlers for attune-help.

Each handler validates inputs (paths especially), calls the
HelpEngine library, and returns a uniform
{"success": bool, ...} dict. Handlers instantiate HelpEngine
lazily so users without a project template directory can
still use the bundled templates.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from attune_help.engine import HelpEngine
from attune_help.mcp.path_validation import validate_file_path
from attune_help.storage import LocalFileStorage

logger = logging.getLogger(__name__)

# Must match the `renderer` enum in tool_schemas.get_tools().
# Kept as a module-level frozenset so the defensive check in
# lookup_topic() is O(1) and trivially greppable. If a new renderer
# is added, update both places.
_VALID_RENDERERS = frozenset({"plain", "claude_code", "cli", "marketplace"})


class AttuneHelpHandlers:
    """Async handlers for the 6 attune-help MCP tools.

    Holds workspace_root for path containment so user input
    cannot escape the project directory when a user-provided
    template_dir or file_path is accepted.
    """

    def __init__(self, workspace_root: str) -> None:
        """Initialize with a pinned workspace root.

        Args:
            workspace_root: Absolute path used to constrain
                all file operations.
        """
        self._workspace_root = workspace_root

    def _engine(
        self,
        template_dir: str | None,
        user_id: str = "mcp-session",
        renderer: str = "plain",
    ) -> HelpEngine:
        """Build a HelpEngine for one request.

        Args:
            template_dir: Optional user override. Validated
                against the workspace root when present.
            user_id: Session identifier.
            renderer: Output renderer name.

        Returns:
            Configured HelpEngine instance.
        """
        override: Path | None = None
        if template_dir:
            # Validate but allow the engine to fall back to
            # bundled templates if the override does not exist.
            override = validate_file_path(
                template_dir,
                allowed_dir=self._workspace_root,
            )
        return HelpEngine(
            template_dir=override,
            storage=LocalFileStorage(),
            renderer=renderer,
            user_id=user_id,
        )

    async def lookup_topic(self, args: dict[str, Any]) -> dict[str, Any]:
        """Progressive depth lookup for a topic."""
        topic = args.get("topic")
        if not topic or not isinstance(topic, str):
            return {
                "success": False,
                "error": "topic is required and must be a string",
            }

        # Defensive enum check — the schema declares this enum but not
        # every MCP client enforces schema enums. Rejecting bad input
        # here turns a cryptic library warning into a clean error.
        renderer = args.get("renderer", "plain")
        if renderer not in _VALID_RENDERERS:
            return {
                "success": False,
                "error": (
                    f"renderer must be one of " f"{sorted(_VALID_RENDERERS)}, got {renderer!r}"
                ),
            }

        try:
            engine = self._engine(
                template_dir=args.get("template_dir"),
                user_id=args.get("user_id", "mcp-session"),
                renderer=renderer,
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            raw = engine.lookup_raw(topic)
        except (OSError, ValueError) as e:
            logger.warning("lookup_raw failed for %s: %s", topic, e)
            return {
                "success": False,
                "error": f"lookup failed: {e}",
            }

        if raw is None:
            return {
                "success": False,
                "error": f"Topic not found: {topic}",
            }

        # Render from the same PopulatedTemplate we already have.
        # Calling engine.lookup() would advance the session a second
        # time and return the NEXT depth level (often None). See
        # test_lookup_topic_does_not_double_advance for the regression
        # test that locks this behavior in.
        rendered = engine.render(raw)
        metadata = raw.metadata or {}
        depth = metadata.get("depth_level", 0)
        return {
            "success": True,
            "topic": topic,
            "depth_level": depth,
            "template_id": metadata.get("template_id"),
            "rendered": rendered,
            "tags": list(raw.tags) if raw.tags else [],
        }

    async def lookup_list(self, args: dict[str, Any]) -> dict[str, Any]:
        """Enumerate available topics as a markdown table."""
        try:
            engine = self._engine(template_dir=args.get("template_dir"))
        except ValueError as e:
            return {"success": False, "error": str(e)}

        tag_filter = args.get("tag")
        limit = args.get("limit", 100)
        if not isinstance(limit, int) or limit < 1:
            limit = 100

        # Read cross_links directly so we can enumerate without
        # calling lookup() and polluting the session state.
        import json

        cl_path = engine.generated_dir / "cross_links.json"
        if not cl_path.exists():
            return {
                "success": False,
                "error": f"cross_links.json not found in {engine.generated_dir}",
            }

        try:
            cross_links = json.loads(cl_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return {
                "success": False,
                "error": f"Failed to read cross_links.json: {e}",
            }

        links = cross_links.get("links", {})
        tag_index = cross_links.get("tag_index", {})

        if tag_filter:
            ids = tag_index.get(tag_filter, [])
        else:
            ids = list(links.keys())

        # Group by prefix (con-, tas-, ref-, war-, err-, etc.)
        grouped: dict[str, list[str]] = {}
        for tid in ids[:limit]:
            prefix = tid.split("-", 1)[0] if "-" in tid else "other"
            grouped.setdefault(prefix, []).append(tid)

        category_names = {
            "com": "comparisons",
            "con": "concepts",
            "err": "errors",
            "faq": "faqs",
            "not": "notes",
            "qui": "quickstarts",
            "ref": "references",
            "tas": "tasks",
            "tip": "tips",
            "tro": "troubleshooting",
            "war": "warnings",
        }

        return {
            "success": True,
            "total": len(ids),
            "shown": min(len(ids), limit),
            "tag_filter": tag_filter,
            "categories": {
                category_names.get(prefix, prefix): sorted(tids)
                for prefix, tids in sorted(grouped.items())
            },
        }

    async def lookup_warn(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get file-context warnings for a file path."""
        file_path = args.get("file_path")
        if not file_path or not isinstance(file_path, str):
            return {
                "success": False,
                "error": "file_path is required and must be a string",
            }

        # precursor_warnings() only reads the extension and name,
        # not the file contents — no disk access required. Still
        # validate the path shape defensively to reject null bytes.
        if "\x00" in file_path:
            return {"success": False, "error": "file_path contains null bytes"}

        max_results = args.get("max_results", 3)
        if not isinstance(max_results, int) or max_results < 1:
            max_results = 3

        try:
            engine = self._engine(template_dir=args.get("template_dir"))
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            warnings = engine.precursor_warnings(
                file_path=file_path,
                max_results=max_results,
            )
        except (OSError, ValueError) as e:
            logger.warning("precursor_warnings failed: %s", e)
            return {
                "success": False,
                "error": f"warnings lookup failed: {e}",
            }

        return {
            "success": True,
            "file_path": file_path,
            "count": len(warnings),
            "warnings": warnings,
        }

    async def lookup_preamble(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get the one-line preamble for a feature."""
        feature_name = args.get("feature_name")
        if not feature_name or not isinstance(feature_name, str):
            return {
                "success": False,
                "error": "feature_name is required and must be a string",
            }

        try:
            engine = self._engine(template_dir=args.get("template_dir"))
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            preamble = engine.preamble(feature_name)
        except (OSError, ValueError) as e:
            logger.warning("preamble failed: %s", e)
            return {
                "success": False,
                "error": f"preamble lookup failed: {e}",
            }

        if preamble is None:
            return {
                "success": False,
                "error": f"No preamble for feature: {feature_name}",
            }

        return {
            "success": True,
            "feature_name": feature_name,
            "preamble": preamble,
        }

    async def lookup_reset(self, args: dict[str, Any]) -> dict[str, Any]:
        """Clear progression state so the next lookup starts over."""
        user_id = args.get("user_id", "mcp-session")
        if not isinstance(user_id, str) or not user_id:
            return {
                "success": False,
                "error": "user_id must be a non-empty string",
            }

        storage = LocalFileStorage()
        try:
            storage.set_session(
                user_id,
                {"last_topic": None, "depth_level": 0},
            )
        except (OSError, ValueError) as e:
            return {"success": False, "error": f"reset failed: {e}"}

        return {
            "success": True,
            "user_id": user_id,
            "message": "Session reset — next lookup starts at concept.",
        }

    async def lookup_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Return current progression state without advancing it.

        Read-only inspection of the session storage. Answers
        "where am I?" without triggering a depth escalation,
        which is useful for skills that need to decide whether
        to call ``lookup_topic`` (advance) or show a recap of
        the current depth.
        """
        user_id = args.get("user_id", "mcp-session")
        if not isinstance(user_id, str) or not user_id:
            return {
                "success": False,
                "error": "user_id must be a non-empty string",
            }

        storage = LocalFileStorage()
        try:
            session = storage.get_session(user_id)
        except (OSError, ValueError) as e:
            return {"success": False, "error": f"status read failed: {e}"}

        depth = session.get("depth_level", 0)
        level_labels = {0: "concept", 1: "procedural", 2: "reference"}
        return {
            "success": True,
            "user_id": user_id,
            "last_topic": session.get("last_topic"),
            "depth_level": depth,
            "level_label": level_labels.get(depth, "unknown"),
        }
