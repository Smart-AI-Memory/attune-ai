"""Class-M receipt checks (release-audit-stage R6, Phase X)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from attune.classes.class_m import (
    BOUNDARY_CLASS_IDS,
    RECEIPT_TYPES,
    check_commit,
    check_range,
)


class TestCheckCommit:
    def test_suite_receipt_on_boundary_class_is_class_m(self):
        msg = "fix memory store\n\nClass-Fix: G1\nReceipt-Type: suite\nEvidence: tests/x.py\n"
        problems = check_commit("a" * 40, msg)
        assert len(problems) == 1
        assert "class M by declaration" in problems[0].problem

    @pytest.mark.parametrize("receipt", ["behavioral", "live-fire"])
    def test_admissible_receipt_passes(self, receipt):
        msg = f"fix\n\nClass-Fix: G1\nReceipt-Type: {receipt}\nEvidence: tests/x.py\n"
        assert check_commit("a" * 40, msg) == []

    def test_unknown_receipt_type_fails(self):
        msg = "fix\n\nClass-Fix: G1\nReceipt-Type: vibes\nEvidence: e\n"
        problems = check_commit("a" * 40, msg)
        assert any("not in" in p.problem for p in problems)

    def test_missing_receipt_type_fails(self):
        msg = "fix\n\nClass-Fix: G1\nEvidence: e\n"
        problems = check_commit("a" * 40, msg)
        assert any("without a Receipt-Type" in p.problem for p in problems)

    def test_missing_evidence_fails(self):
        msg = "fix\n\nClass-Fix: G1\nReceipt-Type: live-fire\n"
        problems = check_commit("a" * 40, msg)
        assert any("without an Evidence pointer" in p.problem for p in problems)

    def test_unknown_class_id_fails(self):
        msg = "fix\n\nClass-Fix: Z9\nReceipt-Type: live-fire\nEvidence: e\n"
        problems = check_commit("a" * 40, msg)
        assert any("not a known class id" in p.problem for p in problems)

    def test_subject_naming_class_without_trailer_fails_closed(self):
        problems = check_commit("a" * 40, "fix(G1): stop losing records\n\nbody\n")
        assert len(problems) == 1
        assert "undeclared fix fails closed" in problems[0].problem

    def test_longest_id_wins_c4a_over_prefix(self):
        problems = check_commit("a" * 40, "close C4a null-byte escape\n")
        assert "C4a" in problems[0].problem

    def test_ordinary_commit_passes(self):
        assert check_commit("a" * 40, "docs: fix typo in README\n") == []

    def test_class_id_inside_word_does_not_fire(self):
        assert check_commit("a" * 40, "feat: add G1000 telemetry panel\n") == []

    def test_problem_str_carries_short_sha(self):
        problems = check_commit(
            "abcdef123456" + "0" * 28,
            "fix\n\nClass-Fix: Z9\nReceipt-Type: live-fire\nEvidence: e\n",
        )
        assert str(problems[0]).startswith("abcdef123456:")

    def test_enum_matches_decision_routine_taxonomy(self):
        assert RECEIPT_TYPES == {"suite", "behavioral", "live-fire", "metric", "evidence-chain"}
        assert "G1" in BOUNDARY_CLASS_IDS


class TestCheckRangeRealGit:
    """Non-mocked round trip through the real git boundary (class M

    binds this module's own tests: the boundary here IS git log
    formatting, so a real repository exercises it).
    """

    @pytest.fixture()
    def repo(self, tmp_path: Path) -> Path:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=30)
        for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
            subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True, timeout=30)
        (tmp_path / "f.txt").write_text("base\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, timeout=30)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-q", "-m", "base"], check=True, timeout=30
        )
        return tmp_path

    def _commit(self, repo: Path, message: str) -> None:
        f = repo / "f.txt"
        f.write_text(f.read_text() + "x\n")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True, timeout=30)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-F", "-"],
            input=message,
            text=True,
            check=True,
            timeout=30,
        )

    def test_squashed_style_commit_with_suite_receipt_is_caught(self, repo):
        self._commit(
            repo,
            "fix G1 store race (#999)\n\nClass-Fix: G1\nReceipt-Type: suite\nEvidence: tests/x.py\n",
        )
        problems = check_range("HEAD~1", "HEAD", cwd=str(repo))
        assert len(problems) == 1
        assert "class M by declaration" in problems[0].problem

    def test_clean_range_passes(self, repo):
        self._commit(
            repo,
            "fix\n\nClass-Fix: H1\nReceipt-Type: live-fire\nEvidence: tests/t.py::test_real_port\n",
        )
        self._commit(repo, "docs: unrelated\n")
        assert check_range("HEAD~2", "HEAD", cwd=str(repo)) == []

    def test_problems_reported_oldest_first(self, repo):
        self._commit(repo, "close I-4 escape\n")
        self._commit(repo, "fix\n\nClass-Fix: H2\nEvidence: e\n")
        problems = check_range("HEAD~2", "HEAD", cwd=str(repo))
        assert len(problems) == 2
        assert "undeclared" in problems[0].problem
        assert "Receipt-Type" in problems[1].problem

    def test_bad_ref_raises(self, repo):
        with pytest.raises(subprocess.CalledProcessError):
            check_range("no-such-ref", "HEAD", cwd=str(repo))
