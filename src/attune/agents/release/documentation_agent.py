"""Documentation agent for Release Preparation Agent Team.

Checks docstring coverage, README currency, and CHANGELOG presence by
walking Python files and inspecting their AST.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from attune.agents.state.store import AgentStateStore

from .base_agent import ReleaseAgent
from .release_models import Tier

logger = logging.getLogger(__name__)


class DocumentationAgent(ReleaseAgent):
    """Checks docstring coverage, README currency, and CHANGELOG presence.

    Rule-based: Walks Python files, counts functions with/without
    docstrings.
    """

    def __init__(
        self,
        redis_client: Any | None = None,
        state_store: AgentStateStore | None = None,
    ) -> None:
        """Initialize the documentation audit agent.

        Args:
            redis_client: Optional Redis connection for coordination.
            state_store: Optional persistent state store.
        """
        super().__init__(
            agent_id=f"documentation-{uuid4().hex[:8]}",
            role="Documentation",
            redis_client=redis_client,
            state_store=state_store,
        )

    def _execute_tier(self, codebase_path: str, tier: Tier) -> tuple[bool, dict[str, Any]]:
        """Run documentation analysis."""
        try:
            src_path = Path(codebase_path) / "src"
            if not src_path.exists():
                src_path = Path(codebase_path)

            # Count functions and docstrings using AST
            total_functions = 0
            documented_functions = 0
            undocumented: list[str] = []

            py_files = list(src_path.rglob("*.py"))
            for py_file in py_files:
                try:
                    source = py_file.read_text(encoding="utf-8")
                    tree = ast.parse(source)
                except (
                    SyntaxError,
                    UnicodeDecodeError,
                    ValueError,
                ):  # ast.parse: null bytes -> ValueError, not SyntaxError
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                        # Skip private/dunder methods
                        if node.name.startswith("_") and not node.name.startswith("__"):
                            continue

                        total_functions += 1
                        docstring = ast.get_docstring(node)
                        if docstring:
                            documented_functions += 1
                        else:
                            rel_path = py_file.relative_to(Path(codebase_path))
                            undocumented.append(f"{rel_path}:{node.lineno}:{node.name}")

            # Calculate coverage
            doc_coverage = (
                (documented_functions / total_functions * 100.0) if total_functions > 0 else 0.0
            )

            # Check README and CHANGELOG
            readme_exists = (Path(codebase_path) / "README.md").exists()
            changelog_exists = (Path(codebase_path) / "CHANGELOG.md").exists()

            findings = {
                "coverage_percent": round(doc_coverage, 1),
                "total_functions": total_functions,
                "documented_functions": documented_functions,
                "undocumented_count": (total_functions - documented_functions),
                "undocumented_sample": undocumented[:10],
                "readme_exists": readme_exists,
                "changelog_exists": changelog_exists,
                "score": doc_coverage,
                "confidence": 0.9,
                "tier": tier.value,
                "mode": "rule_based",
            }

            # Documentation is non-blocking, so always "succeeds"
            # but the quality gate evaluation handles the threshold
            # check
            return True, findings

        except Exception as e:  # noqa: BLE001
            logger.error(f"Documentation analysis failed: {e}")
            return False, {
                "error": str(e),
                "coverage_percent": 0.0,
                "score": 0.0,
                "confidence": 0.1,
            }
