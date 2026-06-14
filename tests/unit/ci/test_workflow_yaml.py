"""Tests validating GitHub Actions workflow YAML files and pytest configuration.

These tests enforce CI/CD guardrails: timeouts, concurrency controls,
SHA-pinned actions, pip caching, coverage thresholds, mypy blocking,
and pytest config correctness.
"""

import re
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Data loading (module-level for pytest.mark.parametrize)
# ---------------------------------------------------------------------------

WORKFLOWS_DIR = Path(__file__).resolve().parents[3] / ".github" / "workflows"


def _load_all_workflows() -> dict[str, dict]:
    """Load and parse all workflow YAML files."""
    workflows = {}
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        with open(path, encoding="utf-8") as f:
            workflows[path.name] = yaml.safe_load(f)
    return workflows


def _collect_all_jobs() -> list[tuple[str, str, dict]]:
    """Collect (workflow_file, job_id, job_dict) for every job."""
    result = []
    for filename, workflow in ALL_WORKFLOWS.items():
        jobs = workflow.get("jobs", {})
        for job_id, job_dict in jobs.items():
            result.append((filename, job_id, job_dict))
    return result


def _collect_all_uses() -> list[tuple[str, str, int, str]]:
    """Collect (workflow_file, job_id, step_idx, uses_value) for every uses: directive."""
    result = []
    for filename, workflow in ALL_WORKFLOWS.items():
        jobs = workflow.get("jobs", {})
        for job_id, job_dict in jobs.items():
            for idx, step in enumerate(job_dict.get("steps", [])):
                if "uses" in step:
                    result.append((filename, job_id, idx, step["uses"]))
    return result


ALL_WORKFLOWS = _load_all_workflows()
ALL_JOBS = _collect_all_jobs()
ALL_USES = _collect_all_uses()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKFLOWS_REQUIRING_CONCURRENCY = {
    "tests.yml",
    "pre-commit.yml",
    # codeql.yml removed post-v6.3.0 — GitHub's default CodeQL
    # setup owns code-scanning for this repo; the custom
    # workflow couldn't upload SARIF while default setup was
    # enabled. Left the lesson intact for future repos.
    "docs.yml",
    "security.yml",
    "security-scan.yml",
    "tier-pattern-analysis.yml",
}

WORKFLOWS_FORBIDDING_CONCURRENCY = {
    "release.yml",
    "publish-pypi.yml",
}

# setup-python steps that intentionally skip pip caching (minimal deps)
PIP_CACHE_EXCEPTIONS = {
    ("tests.yml", "platform-compat"),
    ("tests.yml", "build"),
}

SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


# ===========================================================================
# 1. Schema Validation
# ===========================================================================


class TestSchemaValidation:
    """Every workflow file must be valid YAML with required top-level keys."""

    def test_all_workflow_files_are_valid_yaml(self):
        """Every .yml file in .github/workflows/ must parse as valid YAML."""
        yml_files = list(WORKFLOWS_DIR.glob("*.yml"))
        assert len(yml_files) >= 10, f"Expected >= 10 workflow files, found {len(yml_files)}"

        for path in yml_files:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert isinstance(data, dict), f"{path.name} did not parse as a YAML mapping"

    @pytest.mark.parametrize(
        "filename, workflow",
        ALL_WORKFLOWS.items(),
        ids=ALL_WORKFLOWS.keys(),
    )
    def test_all_workflows_have_required_keys(self, filename, workflow):
        """Every workflow must have 'name', 'on', and 'jobs' top-level keys."""
        assert "name" in workflow, f"{filename} missing 'name'"
        # PyYAML parses bare `on:` as Python True
        assert "on" in workflow or True in workflow, f"{filename} missing 'on' trigger"
        assert "jobs" in workflow, f"{filename} missing 'jobs'"

    @pytest.mark.parametrize(
        "filename, workflow",
        ALL_WORKFLOWS.items(),
        ids=ALL_WORKFLOWS.keys(),
    )
    def test_all_workflows_have_nonempty_name(self, filename, workflow):
        """Every workflow 'name' must be a non-empty string."""
        name = workflow["name"]
        assert isinstance(name, str) and len(name) > 0, f"{filename} has empty/invalid name"


# ===========================================================================
# 2. Timeout Enforcement
# ===========================================================================


class TestTimeoutEnforcement:
    """Every job must declare a reasonable timeout-minutes."""

    @pytest.mark.parametrize(
        "workflow_file, job_id, job_dict",
        ALL_JOBS,
        ids=[f"{wf}:{jid}" for wf, jid, _ in ALL_JOBS],
    )
    def test_every_job_has_timeout(self, workflow_file, job_id, job_dict):
        """Every job must have 'timeout-minutes' set."""
        assert "timeout-minutes" in job_dict, f"{workflow_file}:{job_id} missing timeout-minutes"

    @pytest.mark.parametrize(
        "workflow_file, job_id, job_dict",
        ALL_JOBS,
        ids=[f"{wf}:{jid}" for wf, jid, _ in ALL_JOBS],
    )
    def test_timeout_values_are_reasonable(self, workflow_file, job_id, job_dict):
        """Job timeouts must be between 1 and 75 minutes."""
        timeout = job_dict.get("timeout-minutes")
        if timeout is not None:
            assert (
                1 <= timeout <= 75
            ), f"{workflow_file}:{job_id} timeout={timeout} outside 1-75 range"


# ===========================================================================
# 3. Concurrency Controls
# ===========================================================================


class TestConcurrencyControls:
    """PR/push workflows need concurrency; release/publish must not cancel."""

    @pytest.mark.parametrize("filename", sorted(WORKFLOWS_REQUIRING_CONCURRENCY))
    def test_expected_workflows_have_concurrency(self, filename):
        """PR/push workflows must define a concurrency group with cancel-in-progress."""
        workflow = ALL_WORKFLOWS[filename]
        assert "concurrency" in workflow, f"{filename} missing concurrency block"
        conc = workflow["concurrency"]
        assert "group" in conc, f"{filename} concurrency missing 'group'"
        assert (
            conc.get("cancel-in-progress") is True
        ), f"{filename} concurrency missing cancel-in-progress: true"

    @pytest.mark.parametrize("filename", sorted(WORKFLOWS_FORBIDDING_CONCURRENCY))
    def test_dangerous_workflows_lack_concurrency(self, filename):
        """Release/publish/metrics workflows must not cancel in-progress runs."""
        workflow = ALL_WORKFLOWS[filename]
        conc = workflow.get("concurrency", {})
        assert (
            conc.get("cancel-in-progress") is not True
        ), f"{filename} must not have cancel-in-progress (dangerous to interrupt)"


# ===========================================================================
# 4. SHA Pinning
# ===========================================================================


class TestSHAPinning:
    """All action references must use full commit SHAs, not mutable tags."""

    @pytest.mark.parametrize(
        "workflow_file, job_id, step_idx, uses_value",
        ALL_USES,
        ids=[f"{wf}:{jid}:step{idx}" for wf, jid, idx, _ in ALL_USES],
    )
    def test_all_uses_directives_are_sha_pinned(self, workflow_file, job_id, step_idx, uses_value):
        """All 'uses' action references must use a 40-char SHA, not a mutable tag."""
        if uses_value.startswith("./"):
            pytest.skip("Local action, no SHA needed")

        parts = uses_value.split("@", 1)
        assert len(parts) == 2, f"No @ in uses: {uses_value}"
        ref = parts[1].split()[0]  # strip trailing comment
        assert SHA_PATTERN.fullmatch(
            ref,
        ), f"{workflow_file}:{job_id} step {step_idx} uses mutable ref: {uses_value}"

    @pytest.mark.parametrize("filename", sorted(ALL_WORKFLOWS.keys()))
    def test_sha_pinned_actions_have_version_comment(self, filename):
        """SHA-pinned actions should include a version comment for readability."""
        path = WORKFLOWS_DIR / filename
        text = path.read_text(encoding="utf-8")
        for line_num, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith("uses:"):
                continue
            uses_value = stripped.split("uses:", 1)[1].strip()
            if uses_value.startswith("./"):
                continue
            if "@" in uses_value and SHA_PATTERN.search(uses_value):
                assert (
                    "#" in uses_value
                ), f"{filename}:{line_num} SHA-pinned action missing version comment: {stripped}"


# ===========================================================================
# 5. Pip Caching
# ===========================================================================


class TestPipCaching:
    """setup-python steps should include cache: 'pip' unless excepted."""

    def test_setup_python_steps_have_pip_cache(self):
        """setup-python steps should include cache: 'pip' unless explicitly excepted."""
        missing = []
        for filename, workflow in ALL_WORKFLOWS.items():
            for job_id, job_dict in workflow.get("jobs", {}).items():
                if (filename, job_id) in PIP_CACHE_EXCEPTIONS:
                    continue
                for step in job_dict.get("steps", []):
                    uses = step.get("uses", "")
                    if "setup-python" in uses:
                        cache = step.get("with", {}).get("cache")
                        if cache != "pip":
                            missing.append(f"{filename}:{job_id}")
        assert not missing, f"setup-python steps missing cache: 'pip': {missing}"

    def test_pip_cache_exceptions_are_valid(self):
        """Every pip cache exception must correspond to a real setup-python step."""
        for filename, job_id in PIP_CACHE_EXCEPTIONS:
            workflow = ALL_WORKFLOWS.get(filename)
            assert workflow is not None, f"Exception references missing workflow: {filename}"
            job = workflow.get("jobs", {}).get(job_id)
            assert job is not None, f"Exception references missing job: {filename}:{job_id}"
            has_setup_python = any(
                "setup-python" in step.get("uses", "") for step in job.get("steps", [])
            )
            assert (
                has_setup_python
            ), f"Exception {filename}:{job_id} has no setup-python step (stale exception)"


# ===========================================================================
# 6. Coverage Threshold
# ===========================================================================


class TestCoverageThreshold:
    """tests.yml must enforce a minimum coverage threshold."""

    def test_coverage_threshold_is_at_least_80(self):
        """tests.yml must enforce a coverage threshold >= 80% in *some* job.

        Accepts either form:
        - ``pytest --cov-fail-under=N`` (pytest-cov syntax)
        - ``coverage report --fail-under=N`` (coverage.py canonical syntax)

        Coverage may live in the matrix ``test`` job or in a dedicated
        ``coverage`` job — the policy is "tests.yml must enforce a
        threshold somewhere," not "must be in the matrix step." Searching
        all jobs lets us split coverage into its own job (e.g. to keep
        the matrix memory-disciplined) without losing the gate test.
        """
        workflow = ALL_WORKFLOWS["tests.yml"]

        gate_step = None
        gate_pattern = None
        for _job_name, job in workflow["jobs"].items():
            for step in job.get("steps", []):
                run_cmd = step.get("run", "") or ""
                for pattern in (r"--cov-fail-under=(\d+)", r"--fail-under=(\d+)"):
                    if re.search(pattern, run_cmd):
                        gate_step = step
                        gate_pattern = pattern
                        break
                if gate_step:
                    break
            if gate_step:
                break

        assert gate_step is not None, (
            "tests.yml has no coverage threshold gate in any job "
            "(expected --cov-fail-under= or --fail-under= in either the "
            "matrix test job or a dedicated coverage job)"
        )

        match = re.search(gate_pattern, gate_step["run"])
        threshold = int(match.group(1))
        assert threshold >= 80, f"Coverage threshold is {threshold}%, expected >= 80%"


# ===========================================================================
# 7. MyPy Blocking
# ===========================================================================


class TestMyPyBlocking:
    """The mypy step must block the build — no continue-on-error or || true."""

    @pytest.mark.skip(reason="mypy removed from CI in v3.6.6 — re-enable after type-hint sprint")
    def test_mypy_step_is_blocking(self):
        """The mypy step in the lint job must not suppress failures."""
        workflow = ALL_WORKFLOWS["tests.yml"]
        lint_job = workflow["jobs"]["lint"]

        mypy_step = None
        for step in lint_job["steps"]:
            if "mypy" in step.get("run", "").lower() or "mypy" in step.get("name", "").lower():
                mypy_step = step
                break

        assert mypy_step is not None, "tests.yml:lint has no mypy step"
        assert (
            mypy_step.get("continue-on-error") is not True
        ), "mypy step must not have continue-on-error: true"
        run_cmd = mypy_step.get("run", "")
        assert "|| true" not in run_cmd, "mypy run command must not use '|| true'"
        assert "|| exit 0" not in run_cmd, "mypy run command must not use '|| exit 0'"


# ===========================================================================
# 8. Pytest Config Correctness
# ===========================================================================

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PYTEST_INI = _REPO_ROOT / "pytest.ini"
_TESTS_DIR = _REPO_ROOT / "tests"


class TestPytestConfig:
    """Catch pytest.ini mistakes that silently discard test coverage."""

    # Exclusions that intentionally block real test dirs — document the reason here
    # so the test stays green and the intent is explicit.
    # (Currently empty — JWT_SECRET_KEY is now in .env so tests/backend/ collects fine.)
    _INTENTIONAL_EXCLUSIONS: set[str] = set()

    def test_norecursedirs_does_not_exclude_real_test_dirs(self):
        """No *undocumented* norecursedirs pattern should match a non-empty test dir.

        The 'wizards' entry previously matched tests/unit/wizards/ and silently
        excluded 451 tests from every CI run.  This test catches new accidents.
        Add to _INTENTIONAL_EXCLUSIONS (with a reason comment) for any dir that
        genuinely cannot be collected in the standard CI environment.
        """
        import configparser

        ini = configparser.ConfigParser()
        ini.read(_PYTEST_INI)
        raw = ini.get("pytest", "norecursedirs", fallback="")
        excluded_names = raw.split()

        real_test_dir_names = {
            p.name for p in _TESTS_DIR.rglob("*") if p.is_dir() and any(p.iterdir())
        }

        unexpected = [
            name
            for name in excluded_names
            if name in real_test_dir_names
            and "*" not in name
            and name != "__pycache__"
            and name not in self._INTENTIONAL_EXCLUSIONS
        ]

        assert not unexpected, (
            f"norecursedirs entries match non-empty test directories: {unexpected}. "
            f"This silently excludes tests from collection. Either remove the entry, "
            f"use an anchored pattern (/name), or add it to "
            f"TestPytestConfig._INTENTIONAL_EXCLUSIONS with a reason comment."
        )


# ===========================================================================
# 9. Hang-watchdog dump capture (ci-runner-hang Phase 2)
# ===========================================================================


class TestHangDumpCapture:
    """The pytest lanes that wedge must upload the watchdog's hang dumps.

    The conftest watchdog (Phase 1) writes each process's all-thread stack
    to ``hang-dumps/hang-<worker>.txt``. Phase 2's whole point is that a
    worker dump SURVIVES a ``timeout-minutes`` kill — which only works if
    the job has an ``if: always()`` step that uploads ``hang-dumps/``.
    Without this guard the capture step can be silently dropped in a future
    ``tests.yml`` edit, re-opening the gap that lost the run-27488685349
    stack. Guards the two `-n auto` lanes where the hang was observed.
    """

    LANES = ("test", "coverage")

    @pytest.mark.parametrize("job_id", LANES)
    def test_lane_uploads_hang_dumps_always(self, job_id):
        """The test/coverage job must upload hang-dumps/ with if: always()."""
        job = ALL_WORKFLOWS["tests.yml"]["jobs"][job_id]
        upload = None
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            path = step.get("with", {}).get("path", "") or ""
            if "upload-artifact" in uses and "hang-dumps" in path:
                upload = step
                break
        assert upload is not None, (
            f"tests.yml:{job_id} has no step uploading hang-dumps/ — a wedged "
            f"worker's faulthandler dump would be lost on the timeout kill "
            f"(ci-runner-hang Phase 2 regression)."
        )
        # `always()` is what makes the dump survive a timeout-minutes cancel.
        assert "always()" in str(upload.get("if", "")), (
            f"tests.yml:{job_id} hang-dumps upload must run with "
            f"`if: always()` (else it is skipped when the job times out)."
        )
