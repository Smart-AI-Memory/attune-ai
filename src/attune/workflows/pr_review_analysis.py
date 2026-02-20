"""PR Review analysis mixin.

Contains the scoring, verdict determination, finding-merge, and
diff-generation helpers used by PRReviewWorkflow.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations


class PRReviewAnalysisMixin:
    """Mixin providing analysis helpers for PR review workflows."""

    @staticmethod
    def _auto_generate_diff(target_path: str) -> str:
        """Auto-generate diff from git if not provided.

        Args:
            target_path: Working directory for git commands

        Returns:
            Diff string or placeholder message

        """
        import subprocess

        try:
            # Get diff of staged and unstaged changes
            git_result = subprocess.run(
                ["git", "diff", "HEAD"],
                check=False,
                cwd=target_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            diff = git_result.stdout or ""
            if not diff:
                # Try getting diff against main/master
                for branch in ["main", "master"]:
                    git_result = subprocess.run(
                        ["git", "diff", branch],
                        check=False,
                        cwd=target_path,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if git_result.stdout:
                        diff = git_result.stdout
                        break
            if not diff:
                diff = "(No diff available - no changes detected)"
            return diff
        except Exception:
            return "(Could not generate diff from git)"

    @staticmethod
    def _merge_findings(
        code_findings: list[dict],
        security_findings: list[dict],
    ) -> list[dict]:
        """Merge and deduplicate findings from both sources."""
        # Tag findings with source
        for f in code_findings:
            f["source"] = "code_review"
        for f in security_findings:
            f["source"] = "security_audit"

        # Combine and deduplicate by (file, line, type)
        all_findings = code_findings + security_findings
        seen: set[tuple[str | None, ...]] = set()
        unique: list[dict] = []

        for f in all_findings:
            key = (f.get("file"), f.get("line"), f.get("type") or f.get("title"))
            if key not in seen:
                seen.add(key)
                unique.append(f)

        # Sort by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        unique.sort(key=lambda f: severity_order.get(f.get("severity", "medium"), 2))

        return unique

    @staticmethod
    def _get_code_quality_score(code_review: dict | None) -> float:
        """Extract code quality score from review."""
        if code_review:
            return float(code_review.get("quality_score", 85.0))
        return 85.0  # Default if no review

    @staticmethod
    def _get_security_risk_score(security_audit: dict | None) -> float:
        """Extract security risk score from audit."""
        if security_audit:
            return float(security_audit.get("risk_score", 20.0))
        return 20.0  # Default if no audit

    @staticmethod
    def _calculate_combined_score(
        code_quality: float,
        security_risk: float,
    ) -> float:
        """Calculate combined score.

        Higher is better. Combines code quality (0-100, higher=better)
        with security risk (0-100, lower=better).
        """
        # Convert security risk to "safety score" (invert)
        security_safety = 100.0 - security_risk

        # Weighted average: security is slightly more important
        combined = (code_quality * 0.45) + (security_safety * 0.55)
        return max(0.0, min(100.0, combined))

    @staticmethod
    def _determine_verdict(
        code_review: dict | None,
        security_audit: dict | None,
        combined_score: float,
        blockers: list[str],
    ) -> str:
        """Determine final PR verdict."""
        verdicts: list[str] = []

        # Code review verdict
        if code_review:
            code_verdict = code_review.get("verdict", "approve")
            verdicts.append(code_verdict)

        # Security risk-based verdict
        if security_audit:
            risk = security_audit.get("risk_score", 0)
            if risk >= 70:
                verdicts.append("reject")
            elif risk >= 50:
                verdicts.append("request_changes")
            elif risk >= 30:
                verdicts.append("approve_with_suggestions")

        # Score-based verdict
        if combined_score < 50:
            verdicts.append("reject")
        elif combined_score < 70:
            verdicts.append("request_changes")
        elif combined_score < 85:
            verdicts.append("approve_with_suggestions")
        else:
            verdicts.append("approve")

        # Blockers force request_changes at minimum
        if blockers:
            verdicts.append("request_changes")

        # Return most severe verdict
        priority = ["reject", "request_changes", "approve_with_suggestions", "approve"]
        for v in priority:
            if v in verdicts:
                return v

        return "approve"

    @staticmethod
    def _generate_summary(
        verdict: str,
        code_quality: float,
        security_risk: float,
        total_findings: int,
        critical_count: int,
        high_count: int,
    ) -> str:
        """Generate human-readable summary."""
        verdict_text = {
            "approve": "PR is ready to merge",
            "approve_with_suggestions": "PR can be merged with minor improvements",
            "request_changes": "PR requires changes before merging",
            "reject": "PR has critical issues and should not be merged",
        }.get(verdict, "Unknown status")

        summary_parts = [verdict_text]

        if total_findings > 0:
            findings_text = f"{total_findings} finding(s)"
            if critical_count > 0:
                findings_text += f" ({critical_count} critical)"
            elif high_count > 0:
                findings_text += f" ({high_count} high)"
            summary_parts.append(findings_text)

        summary_parts.append(f"Code quality: {code_quality:.0f}/100")
        summary_parts.append(f"Security risk: {security_risk:.0f}/100")

        return ". ".join(summary_parts) + "."
