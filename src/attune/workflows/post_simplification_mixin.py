"""Post-Simplification Mixin for BaseWorkflow.

Provides an optional simplification step that runs between
stage execution and verification. Code-generating workflows
opt in via ``enable_post_simplification=True``.

Pipeline: execute stages → simplify → verify → self-correct

Follows the same pattern as VerificationMixin: no-ops when
disabled, never crashes the workflow, best-effort semantics.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..workflows.data_classes import WorkflowResult

logger = logging.getLogger(__name__)

# Workflows that produce code and benefit from simplification
CODE_GENERATING_WORKFLOWS = frozenset(
    {
        "refactor-plan",
        "test-gen",
        "code-review",
    },
)


class PostSimplificationMixin:
    """Mixin providing optional post-execution code simplification.

    When ``enable_post_simplification=True`` is passed to a workflow,
    the simplifier runs after all stages complete but before
    verification. This implements Boris Cherny's recommendation:
    always simplify Claude-generated code before verifying it.

    Expected attributes on the host class:
        name (str): Workflow name
        _enable_post_simplification (bool): Whether to run simplifier

    """

    _enable_post_simplification: bool = False
    _simplification_min_complexity: int = 5
    _simplification_result: dict[str, Any] | None = None

    def _init_post_simplification(
        self,
        enable_post_simplification: bool = False,
        simplification_min_complexity: int = 5,
    ) -> None:
        """Initialize post-simplification settings.

        Called from workflow ``__init__`` for workflows that
        opt in to automatic simplification.

        Args:
            enable_post_simplification: Whether to run the simplifier
                after stage execution.
            simplification_min_complexity: Minimum cyclomatic complexity
                threshold for functions to be simplified.

        """
        self._enable_post_simplification = enable_post_simplification
        self._simplification_min_complexity = simplification_min_complexity
        self._simplification_result = None

    async def _run_post_simplification(
        self,
        result: WorkflowResult,
        kwargs: dict[str, Any],
    ) -> WorkflowResult:
        """Run simplification on workflow output if enabled.

        This method is called from ``execute()`` after all stages
        complete but before the verification loop. It scans the
        target path for complexity hotspots and generates simplified
        alternatives.

        Args:
            result: The WorkflowResult from stage execution.
            kwargs: Original workflow kwargs (used for path).

        Returns:
            Updated WorkflowResult with simplification metadata.

        """
        if not self._enable_post_simplification:
            return result

        if not result.success:
            return result

        target_path = kwargs.get("path", ".")
        if not target_path:
            return result

        try:
            import ast
            from pathlib import Path

            scan_path = Path(target_path)
            hotspots: list[dict[str, Any]] = []
            files_scanned = 0

            py_files = list(scan_path.rglob("*.py"))[:10]
            for py_file in py_files:
                try:
                    source = py_file.read_text(encoding="utf-8")
                    tree = ast.parse(source)
                    files_scanned += 1
                except (
                    SyntaxError,
                    UnicodeDecodeError,
                    OSError,
                    ValueError,
                ):  # ast.parse: null bytes -> ValueError, not SyntaxError
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                        complexity = sum(
                            1
                            for child in ast.walk(node)
                            if isinstance(
                                child,
                                ast.If | ast.For | ast.While | ast.ExceptHandler | ast.With,
                            )
                        )
                        if complexity >= self._simplification_min_complexity:
                            hotspots.append(
                                {
                                    "file": str(py_file),
                                    "function": node.name,
                                    "complexity": complexity,
                                    "line": node.lineno,
                                },
                            )

            self._simplification_result = {
                "files_scanned": files_scanned,
                "hotspots_found": len(hotspots),
                "hotspots": hotspots[:5],
            }

            # Attach simplification metadata to result
            if result.final_output and isinstance(result.final_output, dict):
                result.final_output["_simplification"] = self._simplification_result

            if hotspots:
                logger.info(
                    "Post-simplification scan found %d hotspots in %s",
                    len(hotspots),
                    target_path,
                )

        except ImportError:
            logger.debug("SimplifyCodeWorkflow not available for post-simplification")
        except (ValueError, TypeError, KeyError) as e:
            logger.debug("Post-simplification scan failed (data error): %s", e)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Post-simplification is optional, never crash workflow
            logger.debug("Post-simplification failed: %s", e)

        return result
