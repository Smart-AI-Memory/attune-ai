"""Performance Audit Analysis Stages (Mixin)

Mixin class containing the analysis stage methods for the
performance audit workflow: profile, analyze, and hotspots.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import ModelTier
from .perf_audit_patterns import PERF_PATTERNS

# Directories to skip during file scanning
_SKIP_DIRS = [".git", "node_modules", "__pycache__", "venv", "test"]


class PerfAuditAnalysisMixin:
    """Mixin providing analysis stages for PerformanceAuditWorkflow.

    Provides the profile, analyze, and hotspots stages.

    This mixin expects the host class to provide:
    - ``enable_auth_strategy``: bool
    - ``_auth_mode_used``: str | None
    - ``_hotspot_count``: int
    """

    async def _profile(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Static analysis for common performance anti-patterns.

        Scans code for known performance issues.

        Args:
            input_data: Dict with 'path' and optional 'file_types'
            tier: Model tier for this stage

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens)
        """
        target_path = input_data.get("path", ".")
        file_types = input_data.get("file_types", [".py"])

        findings: list[dict] = []
        files_scanned = 0

        target = Path(target_path)

        # === AUTH STRATEGY INTEGRATION ===
        if self.enable_auth_strategy:
            _run_auth_strategy(self, target, file_types, target_path)
        # === END AUTH STRATEGY INTEGRATION ===

        if target.exists():
            for ext in file_types:
                for file_path in target.rglob(f"*{ext}"):
                    if any(skip in str(file_path) for skip in _SKIP_DIRS):
                        continue

                    try:
                        content = file_path.read_text(errors="ignore")
                        files_scanned += 1
                        _scan_file_for_patterns(content, str(file_path), findings)
                    except OSError:
                        continue

        # Group by impact
        by_impact: dict[str, list] = {"high": [], "medium": [], "low": []}
        for f in findings:
            impact = f.get("impact", "low")
            by_impact[impact].append(f)

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(findings)) // 4

        return (
            {
                "findings": findings,
                "finding_count": len(findings),
                "files_scanned": files_scanned,
                "by_impact": {k: len(v) for k, v in by_impact.items()},
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _analyze(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Deep analysis of algorithmic complexity.

        Examines code structure for complexity issues.

        Args:
            input_data: Dict with 'findings' from profile stage
            tier: Model tier for this stage

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens)
        """
        findings = input_data.get("findings", [])

        # Group findings by file
        by_file: dict[str, list] = {}
        for f in findings:
            file_path = f.get("file", "")
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(f)

        # Analyze each file
        analysis: list[dict] = []
        for file_path, file_findings in by_file.items():
            high_count = sum(1 for f in file_findings if f["impact"] == "high")
            medium_count = sum(1 for f in file_findings if f["impact"] == "medium")
            low_count = sum(1 for f in file_findings if f["impact"] == "low")

            complexity_score = high_count * 10 + medium_count * 5 + low_count * 1
            concerns = list({f["type"] for f in file_findings})

            analysis.append(
                {
                    "file": file_path,
                    "complexity_score": complexity_score,
                    "finding_count": len(file_findings),
                    "high_impact": high_count,
                    "concerns": concerns[:5],
                },
            )

        # Sort by complexity score
        analysis.sort(key=lambda x: -x["complexity_score"])

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(analysis)) // 4

        return (
            {
                "analysis": analysis,
                "analyzed_files": len(analysis),
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _hotspots(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Identify performance hotspots.

        Pinpoints files and areas requiring immediate attention.

        Args:
            input_data: Dict with 'analysis' from analyze stage
            tier: Model tier for this stage

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens)
        """
        analysis = input_data.get("analysis", [])

        # Top hotspots (highest complexity scores)
        hotspots = [a for a in analysis if a["complexity_score"] >= 10 or a["high_impact"] >= 2]

        self._hotspot_count = len(hotspots)

        # Categorize hotspots
        critical = [h for h in hotspots if h["complexity_score"] >= 20]
        moderate = [h for h in hotspots if 10 <= h["complexity_score"] < 20]

        # Calculate overall perf score (inverse of problems)
        total_score = sum(a["complexity_score"] for a in analysis)
        max_score = len(analysis) * 30  # Max possible score
        perf_score = max(0, 100 - int((total_score / max(max_score, 1)) * 100))

        hotspot_result = {
            "hotspots": hotspots[:15],  # Top 15
            "hotspot_count": self._hotspot_count,
            "critical_count": len(critical),
            "moderate_count": len(moderate),
            "perf_score": perf_score,
            "perf_level": (
                "critical" if perf_score < 50 else "warning" if perf_score < 75 else "good"
            ),
        }

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(hotspot_result)) // 4

        return (
            {
                "hotspot_result": hotspot_result,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )


def _scan_file_for_patterns(content: str, file_path: str, findings: list[dict]) -> None:
    """Scan file content against all performance anti-patterns.

    Args:
        content: File content to scan
        file_path: Path string for the file
        findings: List to append findings to (mutated in place)
    """
    for pattern_name, pattern_info in PERF_PATTERNS.items():
        for pattern in pattern_info["patterns"]:
            matches = list(re.finditer(pattern, content, re.MULTILINE))
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                findings.append(
                    {
                        "type": pattern_name,
                        "file": file_path,
                        "line": line_num,
                        "description": pattern_info["description"],
                        "impact": pattern_info["impact"],
                        "match": match.group()[:80],
                    },
                )


def _run_auth_strategy(
    workflow: Any,
    target: Path,
    file_types: list[str],
    target_path: str,
) -> None:
    """Run auth strategy integration for profile stage.

    Args:
        workflow: The workflow instance (for setting _auth_mode_used)
        target: Target path to scan
        file_types: File extensions to scan
        target_path: Original target path string
    """
    try:
        import logging

        from attune.models import (
            count_lines_of_code,
            get_auth_strategy,
            get_module_size_category,
        )

        logger = logging.getLogger(__name__)

        # Calculate total LOC for the project/path
        total_lines = 0
        if target.is_file():
            total_lines = count_lines_of_code(target)
        elif target.is_dir():
            for ext in file_types:
                for file_path in target.rglob(f"*{ext}"):
                    if any(skip in str(file_path) for skip in _SKIP_DIRS):
                        continue
                    try:
                        total_lines += count_lines_of_code(file_path)
                    except Exception:
                        pass

        if total_lines > 0:
            strategy = get_auth_strategy()
            recommended_mode = strategy.get_recommended_mode(total_lines)
            workflow._auth_mode_used = recommended_mode.value

            size_category = get_module_size_category(total_lines)
            logger.info(
                f"Performance audit target: {target_path} "
                f"({total_lines:,} LOC, {size_category})"
            )
            logger.info(f"Recommended auth mode: {recommended_mode.value}")

            cost_estimate = strategy.estimate_cost(total_lines, recommended_mode)
            if recommended_mode.value == "subscription":
                logger.info(
                    f"Cost estimate: ~${cost_estimate:.4f} "
                    "(significantly cheaper with subscription)"
                )
            else:
                logger.info(f"Cost estimate: ~${cost_estimate:.4f} (API-based)")

    except ImportError as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"Auth strategy not available: {e}")
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Auth strategy detection failed: {e}")
