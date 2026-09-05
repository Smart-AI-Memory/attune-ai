"""Contract test for the ``/verify`` skill against the installed attune-verify.

``plugin/skills/verify/SKILL.md`` teaches a specific API surface and a
specific report shape: ``verify(content, VerifyContext(...))`` returning
``ok`` / ``checked`` / ``findings``, findings carrying ``kind`` /
``severity`` / ``detail`` / ``evidence`` / ``location``, four
deterministic finding kinds, the ``help_commands`` + ``allowed_help_cmds``
and ``count_sources`` boundary declarations, a WARNING (never a silent
pass) for a flag whose command was not declared, and
``raise_if_failed`` as the opt-in hard gate.

No in-tree module imports attune_verify — the skill drives the Python
API at runtime — so nothing else in the suite would notice a contract
break. The pyproject cap on attune-verify (``<1.0``) is widened per
minor on the strength of "re-validated against the skill's taught
contract at each lock-bump"; this file is that re-validation, replacing
the ad-hoc smoke run used for #2407.

Every fixture below is a form the skill's own text shows the user. If a
test here fails after a lock-bump, either the skill text or the cap is
wrong — fix one of those, never the test, unless the skill text changed
first.
"""

from __future__ import annotations

from pathlib import Path

import pytest

attune_verify = pytest.importorskip("attune_verify")

from attune_verify import (  # noqa: E402  (after importorskip by design)
    FindingKind,
    VerificationError,
    VerifyContext,
    raise_if_failed,
    verify,
)

TAUGHT_KINDS = {"unresolved_import", "unknown_flag", "dead_link", "count_mismatch"}
CHECKED_LAYERS = {"imports", "flags", "links", "counts"}


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / "real.md").write_text("# real\n", encoding="utf-8")
    return tmp_path


def _kinds(result) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for f in result.findings:
        grouped.setdefault(f.kind.value, []).append(f)
    return grouped


class TestTaughtSurface:
    def test_four_deterministic_kinds_exist(self) -> None:
        assert TAUGHT_KINDS <= {k.value for k in FindingKind}

    def test_clean_content_reports_ok_with_all_layers_checked(self, project_root: Path) -> None:
        content = "Run it.\n\n```python\nimport json\n```\n\nSee [real](real.md).\n"
        result = verify(content, VerifyContext(project_root=project_root))
        assert result.ok is True
        assert result.findings == []
        assert set(result.checked) >= CHECKED_LAYERS

    def test_finding_carries_the_five_taught_fields(self, project_root: Path) -> None:
        content = "```python\nimport definitely_not_a_real_pkg_xyz\n```\n"
        result = verify(content, VerifyContext(project_root=project_root))
        (finding,) = result.findings
        # The skill's report shape: kind.value / severity / detail / evidence / location.
        assert finding.kind.value in TAUGHT_KINDS
        assert finding.severity in {"error", "warning"}
        assert isinstance(finding.detail, str) and finding.detail
        assert isinstance(finding.evidence, str) and finding.evidence
        assert finding.location is None or isinstance(finding.location, str)


class TestEachKindIsProducible:
    def test_unresolved_import_is_an_error(self, project_root: Path) -> None:
        content = "```python\nimport definitely_not_a_real_pkg_xyz\nfrom pathlib import Path\n```\n"
        result = verify(content, VerifyContext(project_root=project_root))
        assert result.ok is False
        (finding,) = _kinds(result)["unresolved_import"]
        assert finding.severity == "error"
        assert "definitely_not_a_real_pkg_xyz" in finding.evidence
        assert len(result.findings) == 1, "the real stdlib import must not be flagged"

    def test_dead_link_is_an_error_and_live_link_is_not(self, project_root: Path) -> None:
        content = "See [gone](missing/nope.md) and [real](real.md).\n"
        result = verify(content, VerifyContext(project_root=project_root))
        assert result.ok is False
        (finding,) = _kinds(result)["dead_link"]
        assert finding.severity == "error"
        assert "missing/nope.md" in finding.evidence
        assert len(result.findings) == 1

    def test_unknown_flag_via_help_commands_and_allowlist(self, project_root: Path) -> None:
        # The skill's taught form: pre-captured --help text keyed by command,
        # plus the allow-list of commands it may shell out to.
        ctx = VerifyContext(
            project_root=project_root,
            help_commands={"attune": "usage: attune [--real] [--other]"},
            allowed_help_cmds=frozenset({"attune"}),
        )
        result = verify("Run `attune --bogus-flag` or `attune --real`.\n", ctx)
        assert result.ok is False
        (finding,) = _kinds(result)["unknown_flag"]
        assert finding.severity == "error"
        assert "--bogus-flag" in finding.detail
        assert len(result.findings) == 1, "the real flag must not be flagged"

    def test_undeclared_command_flag_is_a_warning_not_a_silent_pass(
        self, project_root: Path
    ) -> None:
        # Skill text: "A flag whose command is neither pre-captured nor in
        # allowed_help_cmds yields a warning, not a silent pass".
        result = verify("Run `frobnicate --whatever`.\n", VerifyContext(project_root=project_root))
        assert result.ok is True, "a warning must not fail the result"
        (finding,) = _kinds(result)["unknown_flag"]
        assert finding.severity == "warning"
        assert "--whatever" in finding.detail

    def test_count_mismatch_with_int_source(self, project_root: Path) -> None:
        ctx = VerifyContext(project_root=project_root, count_sources={"templates": 259})
        assert verify("There are 259 templates.\n", ctx).ok is True
        result = verify("There are 300 templates.\n", ctx)
        assert result.ok is False
        (finding,) = _kinds(result)["count_mismatch"]
        assert finding.severity == "error"
        assert "300" in finding.detail and "259" in finding.detail

    def test_count_source_may_be_a_zero_arg_callable(self, project_root: Path) -> None:
        # Two-digit values on purpose: the counts checker ignores single-digit
        # numerals (too many incidental "3"s in prose), so 3-vs-4 is not a probe.
        ctx = VerifyContext(project_root=project_root, count_sources={"skills": lambda: 12})
        assert verify("There are 12 skills.\n", ctx).ok is True
        assert verify("There are 13 skills.\n", ctx).ok is False


class TestHardGate:
    def test_raise_if_failed_raises_on_error_and_names_the_kind(self, project_root: Path) -> None:
        content = "```python\nimport definitely_not_a_real_pkg_xyz\n```\n"
        result = verify(content, VerifyContext(project_root=project_root))
        with pytest.raises(VerificationError) as excinfo:
            raise_if_failed(result)
        assert "unresolved_import" in str(excinfo.value)
        assert excinfo.value.result is result

    def test_raise_if_failed_is_silent_on_warnings_only(self, project_root: Path) -> None:
        result = verify("Run `frobnicate --whatever`.\n", VerifyContext(project_root=project_root))
        assert result.findings, "precondition: the warning path fired"
        raise_if_failed(result)  # must not raise
