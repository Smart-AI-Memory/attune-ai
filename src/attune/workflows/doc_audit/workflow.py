"""DocAuditWorkflow — Documentation accuracy audit and gap filling.

Runs 10 programmatic checks on the project's documentation, plans
fixes, applies auto-fixable changes, and verifies results.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import re
from pathlib import Path
from typing import Any

from ..base import BaseWorkflow, ModelTier, estimate_tokens
from .checks import CheckResult, run_all_checks


class DocAuditWorkflow(BaseWorkflow):
    """Documentation accuracy audit and gap filling workflow.

    Stages:
        audit:   Run all 10 check functions; return score + results.
        plan:    For each failing check, generate a fix plan dict.
        execute: Apply auto-fixable changes to files on disk.
        verify:  Re-run all checks; compare before/after scores.

    Example:
        workflow = DocAuditWorkflow(project_root=".")
        result = await workflow.execute()

    """

    name = "doc-audit"
    description = "Audit existing docs for staleness, broken links, and drift (validation)"
    stages = ["audit", "plan", "execute", "verify"]
    tier_map = {
        "audit": ModelTier.CHEAP,
        "plan": ModelTier.CAPABLE,
        "execute": ModelTier.CAPABLE,
        "verify": ModelTier.CHEAP,
    }

    def __init__(
        self,
        auto_fix: bool = True,
        build_docs: bool = True,
        strict: bool = True,
        project_root: str = ".",
        **kwargs: Any,
    ):
        """Initialize the documentation audit workflow.

        Args:
            auto_fix: Apply safe auto-fixable changes (default True).
            build_docs: Run mkdocs build to verify no broken links
                (default True). Skipped gracefully if mkdocs is absent.
            strict: Treat warnings as failures when computing score
                (default True).
            project_root: Root directory of the project to audit.
            **kwargs: Additional arguments passed to BaseWorkflow.

        """
        super().__init__(**kwargs)
        self.auto_fix = auto_fix
        self.build_docs = build_docs
        self.strict = strict
        self.project_root = project_root
        self._audit_score: int = 0

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    async def _audit(
        self, input_data: dict, tier: ModelTier = ModelTier.CHEAP
    ) -> tuple[dict, int, int]:
        """Run all 10 documentation checks and compute a score.

        Checks cover test counts, workflow counts, version consistency,
        broken links, and other documentation accuracy metrics.

        Args:
            input_data: Workflow input dict. May contain "project_root"
                to override the instance default.

        Returns:
            Tuple of (output, input_tokens, output_tokens).
            Output keys: checks (list[dict]), score (int 0-100),
            project_root (str).

        """
        root = input_data.get("project_root", self.project_root)
        results = run_all_checks(root)
        score = self._compute_score(results)
        self._audit_score = score

        serialised = [self._serialise_check(r) for r in results]
        output = {
            "checks": serialised,
            "score": score,
            "project_root": root,
            **input_data,
        }
        input_tokens = estimate_tokens(input_data)
        output_tokens = estimate_tokens(output)
        self.logger.info(
            "doc-audit audit stage complete: score=%d, checks=%d",
            score,
            len(results),
        )
        return output, input_tokens, output_tokens

    async def _plan(
        self, input_data: dict, tier: ModelTier = ModelTier.CAPABLE
    ) -> tuple[dict, int, int]:
        """Generate fix plans for each failing or warning check.

        For each check with status "fail" or "warn", collects metadata
        about the issue and whether it can be auto-fixed.

        Args:
            input_data: Output from the audit stage; must contain "checks".

        Returns:
            Tuple of (output, input_tokens, output_tokens).
            Output keys: fixes (list[dict]), plus all keys from input_data.

        """
        checks = input_data.get("checks", [])
        fixes: list[dict] = []

        for check in checks:
            status = check.get("status", "pass")
            if status not in ("fail", "warn"):
                continue
            fixes.append(
                {
                    "check_id": check["id"],
                    "description": check["details"],
                    "auto_fixable": check.get("auto_fixable", False),
                    "file": check.get("file"),
                }
            )

        output = {
            "fixes": fixes,
            **input_data,
        }
        input_tokens = estimate_tokens(input_data)
        output_tokens = estimate_tokens(output)
        self.logger.info("doc-audit plan stage complete: %d fix(es) planned", len(fixes))
        return output, input_tokens, output_tokens

    async def _execute(
        self, input_data: dict, tier: ModelTier = ModelTier.CAPABLE
    ) -> tuple[dict, int, int]:
        """Apply auto-fixable documentation changes to disk.

        Currently handles updating numeric count badges in README.md
        for test-count, workflow-count, skill-count, and mcp-tool-count.
        Manual-review items are identified but not modified.

        Respects the auto_fix instance flag; if False, no changes
        are applied.

        Args:
            input_data: Output from the plan stage.

        Returns:
            Tuple of (output, input_tokens, output_tokens).
            Output keys: applied (int), manual (int),
            files_modified (list[str]), plus all keys from input_data.

        """
        fixes = input_data.get("fixes", [])
        checks: list[dict] = input_data.get("checks", [])
        root = Path(input_data.get("project_root", self.project_root))

        # Index checks by id for quick lookup
        checks_by_id: dict[str, dict] = {c["id"]: c for c in checks}

        applied = 0
        manual = 0
        files_modified: list[str] = []

        if not self.auto_fix:
            manual = len([f for f in fixes if f.get("auto_fixable")])
            output = {
                "applied": 0,
                "manual": manual,
                "files_modified": [],
                **input_data,
            }
            return output, estimate_tokens(input_data), 0

        for fix in fixes:
            if not fix.get("auto_fixable", False):
                manual += 1
                continue

            check_id = fix["check_id"]
            modified = self._apply_count_fix(check_id, checks_by_id, root)
            if modified:
                applied += 1
                if modified not in files_modified:
                    files_modified.append(modified)
            else:
                manual += 1

        output = {
            "applied": applied,
            "manual": manual,
            "files_modified": files_modified,
            **input_data,
        }
        input_tokens = estimate_tokens(input_data)
        output_tokens = estimate_tokens(output)
        self.logger.info(
            "doc-audit execute stage: applied=%d, manual=%d, files=%s",
            applied,
            manual,
            files_modified,
        )
        return output, input_tokens, output_tokens

    async def _verify(
        self, input_data: dict, tier: ModelTier = ModelTier.CHEAP
    ) -> tuple[dict, int, int]:
        """Re-run all checks and compare before/after scores.

        Optionally runs mkdocs build to verify documentation builds
        without errors. Includes all check results from both audit rounds.

        Args:
            input_data: Output from the execute stage.

        Returns:
            Tuple of (output, input_tokens, output_tokens).
            Output keys: before_score (int), after_score (int),
            improved (bool), mkdocs_build (bool|None),
            after_checks (list[dict]), plus all keys from input_data.

        """
        root = input_data.get("project_root", self.project_root)
        before_score = input_data.get("score", self._audit_score)

        after_results = run_all_checks(root)
        after_score = self._compute_score(after_results)

        mkdocs_result: bool | None = None
        if self.build_docs:
            mkdocs_result = self._run_mkdocs_build(root)

        output = {
            "before_score": before_score,
            "after_score": after_score,
            "improved": after_score >= before_score,
            "mkdocs_build": mkdocs_result,
            "after_checks": [self._serialise_check(r) for r in after_results],
            **input_data,
        }
        input_tokens = estimate_tokens(input_data)
        output_tokens = estimate_tokens(output)
        self.logger.info(
            "doc-audit verify stage: before=%d, after=%d, mkdocs=%s",
            before_score,
            after_score,
            mkdocs_result,
        )
        return output, input_tokens, output_tokens

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_score(self, results: list[CheckResult]) -> int:
        """Compute a 0-100 documentation health score.

        Calculated as (passed_checks / total_checks) * 100.
        In strict mode, warnings count as failures.

        Args:
            results: List of CheckResult objects.

        Returns:
            Integer score 0-100, or 100 if results is empty.

        """
        if not results:
            return 100
        passed = sum(
            1 for r in results if r.status == "pass" or (not self.strict and r.status == "warn")
        )
        return int(passed / len(results) * 100)

    @staticmethod
    def _serialise_check(result: CheckResult) -> dict:
        """Convert a CheckResult dataclass to a JSON-serializable dict.

        Args:
            result: CheckResult instance.

        Returns:
            Dict with keys: id, name, status, details, file, line,
            auto_fixable.

        """
        return {
            "id": result.id,
            "name": result.name,
            "status": result.status,
            "details": result.details,
            "file": result.file,
            "line": result.line,
            "auto_fixable": result.auto_fixable,
        }

    def _apply_count_fix(
        self,
        check_id: str,
        checks_by_id: dict[str, dict],
        root: Path,
    ) -> str | None:
        """Update numeric count badges in README.md.

        Supports: test-count, workflow-count, skill-count, mcp-tool-count.
        Extracts the actual count from the check details and replaces
        the stale badge value with the correct one using regex.

        Args:
            check_id: The check identifier (e.g. "test-count").
            checks_by_id: Dict of check data keyed by check id.
            root: Project root Path.

        Returns:
            Path to README.md if modified, None if no change was made
            or file does not exist.

        """
        readme_path = root / "README.md"
        if not readme_path.exists():
            return None

        check = checks_by_id.get(check_id, {})
        details = check.get("details", "")

        # Extract "actual N" from details like
        # "README badge says 100 tests but pytest collected 146."
        actual_match = re.search(r"(\d+)[^\d]*$", details)
        if not actual_match:
            return None
        actual = actual_match.group(1)

        # Map check id to replacement patterns
        patterns = {
            "test-count": (
                r"(tests[-_]?)(\d+)([-_])",
                lambda m: f"{m.group(1)}{actual}{m.group(3)}",
            ),
            "workflow-count": (
                r"(\d+)(\s+workflows?\b)",
                lambda m: f"{actual}{m.group(2)}",
            ),
            "skill-count": (
                r"(\d+)(\s+(?:skills?|commands?)\b)",
                lambda m: f"{actual}{m.group(2)}",
            ),
            "mcp-tool-count": (
                r"(\d+)(\s+MCP\s+tools?\b)",
                lambda m: f"{actual}{m.group(2)}",
            ),
        }

        if check_id not in patterns:
            return None

        pattern, repl = patterns[check_id]
        try:
            content = readme_path.read_text(encoding="utf-8")
            new_content, n_subs = re.subn(pattern, repl, content, flags=re.IGNORECASE)
            if n_subs == 0 or new_content == content:
                return None
            readme_path.write_text(new_content, encoding="utf-8")
            return str(readme_path)
        except OSError as e:
            self.logger.warning("Could not update README.md: %s", e)
            return None

    def _run_mkdocs_build(self, project_root: str) -> bool | None:
        """Run mkdocs build to verify documentation completeness.

        Builds the documentation site in a temporary directory with
        strict mode enabled to catch missing references.

        Args:
            project_root: Root directory of the project.

        Returns:
            True if build succeeded, False if it failed (exit code != 0),
            None if mkdocs is not installed.

        """
        import subprocess
        import tempfile

        try:
            with tempfile.TemporaryDirectory(prefix="doc-audit-site-") as tmpdir:
                result = subprocess.run(
                    ["mkdocs", "build", "--strict", "--site-dir", tmpdir],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=project_root,
                )
            return result.returncode == 0
        except FileNotFoundError:
            self.logger.info("mkdocs not installed; skipping build check.")
            return None
        except (subprocess.TimeoutExpired, OSError) as e:
            self.logger.warning("mkdocs build failed: %s", e)
            return False
