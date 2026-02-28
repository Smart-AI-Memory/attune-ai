"""Code Simplification Workflow

Reduces unnecessary complexity in code. Inspired by Boris
Cherny's observation that Claude tends to over-engineer:
too many abstractions, unnecessary classes, premature
optimization, over-configurable interfaces.

Stages:
1. scan (CHEAP) - AST scan for complexity hotspots
2. analyze (CHEAP) - Crew-based simplification analysis
3. simplify (CAPABLE) - Generate simplified code
4. review (CAPABLE) - Validate simplifications (conditional)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import ast
import heapq
import logging
from pathlib import Path
from typing import Any

from .base import BaseWorkflow, ModelTier

logger = logging.getLogger(__name__)

# Categories the crew should focus on for simplification
SIMPLIFY_FOCUS_AREAS = [
    "simplify",
    "consolidate_conditional",
    "inline",
    "dead_code",
]

# Simplify-related RefactoringCategory values to keep from crew results
SIMPLIFY_CATEGORIES = {
    "simplify",
    "consolidate_conditional",
    "inline",
    "dead_code",
}


class SimplifyCodeWorkflow(BaseWorkflow):
    """Simplify over-engineered code.

    Uses AST-based complexity scanning and the RefactoringCrew
    to identify and generate simplifications. Verified with
    ``run-tests`` by default (via verification defaults map).

    Boris's insight: Claude over-engineers. This workflow
    counteracts that by flattening nesting, inlining trivial
    helpers, removing dead code, and reducing abstractions.
    """

    name = "simplify-code"
    description = "Simplify over-engineered code"
    stages = ["scan", "analyze", "simplify", "review"]
    tier_map = {
        "scan": ModelTier.CHEAP,
        "analyze": ModelTier.CAPABLE,
        "simplify": ModelTier.CAPABLE,
        "review": ModelTier.PREMIUM,
    }

    def __init__(
        self,
        min_complexity: int = 5,
        min_findings_for_review: int = 3,
        max_files: int = 20,
        crew_config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize code simplification workflow.

        Args:
            min_complexity: Minimum cyclomatic complexity to
                flag a function as a simplification candidate.
            min_findings_for_review: Minimum findings to run
                the review stage (otherwise skipped).
            max_files: Maximum files to scan.
            crew_config: Configuration dict for RefactoringCrew.
            **kwargs: Additional arguments passed to BaseWorkflow.

        """
        super().__init__(**kwargs)
        self.min_complexity = min_complexity
        self.min_findings_for_review = min_findings_for_review
        self.max_files = max_files
        self.crew_config = crew_config or {}
        self._crew: Any = None
        self._crew_available = False
        self._findings_count = 0

    async def _initialize_crew(self) -> None:
        """Initialize RefactoringCrew with simplify focus."""
        if self._crew is not None:
            return

        try:
            from attune.agent_factory.crews.refactoring import (
                RefactoringCrew,
            )
            from attune.agent_factory.crews.refactoring.types import (
                RefactoringConfig,
            )

            config = RefactoringConfig(
                focus_areas=SIMPLIFY_FOCUS_AREAS,
                depth="standard",
                **self.crew_config,
            )
            self._crew = RefactoringCrew(config=config)
            self._crew_available = True
            logger.info("RefactoringCrew initialized for simplification")
        except ImportError as e:
            logger.warning("RefactoringCrew not available: %s", e)
            self._crew_available = False

    def should_skip_stage(
        self,
        stage_name: str,
        input_data: Any,
    ) -> tuple[bool, str | None]:
        """Skip review stage when few findings.

        Args:
            stage_name: Name of the stage to check.
            input_data: Current workflow data.

        Returns:
            Tuple of (should_skip, reason).

        """
        if stage_name == "review":
            if self._findings_count < self.min_findings_for_review:
                return True, (
                    f"Only {self._findings_count} finding(s), "
                    f"below threshold of {self.min_findings_for_review}"
                )
        return False, None

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Route to specific stage implementation.

        Args:
            stage_name: Current stage name.
            tier: Model tier for this stage.
            input_data: Data from previous stages.

        Returns:
            Tuple of (output_dict, input_tokens, output_tokens).

        Raises:
            ValueError: If stage_name is unknown.

        """
        if stage_name == "scan":
            return await self._scan(input_data, tier)
        if stage_name == "analyze":
            return await self._analyze(input_data, tier)
        if stage_name == "simplify":
            return await self._simplify(input_data, tier)
        if stage_name == "review":
            return await self._review(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    # ------------------------------------------------------------------
    # Stage 1: Scan
    # ------------------------------------------------------------------

    async def _scan(
        self,
        input_data: dict[str, Any],
        tier: ModelTier,
    ) -> tuple[dict[str, Any], int, int]:
        """Scan for complexity hotspots via AST analysis.

        No LLM call — pure static analysis.
        """
        target_path = input_data.get("path", ".")
        file_types = input_data.get("file_types", [".py"])

        hotspots: list[dict[str, Any]] = []
        files_scanned = 0
        target = Path(target_path)

        if target.exists():
            py_files: list[Path] = []
            for ext in file_types:
                for file_path in target.rglob(f"*{ext}"):
                    if any(
                        skip in str(file_path)
                        for skip in [
                            ".git",
                            "node_modules",
                            "__pycache__",
                            "venv",
                            ".venv",
                        ]
                    ):
                        continue
                    py_files.append(file_path)

            # Limit files
            py_files = py_files[: self.max_files]

            for file_path in py_files:
                try:
                    content = file_path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                    files_scanned += 1
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(
                            node,
                            ast.FunctionDef | ast.AsyncFunctionDef,
                        ):
                            complexity = self._function_complexity(node)
                            loc = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
                            if complexity >= self.min_complexity:
                                hotspots.append(
                                    {
                                        "file": str(file_path),
                                        "function": node.name,
                                        "line": node.lineno,
                                        "end_line": node.end_lineno or node.lineno,
                                        "complexity": complexity,
                                        "loc": loc,
                                    },
                                )
                except (SyntaxError, OSError) as e:
                    logger.debug("Skipped %s: %s", file_path, e)
                    continue

        # Rank by complexity (top N)
        hotspots = heapq.nlargest(
            50,
            hotspots,
            key=lambda h: h["complexity"],
        )

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(hotspots)) // 4

        return (
            {
                "hotspots": hotspots,
                "files_scanned": files_scanned,
                "total_hotspots": len(hotspots),
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    @staticmethod
    def _function_complexity(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> int:
        """Calculate cyclomatic complexity for a single function.

        Args:
            node: AST function node.

        Returns:
            Cyclomatic complexity score (1 = baseline).

        """
        complexity = 1  # Base complexity
        for child in ast.walk(node):
            if isinstance(child, ast.If | ast.For | ast.While):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each and/or adds a branch
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
        return complexity

    # ------------------------------------------------------------------
    # Stage 2: Analyze
    # ------------------------------------------------------------------

    async def _analyze(
        self,
        input_data: dict[str, Any],
        tier: ModelTier,
    ) -> tuple[dict[str, Any], int, int]:
        """Delegate to RefactoringCrew for simplification analysis.

        Falls back to LLM-only analysis if crew is unavailable.
        """
        await self._initialize_crew()

        hotspots = input_data.get("hotspots", [])
        findings: list[dict[str, Any]] = []

        if self._crew_available and hotspots:
            # Group hotspots by file for batch analysis
            files_to_analyze: dict[str, list[dict[str, Any]]] = {}
            for hotspot in hotspots[:20]:
                fpath = hotspot["file"]
                if fpath not in files_to_analyze:
                    files_to_analyze[fpath] = []
                files_to_analyze[fpath].append(hotspot)

            for fpath, _file_hotspots in files_to_analyze.items():
                try:
                    code = Path(fpath).read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                    crew_result = await self._crew.analyze(
                        code=code,
                        file_path=fpath,
                    )
                    if crew_result and crew_result.findings:
                        for finding in crew_result.findings:
                            # Filter to simplify-related categories
                            if finding.category.value in SIMPLIFY_CATEGORIES:
                                findings.append(finding.to_dict())
                except (OSError, ValueError, RuntimeError) as e:
                    logger.debug(
                        "Crew analysis failed for %s: %s",
                        fpath,
                        e,
                    )
                    continue
        elif hotspots:
            # Fallback: LLM-only analysis
            hotspot_summary = "\n".join(
                f"- {h['file']}:{h['line']} {h['function']} "
                f"(complexity={h['complexity']}, LOC={h['loc']})"
                for h in hotspots[:15]
            )

            response, in_tok, out_tok = await self._call_llm(
                tier=tier,
                system=(
                    "You are a code simplification analyst. "
                    "Identify which functions should be simplified "
                    "and why. Focus on: nested conditionals, "
                    "unnecessary abstractions, dead code, trivial "
                    "helpers that should be inlined. Return JSON "
                    "array of findings with: title, description, "
                    "file_path, start_line, category (simplify, "
                    "dead_code, inline, consolidate_conditional)."
                ),
                user_message=(
                    f"Analyze these complexity hotspots for "
                    f"simplification:\n\n{hotspot_summary}"
                ),
                max_tokens=2048,
            )

            # Parse LLM response as findings
            import json
            import re

            try:
                json_match = re.search(r"\[[\s\S]*\]", response)
                if json_match:
                    parsed = json.loads(json_match.group())
                    for item in parsed:
                        findings.append(item)
            except (json.JSONDecodeError, ValueError):
                logger.debug("Could not parse LLM findings as JSON")

        self._findings_count = len(findings)

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(findings)) // 4

        return (
            {
                "findings": findings,
                "findings_count": len(findings),
                "crew_used": self._crew_available,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    # ------------------------------------------------------------------
    # Stage 3: Simplify
    # ------------------------------------------------------------------

    async def _simplify(
        self,
        input_data: dict[str, Any],
        tier: ModelTier,
    ) -> tuple[dict[str, Any], int, int]:
        """Generate simplified code for each finding."""
        findings = input_data.get("findings", [])
        simplifications: list[dict[str, Any]] = []

        if self._crew_available and findings:
            from attune.agent_factory.crews.refactoring.types import (
                RefactoringFinding,
            )

            for finding_dict in findings[:10]:
                try:
                    finding = RefactoringFinding.from_dict(finding_dict)
                    fpath = finding.file_path
                    if not fpath:
                        continue

                    code = Path(fpath).read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                    updated = await self._crew.generate_refactor(
                        finding,
                        code,
                    )
                    if updated.after_code:
                        simplifications.append(
                            {
                                "title": updated.title,
                                "file": updated.file_path,
                                "line": updated.start_line,
                                "category": updated.category.value,
                                "before": updated.before_code[:500],
                                "after": updated.after_code[:500],
                            },
                        )
                except (OSError, ValueError, KeyError, RuntimeError) as e:
                    logger.debug("Simplification failed: %s", e)
                    continue
        elif findings:
            # Fallback: ask LLM to generate simplifications
            findings_text = "\n\n".join(
                f"### {f.get('title', 'Finding')}\n"
                f"File: {f.get('file_path', 'unknown')}\n"
                f"Category: {f.get('category', 'simplify')}\n"
                f"Description: {f.get('description', '')}"
                for f in findings[:10]
            )

            response, in_tok, out_tok = await self._call_llm(
                tier=tier,
                system=(
                    "You are a code simplification expert. For "
                    "each finding, provide the simplified code. "
                    "Return a JSON array with: title, file, "
                    "before (original), after (simplified). "
                    "Preserve all behavior."
                ),
                user_message=(f"Generate simplified code for these findings:\n\n{findings_text}"),
                max_tokens=4096,
            )

            import json
            import re

            try:
                json_match = re.search(r"\[[\s\S]*\]", response)
                if json_match:
                    simplifications = json.loads(json_match.group())
            except (json.JSONDecodeError, ValueError):
                logger.debug("Could not parse simplifications JSON")

        # Build summary
        categories_found: dict[str, int] = {}
        for simp in simplifications:
            cat = simp.get("category", "simplify")
            categories_found[cat] = categories_found.get(cat, 0) + 1

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(simplifications)) // 4

        return (
            {
                "simplifications": simplifications,
                "simplification_count": len(simplifications),
                "categories": categories_found,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    # ------------------------------------------------------------------
    # Stage 4: Review (conditional)
    # ------------------------------------------------------------------

    async def _review(
        self,
        input_data: dict[str, Any],
        tier: ModelTier,
    ) -> tuple[dict[str, Any], int, int]:
        """Review proposed simplifications for correctness."""
        simplifications = input_data.get("simplifications", [])

        if not simplifications:
            return (
                {**input_data, "review": "No simplifications to review."},
                0,
                0,
            )

        diffs = "\n\n".join(
            f"### {s.get('title', 'Change')}\n"
            f"File: {s.get('file', 'unknown')}\n"
            f"**Before:**\n```\n{s.get('before', '')}\n```\n"
            f"**After:**\n```\n{s.get('after', '')}\n```"
            for s in simplifications[:10]
        )

        response, in_tok, out_tok = await self._call_llm(
            tier=tier,
            system=(
                "You are a code review expert. Review these "
                "simplifications for correctness. For each:\n"
                "1. Does it preserve behavior?\n"
                "2. Is the simplified version actually simpler?\n"
                "3. Any edge cases missed?\n"
                "Flag any issues. Be concise."
            ),
            user_message=(
                f"Review these {len(simplifications)} proposed simplifications:\n\n{diffs}"
            ),
            max_tokens=2048,
        )

        return (
            {
                **input_data,
                "review": response,
                "review_tier": tier.value,
            },
            in_tok,
            out_tok,
        )
