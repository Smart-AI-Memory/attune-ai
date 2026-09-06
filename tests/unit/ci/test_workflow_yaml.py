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
    "changelog-gate.yml",
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


@pytest.mark.parametrize(
    "filename,job_id",
    [
        ("tests.yml", "test"),
        ("tests.yml", "clock-tz"),
        ("tests.yml", "coverage"),
        ("integration-tests.yml", "integration"),
    ],
)
def test_tokenizer_data_is_prepared_before_isolated_pytest(filename, job_id):
    job = ALL_WORKFLOWS[filename]["jobs"][job_id]
    cache_dir = "${{ github.workspace }}/../tiktoken-cache"
    assert job["env"]["TIKTOKEN_CACHE_DIR"] == cache_dir
    steps = job["steps"]
    caches = [step for step in steps if step.get("name") == "Cache tiktoken encodings"]
    warmups = [step for step in steps if step.get("name") == "Warm tiktoken encoding"]
    assert len(caches) == len(warmups) == 1
    cache, warm = caches[0], warmups[0]
    assert cache["with"]["path"] == cache_dir
    assert "tiktoken.get_encoding('cl100k_base')" in warm["run"]
    assert "||" not in warm["run"] and not warm.get("continue-on-error", False)
    pytest_steps = [i for i, step in enumerate(steps) if "pytest " in step.get("run", "")]
    assert pytest_steps
    assert steps.index(cache) < steps.index(warm) < min(pytest_steps)


# ===========================================================================
# 1. Schema Validation
# ===========================================================================


class TestSchemaValidation:
    """Every workflow file must be valid YAML with required top-level keys."""

    def test_job_environment_does_not_use_runner_context(self):
        """Runner context exists in steps, but GitHub rejects it in job env."""
        for filename, workflow in ALL_WORKFLOWS.items():
            for job_id, job in workflow.get("jobs", {}).items():
                for name, value in job.get("env", {}).items():
                    for expression in re.findall(r"\$\{\{(.*?)\}\}", str(value), re.S):
                        assert not re.search(
                            r"\brunner\.", expression
                        ), f"{filename}:{job_id}:env:{name}: runner context unavailable"

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
    # (Currently empty — no test dir is intentionally excluded.)
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


# ===========================================================================
# 10. Dynamic matrix required-lane invariant (ci-matrix-right-sizing)
# ===========================================================================


class TestDynamicMatrixRequiredLane:
    """Every matrix variant must keep the required ``ubuntu-3.12`` lane.

    The ``setup-matrix`` job emits a FULL matrix for source/packaging
    diffs and a SLIM matrix for tests/docs-only diffs (D1/D2 in
    docs/specs/ci-matrix-right-sizing/). GitHub matches required status
    checks by job name *including* matrix params, so the merge gate is the
    exact lane ``test (ubuntu-latest, 3.12)``. If ANY variant of the
    matrix drops ``ubuntu-latest`` or ``3.12``, that variant never emits
    the required check name → the PR is blocked forever ("required check
    stays missing"). This guard parses both JSON variants straight out of
    the workflow and asserts the cartesian product yields the required
    lane in every case.
    """

    REQUIRED_OS = "ubuntu-latest"
    REQUIRED_PY = "3.12"

    @staticmethod
    def _matrix_variants() -> list[dict]:
        """Extract every ``matrix={...}`` JSON blob from setup-matrix."""
        import json

        job = ALL_WORKFLOWS["tests.yml"]["jobs"]["setup-matrix"]
        blobs: list[dict] = []
        for step in job.get("steps", []):
            run_cmd = step.get("run", "") or ""
            for match in re.finditer(r"matrix=(\{.*?\})", run_cmd):
                blobs.append(json.loads(match.group(1)))
        return blobs

    def test_both_matrix_variants_are_emitted(self):
        """setup-matrix must define exactly the full and slim variants."""
        variants = self._matrix_variants()
        assert len(variants) == 2, (
            "Expected 2 matrix variants (full + slim) in setup-matrix; "
            f"found {len(variants)}. The dynamic-matrix design "
            "(ci-matrix-right-sizing) emits one JSON per src=true/false branch."
        )

    @pytest.mark.parametrize("variant_idx", [0, 1])
    def test_variant_keeps_required_lane(self, variant_idx):
        """Each matrix variant must include the required ubuntu-3.12 lane."""
        variant = self._matrix_variants()[variant_idx]
        oses = variant.get("os", [])
        pys = [str(p) for p in variant.get("python-version", [])]
        assert self.REQUIRED_OS in oses, (
            f"matrix variant {variant} drops {self.REQUIRED_OS!r} — the "
            f"required check `test ({self.REQUIRED_OS}, {self.REQUIRED_PY})` "
            "would never emit and the PR would be blocked forever."
        )
        assert self.REQUIRED_PY in pys, (
            f"matrix variant {variant} drops Python {self.REQUIRED_PY!r} — the "
            f"required check `test ({self.REQUIRED_OS}, {self.REQUIRED_PY})` "
            "would never emit and the PR would be blocked forever."
        )


# ---------------------------------------------------------------------------
# auto-merge-safe.yml — Class 2 "when-green" invariants (archive spec D8)
#
# The opt-in class arms GitHub NATIVE auto-merge for a human-labeled
# PR. Invariants: the job exists, fires on label lifecycle events, is
# gated on the owner + the exact label name, re-verifies the path
# carve-out via the guard's when-green mode, disarms on unlabeled,
# and NEVER uses an admin bypass (branch protection stays enforced).
# ---------------------------------------------------------------------------


class TestAutoMergeWhenGreen:
    """Drift guard for the opt-in auto-merge-when-green class."""

    WF = "auto-merge-safe.yml"
    JOB = "when-green"

    @staticmethod
    def _workflow() -> dict:
        return ALL_WORKFLOWS["auto-merge-safe.yml"]

    @classmethod
    def _trigger_types(cls) -> list[str]:
        wf = cls._workflow()
        # YAML 1.1 parses a bare `on:` key as boolean True.
        trigger = wf.get("on") or wf.get(True)
        return trigger["pull_request_target"]["types"]

    @classmethod
    def _job(cls) -> dict:
        return cls._workflow()["jobs"][cls.JOB]

    @classmethod
    def _run_text(cls) -> str:
        return "\n".join(step.get("run", "") or "" for step in cls._job().get("steps", []))

    def test_when_green_job_exists(self):
        assert self.JOB in self._workflow()["jobs"], (
            "auto-merge-safe.yml must define the `when-green` job "
            "(Class 2, opt-in label — archive spec D8)."
        )

    def test_label_lifecycle_triggers_present(self):
        types = self._trigger_types()
        for needed in ("labeled", "unlabeled", "synchronize"):
            assert needed in types, (
                f"pull_request_target types must include {needed!r}: labeled "
                "arms, unlabeled disarms, synchronize re-verifies the class "
                "after every push (stranded-follow-ups defense)."
            )

    def test_job_gated_on_owner_and_label_name(self):
        cond = self._job().get("if", "")
        assert "silversurfer562" in cond
        assert "auto-merge-when-green" in cond

    def test_uses_native_auto_merge_never_admin(self):
        run_text = self._run_text()
        assert "--auto" in run_text, "when-green must arm GitHub native auto-merge"
        assert "--admin" not in run_text, (
            "the when-green class must NEVER admin-bypass branch protection — "
            "full-green enforcement by GitHub is the whole design (D8)."
        )

    def test_reverifies_path_class_with_when_green_mode(self):
        assert "auto_merge_guard.py --mode when-green" in self._run_text(), (
            "the job must re-verify the .github/ carve-out via the guard's "
            "when-green mode before arming (label = necessary, not sufficient)."
        )

    def test_disarms_on_unlabeled(self):
        assert "--disable-auto" in self._run_text(), (
            "removing the label must disarm native auto-merge, or a stripped "
            "label would still merge."
        )

    def test_class1_merge_job_untouched(self):
        # Regression guard: adding Class 2 must not remove Class 1's jobs.
        jobs = self._workflow()["jobs"]
        assert "label" in jobs and "merge" in jobs


# ---------------------------------------------------------------------------
# auto-merge-safe.yml — chair-read gate (incident 2026-08-10, PR #2043)
#
# A PR deliberately opened for a chair read (marked by "(chair-read)"
# in the title or a `chair-read` label) must NEVER be auto-labeled or
# auto-merged by the Class-1 lane. #2043 carried the title marker only
# socially — the auto-labeler applied `auto-merge-safe` and the lane
# merged it ~1.7h before the chair's authorization. These tests pin the
# mechanical skip in BOTH jobs (label = necessary, not sufficient — the
# merge job re-verifies independently, matching the path-class design).
#
# Class 2 (`when-green`) is deliberately NOT gated: per D10 the chair's
# "merge N" authorization is executed by applying the
# `auto-merge-when-green` label to a still-chair-read-titled PR, so the
# marker must not block that lane.
# ---------------------------------------------------------------------------


class TestAutoMergeChairReadGate:
    """Drift guard: chair-read PRs are out of the Class-1 auto-merge lane."""

    TITLE_MARKER = "(chair-read)"
    LABEL_NAME = "chair-read"

    @staticmethod
    def _job(job_id: str) -> dict:
        return ALL_WORKFLOWS["auto-merge-safe.yml"]["jobs"][job_id]

    @classmethod
    def _run_text(cls, job_id: str) -> str:
        return "\n".join(step.get("run", "") or "" for step in cls._job(job_id).get("steps", []))

    def test_label_job_checks_title_marker(self):
        assert self.TITLE_MARKER in self._run_text("label"), (
            "the label job must skip PRs whose title contains "
            f"{self.TITLE_MARKER!r} — without this the auto-labeler puts "
            "chair-read PRs into the Class-1 merge lane (#2043 incident)."
        )

    def test_label_job_checks_chair_read_label(self):
        # The label check rides in via the CHAIR_LABELED env expression.
        step_envs = "\n".join(
            str(step.get("env", "")) for step in self._job("label").get("steps", [])
        )
        assert self.LABEL_NAME in step_envs or self.LABEL_NAME in self._run_text("label"), (
            "the label job must also honor a `chair-read` LABEL, so the "
            "gate works even when a title omits the marker."
        )

    def test_merge_job_reverifies_chair_read_independently(self):
        run_text = self._run_text("merge")
        assert self.TITLE_MARKER in run_text and self.LABEL_NAME in run_text, (
            "the merge job must re-verify the chair-read marker (title AND "
            "label) independent of the label job — label is necessary, not "
            "sufficient, same as the path-class re-check."
        )

    def test_merge_job_chair_read_skip_is_fail_closed(self):
        assert '"$chair_read" != "false"' in self._run_text("merge"), (
            "the merge job's chair-read skip must be fail-closed: anything "
            'but a clean "false" (including a jq error) skips the merge.'
        )

    def test_when_green_job_not_gated_on_chair_read(self):
        # D10: the chair's "merge N" is executed by labeling a PR that
        # still carries "(chair-read)" in its title. Gating Class 2 on
        # the marker would break the authorized merge path.
        assert self.TITLE_MARKER not in self._run_text("when-green"), (
            "when-green must NOT skip chair-read PRs — applying "
            "`auto-merge-when-green` after the read IS the chair's "
            "authorized merge mechanism (D10)."
        )


def test_contributing_smoke_prepares_tokenizer_before_guarded_pytest():
    job = ALL_WORKFLOWS["contributing-smoke.yml"]["jobs"]["clean-venv-smoke"]
    steps = job["steps"]
    warm = next(step for step in steps if step.get("name") == "Warm tiktoken encoding")
    execute = next(
        step for step in steps if step.get("name", "").startswith("Execute the documented")
    )
    cache = next(step for step in steps if step.get("name") == "Cache tiktoken encodings")
    assert steps.index(cache) < steps.index(warm) < steps.index(execute)
    assert job["env"]["TIKTOKEN_CACHE_DIR"] == cache["with"]["path"]
    assert "python -m pip install tiktoken" in warm["run"]
    assert "tiktoken.get_encoding('cl100k_base')" in warm["run"]
    assert "||" not in warm["run"] and not warm.get("continue-on-error")
    assert execute["env"]["ANTHROPIC_API_KEY"] == ""
    assert execute["run"] == 'bash "$RUNNER_TEMP/contributing-setup.sh"'
