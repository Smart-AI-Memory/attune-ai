"""HelpEngine: main entry point for attune-help.

Provides a single class that manages template directories
(bundled + override), session storage, renderer selection,
and progressive depth — all with sensible defaults.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from attune_help.progression import populate_progressive
from attune_help.storage import LocalFileStorage, SessionStorage
from attune_help.templates import (
    AudienceProfile,
    PopulatedTemplate,
    TemplateContext,
    _load_cross_links,
    populate,
)
from attune_help.transformers import (
    render_claude_code,
    render_cli,
    render_marketplace,
)

logger = logging.getLogger(__name__)

# Bundled templates ship inside the package
_BUNDLED_DIR = Path(__file__).resolve().parent / "templates"

# Quick summaries: cached per directory, thread-safe
_SUMMARIES_CACHE: dict[str, dict[str, str]] = {}
_SUMMARIES_LOCK = threading.Lock()


def _load_summaries(template_dir: Path) -> dict[str, str]:
    """Load skill summaries from summaries.json.

    Thread-safe, keyed by directory path so multiple
    HelpEngine instances with different template_dirs
    each get the correct summaries.
    """
    import json

    cache_key = str(template_dir)
    with _SUMMARIES_LOCK:
        if cache_key in _SUMMARIES_CACHE:
            return _SUMMARIES_CACHE[cache_key]

        path = template_dir / "summaries.json"
        if not path.exists():
            _SUMMARIES_CACHE[cache_key] = {}
            return _SUMMARIES_CACHE[cache_key]
        try:
            data = json.loads(
                path.read_text(encoding="utf-8"),
            )
            _SUMMARIES_CACHE[cache_key] = data
            return data
        except (json.JSONDecodeError, OSError):
            _SUMMARIES_CACHE[cache_key] = {}
            return _SUMMARIES_CACHE[cache_key]


_RENDERERS = {
    "plain": lambda t: t.body,
    "claude_code": render_claude_code,
    "cli": render_cli,
    "marketplace": render_marketplace,
}

_DEPTH_PROMPTS = {
    0: '\n\n*(concept view — say "tell me more" for step-by-step)*',
    1: '\n\n*(task view — say "tell me more" for full reference)*',
    2: "",
}


def _depth_prompt(depth: int) -> str:
    """Return the progressive depth prompt for the current level."""
    return _DEPTH_PROMPTS.get(depth, "")


class HelpEngine:
    """Lightweight help runtime with progressive depth.

    Args:
        template_dir: Override template directory. When set,
            templates are loaded from here first; bundled
            templates are the fallback.
        storage: Session storage backend. Defaults to
            LocalFileStorage (~/.attune-help/sessions/).
        renderer: Output renderer. One of "plain" (default),
            "cli", "claude_code", "marketplace", or "auto".
        user_id: User identifier for session tracking.
            Defaults to "default".

    Example:
        >>> engine = HelpEngine()
        >>> result = engine.lookup("security-audit")
        >>> print(result)  # concept template
        >>> result = engine.lookup("security-audit")
        >>> print(result)  # task template (progressive)
    """

    def __init__(
        self,
        template_dir: str | Path | None = None,
        storage: SessionStorage | None = None,
        renderer: str = "plain",
        user_id: str = "default",
    ) -> None:
        self._override_dir = Path(template_dir) if template_dir else None
        self._bundled_dir = _BUNDLED_DIR
        self._storage = storage or LocalFileStorage()
        self._renderer_name = renderer
        self._user_id = user_id

    @property
    def generated_dir(self) -> Path:
        """Resolve the active template directory.

        Override directory wins when present and contains
        templates. Falls back to bundled.

        Returns:
            Path to the active generated/ directory.
        """
        if self._override_dir and self._override_dir.exists():
            cl = self._override_dir / "cross_links.json"
            if cl.exists():
                return self._override_dir
        return self._bundled_dir

    def lookup(
        self,
        topic: str,
        context: TemplateContext | None = None,
        audience: AudienceProfile | None = None,
    ) -> str | None:
        """Look up a topic with progressive depth.

        First call returns concept, repeat calls escalate
        to task then reference. Renders with the configured
        renderer.

        Args:
            topic: Topic slug or template ID.
            context: Optional runtime context.
            audience: Optional audience override.

        Returns:
            Rendered string, or None if not found.
        """
        result = populate_progressive(
            topic,
            storage=self._storage,
            user_id=self._user_id,
            context=context,
            audience=audience,
            generated_dir=self.generated_dir,
        )
        if result is None:
            return None
        rendered = self.render(result)
        depth = result.metadata.get("depth_level", 0)
        return rendered + _depth_prompt(depth)

    def preamble(self, feature_name: str) -> str | None:
        """Get the one-liner preamble for a feature.

        Returns the "Use X when..." sentence from the
        feature's task template. Useful as a context
        tooltip wherever a feature name appears.

        Args:
            feature_name: Feature slug (e.g. "security").

        Returns:
            Preamble string, or None if not available.
        """
        from attune_help.preamble import get_preamble

        if self._override_dir:
            result = get_preamble(feature_name, self._override_dir)
            if result:
                return result
        return get_preamble(feature_name, self._bundled_dir)

    def get_summary(self, skill_name: str) -> str | None:
        """Get a one-line summary for a skill.

        Designed to display instantly when a user invokes a
        skill by name — tells them what's about to happen
        while the skill starts working.

        Args:
            skill_name: Skill slug (e.g. "security-audit").

        Returns:
            One-line summary string, or None if not found.
        """
        summaries = _load_summaries(self.generated_dir)
        return summaries.get(skill_name)

    def get(
        self,
        template_id: str,
        context: TemplateContext | None = None,
        audience: AudienceProfile | None = None,
    ) -> str | None:
        """Get a specific template by ID (no progressive depth).

        Args:
            template_id: Exact template ID.
            context: Optional runtime context.
            audience: Optional audience override.

        Returns:
            Rendered string, or None if not found.
        """
        result = populate(
            template_id,
            context=context,
            audience=audience,
            generated_dir=self.generated_dir,
        )
        if result is None:
            return None
        return self.render(result)

    def lookup_raw(
        self,
        topic: str,
        context: TemplateContext | None = None,
        audience: AudienceProfile | None = None,
    ) -> PopulatedTemplate | None:
        """Look up a topic and return the raw PopulatedTemplate.

        Same progressive depth as lookup(), but returns the
        dataclass instead of rendered text. Useful when the
        app needs structured access to sections, tags, etc.

        Args:
            topic: Topic slug or template ID.
            context: Optional runtime context.
            audience: Optional audience override.

        Returns:
            PopulatedTemplate, or None if not found.
        """
        return populate_progressive(
            topic,
            storage=self._storage,
            user_id=self._user_id,
            context=context,
            audience=audience,
            generated_dir=self.generated_dir,
        )

    def render(self, template: PopulatedTemplate) -> str:
        """Apply the configured renderer to an already-populated template.

        Public API for callers that need to render a template without
        advancing the session state (e.g. MCP handlers that already hold
        the result of ``lookup_raw``). Use ``lookup()`` when you want the
        combined "advance session + render" behavior.

        Args:
            template: Populated template to render.

        Returns:
            Rendered string.
        """
        renderer_fn = _RENDERERS.get(self._renderer_name)
        if renderer_fn is None:
            if self._renderer_name == "auto":
                renderer_fn = self._auto_detect_renderer()
            else:
                logger.warning(
                    "Unknown renderer '%s', falling back to plain",
                    self._renderer_name,
                )
                renderer_fn = _RENDERERS["plain"]
        return renderer_fn(template)

    def precursor_warnings(
        self,
        file_path: str,
        max_results: int = 3,
    ) -> list[str]:
        """Get warnings relevant to a file being edited.

        Maps file extensions and content patterns to tags,
        then finds matching warning and error templates.

        Args:
            file_path: Path to the file being edited.
            max_results: Maximum warnings to return.

        Returns:
            List of rendered warning strings.
        """
        ext = Path(file_path).suffix.lower()
        name = Path(file_path).name.lower()

        tags: list[str] = []

        # Extension-based triggers
        ext_map = {
            ".py": ["python", "imports", "testing", "error-handling"],
            ".yml": ["ci", "github-actions"],
            ".yaml": ["ci", "github-actions"],
            ".json": ["packaging"],
            ".toml": ["packaging", "python", "publishing"],
            ".md": ["claude-code"],
            ".sql": ["database", "migrations"],
            ".env": ["config", "secrets"],
            ".cfg": ["config"],
            ".ini": ["config"],
        }
        tags.extend(ext_map.get(ext, []))

        # Filename-based triggers
        name_map = {
            "pyproject.toml": ["deps", "publishing", "packaging"],
            "requirements.txt": ["deps"],
            "setup.py": ["publishing", "packaging"],
            "setup.cfg": ["publishing", "packaging"],
            "config.py": ["config"],
            "settings.py": ["config"],
            "models.py": ["database"],
            "alembic.ini": ["database", "migrations"],
            "dockerfile": ["ci", "cd"],
            "docker-compose.yml": ["ci", "cd"],
            ".gitignore": ["git"],
            ".env": ["config", "secrets"],
            ".env.example": ["config", "secrets"],
            "manifest.in": ["publishing"],
        }
        tags.extend(name_map.get(name, []))

        if not tags:
            return []

        gen_dir = self.generated_dir
        cross_links = _load_cross_links(gen_dir)
        tag_index = cross_links.get("tag_index", {})

        candidates: dict[str, float] = {}
        for tag in tags:
            for tid in tag_index.get(tag, []):
                if tid.startswith(
                    ("war-", "err-", "con-task-", "qui-task-", "tas-task-", "ref-task-")
                ):
                    score = candidates.get(tid, 0)
                    score += 1
                    # Boost task-category templates —
                    # they're guidance, not error history
                    if "task-" in tid:
                        score += 10
                    candidates[tid] = score

        if not candidates:
            return []

        sorted_ids = sorted(
            candidates,
            key=lambda t: candidates[t],
            reverse=True,
        )

        results: list[str] = []
        for tid in sorted_ids[:max_results]:
            # Task-category templates get normal
            # verbosity; error/warning get compact
            if "task-" in tid:
                aud = AudienceProfile(verbosity="normal")
            else:
                aud = AudienceProfile(verbosity="compact")
            result = populate(
                tid,
                audience=aud,
                generated_dir=gen_dir,
            )
            if result:
                results.append(self.render(result))
        return results

    @staticmethod
    def _auto_detect_renderer() -> Any:
        """Detect the best renderer for the current environment.

        Returns:
            Renderer function.
        """
        import os

        if os.environ.get("CLAUDE_CODE"):
            return render_claude_code
        try:
            import rich  # noqa: F401

            return render_cli
        except ImportError:
            pass
        return _RENDERERS["plain"]
