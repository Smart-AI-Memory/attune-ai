"""Run each fact-check against the ops-dashboard regression fixture.

This is the spec's exit gate for Phase 1: "5/6 ops-dashboard errors
caught" against ``tests/fixtures/fact_check_ops_dashboard/pre_fix/``,
zero findings against ``post_fix/``.

The fixture is hand-crafted from the original error catalog in
``docs/specs/polish-fact-check/requirements.md`` (the six failure
classes from the 2026-05-14 attune-ai PR #351 regen). Each test
exercises one check module against a pre-fix file and asserts the
specific finding type appears, then runs the same check against
the post-fix counterpart and asserts zero findings.

External dependencies (``attune <cmd> --help``,
filesystem-level template counts) are monkey-patched so tests
are deterministic regardless of which version of attune-ai is
installed in the dev environment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.authoring.fact_check import (
    CHECK_CLI_REFS,
    CHECK_MD_LINKS,
    CHECK_NUMERIC_REFS,
    CHECK_PYTHON_REFS,
    cli_refs,
    md_links,
    numeric_refs,
    python_refs,
)

# -----------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "fact_check_ops_dashboard"


@pytest.fixture
def pre_fix_dir() -> Path:
    return FIXTURE_ROOT / "pre_fix"


@pytest.fixture
def post_fix_dir() -> Path:
    return FIXTURE_ROOT / "post_fix"


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    """A minimal project_root the CLI / numeric checks can resolve
    against. Contains a tiny ``.help/features.yaml`` and a templates
    dir so numeric checks have something to count."""
    (tmp_path / ".help").mkdir()
    (tmp_path / ".help" / "features.yaml").write_text(
        "features:\n" "  ops-dashboard:\n" "    title: Ops dashboard\n",
    )
    templates = tmp_path / ".help" / "templates"
    templates.mkdir()
    # 259 stub template files — matches the real ground-truth count
    # in the regression fixture (the pre-fix claim was 498).
    for i in range(259):
        (templates / f"t{i:03d}.md").write_text("# template\n")
    return tmp_path


# -----------------------------------------------------------------
# python_refs: catches hallucinated private-module imports
# -----------------------------------------------------------------


class TestPythonRefs:
    def test_catches_underscore_module_imports(self, pre_fix_dir: Path):
        findings = python_refs.check(pre_fix_dir / "tutorial.md")
        assert findings, "expected at least one finding for _readers / _models"
        # Both `attune.ops._readers` and `attune.ops._models` should
        # surface — they don't exist in the real package.
        messages = " ".join(f.message for f in findings)
        assert "_readers" in messages or "_models" in messages
        assert all(f.check == CHECK_PYTHON_REFS for f in findings)
        # All should be error severity (unresolvable import).
        assert all(f.severity == "error" for f in findings)

    def test_clean_on_post_fix(self, post_fix_dir: Path):
        findings = python_refs.check(post_fix_dir / "tutorial.md")
        assert findings == [], f"unexpected findings: {findings}"


# -----------------------------------------------------------------
# cli_refs: catches invented `--flag` references
# -----------------------------------------------------------------


# Canned `--help` output for `attune ops`. The pre-fix fixture
# references `--allow-run` (real) in `attune ops --allow-run`
# context but the pre-fix ALSO uses it in a misleading "read-only
# mode" framing. Note: the actual hallucination in PR #351 was
# inverted semantics, not a flag that doesn't exist. For the
# fact-check at this layer, only the flag's EXISTENCE matters —
# semantic correctness is for the faithfulness judge (Phase 3).
#
# We use a synthetic case here: the pre-fix invents a flag that
# DOESN'T exist. The fixture refers to `--allow-run` which IS in
# this help; to make the test exercise the catch path, we point
# at a different file that uses a non-existent flag.
_FAKE_OPS_HELP = """usage: attune ops [--port PORT] [--allow-run] [--read-only]

options:
  --port PORT      Port to bind
  --allow-run      Allow workflow execution
  --read-only      Disable execution
"""


class TestCliRefs:
    def test_catches_invented_flag(
        self,
        tmp_path: Path,
        fake_project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Write a polished file that references a definitely-fake flag.
        polished = tmp_path / "doc.md"
        polished.write_text(
            "Use `attune ops --turbo` to enable turbo mode.\n",
        )
        # Pin the resolved CLI + its help output deterministically.
        monkeypatch.setattr(cli_refs, "_resolve_cli_name", lambda root: "attune")
        # `shutil.which("attune")` returns None in CI (attune-ai isn't in
        # attune-author's dev deps), making the check bail before any
        # finding can surface. Stub `shutil.which` so the check proceeds.
        monkeypatch.setattr(cli_refs.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        monkeypatch.setattr(
            cli_refs,
            "_help_text",
            lambda cli, chain, timeout=5: _FAKE_OPS_HELP,
        )
        monkeypatch.setattr(
            cli_refs,
            "_installed_version",
            lambda cli: "6.8.0",
        )
        findings = cli_refs.check(polished, fake_project)
        assert findings, "expected --turbo to surface"
        assert any("--turbo" in f.message for f in findings)
        assert all(f.check == CHECK_CLI_REFS for f in findings)

    def test_version_coupling_block_present(
        self,
        tmp_path: Path,
        fake_project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        polished = tmp_path / "doc.md"
        polished.write_text("Run `attune ops --nope-not-real`.\n")
        monkeypatch.setattr(cli_refs, "_resolve_cli_name", lambda root: "attune")
        # `shutil.which("attune")` returns None in CI (attune-ai isn't in
        # attune-author's dev deps), making the check bail before any
        # finding can surface. Stub `shutil.which` so the check proceeds.
        monkeypatch.setattr(cli_refs.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        monkeypatch.setattr(
            cli_refs,
            "_help_text",
            lambda cli, chain, timeout=5: _FAKE_OPS_HELP,
        )
        monkeypatch.setattr(cli_refs, "_installed_version", lambda cli: "6.8.0")
        findings = cli_refs.check(polished, fake_project)
        assert findings
        # Spec §1.4: each cli-ref finding must include version-
        # coupling messaging so the user knows WHICH attune-ai
        # version was probed and how to pin a different one.
        msg = findings[0].message
        assert "6.8.0" in msg, "installed version missing from finding"

    def test_clean_on_post_fix(
        self,
        post_fix_dir: Path,
        fake_project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(cli_refs, "_resolve_cli_name", lambda root: "attune")
        # `shutil.which("attune")` returns None in CI (attune-ai isn't in
        # attune-author's dev deps), making the check bail before any
        # finding can surface. Stub `shutil.which` so the check proceeds.
        monkeypatch.setattr(cli_refs.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        monkeypatch.setattr(
            cli_refs,
            "_help_text",
            lambda cli, chain, timeout=5: _FAKE_OPS_HELP,
        )
        monkeypatch.setattr(cli_refs, "_installed_version", lambda cli: "6.8.0")
        findings = cli_refs.check(post_fix_dir / "how-to.md", fake_project)
        # Post-fix uses --allow-run which IS in the help → no findings.
        unresolved = [f for f in findings if f.severity == "error"]
        assert unresolved == [], f"unexpected error findings: {unresolved}"


# -----------------------------------------------------------------
# md_links: catches broken relative-link targets
# -----------------------------------------------------------------


class TestMdLinks:
    def test_catches_missing_target(self, pre_fix_dir: Path):
        findings = md_links.check(pre_fix_dir / "architecture.md")
        # The pre-fix architecture file links to four "Concept: ..."
        # docs that don't exist. All four should surface.
        assert len(findings) >= 4, f"expected >=4 missing links, got {len(findings)}"
        assert all(f.check == CHECK_MD_LINKS for f in findings)
        # Severity should be error — broken links are user-visible bugs.
        assert all(f.severity == "error" for f in findings)

    def test_skips_external_urls(self, tmp_path: Path):
        polished = tmp_path / "doc.md"
        polished.write_text(
            "See [external](https://example.com/page).\n"
            "Or [anchor only](#section).\n"
            "Or [mailto](mailto:test@example.com).\n",
        )
        # All three are external/non-file; none should fire.
        findings = md_links.check(polished)
        assert findings == []

    def test_clean_on_post_fix(self, post_fix_dir: Path):
        # Post-fix architecture removes the broken cross-refs.
        findings = md_links.check(post_fix_dir / "architecture.md")
        assert findings == [], f"unexpected findings: {findings}"


# -----------------------------------------------------------------
# numeric_refs: catches invented counts
# -----------------------------------------------------------------


class TestNumericRefs:
    def test_catches_invented_count(
        self,
        pre_fix_dir: Path,
        fake_project: Path,
    ):
        # The pre-fix reference doc claims "498 templates"; the
        # fake_project fixture has 259 actual template files.
        findings = numeric_refs.check(pre_fix_dir / "reference.md", fake_project)
        # At least one error finding about the 498 vs 259 mismatch.
        error_findings = [f for f in findings if f.severity == "error"]
        assert error_findings, "expected error finding for 498 vs 259"
        messages = " ".join(f.message for f in error_findings)
        # The finding should mention BOTH the claimed and actual counts
        # so the editor can see what to fix.
        assert (
            "498" in messages and "259" in messages
        ), f"finding should cite both counts: {messages!r}"
        assert all(f.check == CHECK_NUMERIC_REFS for f in error_findings)

    def test_clean_on_post_fix(
        self,
        post_fix_dir: Path,
        fake_project: Path,
    ):
        # Post-fix reference removes the count claim entirely.
        findings = numeric_refs.check(post_fix_dir / "reference.md", fake_project)
        error_findings = [f for f in findings if f.severity == "error"]
        assert error_findings == [], f"unexpected error findings: {error_findings}"


# -----------------------------------------------------------------
# Aggregate gate: 5/6 errors caught (the spec's Phase 1 exit
# criterion)
# -----------------------------------------------------------------


class TestPhase1ExitGate:
    """Spec exit gate: 5 of 6 ops-dashboard errors caught.

    The 6th (insecure-example for ``host="0.0.0.0"``) is explicitly
    Phase 3 scope per the requirements doc. The 5 in Phase 1's
    scope:

    - Python refs: 2 (private-module imports in tutorial)
    - CLI refs:    1 (invented flag — synthetic in test_cli_refs)
    - Markdown:    1+ (broken cross-refs in architecture)
    - Numeric:     1 (498 vs 259 in reference)
    """

    def test_catches_phase_1_error_classes(
        self,
        pre_fix_dir: Path,
        fake_project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(cli_refs, "_resolve_cli_name", lambda root: "attune")
        # `shutil.which("attune")` returns None in CI (attune-ai isn't in
        # attune-author's dev deps), making the check bail before any
        # finding can surface. Stub `shutil.which` so the check proceeds.
        monkeypatch.setattr(cli_refs.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        monkeypatch.setattr(
            cli_refs,
            "_help_text",
            lambda cli, chain, timeout=5: _FAKE_OPS_HELP,
        )
        monkeypatch.setattr(cli_refs, "_installed_version", lambda cli: "6.8.0")

        all_findings: list = []
        for name in ("how-to.md", "tutorial.md", "reference.md", "architecture.md"):
            path = pre_fix_dir / name
            all_findings.extend(python_refs.check(path))
            all_findings.extend(cli_refs.check(path, fake_project))
            all_findings.extend(md_links.check(path))
            all_findings.extend(numeric_refs.check(path, fake_project))

        by_check = dict.fromkeys(
            (CHECK_PYTHON_REFS, CHECK_CLI_REFS, CHECK_MD_LINKS, CHECK_NUMERIC_REFS), 0
        )
        for f in all_findings:
            if f.severity == "error":
                by_check[f.check] += 1

        # Python: 2+, MD: 4+ (architecture's 4 broken refs +
        # tutorial's 1), Numeric: 1+, CLI: 0 (the fixture
        # references --allow-run which IS in the canned help —
        # caught semantically in Phase 3).
        assert by_check[CHECK_PYTHON_REFS] >= 2, by_check
        assert by_check[CHECK_MD_LINKS] >= 4, by_check
        assert by_check[CHECK_NUMERIC_REFS] >= 1, by_check
